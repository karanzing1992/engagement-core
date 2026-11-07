<?php
/** Versioned authenticated WordPress REST CRM interface. */
defined( 'ABSPATH' ) || exit;

final class ECCRM_REST {
    public static function register(): void {
        add_action( 'rest_api_init', array( __CLASS__, 'routes' ) );
    }

    public static function authorize() {
        return current_user_can( ECCRM_CAPABILITY ) ? true : new WP_Error( 'eccrm_forbidden', 'CRM access denied.', array( 'status' => 403 ) );
    }

    public static function routes(): void {
        register_rest_route( 'eccrm/v1', '/contacts', array(
            array( 'methods' => WP_REST_Server::READABLE, 'permission_callback' => array( __CLASS__, 'authorize' ), 'callback' => array( __CLASS__, 'index' ) ),
            array( 'methods' => WP_REST_Server::CREATABLE, 'permission_callback' => array( __CLASS__, 'authorize' ), 'callback' => array( __CLASS__, 'create' ) ),
        ) );
        register_rest_route( 'eccrm/v1', '/contacts/(?P<id>[0-9]+)', array(
            array( 'methods' => WP_REST_Server::READABLE, 'permission_callback' => array( __CLASS__, 'authorize' ), 'callback' => array( __CLASS__, 'show' ) ),
            array( 'methods' => 'PATCH', 'permission_callback' => array( __CLASS__, 'authorize' ), 'callback' => array( __CLASS__, 'update' ) ),
        ) );
    }

    public static function index( WP_REST_Request $request ) {
        return rest_ensure_response( array( 'items' => ECCRM_Contacts::list( (int) ( $request->get_param( 'limit' ) ?: 25 ), (int) ( $request->get_param( 'offset' ) ?: 0 ) ) ) );
    }

    public static function show( WP_REST_Request $request ) {
        $record = ECCRM_Contacts::find( (int) $request['id'] );
        return $record ? rest_ensure_response( $record ) : new WP_Error( 'eccrm_not_found', 'Contact not found.', array( 'status' => 404 ) );
    }

    private static function input( WP_REST_Request $request ) {
        $json = $request->get_json_params();
        $input = null !== $json ? $json : $request->get_body_params();
        return is_array( $input ) ? $input : new WP_Error( 'eccrm_invalid_payload', 'Expected JSON object or form fields.', array( 'status' => 400 ) );
    }

    public static function create( WP_REST_Request $request ) {
        $input = self::input( $request );
        if ( is_wp_error( $input ) ) { return $input; }
        $record = ECCRM_Contacts::create( $input );
        return is_wp_error( $record ) ? $record : new WP_REST_Response( $record, 201 );
    }

    public static function update( WP_REST_Request $request ) {
        $input = self::input( $request );
        if ( is_wp_error( $input ) ) { return $input; }
        $record = ECCRM_Contacts::update( (int) $request['id'], $input );
        return is_wp_error( $record ) ? $record : rest_ensure_response( $record );
    }
}
