<?php
defined( 'ABSPATH' ) || exit;

final class WPControl_Bridge {
	private const SUPABASE_URL = 'https://saczglesalubroyaucqe.supabase.co';
	private const SUPABASE_KEY = 'sb_publishable_QWn0aEO4-fHulmZaUacbIQ_1ejYsDXY';

	public static function activate(): void {
		if ( ! get_option( 'wp_control_site_id' ) ) {
			add_option( 'wp_control_site_id', wp_generate_uuid4(), '', false );
		}
	}

	public static function init(): void {
		add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ) );
		add_action( 'admin_menu', array( __CLASS__, 'admin_menu' ) );
	}

	private static function site_id(): string {
		$id = (string) get_option( 'wp_control_site_id', '' );
		if ( ! preg_match( '/^[0-9a-f-]{36}$/i', $id ) ) {
			$id = wp_generate_uuid4();
			update_option( 'wp_control_site_id', $id, false );
		}
		return $id;
	}

	public static function admin_menu(): void {
		add_options_page(
			__( 'WP Control', 'wp-control' ),
			__( 'WP Control', 'wp-control' ),
			'manage_options',
			'wp-control',
			array( __CLASS__, 'render_admin' )
		);
	}

	public static function render_admin(): void {
		if ( ! current_user_can( 'manage_options' ) ) {
			return;
		}

		$code = '';
		if ( isset( $_POST['wp_control_pair'] ) && check_admin_referer( 'wp_control_pairing' ) ) {
			$data = self::create_pairing_code();
			$code = $data['code'];
		}

		echo '<div class="wrap"><h1>WP Control</h1>';
		echo '<p>Connect this WordPress site to the public ChatGPT plugin without sharing your WordPress password.</p>';
		echo '<p><strong>Site ID:</strong> <code>' . esc_html( self::site_id() ) . '</code></p>';
		echo '<p><strong>Status:</strong> ' . ( get_option( 'wp_control_owner_id' ) ? 'Connected' : 'Not connected' ) . '</p>';
		if ( $code ) {
			echo '<div class="notice notice-success"><p>Pairing code: <strong style="font-size:1.4em">' . esc_html( $code ) . '</strong> — expires in 15 minutes.</p></div>';
		}
		echo '<form method="post">';
		wp_nonce_field( 'wp_control_pairing' );
		submit_button( 'Generate pairing code', 'primary', 'wp_control_pair' );
		echo '</form></div>';
	}

	public static function create_pairing_code(): array {
		$code = strtoupper( wp_generate_password( 10, false, false ) );
		set_transient(
			'wp_control_pairing',
			array(
				'hash'          => hash_hmac( 'sha256', $code, wp_salt( 'auth' ) ),
				'local_user_id' => get_current_user_id(),
			),
			15 * MINUTE_IN_SECONDS
		);
		return array( 'code' => $code, 'site_id' => self::site_id(), 'expires_in' => 900 );
	}

	public static function register_routes(): void {
		register_rest_route( 'wp-control/v1', '/status', array(
			'methods' => WP_REST_Server::READABLE,
			'callback' => static function () {
				return rest_ensure_response( array(
					'ok' => true,
					'site_id' => self::site_id(),
					'paired' => (bool) get_option( 'wp_control_owner_id', '' ),
					'version' => WPCONTROL_VERSION,
				) );
			},
			'permission_callback' => '__return_true',
		) );
		register_rest_route( 'wp-control/v1', '/pair', array(
			'methods' => WP_REST_Server::CREATABLE,
			'callback' => array( __CLASS__, 'pair' ),
			'permission_callback' => '__return_true',
		) );
		register_rest_route( 'wp-control/v1', '/bridge', array(
			'methods' => WP_REST_Server::CREATABLE,
			'callback' => array( __CLASS__, 'bridge' ),
			'permission_callback' => '__return_true',
		) );
	}

	public static function pair( WP_REST_Request $request ) {
		$body = $request->get_json_params();
		$code = isset( $body['code'] ) ? strtoupper( sanitize_text_field( $body['code'] ) ) : '';
		$owner_id = isset( $body['owner_id'] ) ? sanitize_text_field( $body['owner_id'] ) : '';
		$pairing = get_transient( 'wp_control_pairing' );
		if ( ! is_array( $pairing ) ) {
			return new WP_Error( 'wp_control_pairing_expired', 'Pairing code is missing or expired.', array( 'status' => 410 ) );
		}
		$expected = hash_hmac( 'sha256', $code, wp_salt( 'auth' ) );
		if ( ! hash_equals( (string) $pairing['hash'], $expected ) ) {
			return new WP_Error( 'wp_control_pairing_invalid', 'Pairing code is invalid.', array( 'status' => 403 ) );
		}
		if ( ! preg_match( '/^[0-9a-f-]{36}$/i', $owner_id ) ) {
			return new WP_Error( 'wp_control_owner_invalid', 'Owner id is invalid.', array( 'status' => 400 ) );
		}
		$local_user_id = absint( $pairing['local_user_id'] ?? 0 );
		$local_user = $local_user_id ? get_user_by( 'id', $local_user_id ) : false;
		if ( ! $local_user || ! user_can( $local_user, 'manage_options' ) ) {
			return new WP_Error( 'wp_control_admin_invalid', 'Pairing administrator is unavailable.', array( 'status' => 403 ) );
		}
		update_option( 'wp_control_owner_id', $owner_id, false );
		update_option( 'wp_control_local_user_id', $local_user_id, false );
		delete_transient( 'wp_control_pairing' );
		return rest_ensure_response( array(
			'ok' => true,
			'site_id' => self::site_id(),
			'name' => get_bloginfo( 'name' ),
			'base_url' => home_url( '/' ),
			'capabilities' => array(
				'wordpress' => true,
				'woocommerce' => class_exists( 'WooCommerce' ),
				'cowboy_mcp' => class_exists( 'Cowboy_MCP_Tools' ),
				'undo' => class_exists( 'Cowboy_MCP_Undo' ),
			),
		) );
	}

	private static function token( WP_REST_Request $request ): string {
		$h = trim( (string) $request->get_header( 'authorization' ) );
		return preg_match( '/^Bearer\s+(.+)$/i', $h, $m ) ? trim( $m[1] ) : '';
	}

	private static function validate_token( string $token ) {
		if ( ! $token ) {
			return new WP_Error( 'wp_control_unauthorized', 'Missing bearer token.', array( 'status' => 401 ) );
		}
		$r = wp_remote_get( self::SUPABASE_URL . '/auth/v1/user', array(
			'timeout' => 12,
			'headers' => array( 'Authorization' => 'Bearer ' . $token, 'apikey' => self::SUPABASE_KEY ),
		) );
		if ( is_wp_error( $r ) || 200 !== (int) wp_remote_retrieve_response_code( $r ) ) {
			return new WP_Error( 'wp_control_unauthorized', 'Gateway identity is invalid or expired.', array( 'status' => 401 ) );
		}
		$user = json_decode( wp_remote_retrieve_body( $r ), true );
		$owner = (string) get_option( 'wp_control_owner_id', '' );
		if ( ! is_array( $user ) || empty( $user['id'] ) || ! $owner || ! hash_equals( $owner, (string) $user['id'] ) ) {
			return new WP_Error( 'wp_control_forbidden', 'This account does not own the paired site.', array( 'status' => 403 ) );
		}
		return $user;
	}

	private static function actions(): array {
		return array(
			'site_overview' => 'cowboy-mcp/wp-site-info',
			'list_content' => 'cowboy-mcp/wp-list-posts',
			'get_content' => 'cowboy-mcp/wp-get-post',
			'create_content' => 'cowboy-mcp/wp-create-post',
			'update_content' => 'cowboy-mcp/wp-update-post',
			'list_products' => 'cowboy-mcp/wp-woo-list-products',
			'get_product' => 'cowboy-mcp/wp-woo-get-product',
			'update_product' => 'cowboy-mcp/wp-woo-update-product',
			'list_orders' => 'cowboy-mcp/wp-woo-list-orders',
			'get_order' => 'cowboy-mcp/wp-woo-get-order',
			'add_order_note' => 'cowboy-mcp/wp-woo-add-order-note',
			'seo_audit' => 'cowboy-mcp/wp-seo-audit',
			'update_seo' => 'cowboy-mcp/wp-seo-update-meta',
			'flush_cache' => 'cowboy-mcp/wp-cache-flush',
			'list_changes' => 'cowboy-mcp/wp-list-changes',
			'undo_change' => 'cowboy-mcp/wp-undo-change',
		);
	}


	// Staging-safe, non-mutating diagnostics. The bridge still requires a
	// valid owner token, paired site ID and local manage_options user.
	private static function staycore_read_actions(): array {
		return array( 'staycore_diagnostics', 'staycore_inventory_check', 'staycore_availability_check' );
	}

	private static function staycore_table( array $tables, string $key ) {
		if ( ! isset( $tables[ $key ] ) || ! preg_match( '/^[a-zA-Z0-9_]+$/', $tables[ $key ] ) ) {
			return new WP_Error( 'staycore_bad_table', 'Invalid StayCore table mapping.', array( 'status' => 500 ) );
		}
		return chr( 96 ) . $tables[ $key ] . chr( 96 );
	}

	// Never returns guest names, identity documents, contacts or payment rows.
	private static function staycore_readonly( string $action, array $input ) {
		if ( ! current_user_can( 'manage_options' ) ) {
			return new WP_Error( 'staycore_forbidden', 'Administrator access required.', array( 'status' => 403 ) );
		}
		if ( ! class_exists( 'StayCore_DB' ) || ! defined( 'STAYCORE_PMS_VERSION' ) ) {
			return new WP_Error( 'staycore_unavailable', 'StayCore is not active.', array( 'status' => 501 ) );
		}
		global $wpdb;
		$tables = StayCore_DB::tables();
		$units_table = self::staycore_table( $tables, 'units' );
		if ( is_wp_error( $units_table ) ) return $units_table;

		if ( 'staycore_diagnostics' === $action ) {
			$counts = array();
			foreach ( array( 'units', 'guests', 'reservations', 'reservation_units', 'reservation_guests', 'payments', 'tasks', 'activity' ) as $key ) {
				$table = self::staycore_table( $tables, $key );
				if ( is_wp_error( $table ) ) return $table;
				$exists = $wpdb->get_var( $wpdb->prepare( 'SHOW TABLES LIKE %s', $tables[ $key ] ) );
				$counts[ $key ] = $exists === $tables[ $key ]
					? (int) $wpdb->get_var( "SELECT COUNT(*) FROM {$table}" )
					: null;
			}
			return array(
				'version' => STAYCORE_PMS_VERSION,
				'database_schema_version' => get_option( 'staycore_pms_db_version', '' ),
				'wordpress_environment' => wp_get_environment_type(),
				'table_counts' => $counts,
				'rest_health_url' => rest_url( 'staycore/v1/health' ),
				'read_only' => true,
			);
		}

		$rows = $wpdb->get_results(
			"SELECT id, name, type, room_group, capacity, base_rate, status, housekeeping_status
			 FROM {$units_table} ORDER BY id ASC LIMIT 250", ARRAY_A
		);
		if ( ! is_array( $rows ) ) {
			return new WP_Error( 'staycore_inventory_unavailable', 'Could not read StayCore units.', array( 'status' => 500 ) );
		}
		$units = array_map( static function ( array $row ): array {
			return array(
				'id' => (int) $row['id'],
				'name' => sanitize_text_field( (string) $row['name'] ),
				'type' => sanitize_key( (string) $row['type'] ),
				'room_group' => sanitize_text_field( (string) $row['room_group'] ),
				'capacity' => (int) $row['capacity'],
				'base_rate' => (float) $row['base_rate'],
				'status' => sanitize_key( (string) $row['status'] ),
				'housekeeping_status' => sanitize_key( (string) $row['housekeeping_status'] ),
			);
		}, $rows );

		if ( 'staycore_inventory_check' === $action ) {
			return array( 'units' => $units, 'shown' => count( $units ), 'limit' => 250, 'read_only' => true );
		}
		if ( 'staycore_availability_check' !== $action ) {
			return new WP_Error( 'staycore_action_not_allowed', 'Unsupported StayCore diagnostic.', array( 'status' => 400 ) );
		}
		$from = isset( $input['from'] ) && is_string( $input['from'] ) ? $input['from'] : '';
		$to = isset( $input['to'] ) && is_string( $input['to'] ) ? $input['to'] : '';
		$start = DateTimeImmutable::createFromFormat( '!Y-m-d', $from );
		$end = DateTimeImmutable::createFromFormat( '!Y-m-d', $to );
		if ( ! $start || ! $end || $start->format( 'Y-m-d' ) !== $from || $end->format( 'Y-m-d' ) !== $to
			|| $end <= $start || (int) $start->diff( $end )->format( '%a' ) > 31 ) {
			return new WP_Error( 'staycore_invalid_dates', 'Supply valid dates spanning 1–31 nights.', array( 'status' => 400 ) );
		}
		$res_table = self::staycore_table( $tables, 'reservations' );
		$link_table = self::staycore_table( $tables, 'reservation_units' );
		if ( is_wp_error( $res_table ) ) return $res_table;
		if ( is_wp_error( $link_table ) ) return $link_table;
		$matches = $wpdb->get_col( $wpdb->prepare(
			"SELECT DISTINCT ru.unit_id FROM {$link_table} ru
			 INNER JOIN {$res_table} r ON r.id=ru.reservation_id
			 WHERE r.status NOT IN ('cancelled','checked_out')
			 AND r.check_in < %s AND r.check_out > %s",
			$to . ' 00:00:00', $from . ' 00:00:00'
		) );
		if ( ! is_array( $matches ) ) {
			return new WP_Error( 'staycore_availability_unavailable', 'Could not query overlapping allocations.', array( 'status' => 500 ) );
		}
		$occupied = array_map( 'intval', $matches );
		$free = array();
		foreach ( $units as $unit ) {
			if ( 'available' === $unit['status'] && ! in_array( $unit['id'], $occupied, true ) ) {
				$free[] = $unit['id'];
			}
		}
		return array(
			'from' => $from, 'to' => $to,
			'inventory_scanned' => count( $units ),
			'occupied_unit_count' => count( $occupied ),
			'available_unit_ids' => $free,
			'available_unit_count' => count( $free ),
			'read_only' => true,
			'note' => 'Informational only; bookings remain authoritative.',
		);
	}

	public static function bridge( WP_REST_Request $request ) {
		$auth = self::validate_token( self::token( $request ) );
		if ( is_wp_error( $auth ) ) return $auth;
		$body = $request->get_json_params();
		if ( ! hash_equals( self::site_id(), sanitize_text_field( (string) ( $body['site_id'] ?? '' ) ) ) ) {
			return new WP_Error( 'wp_control_site_mismatch', 'Site id mismatch.', array( 'status' => 409 ) );
		}
		$action = sanitize_key( (string) ( $body['action'] ?? '' ) );
		$native_read = in_array( $action, self::staycore_read_actions(), true );
		$map = self::actions();
		if ( ! $native_read && ! isset( $map[ $action ] ) ) {
			return new WP_Error( 'wp_control_action_not_allowed', 'Gateway action is not allowed.', array( 'status' => 400 ) );
		}
		$ability = $native_read ? null : ( function_exists( 'wp_get_ability' ) ? wp_get_ability( $map[ $action ] ) : null );
		if ( ! $native_read && ! $ability ) {
			return new WP_Error( 'wp_control_capability_unavailable', 'Requested capability is unavailable.', array( 'status' => 501 ) );
		}
		$local_user_id = absint( get_option( 'wp_control_local_user_id', 0 ) );
		$local_user = $local_user_id ? get_user_by( 'id', $local_user_id ) : false;
		if ( ! $local_user || ! user_can( $local_user, 'manage_options' ) ) {
			return new WP_Error( 'wp_control_admin_invalid', 'Paired local administrator is unavailable.', array( 'status' => 403 ) );
		}
		$previous = get_current_user_id();
		wp_set_current_user( $local_user_id );
		try {
			$input = isset( $body['input'] ) && is_array( $body['input'] ) ? $body['input'] : array();
			$result = $native_read ? self::staycore_readonly( $action, $input ) : $ability->execute( $input );
		} finally {
			wp_set_current_user( $previous );
		}
		return is_wp_error( $result ) ? $result : rest_ensure_response( array( 'ok' => true, 'action' => $action, 'result' => $result ) );
	}
}
