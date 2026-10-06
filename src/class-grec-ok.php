<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_OK {
	private const API_URL    = 'https://api.ok.ru/fb.do';
	private const MAX_PHOTOS = 10;

	public static function credentials(): array {
		return GREC_Secrets::open( (string) get_option( 'grec_ok_credentials', '' ) );
	}

	public static function save_credentials( array $incoming ): void {
		$current = self::credentials();
		$fields  = array( 'application_id', 'application_key', 'application_secret', 'access_token' );

		foreach ( $fields as $field ) {
			$value = trim( (string) ( $incoming[ $field ] ?? '' ) );
			if ( '' !== $value ) {
				$current[ $field ] = $value;
			}
		}

		update_option( 'grec_ok_credentials', GREC_Secrets::seal( $current ), false );
	}

	public static function save_group_id( string $group_id ): void {
		$group_id = trim( $group_id );
		if ( ! preg_match( '/^\d+$/', $group_id ) ) {
			throw new InvalidArgumentException( 'OK group ID must be a positive numeric ID.' );
		}
		update_option( 'grec_ok_group_id', $group_id, false );
	}

	public static function group_id(): string {
		return trim( (string) get_option( 'grec_ok_group_id', '' ) );
	}

	public static function is_connected(): bool {
		$c = self::credentials();
		return ! empty( $c['application_key'] )
			&& ! empty( $c['application_secret'] )
			&& ! empty( $c['access_token'] )
			&& '' !== self::group_id();
	}

	private static function signature( array $params, string $access_token, string $application_secret ): string {
		unset( $params['access_token'], $params['session_key'], $params['sig'] );
		ksort( $params, SORT_STRING );

		$joined = '';
		foreach ( $params as $key => $value ) {
			$joined .= $key . '=' . $value;
		}

		$session_secret = md5( $access_token . $application_secret );
		return strtolower( md5( $joined . $session_secret ) );
	}

	private static function api( string $method, array $params = array() ) {
		$c = self::credentials();
		if ( empty( $c['application_key'] ) || empty( $c['application_secret'] ) || empty( $c['access_token'] ) ) {
			throw new RuntimeException( 'Odnoklassniki API credentials are incomplete.' );
		}

		$params['method']          = $method;
		$params['application_key'] = (string) $c['application_key'];
		$params['format']          = 'json';
		$params['sig']             = self::signature( $params, (string) $c['access_token'], (string) $c['application_secret'] );
		$params['access_token']    = (string) $c['access_token'];

		$response = wp_remote_post(
			self::API_URL,
			array(
				'timeout' => 60,
				'body'    => $params,
			)
		);

		if ( is_wp_error( $response ) ) {
			throw new RuntimeException( $response->get_error_message() );
		}

		$raw  = wp_remote_retrieve_body( $response );
		$data = json_decode( $raw, true );
		if ( null === $data && 'null' !== trim( $raw ) ) {
			throw new RuntimeException( 'Odnoklassniki returned an invalid response.' );
		}
		if ( is_array( $data ) && isset( $data['error_code'] ) ) {
			throw new RuntimeException(
				sprintf(
					'OK API error %s: %s',
					(string) $data['error_code'],
					(string) ( $data['error_msg'] ?? 'Unknown Odnoklassniki API error' )
				)
			);
		}

		return $data;
	}

	public static function test_connection(): array {
		if ( ! self::is_connected() ) {
			throw new RuntimeException( 'Odnoklassniki credentials or group ID are incomplete.' );
		}

		$user = self::api( 'users.getCurrentUser' );
		return array(
			'ok'                    => true,
			'group_id'              => self::group_id(),
			'user_name'             => is_array( $user ) ? (string) ( $user['name'] ?? '' ) : '',
			'requires_approved_app' => true,
		);
	}

	private static function download_temp( string $url ): string {
		if ( ! wp_http_validate_url( $url ) ) {
			throw new InvalidArgumentException( 'OK photo URL must be a valid public HTTP(S) URL.' );
		}
		require_once ABSPATH . 'wp-admin/includes/file.php';
		$tmp = download_url( $url, 60 );
		if ( is_wp_error( $tmp ) ) {
			throw new RuntimeException( 'Unable to download OK photo: ' . $tmp->get_error_message() );
		}
		return $tmp;
	}

	private static function upload_photos( array $urls ): array {
		if ( empty( $urls ) ) {
			return array();
		}
		if ( ! function_exists( 'curl_init' ) || ! function_exists( 'curl_file_create' ) ) {
			throw new RuntimeException( 'The server cURL extension is required for Odnoklassniki photo uploads.' );
		}

		$upload = self::api(
			'photosV2.getUploadUrl',
			array(
				'gid'   => self::group_id(),
				'count' => count( $urls ),
			)
		);
		$upload_url = is_array( $upload ) ? (string) ( $upload['upload_url'] ?? '' ) : '';
		if ( '' === $upload_url ) {
			throw new RuntimeException( 'Odnoklassniki did not return a photo upload URL.' );
		}

		$tmp_files = array();
		$post      = array();
		try {
			foreach ( array_values( $urls ) as $index => $url ) {
				$tmp = self::download_temp( $url );
				$tmp_files[] = $tmp;
				$mime = function_exists( 'mime_content_type' ) ? (string) mime_content_type( $tmp ) : 'image/jpeg';
				$post[ 'pic' . ( $index + 1 ) ] = curl_file_create( $tmp, $mime ?: 'image/jpeg', basename( $tmp ) );
			}

			$ch = curl_init( $upload_url );
			curl_setopt_array(
				$ch,
				array(
					CURLOPT_POST           => true,
					CURLOPT_POSTFIELDS     => $post,
					CURLOPT_RETURNTRANSFER => true,
					CURLOPT_CONNECTTIMEOUT => 20,
					CURLOPT_TIMEOUT        => 120,
				)
			);
			$raw  = curl_exec( $ch );
			$code = (int) curl_getinfo( $ch, CURLINFO_HTTP_CODE );
			$err  = curl_error( $ch );
			curl_close( $ch );

			if ( false === $raw || $code >= 300 ) {
				throw new RuntimeException( 'Odnoklassniki photo upload failed. ' . ( $err ?: 'HTTP ' . $code ) );
			}
			$data = json_decode( (string) $raw, true );
			if ( ! is_array( $data ) || empty( $data['photos'] ) || ! is_array( $data['photos'] ) ) {
				throw new RuntimeException( 'Odnoklassniki photo upload returned an invalid response.' );
			}

			$tokens = array();
			foreach ( $data['photos'] as $photo ) {
				if ( is_array( $photo ) && ! empty( $photo['token'] ) ) {
					$tokens[] = (string) $photo['token'];
				}
			}
			if ( empty( $tokens ) ) {
				throw new RuntimeException( 'Odnoklassniki photo upload did not return media tokens.' );
			}
			return $tokens;
		} finally {
			foreach ( $tmp_files as $tmp ) {
				@unlink( $tmp );
			}
		}
	}

	public static function publish( string $text = '', array $media = array(), string $link = '' ): array {
		if ( ! self::is_connected() ) {
			throw new RuntimeException( 'Odnoklassniki is not configured.' );
		}

		$text = trim( wp_strip_all_tags( $text ) );
		$link = esc_url_raw( $link );
		$photo_urls = array();

		foreach ( $media as $item ) {
			if ( ! is_array( $item ) ) {
				continue;
			}
			$type = sanitize_key( (string) ( $item['type'] ?? 'photo' ) );
			$url  = esc_url_raw( (string) ( $item['url'] ?? '' ) );
			if ( '' === $url ) {
				continue;
			}
			if ( 'photo' !== $type ) {
				throw new InvalidArgumentException( 'Odnoklassniki v0.6 currently accepts photo media in the WordPress publisher.' );
			}
			$photo_urls[] = $url;
		}

		if ( count( $photo_urls ) > self::MAX_PHOTOS ) {
			throw new InvalidArgumentException( 'Engagement Core limits Odnoklassniki posts to 10 photos.' );
		}
		if ( '' === $text && empty( $photo_urls ) && '' === $link ) {
			throw new InvalidArgumentException( 'An Odnoklassniki post needs text, a photo, or a link.' );
		}

		$media_blocks = array();
		if ( '' !== $text ) {
			$media_blocks[] = array( 'type' => 'text', 'text' => $text );
		}

		$tokens = self::upload_photos( $photo_urls );
		if ( ! empty( $tokens ) ) {
			$list = array();
			foreach ( $tokens as $token ) {
				$list[] = array( 'id' => $token );
			}
			$media_blocks[] = array( 'type' => 'photo', 'list' => $list );
		}

		if ( '' !== $link ) {
			$media_blocks[] = array( 'type' => 'link', 'url' => $link );
		}

		$attachment = wp_json_encode( array( 'media' => $media_blocks ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
		$topic_id = self::api(
			'mediatopic.post',
			array(
				'type'            => 'GROUP_THEME',
				'gid'             => self::group_id(),
				'attachment'      => $attachment,
				'onBehalfOfGroup' => 'true',
			)
		);

		update_option(
			'grec_ok_last_publish',
			array(
				'at'          => time(),
				'group_id'    => self::group_id(),
				'topic_id'    => is_scalar( $topic_id ) ? (string) $topic_id : '',
				'photo_count' => count( $photo_urls ),
				'link'        => $link,
			),
			false
		);

		return array(
			'ok'                    => true,
			'group_id'              => self::group_id(),
			'topic_id'              => is_scalar( $topic_id ) ? (string) $topic_id : '',
			'photo_count'           => count( $photo_urls ),
			'requires_approved_app' => true,
		);
	}

	public static function status(): array {
		$c = self::credentials();
		return array(
			'connected'             => self::is_connected(),
			'group_id'              => self::group_id(),
			'application_id'        => (string) ( $c['application_id'] ?? '' ),
			'application_key_saved' => ! empty( $c['application_key'] ),
			'access_token_saved'    => ! empty( $c['access_token'] ),
			'requires_approved_app' => true,
			'last_publish'          => get_option( 'grec_ok_last_publish', array() ),
		);
	}
}
