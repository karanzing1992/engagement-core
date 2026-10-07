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
	private const CHANGE_OPTION = 'grec_wp_control_changes';
	private const CHANGE_SEQ_OPTION = 'grec_wp_control_change_seq';
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
		add_action( 'template_redirect', array( __CLASS__, 'maybe_render_oauth_consent' ), 0 );
		add_action( 'template_redirect', array( __CLASS__, 'maybe_render_pairing_page' ), 1 );
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



	public static function maybe_render_pairing_page(): void {
		if ( is_admin() ) {
			return;
		}
		$request_uri = isset( $_SERVER['REQUEST_URI'] ) ? (string) $_SERVER['REQUEST_URI'] : '';
		$path = (string) wp_parse_url( $request_uri, PHP_URL_PATH );
		if ( '/wp-control/pairing' !== untrailingslashit( $path ) ) {
			return;
		}
		if ( ! is_user_logged_in() || ! current_user_can( 'manage_options' ) ) {
			status_header( 403 );
			wp_die( esc_html__( 'Administrator access is required.', 'engagement-core' ), 'Forbidden', array( 'response' => 403 ) );
		}
		$pairing = self::create_pairing_code();
		status_header( 200 );
		nocache_headers();
		header( 'Content-Type: text/html; charset=' . get_bloginfo( 'charset' ) );
		header( 'Referrer-Policy: no-referrer' );
		header( 'X-Content-Type-Options: nosniff' );
		?>
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WP Control Pairing</title>
<style>body{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f5f1;color:#191919;margin:0;padding:32px}.card{max-width:560px;margin:auto;background:#fff;border:1px solid #ddd9cf;border-radius:18px;padding:28px}.code{font:700 28px ui-monospace,monospace;letter-spacing:.08em;padding:16px;background:#f5f2ea;border-radius:12px;text-align:center}.muted{color:#666}</style>
</head><body><main class="card"><p class="muted">WP CONTROL</p><h1>Pair ChatGPT</h1>
<p>Use this one-time code to pair this WordPress site. It expires in 15 minutes.</p>
<div class="code"><?php echo esc_html( (string) $pairing['code'] ); ?></div>
<p class="muted">Site: <?php echo esc_html( (string) $pairing['site_name'] ); ?><br>Site ID: <?php echo esc_html( (string) $pairing['site_id'] ); ?></p>
</main></body></html>
		<?php
		exit;
	}

	public static function maybe_render_oauth_consent(): void {
		if ( is_admin() ) {
			return;
		}

		$request_uri = isset( $_SERVER['REQUEST_URI'] ) ? (string) $_SERVER['REQUEST_URI'] : '';
		$path        = (string) wp_parse_url( $request_uri, PHP_URL_PATH );
		if ( '/wp-control/connect' !== untrailingslashit( $path ) ) {
			return;
		}

		$nonce        = wp_generate_password( 24, false, false );
		$supabase_url = self::gateway_supabase_url();
		$public_key   = self::gateway_publishable_key();
		$relay_url    = $supabase_url . '/functions/v1/wpcontrol-auth';

		status_header( 200 );
		nocache_headers();
		header( 'Content-Type: text/html; charset=' . get_bloginfo( 'charset' ) );
		header( "Content-Security-Policy: default-src 'self'; script-src 'nonce-" . $nonce . "' https://cdn.jsdelivr.net; connect-src 'self' https://*.supabase.co; style-src 'nonce-" . $nonce . "'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'" );
		header( 'Referrer-Policy: no-referrer' );
		header( 'X-Content-Type-Options: nosniff' );

		$project_json = wp_json_encode( $supabase_url, JSON_UNESCAPED_SLASHES );
		$key_json     = wp_json_encode( $public_key, JSON_UNESCAPED_SLASHES );
		$relay_json   = wp_json_encode( $relay_url, JSON_UNESCAPED_SLASHES );
		?>
<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width,initial-scale=1">
	<title>WP Control — Connect ChatGPT</title>
	<style nonce="<?php echo esc_attr( $nonce ); ?>">
		:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#191919;background:#f6f5f1}
		*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px}.card{width:min(520px,100%);background:#fff;border:1px solid #ddd9cf;border-radius:20px;padding:28px;box-shadow:0 16px 45px rgba(0,0,0,.08)}h1{font-size:28px;margin:0 0 8px}.muted{color:#666;line-height:1.5}.row{display:flex;gap:10px;flex-wrap:wrap}label{display:block;margin:14px 0 6px;font-weight:600}input{width:100%;padding:13px 14px;border:1px solid #cfcac0;border-radius:12px;font:inherit}button{border:0;border-radius:12px;padding:12px 16px;font:600 15px inherit;cursor:pointer;background:#191919;color:#fff}button.secondary{background:#eeeae1;color:#191919}button:disabled{opacity:.55;cursor:wait}#status{min-height:24px;margin:12px 0;color:#555}.scope{background:#f5f2ea;padding:12px;border-radius:12px;margin:14px 0}.hidden{display:none}.brand{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#7a746b;margin-bottom:14px}
	</style>
</head>
<body>
	<main class="card">
		<div class="brand">WP Control</div>
		<h1>Connect ChatGPT</h1>
		<p class="muted">Authorize ChatGPT to use only WordPress sites you explicitly pair. WP Control never asks for or stores your WordPress administrator password.</p>
		<section id="login" class="hidden">
			<label for="email">Email</label>
			<input id="email" type="email" autocomplete="email" placeholder="you@example.com">
			<div class="row" style="margin-top:12px"><button id="send">Email me a sign-in link</button></div>
		</section>
		<section id="consent" class="hidden">
			<p><strong id="clientName">ChatGPT</strong> wants to connect to your WP Control account.</p>
			<div class="scope">Requested access: <span id="scopeText">email</span></div>
			<div class="row"><button id="approve">Approve</button><button id="deny" class="secondary">Deny</button></div>
		</section>
		<p id="status" aria-live="polite"></p>
	</main>
	<script type="module" nonce="<?php echo esc_attr( $nonce ); ?>">
		import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.117.2/+esm";
		const PROJECT_URL=<?php echo $project_json; ?>;
		const PUBLIC_KEY=<?php echo $key_json; ?>;
		const AUTH_RELAY=<?php echo $relay_json; ?>;
		const initialParams=new URLSearchParams(location.search);
		const authorizationId=initialParams.get("authorization_id")||sessionStorage.getItem("wpcontrol_authorization_id");
		if(authorizationId) sessionStorage.setItem("wpcontrol_authorization_id",authorizationId);
		const supabase=createClient(PROJECT_URL,PUBLIC_KEY,{auth:{detectSessionInUrl:true,persistSession:true,flowType:"pkce"}});
		const login=document.querySelector("#login"),consent=document.querySelector("#consent"),status=document.querySelector("#status"),email=document.querySelector("#email"),send=document.querySelector("#send"),approve=document.querySelector("#approve"),deny=document.querySelector("#deny");
		const say=(t)=>status.textContent=t||"";
		async function boot(){
			if(!authorizationId){say("Missing authorization request. Start the connection from ChatGPT.");return}
			const s=await supabase.auth.getSession();
			if(s.error){say(s.error.message);return}
			if(!s.data.session){login.classList.remove("hidden");consent.classList.add("hidden");say("Sign in to continue.");return}
			const r=await supabase.auth.oauth.getAuthorizationDetails(authorizationId);
			if(r.error){say(r.error.message||"Could not load the authorization request.");return}
			if(r.data?.redirect_url&&!r.data?.authorization_id){location.href=r.data.redirect_url;return}
			document.querySelector("#clientName").textContent=r.data?.client?.name||r.data?.client_name||"ChatGPT";
			document.querySelector("#scopeText").textContent=r.data?.scope||"email";
			consent.classList.remove("hidden");login.classList.add("hidden");say("Review the request, then approve or deny.");
		}
		send.addEventListener("click",async()=>{
			const v=email.value.trim();if(!v){say("Enter your email address.");return}
			send.disabled=true;
			const redirect=new URL(AUTH_RELAY);redirect.searchParams.set("authorization_id",authorizationId);
			const r=await supabase.auth.signInWithOtp({email:v,options:{emailRedirectTo:redirect.toString()}});
			send.disabled=false;say(r.error?r.error.message:"Check your email for the sign-in link.");
		});
		approve.addEventListener("click",async()=>{
			approve.disabled=true;const r=await supabase.auth.oauth.approveAuthorization(authorizationId);
			if(r.error){approve.disabled=false;say(r.error.message);return}
			sessionStorage.removeItem("wpcontrol_authorization_id");location.href=r.data.redirect_url;
		});
		deny.addEventListener("click",async()=>{
			deny.disabled=true;const r=await supabase.auth.oauth.denyAuthorization(authorizationId);
			if(r.error){deny.disabled=false;say(r.error.message);return}
			sessionStorage.removeItem("wpcontrol_authorization_id");location.href=r.data.redirect_url;
		});
		supabase.auth.onAuthStateChange((_event,session)=>{if(session) boot()});
		boot();
	</script>
</body>
</html>
		<?php
		exit;
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

	private static function change_rows(): array {
		$rows = get_option( self::CHANGE_OPTION, array() );
		return is_array( $rows ) ? array_values( $rows ) : array();
	}

	private static function save_change_rows( array $rows ): void {
		$rows = array_slice( array_values( $rows ), -250 );
		if ( false === get_option( self::CHANGE_OPTION, false ) ) {
			add_option( self::CHANGE_OPTION, $rows, '', false );
			return;
		}
		update_option( self::CHANGE_OPTION, $rows, false );
	}

	private static function state_hash( $state ): string {
		return hash( 'sha256', wp_json_encode( $state ) );
	}

	private static function next_change_id(): int {
		$id = max( 0, (int) get_option( self::CHANGE_SEQ_OPTION, 0 ) ) + 1;
		update_option( self::CHANGE_SEQ_OPTION, $id, false );
		return $id;
	}

	private static function record_native_change( string $action, string $object_type, int $object_id, string $label, $before, $after, bool $undoable = true ): int {
		$rows   = self::change_rows();
		$id     = self::next_change_id();
		$rows[] = array(
			'id'          => $id,
			'created_at'  => gmdate( DATE_ATOM ),
			'action'      => $action,
			'object_type' => $object_type,
			'object_id'   => $object_id,
			'label'       => sanitize_text_field( $label ),
			'status'      => $undoable ? 'active' : 'not_undoable',
			'undoable'    => $undoable,
			'before'      => $before,
			'after_hash'  => self::state_hash( $after ),
			'undone_at'   => '',
		);
		self::save_change_rows( $rows );
		return $id;
	}

	private static function content_state( int $id ): ?array {
		$post = get_post( $id );
		if ( ! $post ) {
			return null;
		}
		return array(
			'id'         => (int) $post->ID,
			'post_type'  => (string) $post->post_type,
			'status'     => (string) $post->post_status,
			'title'      => (string) $post->post_title,
			'content'    => (string) $post->post_content,
			'excerpt'    => (string) $post->post_excerpt,
			'slug'       => (string) $post->post_name,
			'parent'     => (int) $post->post_parent,
			'menu_order' => (int) $post->menu_order,
		);
	}

	private static function product_state( int $id ): ?array {
		if ( ! function_exists( 'wc_get_product' ) ) {
			return null;
		}
		$product = wc_get_product( $id );
		if ( ! $product ) {
			return null;
		}
		return array(
			'id'                => (int) $product->get_id(),
			'name'              => (string) $product->get_name(),
			'status'            => (string) $product->get_status(),
			'regular_price'     => (string) $product->get_regular_price(),
			'sale_price'        => (string) $product->get_sale_price(),
			'sku'               => (string) $product->get_sku(),
			'description'       => (string) $product->get_description(),
			'short_description' => (string) $product->get_short_description(),
			'manage_stock'      => (bool) $product->get_manage_stock(),
			'stock_quantity'    => null === $product->get_stock_quantity() ? null : (int) $product->get_stock_quantity(),
			'stock_status'      => (string) $product->get_stock_status(),
		);
	}

	private static function native_list_changes( $input ): array {
		$input    = is_array( $input ) ? $input : array();
		$status   = isset( $input['status'] ) ? sanitize_key( $input['status'] ) : '';
		$page     = max( 1, isset( $input['page'] ) ? absint( $input['page'] ) : 1 );
		$per_page = max( 1, min( 200, isset( $input['per_page'] ) ? absint( $input['per_page'] ) : 50 ) );
		$rows     = array_reverse( self::change_rows() );
		if ( $status ) {
			$rows = array_values( array_filter( $rows, static fn( $row ) => isset( $row['status'] ) && $row['status'] === $status ) );
		}
		$total = count( $rows );
		$rows  = array_slice( $rows, ( $page - 1 ) * $per_page, $per_page );
		$items = array_map(
			static function ( $row ) {
				return array(
					'id'          => (int) ( $row['id'] ?? 0 ),
					'created_at'  => (string) ( $row['created_at'] ?? '' ),
					'action'      => (string) ( $row['action'] ?? '' ),
					'object_type' => (string) ( $row['object_type'] ?? '' ),
					'object_id'   => (int) ( $row['object_id'] ?? 0 ),
					'label'       => (string) ( $row['label'] ?? '' ),
					'status'      => (string) ( $row['status'] ?? '' ),
					'undoable'    => ! empty( $row['undoable'] ),
					'undone_at'   => (string) ( $row['undone_at'] ?? '' ),
				);
			},
			$rows
		);
		return array(
			'items'   => $items,
			'entries' => $items,
			'page'    => $page,
			'total'   => $total,
			'pages'   => (int) ceil( $total / $per_page ),
		);
	}

	private static function native_undo_change( $input ) {
		$input     = is_array( $input ) ? $input : array();
		$change_id = isset( $input['change_id'] ) ? absint( $input['change_id'] ) : 0;
		$force     = ! empty( $input['force'] );
		$dry_run   = ! empty( $input['dry_run'] );
		$rows      = self::change_rows();
		$index     = null;
		$row       = null;
		foreach ( $rows as $i => $candidate ) {
			if ( (int) ( $candidate['id'] ?? 0 ) === $change_id ) {
				$index = $i;
				$row   = $candidate;
				break;
			}
		}
		if ( null === $index || ! is_array( $row ) ) {
			return new WP_Error( 'wp_control_change_not_found', 'Change was not found.', array( 'status' => 404 ) );
		}
		if ( 'active' !== (string) ( $row['status'] ?? '' ) || empty( $row['undoable'] ) ) {
			return new WP_Error( 'wp_control_change_not_active', 'Change is not currently undoable.', array( 'status' => 409 ) );
		}

		$type = (string) ( $row['object_type'] ?? '' );
		$id   = (int) ( $row['object_id'] ?? 0 );
		$current = 'product' === $type ? self::product_state( $id ) : self::content_state( $id );
		if ( ! $force && self::state_hash( $current ) !== (string) ( $row['after_hash'] ?? '' ) ) {
			return new WP_Error( 'wp_control_change_conflict', 'The object changed after this action. Re-read it before using force.', array( 'status' => 409 ) );
		}
		if ( $dry_run ) {
			return array( 'ok' => true, 'dry_run' => true, 'change_id' => $change_id, 'object_type' => $type, 'object_id' => $id );
		}

		if ( 'content_create' === (string) $row['action'] ) {
			if ( get_post( $id ) ) {
				wp_delete_post( $id, true );
			}
		} elseif ( 'content_update' === (string) $row['action'] ) {
			$before = is_array( $row['before'] ?? null ) ? $row['before'] : array();
			$result = wp_update_post(
				wp_slash(
					array(
						'ID'           => $id,
						'post_type'    => $before['post_type'] ?? 'post',
						'post_status'  => $before['status'] ?? 'draft',
						'post_title'   => $before['title'] ?? '',
						'post_content' => $before['content'] ?? '',
						'post_excerpt' => $before['excerpt'] ?? '',
						'post_name'    => $before['slug'] ?? '',
						'post_parent'  => (int) ( $before['parent'] ?? 0 ),
						'menu_order'   => (int) ( $before['menu_order'] ?? 0 ),
					)
				),
				true
			);
			if ( is_wp_error( $result ) ) {
				return $result;
			}
		} elseif ( 'product_update' === (string) $row['action'] ) {
			if ( ! function_exists( 'wc_get_product' ) ) {
				return new WP_Error( 'wp_control_woocommerce_missing', 'WooCommerce is unavailable.' );
			}
			$product = wc_get_product( $id );
			$before  = is_array( $row['before'] ?? null ) ? $row['before'] : array();
			if ( ! $product ) {
				return new WP_Error( 'wp_control_product_not_found', 'Product was not found.' );
			}
			$product->set_name( (string) ( $before['name'] ?? '' ) );
			$product->set_status( (string) ( $before['status'] ?? 'draft' ) );
			$product->set_regular_price( (string) ( $before['regular_price'] ?? '' ) );
			$product->set_sale_price( (string) ( $before['sale_price'] ?? '' ) );
			$product->set_sku( (string) ( $before['sku'] ?? '' ) );
			$product->set_description( (string) ( $before['description'] ?? '' ) );
			$product->set_short_description( (string) ( $before['short_description'] ?? '' ) );
			$product->set_manage_stock( ! empty( $before['manage_stock'] ) );
			$product->set_stock_quantity( $before['stock_quantity'] ?? null );
			if ( isset( $before['stock_status'] ) ) {
				$product->set_stock_status( (string) $before['stock_status'] );
			}
			$product->save();
		} else {
			return new WP_Error( 'wp_control_change_not_supported', 'This change type cannot be undone by Engagement Core yet.', array( 'status' => 501 ) );
		}

		$rows[ $index ]['status']    = 'undone';
		$rows[ $index ]['undone_at'] = gmdate( DATE_ATOM );
		self::save_change_rows( $rows );
		return array( 'ok' => true, 'change_id' => $change_id, 'status' => 'undone', 'object_type' => $type, 'object_id' => $id );
	}

	private static function native_list_products( $input ) {
		if ( ! function_exists( 'wc_get_products' ) ) {
			return new WP_Error( 'wp_control_woocommerce_missing', 'WooCommerce is unavailable.', array( 'status' => 501 ) );
		}
		$input    = is_array( $input ) ? $input : array();
		$page     = max( 1, isset( $input['page'] ) ? absint( $input['page'] ) : 1 );
		$per_page = max( 1, min( 100, isset( $input['per_page'] ) ? absint( $input['per_page'] ) : 20 ) );
		$args = array( 'limit' => $per_page, 'page' => $page, 'paginate' => true, 'orderby' => 'date', 'order' => 'DESC' );
		if ( ! empty( $input['status'] ) && 'any' !== $input['status'] ) $args['status'] = sanitize_key( $input['status'] );
		if ( ! empty( $input['search'] ) ) $args['search'] = sanitize_text_field( $input['search'] );
		if ( ! empty( $input['sku'] ) ) $args['sku'] = sanitize_text_field( $input['sku'] );
		if ( ! empty( $input['category'] ) ) $args['category'] = array( sanitize_title( $input['category'] ) );
		$result = wc_get_products( $args );
		$products = is_object( $result ) && isset( $result->products ) ? $result->products : (array) $result;
		$items = array();
		foreach ( $products as $product ) {
			$items[] = array(
				'id' => (int) $product->get_id(), 'name' => $product->get_name(), 'status' => $product->get_status(),
				'type' => $product->get_type(), 'sku' => $product->get_sku(), 'price' => $product->get_price(),
				'regular_price' => $product->get_regular_price(), 'sale_price' => $product->get_sale_price(),
				'manage_stock' => (bool) $product->get_manage_stock(), 'stock_quantity' => $product->get_stock_quantity(),
				'stock_status' => $product->get_stock_status(), 'link' => get_permalink( $product->get_id() ),
			);
		}
		$total = is_object( $result ) && isset( $result->total ) ? (int) $result->total : count( $items );
		$pages = is_object( $result ) && isset( $result->max_num_pages ) ? (int) $result->max_num_pages : 1;
		return array( 'items' => $items, 'page' => $page, 'total' => $total, 'pages' => $pages );
	}

	private static function native_get_product( $input ) {
		$id = is_array( $input ) && isset( $input['product_id'] ) ? absint( $input['product_id'] ) : 0;
		$state = $id ? self::product_state( $id ) : null;
		if ( ! $state ) {
			return new WP_Error( 'wp_control_product_not_found', 'Product was not found.', array( 'status' => 404 ) );
		}
		$state['link'] = get_permalink( $id );
		return $state;
	}

	private static function native_update_product( $input ) {
		if ( ! function_exists( 'wc_get_product' ) ) {
			return new WP_Error( 'wp_control_woocommerce_missing', 'WooCommerce is unavailable.', array( 'status' => 501 ) );
		}
		$input = is_array( $input ) ? $input : array();
		$id = isset( $input['product_id'] ) ? absint( $input['product_id'] ) : 0;
		$product = $id ? wc_get_product( $id ) : false;
		if ( ! $product || ! current_user_can( 'edit_post', $id ) ) {
			return new WP_Error( 'wp_control_product_not_found', 'Product was not found or is not editable.', array( 'status' => 404 ) );
		}
		$before = self::product_state( $id );
		if ( ! empty( $input['dry_run'] ) ) {
			return array( 'ok' => true, 'dry_run' => true, 'product_id' => $id, 'changes' => array_diff_key( $input, array( 'product_id' => 1, 'dry_run' => 1 ) ) );
		}
		$setters = array(
			'name' => 'set_name', 'status' => 'set_status', 'regular_price' => 'set_regular_price',
			'sale_price' => 'set_sale_price', 'sku' => 'set_sku', 'description' => 'set_description',
			'short_description' => 'set_short_description', 'manage_stock' => 'set_manage_stock',
			'stock_quantity' => 'set_stock_quantity',
		);
		foreach ( $setters as $key => $method ) {
			if ( array_key_exists( $key, $input ) ) {
				$product->{$method}( $input[ $key ] );
			}
		}
		$product->save();
		$after = self::product_state( $id );
		$change_id = self::record_native_change( 'product_update', 'product', $id, (string) $product->get_name(), $before, $after, true );
		$after['change_id'] = $change_id;
		return $after;
	}

	private static function native_list_orders( $input ) {
		if ( ! function_exists( 'wc_get_orders' ) ) {
			return new WP_Error( 'wp_control_woocommerce_missing', 'WooCommerce is unavailable.', array( 'status' => 501 ) );
		}
		$input = is_array( $input ) ? $input : array();
		$page = max( 1, isset( $input['page'] ) ? absint( $input['page'] ) : 1 );
		$per_page = max( 1, min( 100, isset( $input['per_page'] ) ? absint( $input['per_page'] ) : 20 ) );
		$args = array( 'limit' => $per_page, 'page' => $page, 'paginate' => true, 'orderby' => 'date', 'order' => 'DESC' );
		if ( ! empty( $input['status'] ) && 'any' !== $input['status'] ) $args['status'] = sanitize_key( $input['status'] );
		if ( ! empty( $input['customer'] ) ) $args['customer_id'] = absint( $input['customer'] );
		if ( ! empty( $input['search'] ) ) $args['search'] = sanitize_text_field( $input['search'] );
		if ( ! empty( $input['date_after'] ) || ! empty( $input['date_before'] ) ) {
			$after = ! empty( $input['date_after'] ) ? strtotime( $input['date_after'] ) : 0;
			$before = ! empty( $input['date_before'] ) ? strtotime( $input['date_before'] ) : time();
			if ( $after ) $args['date_created'] = $after . '...' . $before;
		}
		$result = wc_get_orders( $args );
		$orders = is_object( $result ) && isset( $result->orders ) ? $result->orders : (array) $result;
		$items = array();
		foreach ( $orders as $order ) {
			$items[] = array(
				'id' => (int) $order->get_id(), 'status' => $order->get_status(), 'total' => $order->get_total(),
				'currency' => $order->get_currency(), 'customer_id' => (int) $order->get_customer_id(),
				'customer' => trim( $order->get_billing_first_name() . ' ' . $order->get_billing_last_name() ),
				'email' => $order->get_billing_email(), 'phone' => $order->get_billing_phone(),
				'date_created' => $order->get_date_created() ? $order->get_date_created()->date( DATE_ATOM ) : '',
			);
		}
		return array(
			'items' => $items, 'page' => $page,
			'total' => is_object( $result ) && isset( $result->total ) ? (int) $result->total : count( $items ),
			'pages' => is_object( $result ) && isset( $result->max_num_pages ) ? (int) $result->max_num_pages : 1,
		);
	}

	private static function native_get_order( $input ) {
		if ( ! function_exists( 'wc_get_order' ) ) {
			return new WP_Error( 'wp_control_woocommerce_missing', 'WooCommerce is unavailable.', array( 'status' => 501 ) );
		}
		$id = is_array( $input ) && isset( $input['order_id'] ) ? absint( $input['order_id'] ) : 0;
		$order = $id ? wc_get_order( $id ) : false;
		if ( ! $order ) {
			return new WP_Error( 'wp_control_order_not_found', 'Order was not found.', array( 'status' => 404 ) );
		}
		$lines = array();
		foreach ( $order->get_items() as $item ) {
			$lines[] = array(
				'name' => $item->get_name(), 'product_id' => (int) $item->get_product_id(),
				'variation_id' => (int) $item->get_variation_id(), 'quantity' => (int) $item->get_quantity(),
				'subtotal' => $item->get_subtotal(), 'total' => $item->get_total(),
			);
		}
		return array(
			'id' => (int) $order->get_id(), 'status' => $order->get_status(), 'total' => $order->get_total(),
			'currency' => $order->get_currency(), 'customer_id' => (int) $order->get_customer_id(),
			'customer' => trim( $order->get_billing_first_name() . ' ' . $order->get_billing_last_name() ),
			'email' => $order->get_billing_email(), 'phone' => $order->get_billing_phone(),
			'billing_address_1' => $order->get_billing_address_1(), 'billing_city' => $order->get_billing_city(),
			'payment_method' => $order->get_payment_method_title(), 'customer_note' => $order->get_customer_note(),
			'date_created' => $order->get_date_created() ? $order->get_date_created()->date( DATE_ATOM ) : '',
			'line_items' => $lines,
		);
	}

	private static function native_add_order_note( $input ) {
		if ( ! function_exists( 'wc_get_order' ) ) {
			return new WP_Error( 'wp_control_woocommerce_missing', 'WooCommerce is unavailable.', array( 'status' => 501 ) );
		}
		$input = is_array( $input ) ? $input : array();
		$id = isset( $input['order_id'] ) ? absint( $input['order_id'] ) : 0;
		$order = $id ? wc_get_order( $id ) : false;
		$note = isset( $input['note'] ) ? sanitize_textarea_field( $input['note'] ) : '';
		if ( ! $order || '' === $note ) {
			return new WP_Error( 'wp_control_order_note_invalid', 'A valid order and note are required.', array( 'status' => 400 ) );
		}
		if ( ! empty( $input['dry_run'] ) ) {
			return array( 'ok' => true, 'dry_run' => true, 'order_id' => $id, 'is_customer' => ! empty( $input['is_customer'] ) );
		}
		$note_id = $order->add_order_note( $note, ! empty( $input['is_customer'] ), true );
		$change_id = self::record_native_change( 'order_note_add', 'order', $id, 'Order #' . $id . ' note', null, array( 'note_id' => $note_id ), false );
		return array( 'ok' => true, 'order_id' => $id, 'note_id' => (int) $note_id, 'change_id' => $change_id, 'undoable' => false );
	}

	private static function native_seo_audit( $input ) {
		$input = is_array( $input ) ? $input : array();
		$post_types = ! empty( $input['post_type'] ) && is_array( $input['post_type'] ) ? array_map( 'sanitize_key', $input['post_type'] ) : array( 'post', 'page', 'product' );
		$status = ! empty( $input['post_status'] ) ? sanitize_key( $input['post_status'] ) : 'publish';
		$page = max( 1, isset( $input['page'] ) ? absint( $input['page'] ) : 1 );
		$per_page = max( 1, min( 100, isset( $input['per_page'] ) ? absint( $input['per_page'] ) : 50 ) );
		$query = new WP_Query( array(
			'post_type' => $post_types, 'post_status' => $status, 'paged' => $page, 'posts_per_page' => $per_page,
			'orderby' => 'modified', 'order' => 'DESC',
		) );
		$items = array();
		foreach ( $query->posts as $post ) {
			$issues = array();
			if ( '' === trim( wp_strip_all_tags( get_the_title( $post ) ) ) ) $issues[] = 'missing_title';
			$description = trim( (string) get_post_meta( $post->ID, '_yoast_wpseo_metadesc', true ) );
			if ( '' === $description ) $description = trim( (string) get_post_meta( $post->ID, '_aioseo_description', true ) );
			if ( '' === $description && '' === trim( (string) $post->post_excerpt ) ) $issues[] = 'missing_description';
			$row = array( 'post_id' => (int) $post->ID, 'post_type' => $post->post_type, 'title' => get_the_title( $post ), 'status' => $post->post_status, 'issues' => $issues, 'link' => get_permalink( $post ) );
			if ( empty( $input['only_issues'] ) || $issues ) $items[] = $row;
		}
		return array( 'items' => $items, 'page' => $page, 'total' => (int) $query->found_posts, 'pages' => (int) $query->max_num_pages, 'mode' => 'engagement-core-native' );
	}

	private static function native_update_seo( $input ) {
		$input = is_array( $input ) ? $input : array();
		$id = isset( $input['post_id'] ) ? absint( $input['post_id'] ) : 0;
		if ( ! $id || ! get_post( $id ) || ! current_user_can( 'edit_post', $id ) ) {
			return new WP_Error( 'wp_control_seo_post_not_found', 'Post was not found or is not editable.', array( 'status' => 404 ) );
		}
		if ( ! empty( $input['dry_run'] ) ) {
			return array( 'ok' => true, 'dry_run' => true, 'post_id' => $id );
		}
		// Prefer an installed SEO plugin's public WordPress Ability, but the control path remains Engagement Core.
		$ability = function_exists( 'wp_get_ability' ) ? wp_get_ability( 'aioseo-posts/seo-data-update' ) : null;
		if ( $ability ) {
			$result = $ability->execute( $input );
			if ( is_wp_error( $result ) ) return $result;
			self::record_native_change( 'seo_update', 'content', $id, get_the_title( $id ) . ' SEO', null, array( 'provider' => 'aioseo', 'post_id' => $id ), false );
			return $result;
		}
		$map = array(
			'title' => '_yoast_wpseo_title', 'description' => '_yoast_wpseo_metadesc',
			'focus_keyword' => '_yoast_wpseo_focuskw', 'canonical_url' => '_yoast_wpseo_canonical',
		);
		foreach ( $map as $key => $meta_key ) {
			if ( array_key_exists( $key, $input ) ) update_post_meta( $id, $meta_key, sanitize_text_field( (string) $input[ $key ] ) );
		}
		if ( array_key_exists( 'noindex', $input ) || array_key_exists( 'nofollow', $input ) ) {
			$robots = array();
			if ( ! empty( $input['noindex'] ) ) $robots[] = 'noindex';
			if ( ! empty( $input['nofollow'] ) ) $robots[] = 'nofollow';
			update_post_meta( $id, '_grec_robots', implode( ',', $robots ) );
		}
		self::record_native_change( 'seo_update', 'content', $id, get_the_title( $id ) . ' SEO', null, array( 'provider' => 'meta', 'post_id' => $id ), false );
		return array( 'ok' => true, 'post_id' => $id, 'provider' => 'wordpress-meta' );
	}

	private static function native_flush_cache( $input ): array {
		if ( is_array( $input ) && ! empty( $input['dry_run'] ) ) {
			return array( 'ok' => true, 'dry_run' => true, 'scope' => sanitize_key( $input['scope'] ?? 'all' ) );
		}
		return self::cache_purge();
	}

	private static function native_telegram_status(): array {
		return array(
			'connected' => class_exists( 'GREC_Telegram' ) && GREC_Telegram::is_connected(),
			'destinations' => class_exists( 'GREC_Telegram' ) ? GREC_Telegram::destinations() : array(),
			'enabled_count' => class_exists( 'GREC_Telegram' ) ? count( GREC_Telegram::enabled_destinations() ) : 0,
			'last_publish' => get_option( 'grec_telegram_last_publish', array() ),
		);
	}

	private static function native_telegram_publish( $input ) {
		if ( ! class_exists( 'GREC_Telegram' ) ) {
			return new WP_Error( 'wp_control_telegram_missing', 'Engagement Core Telegram publisher is unavailable.', array( 'status' => 501 ) );
		}
		$input = is_array( $input ) ? $input : array();
		if ( ! empty( $input['dry_run'] ) ) {
			return array(
				'ok' => true, 'dry_run' => true, 'enabled_count' => count( GREC_Telegram::enabled_destinations( (array) ( $input['targets'] ?? array() ), (array) ( $input['levels'] ?? array() ) ) ),
			);
		}
		return GREC_Telegram::send_post(
			(string) ( $input['text'] ?? '' ),
			is_array( $input['media'] ?? null ) ? $input['media'] : array(),
			is_array( $input['targets'] ?? null ) ? $input['targets'] : array(),
			is_array( $input['levels'] ?? null ) ? $input['levels'] : array()
		);
	}

	private static function gateway_execute_native( string $action, array $input ) {
		switch ( $action ) {
			case 'site_overview':
				return self::site_snapshot();
			case 'list_content':
				return self::content_query( array(
					'post_type' => $input['post_type'] ?? 'post', 'status' => $input['status'] ?? 'any',
					'search' => $input['search'] ?? '', 'page' => $input['page'] ?? 1, 'limit' => $input['per_page'] ?? 20,
				) );
			case 'get_content':
				return self::content_get( array( 'id' => $input['post_id'] ?? 0 ) );
			case 'create_content':
				if ( ! empty( $input['dry_run'] ) ) return array( 'ok' => true, 'dry_run' => true, 'status' => $input['status'] ?? 'draft' );
				return self::content_save( $input );
			case 'update_content':
				if ( isset( $input['status'] ) && 'trash' === $input['status'] ) return self::content_trash( array( 'id' => $input['post_id'] ?? 0 ) );
				$input['id'] = $input['post_id'] ?? 0;
				unset( $input['post_id'] );
				if ( ! empty( $input['dry_run'] ) ) return array( 'ok' => true, 'dry_run' => true, 'id' => $input['id'] );
				return self::content_save( $input );
			case 'list_products': return self::native_list_products( $input );
			case 'get_product': return self::native_get_product( $input );
			case 'update_product': return self::native_update_product( $input );
			case 'list_orders': return self::native_list_orders( $input );
			case 'get_order': return self::native_get_order( $input );
			case 'add_order_note': return self::native_add_order_note( $input );
			case 'seo_audit': return self::native_seo_audit( $input );
			case 'update_seo': return self::native_update_seo( $input );
			case 'flush_cache': return self::native_flush_cache( $input );
			case 'list_changes': return self::native_list_changes( $input );
			case 'undo_change': return self::native_undo_change( $input );
			case 'plugin_list': return self::plugin_list();
			case 'plugin_toggle': return self::plugin_toggle( $input );
			case 'theme_list': return self::theme_list();
			case 'options_get': return self::options_get( $input );
			case 'options_update': return self::options_update( $input );
			case 'cron_list': return self::cron_list( $input );
			case 'audit_query': return self::audit_query( $input );
			case 'telegram_status': return self::native_telegram_status();
			case 'telegram_publish': return self::native_telegram_publish( $input );
			case 'engine_status': return GREC_Updater::status();
			case 'engine_check': return GREC_Updater::check( true );
			case 'engine_update': return GREC_Updater::apply( $input );
			case 'engine_rollback': return GREC_Updater::rollback( $input );
		}
		return new WP_Error( 'wp_control_action_not_allowed', 'Gateway action is not allowed.', array( 'status' => 400 ) );
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

		$local_user_id = absint( get_option( 'wp_control_local_user_id', 0 ) );
		$local_user    = $local_user_id ? get_user_by( 'id', $local_user_id ) : false;
		if ( ! $local_user || ! user_can( $local_user, 'manage_options' ) ) {
			return new WP_Error( 'wp_control_local_admin_missing', 'The paired local administrator is unavailable.', array( 'status' => 403 ) );
		}

		$previous_user_id = get_current_user_id();
		wp_set_current_user( $local_user_id );
		try {
			$result = self::gateway_execute_native( $action, $input );
		} finally {
			wp_set_current_user( $previous_user_id );
		}

		if ( is_wp_error( $result ) ) {
			return $result;
		}

		return rest_ensure_response(
			array(
				'ok'     => true,
				'action' => $action,
				'result' => $result,
				'engine' => 'engagement-core-native',
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
		$before   = $id ? self::content_state( $id ) : null;

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

		$post       = get_post( $result );
		$after      = self::content_state( (int) $result );
		$change_id  = self::record_native_change(
			$id ? 'content_update' : 'content_create',
			'content',
			(int) $result,
			$post ? (string) $post->post_title : (string) ( $input['title'] ?? '' ),
			$before,
			$after,
			true
		);
		return array(
			'id'        => (int) $result,
			'post_id'   => (int) $result,
			'status'    => $post ? $post->post_status : $status,
			'link'      => get_permalink( $result ),
			'modified'  => get_post_modified_time( DATE_ATOM, true, $result ),
			'change_id' => $change_id,
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
