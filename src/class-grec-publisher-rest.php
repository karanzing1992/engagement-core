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
					'text'      => array( 'required' => true, 'type' => 'string' ),
					'media_url' => array( 'required' => false, 'type' => 'string', 'format' => 'uri' ),
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
			),
			200
		);
	}

	public static function config( WP_REST_Request $request ): WP_REST_Response {
		$token = trim( (string) $request->get_param( 'token' ) );
		$chat  = sanitize_text_field( (string) $request->get_param( 'chat_id' ) );

		if ( '' !== $token ) {
			GREC_Telegram::save_token( $token );
		}
		if ( '' !== $chat ) {
			update_option( 'grec_telegram_chat_id', $chat, false );
		}

		return self::status();
	}

	public static function test(): WP_REST_Response {
		try {
			$data = GREC_Telegram::send( 'Publishing connection test ✓' );
			return new WP_REST_Response(
				array(
					'ok'         => true,
					'message_id' => $data['result']['message_id'] ?? null,
				),
				200
			);
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 502 );
		}
	}

	public static function publish( WP_REST_Request $request ): WP_REST_Response {
		$text      = sanitize_textarea_field( (string) $request->get_param( 'text' ) );
		$media_url = esc_url_raw( (string) $request->get_param( 'media_url' ) );

		if ( '' === $text ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => 'Text is required.' ), 400 );
		}

		try {
			$data = GREC_Telegram::send( $text, $media_url );
			return new WP_REST_Response(
				array(
					'ok'         => true,
					'message_id' => $data['result']['message_id'] ?? null,
					'media'      => '' !== $media_url,
				),
				200
			);
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 502 );
		}
	}

	public static function status(): WP_REST_Response {
		return new WP_REST_Response(
			array(
				'connected'    => GREC_Telegram::is_connected(),
				'chat_id'      => get_option( 'grec_telegram_chat_id', '' ),
				'last_publish' => get_option( 'grec_telegram_last_publish', array() ),
			),
			200
		);
	}
}
