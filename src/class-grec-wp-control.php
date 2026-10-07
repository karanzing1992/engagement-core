<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Generic WordPress control abilities intended for MCP/AI clients.
 *
 * The public ability namespace is deliberately wp-control/* so these abilities
 * can later move into a standalone commercial plugin without changing clients.
 */
final class GREC_WordPress_Control {
	private const CATEGORY = 'wp-control';
	private const AUDIT_DB_VERSION = '1';
	private static $audit_starts = array();

	private const MCP_ABILITY_ALLOWLIST = array(
		'core/get-site-info',
		'core/get-user-info',
		'core/get-environment-info',
		'aioseo-posts/seo-data-get',
		'aioseo-posts/seo-data-update',
		'aioseo-posts/list-missing-seo',
		'aioseo-posts/list-truseo-score',
		'aioseo-audit/homepage-get',
		'aioseo-audit/site-get',
		'woocommerce/orders-query',
		'woocommerce/order-add-note',
		'woocommerce/order-update-status',
		'woocommerce/products-query',
		'woocommerce/product-create',
		'woocommerce/product-delete',
		'woocommerce/product-update',
	);

	private const SAFE_OPTIONS = array(
		'blogname',
		'blogdescription',
		'blog_public',
		'timezone_string',
		'date_format',
		'time_format',
		'start_of_week',
		'show_on_front',
		'page_on_front',
		'page_for_posts',
		'posts_per_page',
		'permalink_structure',
		'default_role',
		'woocommerce_currency',
		'woocommerce_default_country',
		'woocommerce_store_address',
		'woocommerce_store_city',
		'woocommerce_store_postcode',
		'woocommerce_calc_taxes',
	);

	public static function init(): void {
		if ( ! function_exists( 'wp_register_ability' ) ) {
			return;
		}

		add_filter( 'wp_register_ability_args', array( __CLASS__, 'expose_existing_abilities_to_mcp' ), 20, 2 );
		add_action( 'wp_abilities_api_categories_init', array( __CLASS__, 'register_category' ) );
		add_action( 'wp_abilities_api_init', array( __CLASS__, 'register_abilities' ), 20 );
		add_action( 'init', array( __CLASS__, 'ensure_audit_table' ), 5 );
		add_action( 'wp_before_execute_ability', array( __CLASS__, 'audit_before' ), 10, 3 );
		add_action( 'wp_after_execute_ability', array( __CLASS__, 'audit_after' ), 10, 4 );
		add_action( 'rest_api_init', array( __CLASS__, 'register_gateway_routes' ) );
	}

	public static function expose_existing_abilities_to_mcp( array $args, string $ability_name ): array {
		if ( in_array( $ability_name, self::MCP_ABILITY_ALLOWLIST, true ) ) {
			if ( ! isset( $args['meta'] ) || ! is_array( $args['meta'] ) ) {
				$args['meta'] = array();
			}
			if ( ! isset( $args['meta']['mcp'] ) || ! is_array( $args['meta']['mcp'] ) ) {
				$args['meta']['mcp'] = array();
			}
			$args['meta']['mcp']['public'] = true;
		}
		return $args;
	}

	public static function register_category(): void {
		wp_register_ability_category(
			self::CATEGORY,
			array(
				'label'       => __( 'WordPress Control', 'engagement-core' ),
				'description' => __( 'Secure, typed WordPress administration abilities for AI and automation clients.', 'engagement-core' ),
			)
		);
	}

