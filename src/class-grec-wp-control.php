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
