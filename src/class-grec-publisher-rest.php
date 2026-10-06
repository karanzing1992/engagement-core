<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class GREC_Publisher_REST {
	public static function init(): void {
		add_action( 'rest_api_init', array( __CLASS__, 'routes' ) );
	}

	public static function routes(): void {
		register_rest_route(
			'engagement-core/v1',
			'/health',
			array(
				'methods'             => 'GET',
				'callback'            => array( __CLASS__, 'health' ),
				'permission_callback' => '__return_true',
			)
		);
		register_rest_route( 'engagement-core/v1', '/telegram/config', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'config' ), 'permission_callback' => array( __CLASS__, 'admin' ) ) );
		register_rest_route( 'engagement-core/v1', '/telegram/test', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'test' ), 'permission_callback' => array( __CLASS__, 'admin' ) ) );
		register_rest_route( 'engagement-core/v1', '/telegram/status', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'status' ), 'permission_callback' => array( __CLASS__, 'admin' ) ) );
		register_rest_route(
			'engagement-core/v1',
			'/telegram/publish',
			array(
				'methods'             => 'POST',
				'callback'            => array( __CLASS__, 'publish' ),
				'permission_callback' => array( __CLASS__, 'admin' ),
				'args'                => array(
					'text'      => array( 'required' => false, 'type' => 'string' ),
					'media_url' => array( 'required' => false, 'type' => 'string', 'format' => 'uri' ),
					'media'     => array( 'required' => false, 'type' => 'array' ),
					'targets'   => array( 'required' => false, 'type' => 'array', 'items' => array( 'type' => 'string' ) ),
					'levels'    => array( 'required' => false, 'type' => 'array', 'items' => array( 'type' => 'string' ) ),
				),
			)
		);
	}

	public static function admin(): bool {
		return current_user_can( 'manage_options' );
	}

	public static function health(): WP_REST_Response {
		return new WP_REST_Response(
			array(
				'ok'                 => true,
				'version'            => defined( 'GREC_VERSION' ) ? GREC_VERSION : null,
				'telegram_connected' => GREC_Telegram::is_connected(),
				'telegram_destinations' => count( GREC_Telegram::enabled_destinations() ),
				'telegram_rich_media' => true,
			),
			200
		);
	}

	public static function config( WP_REST_Request $request ): WP_REST_Response {
		$token        = trim( (string) $request->get_param( 'token' ) );
		$chat         = sanitize_text_field( (string) $request->get_param( 'chat_id' ) );
		$destinations = $request->get_param( 'destinations' );

		try {
			if ( '' !== $token ) {
				GREC_Telegram::save_token( $token );
			}
			if ( is_array( $destinations ) ) {
				GREC_Telegram::save_destinations( $destinations );
			} elseif ( '' !== $chat ) {
				GREC_Telegram::save_destinations(
					array(
						array(
							'name'    => 'Primary',
							'chat_id' => $chat,
							'level'   => 'primary',
							'enabled' => true,
						),
					)
				);
			}
			return self::status();
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 400 );
		}
	}

	public static function test(): WP_REST_Response {
		try {
			$data = GREC_Telegram::send( 'Publishing connection test ✓' );
			return new WP_REST_Response(
				array(
					'ok'     => ! empty( $data['ok'] ),
					'sent'   => $data['sent'] ?? array(),
					'failed' => $data['failed'] ?? array(),
				),
				empty( $data['failed'] ) ? 200 : 207
			);
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 502 );
		}
	}

	public static function publish( WP_REST_Request $request ): WP_REST_Response {
		$text       = GREC_Telegram::sanitize_message_html( (string) $request->get_param( 'text' ) );
		$media_url  = esc_url_raw( (string) $request->get_param( 'media_url' ) );
		$media      = $request->get_param( 'media' );
		$targets    = is_array( $request->get_param( 'targets' ) ) ? array_map( 'sanitize_text_field', $request->get_param( 'targets' ) ) : array();
		$levels     = is_array( $request->get_param( 'levels' ) ) ? array_map( 'sanitize_key', $request->get_param( 'levels' ) ) : array();

		if ( ! is_array( $media ) ) {
			$media = array();
		}
		if ( '' !== $media_url && empty( $media ) ) {
			$media[] = array(
				'type' => 'video',
				'url'  => $media_url,
				'name' => '',
			);
		}
		if ( '' === $text && empty( $media ) ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => 'Text or media is required.' ), 400 );
		}

		try {
			$data = GREC_Telegram::send_post( $text, $media, $targets, $levels );
			return new WP_REST_Response(
				array(
					'ok'          => ! empty( $data['ok'] ),
					'media_count' => count( $media ),
					'sent'        => $data['sent'] ?? array(),
					'failed'      => $data['failed'] ?? array(),
				),
				empty( $data['failed'] ) ? 200 : 207
			);
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 502 );
		}
	}

	public static function status(): WP_REST_Response {
		return new WP_REST_Response(
			array(
				'connected'         => GREC_Telegram::is_connected(),
				'destinations'      => GREC_Telegram::destinations(),
				'enabled_count'     => count( GREC_Telegram::enabled_destinations() ),
				'legacy_chat_id'    => get_option( 'grec_telegram_chat_id', '' ),
				'media_types'       => GREC_Telegram::media_types(),
				'media_group_limit' => 10,
				'formatting'        => 'HTML',
				'last_publish'      => get_option( 'grec_telegram_last_publish', array() ),
			),
			200
		);
	}
}