	public static function register_abilities(): void {
		self::register_ability(
			'wp-control/pairing-code',
			'Create ChatGPT pairing code',
			'Create a short-lived one-time code that pairs this WordPress site to the authenticated WP Control account. The code expires after 15 minutes.',
			array(),
			array( __CLASS__, 'create_pairing_code' ),
			array( __CLASS__, 'can_manage_options' ),
			false,
			false,
			false
		);

		self::register_ability(
			'wp-control/site-snapshot',
			'Site snapshot',
			'Return a concise operational snapshot of WordPress, theme, plugins, content counts and scheduled jobs without exposing secrets.',
			array(),
			array( __CLASS__, 'site_snapshot' ),
			array( __CLASS__, 'can_manage_options' ),
			true,
			false,
			true
		);

		self::register_ability(
			'wp-control/content-query',
			'Query content',
			'Find posts, pages or custom post types using status, search text and pagination. Returns summaries rather than full content.',
			array(
				'type'       => 'object',
				'properties' => array(
					'post_type' => array( 'type' => 'string', 'default' => 'any' ),
					'status'    => array( 'type' => 'string', 'default' => 'any' ),
					'search'    => array( 'type' => 'string', 'default' => '' ),
					'page'      => array( 'type' => 'integer', 'minimum' => 1, 'default' => 1 ),
					'limit'     => array( 'type' => 'integer', 'minimum' => 1, 'maximum' => 100, 'default' => 20 ),
				),
			),
			array( __CLASS__, 'content_query' ),
			array( __CLASS__, 'can_edit_posts' ),
			true,
			false,
			true
		);

		self::register_ability(
			'wp-control/content-get',
			'Get content',
			'Return editable fields for one WordPress post, page or custom post type by ID.',
			array(
				'type'       => 'object',
				'required'   => array( 'id' ),
				'properties' => array(
					'id' => array( 'type' => 'integer', 'minimum' => 1 ),
				),
			),
			array( __CLASS__, 'content_get' ),
			array( __CLASS__, 'can_edit_posts' ),
			true,
			false,
			true
		);

		self::register_ability(
			'wp-control/content-save',
			'Save content',
			'Create or update a post, page or custom post type using WordPress APIs so revisions, hooks and permissions are preserved. New content defaults to draft.',
			array(
				'type'       => 'object',
				'properties' => array(
					'id'         => array( 'type' => 'integer', 'minimum' => 1 ),
					'post_type'  => array( 'type' => 'string', 'default' => 'post' ),
					'title'      => array( 'type' => 'string' ),
					'content'    => array( 'type' => 'string' ),
					'excerpt'    => array( 'type' => 'string' ),
					'status'     => array( 'type' => 'string', 'enum' => array( 'draft', 'pending', 'private', 'publish' ), 'default' => 'draft' ),
					'slug'       => array( 'type' => 'string' ),
					'parent'     => array( 'type' => 'integer', 'minimum' => 0 ),
					'menu_order' => array( 'type' => 'integer' ),
				),
			),
			array( __CLASS__, 'content_save' ),
			array( __CLASS__, 'can_edit_posts' ),
			false,
			false,
			false
		);

		self::register_ability(
			'wp-control/content-trash',
			'Trash content',
			'Move one WordPress post or page to Trash. This is reversible from WordPress admin.',
			array(
				'type'       => 'object',
				'required'   => array( 'id' ),
				'properties' => array(
					'id' => array( 'type' => 'integer', 'minimum' => 1 ),
				),
			),
			array( __CLASS__, 'content_trash' ),
			array( __CLASS__, 'can_edit_posts' ),
			false,
			true,
			true
		);

		self::register_ability(
			'wp-control/plugin-list',
			'List plugins',
			'List installed WordPress plugins with version and active state.',
			array(),
			array( __CLASS__, 'plugin_list' ),
			array( __CLASS__, 'can_activate_plugins' ),
			true,
			false,
			true
		);

		self::register_ability(
			'wp-control/plugin-toggle',
			'Activate or deactivate plugin',
			'Activate or deactivate an already-installed WordPress plugin. The MCP/control plugins are protected from self-deactivation.',
			array(
				'type'       => 'object',
				'required'   => array( 'plugin', 'action' ),
				'properties' => array(
					'plugin' => array( 'type' => 'string' ),
					'action' => array( 'type' => 'string', 'enum' => array( 'activate', 'deactivate' ) ),
				),
			),
			array( __CLASS__, 'plugin_toggle' ),
			array( __CLASS__, 'can_activate_plugins' ),
			false,
			true,
			true
		);

		self::register_ability(
			'wp-control/theme-list',
			'List themes',
			'List installed themes and identify the active stylesheet.',
			array(),
			array( __CLASS__, 'theme_list' ),
			array( __CLASS__, 'can_edit_theme_options' ),
			true,
			false,
			true
		);

		self::register_ability(
			'wp-control/options-get',
			'Read safe site settings',
			'Read an allowlisted set of common WordPress and WooCommerce settings. Secrets and arbitrary options are intentionally excluded.',
			array(
				'type'       => 'object',
				'properties' => array(
					'names' => array( 'type' => 'array', 'items' => array( 'type' => 'string' ) ),
				),
			),
			array( __CLASS__, 'options_get' ),
			array( __CLASS__, 'can_manage_options' ),
			true,
			false,
			true
		);

		self::register_ability(
			'wp-control/options-update',
			'Update safe site settings',
			'Update allowlisted common WordPress and WooCommerce scalar settings. Arbitrary options and secrets cannot be changed through this ability.',
			array(
				'type'       => 'object',
				'required'   => array( 'values' ),
				'properties' => array(
					'values' => array( 'type' => 'object', 'additionalProperties' => true ),
				),
			),
			array( __CLASS__, 'options_update' ),
			array( __CLASS__, 'can_manage_options' ),
			false,
			false,
			true
		);

		self::register_ability(
			'wp-control/cache-purge',
			'Purge caches',
			'Flush WordPress object cache and trigger supported full-page cache purges, including LiteSpeed when available.',
			array(),
			array( __CLASS__, 'cache_purge' ),
			array( __CLASS__, 'can_manage_options' ),
			false,
			false,
			true
		);

		self::register_ability(
			'wp-control/cron-list',
			'List scheduled jobs',
			'List scheduled WordPress cron hooks and schedules without returning cron arguments that might contain sensitive data.',
			array(
				'type'       => 'object',
				'properties' => array(
					'limit' => array( 'type' => 'integer', 'minimum' => 1, 'maximum' => 200, 'default' => 100 ),
				),
			),
			array( __CLASS__, 'cron_list' ),
			array( __CLASS__, 'can_manage_options' ),
			true,
			false,
			true
		);

		self::register_ability(
			'wp-control/audit-query',
			'Query GPT control audit log',
			'Return recent privacy-safe execution records for wp-control abilities. Inputs and content bodies are never stored; only an input hash is retained.',
			array(
				'type'       => 'object',
				'properties' => array(
					'limit'   => array( 'type' => 'integer', 'minimum' => 1, 'maximum' => 100, 'default' => 50 ),
					'ability' => array( 'type' => 'string', 'default' => '' ),
					'outcome' => array( 'type' => 'string', 'enum' => array( '', 'success', 'error' ), 'default' => '' ),
				),
			),
			array( __CLASS__, 'audit_query' ),
			array( __CLASS__, 'can_manage_options' ),
			true,
			false,
			true
		);

		wp_register_ability(
			'wp-control/gateway-credential-list',
			array(
				'label'               => __( 'List gateway credentials', 'engagement-core' ),
				'description'         => __( 'List Cowboy MCP gateway credentials without exposing their secret values.', 'engagement-core' ),
				'category'            => self::CATEGORY,
				'execute_callback'    => array( __CLASS__, 'gateway_credential_list' ),
				'permission_callback' => array( __CLASS__, 'can_manage_options' ),
				'meta'                => array(
					'public'       => true,
					'show_in_rest' => true,
					'annotations'  => array( 'readonly' => true, 'destructive' => false, 'idempotent' => true ),
					'mcp'          => array( 'public' => false ),
				),
			)
		);

		wp_register_ability(
			'wp-control/gateway-credential-create',
			array(
				'label'               => __( 'Create gateway credential', 'engagement-core' ),
				'description'         => __( 'Create a dedicated Cowboy MCP API key for an external gateway. The secret is returned once and is never stored in plaintext by WordPress.', 'engagement-core' ),
				'category'            => self::CATEGORY,
				'execute_callback'    => array( __CLASS__, 'gateway_credential_create' ),
				'permission_callback' => array( __CLASS__, 'can_manage_options' ),
				'input_schema'        => array(
					'type'       => 'object',
					'properties' => array(
						'label' => array( 'type' => 'string', 'default' => 'WP Control Gateway' ),
					),
				),
				'meta'                => array(
					'public'       => true,
					'show_in_rest' => true,
					'annotations'  => array( 'readonly' => false, 'destructive' => false, 'idempotent' => false ),
					'mcp'          => array( 'public' => false ),
				),
			)
		);

		wp_register_ability(
			'wp-control/gateway-credential-revoke',
			array(
				'label'               => __( 'Revoke gateway credential', 'engagement-core' ),
				'description'         => __( 'Revoke a dedicated Cowboy MCP gateway credential by key ID.', 'engagement-core' ),
				'category'            => self::CATEGORY,
				'execute_callback'    => array( __CLASS__, 'gateway_credential_revoke' ),
				'permission_callback' => array( __CLASS__, 'can_manage_options' ),
				'input_schema'        => array(
					'type'       => 'object',
					'required'   => array( 'id' ),
					'properties' => array(
						'id' => array( 'type' => 'string' ),
					),
				),
				'meta'                => array(
					'public'       => true,
					'show_in_rest' => true,
					'annotations'  => array( 'readonly' => false, 'destructive' => true, 'idempotent' => true ),
					'mcp'          => array( 'public' => false ),
				),
			)
		);

		self::register_ability(
			'wp-control/package-list',
			'List Git-managed packages',
			'List Deployer for Git packages that WordPress is already configured to pull. Repository credentials and secrets are never returned.',
			array(),
			array( __CLASS__, 'package_list' ),
			array( __CLASS__, 'can_manage_options' ),
			true,
			false,
			true
		);

		self::register_ability(
			'wp-control/oauth-registration-status',
			'GPT OAuth registration status',
			'Return the direct MCP endpoint and whether Cowboy MCP OAuth and its temporary new-connections window are available.',
			array(),
			array( __CLASS__, 'oauth_registration_status' ),
			array( __CLASS__, 'can_manage_options' ),
			true,
			false,
			true
		);

		self::register_ability(
			'wp-control/oauth-registration-open',
			'Open GPT OAuth registration window',
			'Open Cowboy MCP dynamic client registration for 30 minutes so a new ChatGPT MCP app can register. Existing OAuth safety rules and redirect allowlists remain enforced.',
			array(),
			array( __CLASS__, 'oauth_registration_open' ),
			array( __CLASS__, 'can_manage_options' ),
			false,
			false,
			false
		);

		self::register_ability(
			'wp-control/package-sync',
			'Sync Git-managed package',
			'Ask WordPress itself to pull and install a configured plugin or theme from its Deployer for Git source. This removes GitHub Actions from the deployment path.',
			array(
				'type'       => 'object',
				'required'   => array( 'type', 'package' ),
				'properties' => array(
					'type'    => array( 'type' => 'string', 'enum' => array( 'plugin', 'theme' ) ),
					'package' => array( 'type' => 'string' ),
				),
			),
			array( __CLASS__, 'package_sync' ),
			array( __CLASS__, 'can_manage_options' ),
			false,
			true,
			true
		);
	}

