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
		register_rest_route( 'engagement-core/v1', '/telegram/status', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'status' ), 'permission_callback' => self::scope_permission( 'telegram.status' ) ) );
		register_rest_route( 'engagement-core/v1', '/vk/config', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'vk_config' ), 'permission_callback' => array( __CLASS__, 'admin' ) ) );
		register_rest_route( 'engagement-core/v1', '/vk/test', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'vk_test' ), 'permission_callback' => array( __CLASS__, 'admin' ) ) );
		register_rest_route( 'engagement-core/v1', '/vk/status', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'vk_status' ), 'permission_callback' => self::scope_permission( 'vk.status' ) ) );
		register_rest_route( 'engagement-core/v1', '/ok/config', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'ok_config' ), 'permission_callback' => array( __CLASS__, 'admin' ) ) );
		register_rest_route( 'engagement-core/v1', '/ok/test', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'ok_test' ), 'permission_callback' => array( __CLASS__, 'admin' ) ) );
		register_rest_route( 'engagement-core/v1', '/ok/status', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'ok_status' ), 'permission_callback' => self::scope_permission( 'ok.status' ) ) );
		register_rest_route( 'engagement-core/v1', '/snapchat/config', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'snapchat_config' ), 'permission_callback' => array( __CLASS__, 'admin' ) ) );
		register_rest_route( 'engagement-core/v1', '/snapchat/status', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'snapchat_status' ), 'permission_callback' => self::scope_permission( 'snapchat.status' ) ) );
		register_rest_route( 'engagement-core/v1', '/snapchat/handoff', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'snapchat_handoff' ), 'permission_callback' => self::scope_permission( 'snapchat.handoff' ) ) );
		register_rest_route( 'engagement-core/v1', '/snapchat/device/next', array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'snapchat_device_next' ), 'permission_callback' => array( __CLASS__, 'snapchat_device_auth' ) ) );
		register_rest_route( 'engagement-core/v1', '/snapchat/device/complete', array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'snapchat_device_complete' ), 'permission_callback' => array( __CLASS__, 'snapchat_device_auth' ) ) );
		register_rest_route(
			'engagement-core/v1',
			'/ok/publish',
			array(
				'methods'             => 'POST',
				'callback'            => array( __CLASS__, 'ok_publish' ),
				'permission_callback' => self::scope_permission( 'ok.publish' ),
				'args'                => array(
					'text'  => array( 'required' => false, 'type' => 'string' ),
					'link'  => array( 'required' => false, 'type' => 'string', 'format' => 'uri' ),
					'media' => array( 'required' => false, 'type' => 'array' ),
				),
			)
		);
		register_rest_route(
			'engagement-core/v1',
			'/vk/publish',
			array(
				'methods'             => 'POST',
				'callback'            => array( __CLASS__, 'vk_publish' ),
				'permission_callback' => self::scope_permission( 'vk.publish' ),
				'args'                => array(
					'text'  => array( 'required' => false, 'type' => 'string' ),
					'link'  => array( 'required' => false, 'type' => 'string', 'format' => 'uri' ),
					'media' => array( 'required' => false, 'type' => 'array' ),
				),
			)
		);
		register_rest_route(
			'engagement-core/v1',
			'/telegram/publish',
			array(
				'methods'             => 'POST',
				'callback'            => array( __CLASS__, 'publish' ),
				'permission_callback' => self::scope_permission( 'telegram.publish' ),
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

	public static function machine_scopes(): array {
		$defaults = array( 'telegram.status', 'telegram.publish', 'vk.status', 'vk.publish', 'ok.status', 'ok.publish', 'snapchat.status', 'snapchat.handoff' );
		$stored = get_option( 'grec_publish_key_scopes', $defaults );
		return is_array( $stored ) ? array_values( array_unique( array_map( 'sanitize_key', $stored ) ) ) : $defaults;
	}

	public static function scope_permission( string $scope ): Closure {
		return static function ( WP_REST_Request $request ) use ( $scope ): bool {
			return GREC_Publisher_REST::machine_auth( $request, $scope );
		};
	}

	public static function machine_auth( WP_REST_Request $request, string $scope = '' ): bool {
		if ( self::admin() ) { return true; }
		$provided = trim( (string) $request->get_header( 'x-grec-publish-key' ) );
		if ( '' === $provided ) { return false; }
		$valid = false;
		if ( defined( 'GREC_PUBLISH_KEY' ) ) {
			$expected = trim( (string) GREC_PUBLISH_KEY );
			$valid = '' !== $expected && hash_equals( $expected, $provided );
		} else {
			$expected_hash = trim( (string) get_option( 'grec_publish_key_hash', '' ) );
			$valid = '' !== $expected_hash && hash_equals( $expected_hash, hash( 'sha256', $provided ) );
		}
		return $valid && ( '' === $scope || in_array( $scope, self::machine_scopes(), true ) );
	}

	public static function publisher_auth( WP_REST_Request $request ): bool {
		return self::machine_auth( $request );
	}

	public static function health(): WP_REST_Response {
		return new WP_REST_Response(
			array(
				'ok'                 => true,
				'version'            => defined( 'GREC_VERSION' ) ? GREC_VERSION : null,
				'telegram_connected' => GREC_Telegram::is_connected(),
				'telegram_destinations' => count( GREC_Telegram::enabled_destinations() ),
				'telegram_rich_media' => true,
				'vk_connected'       => GREC_VK::is_connected(),
				'vk_photo_upload'    => true,
				'ok_connected'       => GREC_OK::is_connected(),
				'ok_requires_approval' => true,
				'snapchat_mode'       => 'creative-kit-lite-preview',
				'snapchat_configured' => GREC_Snapchat::is_configured(),
				'snapchat_pending'    => GREC_Snapchat::pending_count(),
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

	public static function vk_config( WP_REST_Request $request ): WP_REST_Response {
		$token    = trim( (string) $request->get_param( 'token' ) );
		$owner_id = sanitize_text_field( (string) $request->get_param( 'owner_id' ) );

		try {
			if ( '' !== $token ) {
				GREC_VK::save_token( $token );
			}
			if ( '' !== $owner_id ) {
				GREC_VK::save_owner_id( $owner_id );
			}
			return self::vk_status();
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 400 );
		}
	}

	public static function vk_test(): WP_REST_Response {
		try {
			return new WP_REST_Response( GREC_VK::test_connection(), 200 );
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 502 );
		}
	}

	public static function vk_publish( WP_REST_Request $request ): WP_REST_Response {
		$text  = sanitize_textarea_field( (string) $request->get_param( 'text' ) );
		$link  = esc_url_raw( (string) $request->get_param( 'link' ) );
		$media = $request->get_param( 'media' );
		if ( ! is_array( $media ) ) {
			$media = array();
		}

		try {
			$data = GREC_VK::publish( $text, $media, $link );
			return new WP_REST_Response( $data, 200 );
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 502 );
		}
	}

	public static function vk_status(): WP_REST_Response {
		return new WP_REST_Response( GREC_VK::status(), 200 );
	}


	public static function ok_config( WP_REST_Request $request ): WP_REST_Response {
		try {
			GREC_OK::save_credentials(
				array(
					'application_id'     => (string) $request->get_param( 'application_id' ),
					'application_key'    => (string) $request->get_param( 'application_key' ),
					'application_secret' => (string) $request->get_param( 'application_secret' ),
					'access_token'       => (string) $request->get_param( 'access_token' ),
				)
			);
			$group_id = sanitize_text_field( (string) $request->get_param( 'group_id' ) );
			if ( '' !== $group_id ) {
				GREC_OK::save_group_id( $group_id );
			}
			return self::ok_status();
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 400 );
		}
	}

	public static function ok_test(): WP_REST_Response {
		try {
			return new WP_REST_Response( GREC_OK::test_connection(), 200 );
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 502 );
		}
	}

	public static function ok_publish( WP_REST_Request $request ): WP_REST_Response {
		$text  = sanitize_textarea_field( (string) $request->get_param( 'text' ) );
		$link  = esc_url_raw( (string) $request->get_param( 'link' ) );
		$media = $request->get_param( 'media' );
		if ( ! is_array( $media ) ) {
			$media = array();
		}
		try {
			return new WP_REST_Response( GREC_OK::publish( $text, $media, $link ), 200 );
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 502 );
		}
	}

	public static function ok_status(): WP_REST_Response {
		return new WP_REST_Response( GREC_OK::status(), 200 );
	}


	public static function snapchat_config( WP_REST_Request $request ): WP_REST_Response {
		try {
			$client_id = sanitize_text_field( (string) $request->get_param( 'client_id' ) );
			$key       = trim( (string) $request->get_param( 'device_key' ) );
			if ( '' !== $client_id ) {
				GREC_Snapchat::save_client_id( $client_id );
			}
			if ( '' !== $key ) {
				GREC_Snapchat::save_device_key( $key );
			} elseif ( '' === GREC_Snapchat::device_key() ) {
				GREC_Snapchat::ensure_device_key();
			}
			return self::snapchat_status();
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 400 );
		}
	}

	public static function snapchat_status(): WP_REST_Response {
		return new WP_REST_Response( GREC_Snapchat::status(), 200 );
	}

	public static function snapchat_handoff( WP_REST_Request $request ): WP_REST_Response {
		try {
			$task = GREC_Snapchat::queue_handoff(
				sanitize_textarea_field( (string) $request->get_param( 'caption' ) ),
				esc_url_raw( (string) $request->get_param( 'media_url' ) ),
				sanitize_key( (string) $request->get_param( 'media_type' ) )
			);
			return new WP_REST_Response( array( 'ok' => true, 'task' => $task ), 201 );
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 400 );
		}
	}

	public static function snapchat_device_auth( WP_REST_Request $request ): bool {
		$expected = GREC_Snapchat::device_key();
		$provided = trim( (string) $request->get_header( 'x-grec-snap-key' ) );
		return '' !== $expected && '' !== $provided && hash_equals( $expected, $provided );
	}

	public static function snapchat_device_next(): WP_REST_Response {
		$task = GREC_Snapchat::claim_next();
		if ( null === $task ) {
			return new WP_REST_Response( array( 'ok' => true, 'task' => null ), 200 );
		}
		return new WP_REST_Response( array( 'ok' => true, 'task' => $task ), 200 );
	}

	public static function snapchat_device_complete( WP_REST_Request $request ): WP_REST_Response {
		try {
			$task = GREC_Snapchat::complete(
				sanitize_text_field( (string) $request->get_param( 'id' ) ),
				sanitize_key( (string) $request->get_param( 'status' ) ),
				sanitize_text_field( (string) $request->get_param( 'error' ) )
			);
			return new WP_REST_Response( array( 'ok' => true, 'task' => $task ), 200 );
		} catch ( Throwable $e ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $e->getMessage() ), 400 );
		}
	}

}
