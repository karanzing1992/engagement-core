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