	private static function register_ability( $name, $label, $description, array $input_schema, $execute_callback, $permission_callback, $readonly, $destructive, $idempotent ): void {
		$args = array(
			'label'               => __( $label, 'engagement-core' ),
			'description'         => __( $description, 'engagement-core' ),
			'category'            => self::CATEGORY,
			'execute_callback'    => $execute_callback,
			'permission_callback' => $permission_callback,
			'meta'                => array(
				'public'       => true,
				'show_in_rest' => true,
				'annotations'  => array(
					'readonly'    => (bool) $readonly,
					'destructive' => (bool) $destructive,
					'idempotent'  => (bool) $idempotent,
				),
				'mcp' => array(
					'public' => true,
				),
			),
		);

		if ( ! empty( $input_schema ) ) {
			$args['input_schema'] = $input_schema;
		}

		wp_register_ability( $name, $args );
	}

	public static function can_manage_options(): bool {
		return current_user_can( 'manage_options' );
	}

	public static function can_edit_posts(): bool {
		return current_user_can( 'edit_posts' );
	}

	public static function can_activate_plugins(): bool {
		return current_user_can( 'activate_plugins' );
	}

	public static function can_edit_theme_options(): bool {
		return current_user_can( 'edit_theme_options' );
	}


	private static function gateway_supabase_url(): string {
		return rtrim(
			(string) get_option( 'wp_control_supabase_url', 'https://saczglesalubroyaucqe.supabase.co' ),
			'/'
		);
	}

	private static function gateway_publishable_key(): string {
		return (string) get_option(
			'wp_control_supabase_publishable_key',
			'sb_publishable_QWn0aEO4-fHulmZaUacbIQ_1ejYsDXY'
		);
	}

	private static function ensure_site_id(): string {
		$id = (string) get_option( 'wp_control_site_id', '' );
		if ( ! preg_match( '/^[0-9a-f-]{36}$/i', $id ) ) {
			$id = wp_generate_uuid4();
			update_option( 'wp_control_site_id', $id, false );
		}
		return $id;
	}

	public static function create_pairing_code(): array {
		$code = strtoupper( wp_generate_password( 10, false, false ) );
		$hash = hash_hmac( 'sha256', $code, wp_salt( 'auth' ) );
		$user = get_current_user_id();

		set_transient(
			'wp_control_pairing',
			array(
				'hash'          => $hash,
				'local_user_id' => $user,
				'created_at'    => time(),
			),
			15 * MINUTE_IN_SECONDS
		);

		return array(
			'site_id'    => self::ensure_site_id(),
			'site_url'   => home_url( '/' ),
			'site_name'  => get_bloginfo( 'name' ),
			'code'       => $code,
			'expires_in' => 15 * MINUTE_IN_SECONDS,
		);
	}

	public static function register_gateway_routes(): void {
		register_rest_route(
			'wp-control/v1',
			'/pair',
			array(
				'methods'             => WP_REST_Server::CREATABLE,
				'callback'            => array( __CLASS__, 'gateway_pair' ),
				'permission_callback' => '__return_true',
			)
		);

		register_rest_route(
			'wp-control/v1',
			'/bridge',
			array(
				'methods'             => WP_REST_Server::CREATABLE,
				'callback'            => array( __CLASS__, 'gateway_bridge' ),
				'permission_callback' => '__return_true',
			)
		);

		register_rest_route(
			'wp-control/v1',
			'/status',
			array(
				'methods'             => WP_REST_Server::READABLE,
				'callback'            => static function () {
					return rest_ensure_response(
						array(
							'ok'      => true,
							'site_id' => self::ensure_site_id(),
							'paired'  => (bool) get_option( 'wp_control_owner_id', '' ),
							'version' => defined( 'GREC_VERSION' ) ? GREC_VERSION : 'standalone',
						)
					);
				},
				'permission_callback' => '__return_true',
			)
		);
	}

	private static function rate_limit_pairing( WP_REST_Request $request ) {
		$ip  = sanitize_text_field( (string) $request->get_header( 'x-forwarded-for' ) );
		$ip  = $ip ? trim( explode( ',', $ip )[0] ) : sanitize_text_field( (string) ( $_SERVER['REMOTE_ADDR'] ?? '' ) );
		$key = 'wp_control_pair_rl_' . md5( $ip ?: 'unknown' );
		$n   = (int) get_transient( $key );

		if ( $n >= 10 ) {
			return new WP_Error( 'wp_control_rate_limited', 'Too many pairing attempts. Try again shortly.', array( 'status' => 429 ) );
		}

		set_transient( $key, $n + 1, MINUTE_IN_SECONDS );
		return true;
	}

