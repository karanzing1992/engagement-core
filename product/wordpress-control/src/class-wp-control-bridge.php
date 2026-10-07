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

	public static function bridge( WP_REST_Request $request ) {
		$auth = self::validate_token( self::token( $request ) );
		if ( is_wp_error( $auth ) ) return $auth;
		$body = $request->get_json_params();
		if ( ! hash_equals( self::site_id(), sanitize_text_field( (string) ( $body['site_id'] ?? '' ) ) ) ) {
			return new WP_Error( 'wp_control_site_mismatch', 'Site id mismatch.', array( 'status' => 409 ) );
		}
		$action = sanitize_key( (string) ( $body['action'] ?? '' ) );
		$map = self::actions();
		if ( ! isset( $map[ $action ] ) ) {
			return new WP_Error( 'wp_control_action_not_allowed', 'Gateway action is not allowed.', array( 'status' => 400 ) );
		}
		$ability = function_exists( 'wp_get_ability' ) ? wp_get_ability( $map[ $action ] ) : null;
		if ( ! $ability ) {
			return new WP_Error( 'wp_control_capability_unavailable', 'Requested capability is unavailable.', array( 'status' => 501 ) );
		}
		$local_user_id = absint( get_option( 'wp_control_local_user_id', 0 ) );
		$local_user = $local_user_id ? get_user_by( 'id', $local_user_id ) : false;
		if ( ! $local_user || ! user_can( $local_user, 'manage_options' ) ) {
			return new WP_Error( 'wp_control_admin_invalid', 'Paired local administrator is unavailable.', array( 'status' => 403 ) );
		}
		$previous = get_current_user_id();
		wp_set_current_user( $local_user_id );
		$result = $ability->execute( isset( $body['input'] ) && is_array( $body['input'] ) ? $body['input'] : array() );
		wp_set_current_user( $previous );
		return is_wp_error( $result ) ? $result : rest_ensure_response( array( 'ok' => true, 'action' => $action, 'result' => $result ) );
	}
}