	public static function gateway_pair( WP_REST_Request $request ) {
		$limited = self::rate_limit_pairing( $request );
		if ( is_wp_error( $limited ) ) {
			return $limited;
		}

		$body     = $request->get_json_params();
		$code     = isset( $body['code'] ) ? strtoupper( sanitize_text_field( $body['code'] ) ) : '';
		$owner_id = isset( $body['owner_id'] ) ? sanitize_text_field( $body['owner_id'] ) : '';
		$pairing  = get_transient( 'wp_control_pairing' );

		if ( ! is_array( $pairing ) || empty( $pairing['hash'] ) ) {
			return new WP_Error( 'wp_control_pairing_expired', 'Pairing code is missing or expired.', array( 'status' => 410 ) );
		}

		$expected = hash_hmac( 'sha256', $code, wp_salt( 'auth' ) );
		if ( '' === $code || ! hash_equals( (string) $pairing['hash'], $expected ) ) {
			return new WP_Error( 'wp_control_pairing_invalid', 'Pairing code is invalid.', array( 'status' => 403 ) );
		}

		if ( ! preg_match( '/^[0-9a-f-]{36}$/i', $owner_id ) ) {
			return new WP_Error( 'wp_control_owner_invalid', 'Owner id is invalid.', array( 'status' => 400 ) );
		}

		$local_user_id = isset( $pairing['local_user_id'] ) ? absint( $pairing['local_user_id'] ) : 0;
		$local_user    = $local_user_id ? get_user_by( 'id', $local_user_id ) : false;
		if ( ! $local_user || ! user_can( $local_user, 'manage_options' ) ) {
			return new WP_Error( 'wp_control_local_admin_missing', 'The pairing administrator is no longer authorized.', array( 'status' => 403 ) );
		}

		update_option( 'wp_control_owner_id', $owner_id, false );
		update_option( 'wp_control_local_user_id', $local_user_id, false );
		delete_transient( 'wp_control_pairing' );

		return rest_ensure_response(
			array(
				'ok'           => true,
				'site_id'      => self::ensure_site_id(),
				'name'         => get_bloginfo( 'name' ),
				'base_url'     => home_url( '/' ),
				'capabilities' => array(
					'wordpress'   => true,
					'woocommerce' => class_exists( 'WooCommerce' ),
					'seo'         => defined( 'AIOSEO_VERSION' ) || class_exists( 'AIOSEO\\Plugin\\AIOSEO' ),
					'cowboy_mcp'  => class_exists( 'Cowboy_MCP_Tools' ),
					'undo'        => class_exists( 'Cowboy_MCP_Undo' ),
				),
			)
		);
	}

	private static function bearer_token( WP_REST_Request $request ): string {
		$header = trim( (string) $request->get_header( 'authorization' ) );
		return preg_match( '/^Bearer\\s+(.+)$/i', $header, $m ) ? trim( $m[1] ) : '';
	}

	private static function validate_gateway_user_token( string $token ) {
		if ( '' === $token ) {
			return new WP_Error( 'wp_control_unauthorized', 'Missing bearer token.', array( 'status' => 401 ) );
		}

		$response = wp_remote_get(
			self::gateway_supabase_url() . '/auth/v1/user',
			array(
				'timeout' => 12,
				'headers' => array(
					'Authorization' => 'Bearer ' . $token,
					'apikey'        => self::gateway_publishable_key(),
				),
			)
		);

		if ( is_wp_error( $response ) ) {
			return new WP_Error( 'wp_control_auth_unreachable', 'Could not validate the gateway identity.', array( 'status' => 503 ) );
		}

		if ( 200 !== (int) wp_remote_retrieve_response_code( $response ) ) {
			return new WP_Error( 'wp_control_unauthorized', 'Gateway identity is invalid or expired.', array( 'status' => 401 ) );
		}

		$user = json_decode( wp_remote_retrieve_body( $response ), true );
		if ( ! is_array( $user ) || empty( $user['id'] ) ) {
			return new WP_Error( 'wp_control_unauthorized', 'Gateway identity could not be resolved.', array( 'status' => 401 ) );
		}

		$owner_id = (string) get_option( 'wp_control_owner_id', '' );
		if ( '' === $owner_id || ! hash_equals( $owner_id, (string) $user['id'] ) ) {
			return new WP_Error( 'wp_control_forbidden', 'This account does not own the paired site.', array( 'status' => 403 ) );
		}

		return $user;
	}

	private static function gateway_action_map(): array {
		return array(
			'site_overview'   => 'cowboy-mcp/wp-site-info',
			'list_content'    => 'cowboy-mcp/wp-list-posts',
			'get_content'     => 'cowboy-mcp/wp-get-post',
			'create_content'  => 'cowboy-mcp/wp-create-post',
			'update_content'  => 'cowboy-mcp/wp-update-post',
			'list_products'   => 'cowboy-mcp/wp-woo-list-products',
			'get_product'     => 'cowboy-mcp/wp-woo-get-product',
			'update_product'  => 'cowboy-mcp/wp-woo-update-product',
			'list_orders'     => 'cowboy-mcp/wp-woo-list-orders',
			'get_order'       => 'cowboy-mcp/wp-woo-get-order',
			'add_order_note'  => 'cowboy-mcp/wp-woo-add-order-note',
			'seo_audit'       => 'cowboy-mcp/wp-seo-audit',
			'update_seo'      => 'cowboy-mcp/wp-seo-update-meta',
			'flush_cache'     => 'cowboy-mcp/wp-cache-flush',
			'list_changes'    => 'cowboy-mcp/wp-list-changes',
			'undo_change'     => 'cowboy-mcp/wp-undo-change',
		);
	}

	public static function gateway_bridge( WP_REST_Request $request ) {
		$user = self::validate_gateway_user_token( self::bearer_token( $request ) );
		if ( is_wp_error( $user ) ) {
			return $user;
		}

		$body    = $request->get_json_params();
		$site_id = isset( $body['site_id'] ) ? sanitize_text_field( $body['site_id'] ) : '';
		$action  = isset( $body['action'] ) ? sanitize_key( $body['action'] ) : '';
		$input   = isset( $body['input'] ) && is_array( $body['input'] ) ? $body['input'] : array();

		if ( ! hash_equals( self::ensure_site_id(), $site_id ) ) {
			return new WP_Error( 'wp_control_site_mismatch', 'Site id does not match this WordPress installation.', array( 'status' => 409 ) );
		}

		$map = self::gateway_action_map();
		if ( ! isset( $map[ $action ] ) ) {
			return new WP_Error( 'wp_control_action_not_allowed', 'Gateway action is not allowed.', array( 'status' => 400 ) );
		}

		$ability = function_exists( 'wp_get_ability' ) ? wp_get_ability( $map[ $action ] ) : null;
		if ( ! $ability ) {
			return new WP_Error( 'wp_control_capability_unavailable', 'This WordPress site does not provide the requested capability.', array( 'status' => 501 ) );
		}

		$local_user_id = absint( get_option( 'wp_control_local_user_id', 0 ) );
		$local_user    = $local_user_id ? get_user_by( 'id', $local_user_id ) : false;
		if ( ! $local_user || ! user_can( $local_user, 'manage_options' ) ) {
			return new WP_Error( 'wp_control_local_admin_missing', 'The paired local administrator is unavailable.', array( 'status' => 403 ) );
		}

		$previous_user_id = get_current_user_id();
		wp_set_current_user( $local_user_id );
		$result = $ability->execute( $input );
		wp_set_current_user( $previous_user_id );

		if ( is_wp_error( $result ) ) {
			return $result;
		}

		return rest_ensure_response(
			array(
				'ok'     => true,
				'action' => $action,
				'result' => $result,
			)
		);
	}


	public static function site_snapshot(): array {
		require_once ABSPATH . 'wp-admin/includes/plugin.php';

		$plugin_rows = array();
		foreach ( get_plugins() as $file => $data ) {
			$plugin_rows[] = array(
				'file'    => $file,
				'name'    => isset( $data['Name'] ) ? $data['Name'] : $file,
				'version' => isset( $data['Version'] ) ? $data['Version'] : '',
				'active'  => is_plugin_active( $file ),
			);
		}

		$counts = array();
		foreach ( get_post_types( array( 'show_ui' => true ), 'names' ) as $post_type ) {
			$obj = wp_count_posts( $post_type );
			if ( $obj ) {
				$counts[ $post_type ] = array_filter(
					get_object_vars( $obj ),
					static function ( $value ) {
						return (int) $value > 0;
					}
				);
			}
		}

		$cron  = _get_cron_array();
		$theme = wp_get_theme();

		return array(
			'site' => array(
				'name'        => get_bloginfo( 'name' ),
				'url'         => home_url( '/' ),
				'admin_url'   => admin_url(),
				'environment' => wp_get_environment_type(),
				'wp_version'  => get_bloginfo( 'version' ),
				'php_version' => PHP_VERSION,
				'timezone'    => wp_timezone_string(),
			),
			'theme' => array(
				'name'       => $theme->get( 'Name' ),
				'stylesheet' => get_stylesheet(),
				'version'    => $theme->get( 'Version' ),
			),
			'plugins'            => $plugin_rows,
			'content_counts'     => $counts,
			'cron_timestamps'    => is_array( $cron ) ? count( $cron ) : 0,
			'woocommerce_active' => class_exists( 'WooCommerce' ),
			'mcp_adapter_active' => is_plugin_active( 'mcp-adapter/mcp-adapter.php' ),
		);
	}

	private static function normalize_post_type( $value ) {
		$value = sanitize_key( (string) $value );
		if ( '' === $value || 'any' === $value ) {
			return 'any';
		}

		$obj = get_post_type_object( $value );
		if ( ! $obj || ! $obj->show_ui ) {
			return new WP_Error( 'wp_control_invalid_post_type', 'Unknown or non-editable post type.' );
		}
		return $value;
	}

	public static function content_query( $input ) {
		$input     = is_array( $input ) ? $input : array();
		$post_type = self::normalize_post_type( isset( $input['post_type'] ) ? $input['post_type'] : 'any' );
		if ( is_wp_error( $post_type ) ) {
			return $post_type;
		}

		$status           = isset( $input['status'] ) ? sanitize_key( $input['status'] ) : 'any';
		$allowed_statuses = array_merge( array( 'any' ), array_keys( get_post_stati() ) );
		if ( ! in_array( $status, $allowed_statuses, true ) ) {
			$status = 'any';
		}

		$limit = max( 1, min( 100, isset( $input['limit'] ) ? absint( $input['limit'] ) : 20 ) );
		$page  = max( 1, isset( $input['page'] ) ? absint( $input['page'] ) : 1 );

		$query = new WP_Query(
			array(
				'post_type'      => $post_type,
				'post_status'    => $status,
				's'              => isset( $input['search'] ) ? sanitize_text_field( $input['search'] ) : '',
				'posts_per_page' => $limit,
				'paged'          => $page,
				'orderby'        => 'modified',
				'order'          => 'DESC',
			)
		);

		$items = array();
		foreach ( $query->posts as $post ) {
			if ( ! current_user_can( 'edit_post', $post->ID ) ) {
				continue;
			}

			$items[] = array(
				'id'       => (int) $post->ID,
				'type'     => $post->post_type,
				'status'   => $post->post_status,
				'title'    => get_the_title( $post ),
				'slug'     => $post->post_name,
				'modified' => get_post_modified_time( DATE_ATOM, true, $post ),
				'link'     => get_permalink( $post ),
			);
		}

		return array(
			'items' => $items,
			'page'  => $page,
			'total' => (int) $query->found_posts,
			'pages' => (int) $query->max_num_pages,
		);
	}

	public static function content_get( $input ) {
		$id   = is_array( $input ) && isset( $input['id'] ) ? absint( $input['id'] ) : 0;
		$post = $id ? get_post( $id ) : null;

		if ( ! $post || ! current_user_can( 'edit_post', $id ) ) {
			return new WP_Error( 'wp_control_content_not_found', 'Content was not found or is not editable.', array( 'status' => 404 ) );
		}

		return array(
			'id'         => (int) $post->ID,
			'post_type'  => $post->post_type,
			'status'     => $post->post_status,
			'title'      => $post->post_title,
			'content'    => $post->post_content,
			'excerpt'    => $post->post_excerpt,
			'slug'       => $post->post_name,
			'parent'     => (int) $post->post_parent,
			'menu_order' => (int) $post->menu_order,
			'modified'   => get_post_modified_time( DATE_ATOM, true, $post ),
			'link'       => get_permalink( $post ),
		);
	}

	public static function content_save( $input ) {
		$input    = is_array( $input ) ? $input : array();
		$id       = isset( $input['id'] ) ? absint( $input['id'] ) : 0;
		$existing = $id ? get_post( $id ) : null;

		if ( $id && ( ! $existing || ! current_user_can( 'edit_post', $id ) ) ) {
			return new WP_Error( 'wp_control_content_not_editable', 'Content does not exist or cannot be edited.' );
		}

		$post_type = $existing
			? $existing->post_type
			: ( isset( $input['post_type'] ) ? self::normalize_post_type( $input['post_type'] ) : 'post' );

		if ( is_wp_error( $post_type ) ) {
			return $post_type;
		}
		if ( 'any' === $post_type ) {
			$post_type = 'post';
		}

		$type_obj = get_post_type_object( $post_type );
		if ( ! $type_obj || ! current_user_can( $type_obj->cap->edit_posts ) ) {
			return new WP_Error( 'wp_control_post_type_forbidden', 'You cannot edit this post type.' );
		}

		$status = isset( $input['status'] )
			? sanitize_key( $input['status'] )
			: ( $existing ? $existing->post_status : 'draft' );

		if ( ! in_array( $status, array( 'draft', 'pending', 'private', 'publish' ), true ) ) {
			$status = 'draft';
		}
		if ( 'publish' === $status && ! current_user_can( $type_obj->cap->publish_posts ) ) {
			return new WP_Error( 'wp_control_publish_forbidden', 'You cannot publish this post type.' );
		}

		$data = array(
			'ID'          => $id,
			'post_type'   => $post_type,
			'post_status' => $status,
		);

		$map = array(
			'title'   => 'post_title',
			'content' => 'post_content',
			'excerpt' => 'post_excerpt',
		);

		foreach ( $map as $key => $field ) {
			if ( array_key_exists( $key, $input ) ) {
				$data[ $field ] = wp_unslash( (string) $input[ $key ] );
			}
		}

		if ( array_key_exists( 'slug', $input ) ) {
			$data['post_name'] = sanitize_title( $input['slug'] );
		}
		if ( array_key_exists( 'parent', $input ) ) {
			$data['post_parent'] = absint( $input['parent'] );
		}
		if ( array_key_exists( 'menu_order', $input ) ) {
			$data['menu_order'] = intval( $input['menu_order'] );
		}

		$result = $id
			? wp_update_post( wp_slash( $data ), true )
			: wp_insert_post( wp_slash( $data ), true );

		if ( is_wp_error( $result ) ) {
			return $result;
		}

		$post = get_post( $result );
		return array(
			'id'       => (int) $result,
			'status'   => $post ? $post->post_status : $status,
			'link'     => get_permalink( $result ),
			'modified' => get_post_modified_time( DATE_ATOM, true, $result ),
		);
	}

	public static function content_trash( $input ) {
		$id = is_array( $input ) && isset( $input['id'] ) ? absint( $input['id'] ) : 0;

		if ( ! $id || ! get_post( $id ) || ! current_user_can( 'delete_post', $id ) ) {
			return new WP_Error( 'wp_control_delete_forbidden', 'Content does not exist or cannot be trashed.' );
		}

		$post = wp_trash_post( $id );
		return $post
			? array( 'id' => $id, 'status' => 'trash' )
			: new WP_Error( 'wp_control_trash_failed', 'WordPress could not move the content to Trash.' );
	}

	public static function plugin_list(): array {
		require_once ABSPATH . 'wp-admin/includes/plugin.php';

		$rows = array();
		foreach ( get_plugins() as $file => $data ) {
			$rows[] = array(
				'plugin'  => $file,
				'name'    => isset( $data['Name'] ) ? $data['Name'] : $file,
				'version' => isset( $data['Version'] ) ? $data['Version'] : '',
				'active'  => is_plugin_active( $file ),
			);
		}

		return array( 'plugins' => $rows );
	}

	public static function plugin_toggle( $input ) {
		require_once ABSPATH . 'wp-admin/includes/plugin.php';

		$plugin = is_array( $input ) && isset( $input['plugin'] )
			? plugin_basename( sanitize_text_field( $input['plugin'] ) )
			: '';
		$action = is_array( $input ) && isset( $input['action'] )
			? sanitize_key( $input['action'] )
			: '';

		$protected = array(
			'engagement-core/engagement-core.php',
			'mcp-adapter/mcp-adapter.php',
		);

		if ( in_array( $plugin, $protected, true ) && 'deactivate' === $action ) {
			return new WP_Error( 'wp_control_protected_plugin', 'This control-path plugin cannot deactivate itself or the MCP Adapter.' );
		}

		$plugins = get_plugins();
		if ( ! isset( $plugins[ $plugin ] ) ) {
			return new WP_Error( 'wp_control_plugin_not_found', 'Plugin is not installed.' );
		}

		if ( 'activate' === $action ) {
			$error = activate_plugin( $plugin, '', false, false );
			if ( is_wp_error( $error ) ) {
				return $error;
			}
		} elseif ( 'deactivate' === $action ) {
			deactivate_plugins( $plugin, false, false );
		} else {
			return new WP_Error( 'wp_control_invalid_plugin_action', 'Action must be activate or deactivate.' );
		}

		return array(
			'plugin' => $plugin,
			'active' => is_plugin_active( $plugin ),
		);
	}

	public static function theme_list(): array {
		$rows   = array();
		$active = get_stylesheet();

		foreach ( wp_get_themes() as $stylesheet => $theme ) {
			$rows[] = array(
				'stylesheet' => $stylesheet,
				'name'       => $theme->get( 'Name' ),
				'version'    => $theme->get( 'Version' ),
				'active'     => $stylesheet === $active,
			);
		}

		return array( 'themes' => $rows );
	}

	private static function requested_safe_options( $input ): array {
		$requested = is_array( $input ) && isset( $input['names'] ) && is_array( $input['names'] )
			? array_map( 'sanitize_key', $input['names'] )
			: self::SAFE_OPTIONS;

		return array_values( array_intersect( array_unique( $requested ), self::SAFE_OPTIONS ) );
	}

	public static function options_get( $input ): array {
		$values = array();

		foreach ( self::requested_safe_options( $input ) as $name ) {
			$values[ $name ] = get_option( $name, null );
		}

		return array(
			'values'  => $values,
			'allowed' => self::SAFE_OPTIONS,
		);
	}

	public static function options_update( $input ) {
		$values   = is_array( $input ) && isset( $input['values'] ) && is_array( $input['values'] ) ? $input['values'] : array();
		$updated  = array();
		$rejected = array();

		foreach ( $values as $name => $value ) {
			$name = sanitize_key( $name );

			if ( ! in_array( $name, self::SAFE_OPTIONS, true ) || ( ! is_scalar( $value ) && null !== $value ) ) {
				$rejected[] = $name;
				continue;
			}

			$clean = is_string( $value ) ? sanitize_text_field( $value ) : $value;
			update_option( $name, $clean );
			$updated[ $name ] = get_option( $name, null );
		}

		return array(
			'updated'  => $updated,
			'rejected' => array_values( array_unique( $rejected ) ),
		);
	}

	public static function cache_purge(): array {
		$actions = array();

		if ( function_exists( 'wp_cache_flush' ) ) {
			wp_cache_flush();
			$actions[] = 'wp_cache_flush';
		}

		if ( defined( 'LSCWP_V' ) || has_action( 'litespeed_purge_all' ) ) {
			do_action( 'litespeed_purge_all' );
			$actions[] = 'litespeed_purge_all';
		}

		if ( function_exists( 'rocket_clean_domain' ) ) {
			rocket_clean_domain();
			$actions[] = 'rocket_clean_domain';
		}

		return array(
			'ok'      => true,
			'actions' => array_values( array_unique( $actions ) ),
		);
	}

	private static function audit_table(): string {
		global $wpdb;
		return $wpdb->prefix . 'grec_wp_control_audit';
	}

	public static function ensure_audit_table(): void {
		if ( get_option( 'grec_wp_control_audit_db_version' ) === self::AUDIT_DB_VERSION ) {
			return;
		}

		global $wpdb;
		require_once ABSPATH . 'wp-admin/includes/upgrade.php';

		$table   = self::audit_table();
		$charset = $wpdb->get_charset_collate();
		$sql     = "CREATE TABLE {$table} (
			id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
			created_at datetime NOT NULL,
			ability_name varchar(191) NOT NULL,
			user_id bigint(20) unsigned NOT NULL DEFAULT 0,
			context varchar(32) NOT NULL DEFAULT 'php',
			outcome varchar(16) NOT NULL DEFAULT 'success',
			error_code varchar(191) NOT NULL DEFAULT '',
			duration_ms int(10) unsigned NOT NULL DEFAULT 0,
			input_hash char(64) NOT NULL DEFAULT '',
			PRIMARY KEY  (id),
			KEY ability_name (ability_name),
			KEY created_at (created_at),
			KEY user_id (user_id)
		) {$charset};";

		dbDelta( $sql );
		update_option( 'grec_wp_control_audit_db_version', self::AUDIT_DB_VERSION, false );
	}

	private static function audit_context(): string {
		if ( defined( 'WP_CLI' ) && WP_CLI ) {
			return 'cli';
		}

		if ( defined( 'REST_REQUEST' ) && REST_REQUEST ) {
			$uri = isset( $_SERVER['REQUEST_URI'] ) ? (string) $_SERVER['REQUEST_URI'] : '';
			return false !== strpos( $uri, '/mcp/' ) ? 'mcp' : 'rest';
		}

		return 'php';
	}

	public static function audit_before( $ability_name, $input, $ability ): void {
		if ( 0 !== strpos( (string) $ability_name, 'wp-control/' ) ) {
			return;
		}

		if ( ! isset( self::$audit_starts[ $ability_name ] ) ) {
			self::$audit_starts[ $ability_name ] = array();
		}
		self::$audit_starts[ $ability_name ][] = microtime( true );
	}

	public static function audit_after( $ability_name, $input, $result, $ability ): void {
		if ( 0 !== strpos( (string) $ability_name, 'wp-control/' ) || 'wp-control/audit-query' === $ability_name ) {
			return;
		}

		self::ensure_audit_table();

		$started = microtime( true );
		if ( ! empty( self::$audit_starts[ $ability_name ] ) ) {
			$started = array_pop( self::$audit_starts[ $ability_name ] );
		}

		$encoded = wp_json_encode( $input, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
		$hash    = is_string( $encoded ) ? hash( 'sha256', $encoded ) : '';

		global $wpdb;
		$wpdb->insert(
			self::audit_table(),
			array(
				'created_at'  => current_time( 'mysql', true ),
				'ability_name'=> (string) $ability_name,
				'user_id'     => get_current_user_id(),
				'context'     => self::audit_context(),
				'outcome'     => is_wp_error( $result ) ? 'error' : 'success',
				'error_code'  => is_wp_error( $result ) ? (string) $result->get_error_code() : '',
				'duration_ms' => max( 0, (int) round( ( microtime( true ) - $started ) * 1000 ) ),
				'input_hash'  => $hash,
			),
			array( '%s', '%s', '%d', '%s', '%s', '%s', '%d', '%s' )
		);

		if ( false === get_transient( 'grec_wp_control_audit_pruned' ) ) {
			$table = self::audit_table();
			$wpdb->query( "DELETE FROM {$table} WHERE created_at < (UTC_TIMESTAMP() - INTERVAL 90 DAY)" );
			set_transient( 'grec_wp_control_audit_pruned', '1', 12 * HOUR_IN_SECONDS );
		}
	}

	public static function audit_query( $input ): array {
		self::ensure_audit_table();
		$input = is_array( $input ) ? $input : array();
		$limit = max( 1, min( 100, isset( $input['limit'] ) ? absint( $input['limit'] ) : 50 ) );

		$where  = array( '1=1' );
		$params = array();

		if ( ! empty( $input['ability'] ) ) {
			$where[]  = 'ability_name = %s';
			$params[] = sanitize_text_field( $input['ability'] );
		}
		if ( ! empty( $input['outcome'] ) && in_array( $input['outcome'], array( 'success', 'error' ), true ) ) {
			$where[]  = 'outcome = %s';
			$params[] = $input['outcome'];
		}

		global $wpdb;
		$table = self::audit_table();
		$sql   = "SELECT id, created_at, ability_name, user_id, context, outcome, error_code, duration_ms, input_hash
			FROM {$table}
			WHERE " . implode( ' AND ', $where ) . "
			ORDER BY id DESC
			LIMIT " . (int) $limit;

		if ( $params ) {
			$sql = $wpdb->prepare( $sql, $params );
		}

		return array( 'items' => $wpdb->get_results( $sql, ARRAY_A ) );
	}

	public static function oauth_registration_status(): array {
		$available = class_exists( 'Cowboy_MCP_OAuth' );
		$settings  = get_option( 'cowboy_mcp_settings', array() );
		$seconds   = $available ? Cowboy_MCP_OAuth::registration_seconds_left() : 0;

		return array(
			'available'            => $available,
			'oauth_enabled'        => is_array( $settings ) && ! empty( $settings['oauth_enabled'] ),
			'registration_open'    => $seconds > 0,
			'seconds_left'         => $seconds,
			'mcp_endpoint'         => rest_url( 'cowboy-mcp/v1/endpoint' ),
			'protected_resource'   => home_url( '/.well-known/oauth-protected-resource' ),
			'authorization_server'=> home_url( '/.well-known/oauth-authorization-server' ),
			'power_mode_exposed'   => false,
		);
	}

	public static function oauth_registration_open() {
		if ( ! class_exists( 'Cowboy_MCP_OAuth' ) ) {
			return new WP_Error( 'wp_control_cowboy_missing', 'Cowboy MCP is not active.' );
		}

		$settings = get_option( 'cowboy_mcp_settings', array() );
		if ( ! is_array( $settings ) || empty( $settings['oauth_enabled'] ) ) {
			return new WP_Error( 'wp_control_cowboy_oauth_disabled', 'Cowboy MCP OAuth is disabled.' );
		}

		$until = Cowboy_MCP_OAuth::open_registration_window();
		return array(
			'ok'                => true,
			'registration_open' => true,
			'closes_at_utc'     => gmdate( DATE_ATOM, $until ),
			'seconds_left'      => Cowboy_MCP_OAuth::registration_seconds_left(),
			'mcp_endpoint'      => rest_url( 'cowboy-mcp/v1/endpoint' ),
		);
	}


	private static function dfg_packages( string $type ): array {
		$option = 'theme' === $type ? 'dfg_themes_list' : 'dfg_plugins_list';
		$rows   = get_option( $option, array() );
		return is_array( $rows ) ? $rows : array();
	}

	public static function gateway_credential_list(): array {
		if ( ! class_exists( 'Cowboy_MCP_Auth' ) ) {
			return array( 'credentials' => array() );
		}
		$rows = array();
		foreach ( Cowboy_MCP_Auth::list_keys() as $row ) {
			if ( ! is_array( $row ) ) {
				continue;
			}
			$rows[] = array(
				'id'        => isset( $row['id'] ) ? (string) $row['id'] : '',
				'label'     => isset( $row['label'] ) ? (string) $row['label'] : '',
				'prefix'    => isset( $row['prefix'] ) ? (string) $row['prefix'] : '',
				'created'   => isset( $row['created'] ) ? (int) $row['created'] : 0,
				'last_used' => isset( $row['last_used'] ) && null !== $row['last_used'] ? (int) $row['last_used'] : null,
				'scope'     => isset( $row['scope'] ) ? $row['scope'] : null,
			);
		}
		return array( 'credentials' => $rows );
	}

	public static function gateway_credential_create( $input ) {
		if ( ! class_exists( 'Cowboy_MCP_Auth' ) ) {
			return new WP_Error( 'wp_control_cowboy_missing', 'Cowboy MCP is not active.' );
		}

		$input = is_array( $input ) ? $input : array();
		$label = ! empty( $input['label'] ) ? sanitize_text_field( $input['label'] ) : 'WP Control Gateway';

		foreach ( Cowboy_MCP_Auth::list_keys() as $row ) {
			if ( is_array( $row ) && isset( $row['label'], $row['id'] ) && $label === (string) $row['label'] ) {
				Cowboy_MCP_Auth::revoke_key( (string) $row['id'] );
			}
		}

		$key = Cowboy_MCP_Auth::generate_key( $label, null );
		update_option( 'grec_gateway_key_id', (string) $key['id'], false );

		return array(
			'id'      => (string) $key['id'],
			'key'     => (string) $key['key'],
			'label'   => (string) $key['label'],
			'created' => (int) $key['created'],
			'scope'   => 'full_non_power',
		);
	}

	public static function gateway_credential_revoke( $input ) {
		if ( ! class_exists( 'Cowboy_MCP_Auth' ) ) {
			return new WP_Error( 'wp_control_cowboy_missing', 'Cowboy MCP is not active.' );
		}

		$id = is_array( $input ) && isset( $input['id'] ) ? sanitize_text_field( $input['id'] ) : '';
		if ( '' === $id ) {
			return new WP_Error( 'wp_control_missing_key_id', 'Credential id is required.' );
		}

		$ok = Cowboy_MCP_Auth::revoke_key( $id );
		if ( $ok && get_option( 'grec_gateway_key_id' ) === $id ) {
			delete_option( 'grec_gateway_key_id' );
		}
		return array( 'id' => $id, 'revoked' => (bool) $ok );
	}


	public static function package_list(): array {
		$out = array( 'plugins' => array(), 'themes' => array() );

		foreach ( array( 'plugin' => 'plugins', 'theme' => 'themes' ) as $type => $bucket ) {
			foreach ( self::dfg_packages( $type ) as $row ) {
				if ( ! is_array( $row ) || empty( $row['slug'] ) ) {
					continue;
				}
				$out[ $bucket ][] = array(
					'slug'                  => sanitize_key( $row['slug'] ),
					'repo_url'              => isset( $row['repo_url'] ) ? esc_url_raw( $row['repo_url'] ) : '',
					'branch'                => isset( $row['branch'] ) ? sanitize_text_field( $row['branch'] ) : '',
					'provider'              => isset( $row['provider'] ) ? sanitize_key( $row['provider'] ) : '',
					'is_private_repository' => ! empty( $row['is_private_repository'] ),
				);
			}
		}

		return $out;
	}

	public static function package_sync( $input ) {
		$input   = is_array( $input ) ? $input : array();
		$type    = isset( $input['type'] ) ? sanitize_key( $input['type'] ) : '';
		$package = isset( $input['package'] ) ? sanitize_key( $input['package'] ) : '';

		if ( ! in_array( $type, array( 'plugin', 'theme' ), true ) || ! $package ) {
			return new WP_Error( 'wp_control_invalid_package', 'A configured plugin/theme package is required.' );
		}

		$allowed = array();
		foreach ( self::dfg_packages( $type ) as $row ) {
			if ( is_array( $row ) && ! empty( $row['slug'] ) ) {
				$allowed[] = sanitize_key( $row['slug'] );
			}
		}
		if ( ! in_array( $package, $allowed, true ) ) {
			return new WP_Error( 'wp_control_package_not_configured', 'Package is not configured in Deployer for Git.' );
		}

		$secret = (string) get_option( 'deployer_for_git_api_secret', '' );
		if ( '' === $secret ) {
			return new WP_Error( 'wp_control_deployer_unavailable', 'Deployer for Git is not configured.' );
		}

		$request = new WP_REST_Request( 'POST', '/dfg/v1/package_update' );
		$request->set_query_params(
			array(
				'secret'  => $secret,
				'type'    => $type,
				'package' => $package,
			)
		);
		$response = rest_do_request( $request );

		if ( is_wp_error( $response ) ) {
			return $response;
		}

		$status = $response->get_status();
		$data   = $response->get_data();
		if ( $status >= 400 || ! is_array( $data ) || empty( $data['success'] ) ) {
			return new WP_Error(
				'wp_control_package_sync_failed',
				is_array( $data ) && ! empty( $data['message'] ) ? sanitize_text_field( $data['message'] ) : 'Package sync failed.',
				array( 'status' => $status )
			);
		}

		return array(
			'ok'      => true,
			'type'    => $type,
			'package' => $package,
			'message' => isset( $data['message'] ) ? sanitize_text_field( $data['message'] ) : 'Package updated successfully.',
		);
	}


	public static function cron_list( $input ): array {
		$limit = is_array( $input ) && isset( $input['limit'] )
			? max( 1, min( 200, absint( $input['limit'] ) ) )
			: 100;

		$cron  = _get_cron_array();
		$items = array();

		if ( is_array( $cron ) ) {
			foreach ( $cron as $timestamp => $hooks ) {
				foreach ( $hooks as $hook => $instances ) {
					foreach ( $instances as $instance ) {
						$items[] = array(
							'hook'      => $hook,
							'timestamp' => (int) $timestamp,
							'iso'       => gmdate( DATE_ATOM, (int) $timestamp ),
							'schedule'  => isset( $instance['schedule'] ) ? $instance['schedule'] : false,
							'interval'  => isset( $instance['interval'] ) ? (int) $instance['interval'] : null,
						);

						if ( count( $items ) >= $limit ) {
							break 3;
						}
					}
				}
			}
		}

		return array(
			'items' => $items,
			'limit' => $limit,
		);
	}
}
