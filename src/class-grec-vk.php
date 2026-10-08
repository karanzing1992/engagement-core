<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_VK {
	private const API_VERSION = '5.199';
	private const MAX_PHOTOS  = 10;
	private const OAUTH_AUTHORIZE_URL = 'https://oauth.vk.com/authorize';
	private const OAUTH_TOKEN_URL = 'https://oauth.vk.com/access_token';

	public static function credentials(): array {
		return GREC_Secrets::open( (string) get_option( 'grec_vk_credentials', '' ) );
	}


	public static function oauth_app(): array {
		return GREC_Secrets::open( (string) get_option( 'grec_vk_oauth_app', '' ) );
	}

	public static function save_oauth_app( string $client_id, string $client_secret ): void {
		$client_id = trim( $client_id );
		$client_secret = trim( $client_secret );
		if ( '' === $client_id || ! preg_match( '/^\d+$/', $client_id ) ) {
			throw new InvalidArgumentException( 'VK application ID must be numeric.' );
		}
		if ( '' === $client_secret ) {
			$existing = self::oauth_app();
			$client_secret = (string) ( $existing['client_secret'] ?? '' );
		}
		if ( '' === $client_secret ) {
			throw new InvalidArgumentException( 'VK application secure key is required.' );
		}
		update_option(
			'grec_vk_oauth_app',
			GREC_Secrets::seal(
				array(
					'client_id'     => $client_id,
					'client_secret' => $client_secret,
				)
			),
			false
		);
	}

	public static function oauth_app_configured(): bool {
		$app = self::oauth_app();
		return ! empty( $app['client_id'] ) && ! empty( $app['client_secret'] );
	}

	public static function oauth_callback_url(): string {
		return home_url( '/vk-oauth/callback/' );
	}

	public static function oauth_authorize_url( string $state ): string {
		$app = self::oauth_app();
		if ( empty( $app['client_id'] ) ) {
			throw new RuntimeException( 'VK application ID is not configured.' );
		}
		return add_query_arg(
			array(
				'client_id'     => (string) $app['client_id'],
				'redirect_uri'  => self::oauth_callback_url(),
				'display'       => 'page',
				'scope'         => 'wall,photos,groups,offline',
				'response_type' => 'code',
				'v'             => self::API_VERSION,
				'state'         => $state,
			),
			self::OAUTH_AUTHORIZE_URL
		);
	}

	public static function exchange_oauth_code( string $code ): array {
		$app = self::oauth_app();
		if ( empty( $app['client_id'] ) || empty( $app['client_secret'] ) ) {
			throw new RuntimeException( 'VK application credentials are not configured.' );
		}
		$response = wp_remote_post(
			self::OAUTH_TOKEN_URL,
			array(
				'timeout' => 30,
				'body' => array(
					'client_id'     => (string) $app['client_id'],
					'client_secret' => (string) $app['client_secret'],
					'redirect_uri'  => self::oauth_callback_url(),
					'code'          => trim( $code ),
				),
			)
		);
		if ( is_wp_error( $response ) ) {
			throw new RuntimeException( 'VK OAuth token exchange failed: ' . $response->get_error_message() );
		}
		$data = json_decode( wp_remote_retrieve_body( $response ), true );
		if ( ! is_array( $data ) ) {
			throw new RuntimeException( 'VK OAuth returned an invalid token response.' );
		}
		if ( ! empty( $data['error'] ) ) {
			$message = is_string( $data['error_description'] ?? null ) ? $data['error_description'] : (string) $data['error'];
			throw new RuntimeException( 'VK OAuth error: ' . $message );
		}
		$token = trim( (string) ( $data['access_token'] ?? '' ) );
		if ( '' === $token ) {
			throw new RuntimeException( 'VK OAuth did not return an access token.' );
		}
		self::save_token( $token );
		update_option(
			'grec_vk_oauth_meta',
			array(
				'user_id'    => isset( $data['user_id'] ) ? (int) $data['user_id'] : 0,
				'expires_in' => isset( $data['expires_in'] ) ? (int) $data['expires_in'] : 0,
				'connected_at' => time(),
			),
			false
		);
		return $data;
	}

	public static function managed_communities(): array {
		if ( empty( self::credentials()['token'] ) ) {
			throw new RuntimeException( 'VK is not authorized yet.' );
		}
		$data = self::api(
			'groups.get',
			array(
				'extended' => 1,
				'filter'   => 'admin',
				'count'    => 1000,
			)
		);
		$items = array();
		if ( isset( $data['items'] ) && is_array( $data['items'] ) ) {
			$items = $data['items'];
		} elseif ( isset( $data['groups'] ) && is_array( $data['groups'] ) ) {
			$items = $data['groups'];
		} elseif ( isset( $data[0] ) ) {
			$items = $data;
		}

		$out = array();
		foreach ( $items as $group ) {
			if ( ! is_array( $group ) || empty( $group['id'] ) ) {
				continue;
			}
			$id = absint( $group['id'] );
			if ( ! $id ) {
				continue;
			}
			$out[] = array(
				'id'         => $id,
				'owner_id'   => '-' . $id,
				'name'       => sanitize_text_field( (string) ( $group['name'] ?? ( 'VK Community ' . $id ) ) ),
				'screen_name'=> sanitize_key( (string) ( $group['screen_name'] ?? '' ) ),
				'photo'      => esc_url_raw( (string) ( $group['photo_100'] ?? $group['photo_50'] ?? '' ) ),
			);
		}
		return $out;
	}

	public static function disconnect(): void {
		delete_option( 'grec_vk_credentials' );
		delete_option( 'grec_vk_owner_id' );
		delete_option( 'grec_vk_oauth_meta' );
		delete_option( 'grec_vk_last_publish' );
	}

	public static function save_token( string $token ): void {
		update_option(
			'grec_vk_credentials',
			GREC_Secrets::seal( array( 'token' => trim( $token ) ) ),
			false
		);
	}

	public static function save_owner_id( string $owner_id ): void {
		$owner_id = trim( $owner_id );
		if ( ! preg_match( '/^-?\d+$/', $owner_id ) ) {
			throw new InvalidArgumentException( 'VK owner ID must be numeric. Community owner IDs are negative, for example -123456789.' );
		}
		update_option( 'grec_vk_owner_id', $owner_id, false );
	}

	public static function owner_id(): string {
		return trim( (string) get_option( 'grec_vk_owner_id', '' ) );
	}

	public static function is_connected(): bool {
		$credentials = self::credentials();
		return ! empty( $credentials['token'] ) && '' !== self::owner_id();
	}

	private static function api( string $method, array $params = array() ): array {
		$credentials = self::credentials();
		if ( empty( $credentials['token'] ) ) {
			throw new RuntimeException( 'VK access token is not configured.' );
		}

		$params['access_token'] = (string) $credentials['token'];
		$params['v']            = self::API_VERSION;

		$response = wp_remote_post(
			'https://api.vk.com/method/' . rawurlencode( $method ),
			array(
				'timeout' => 60,
				'body'    => $params,
			)
		);

		if ( is_wp_error( $response ) ) {
			throw new RuntimeException( $response->get_error_message() );
		}

		$data = json_decode( wp_remote_retrieve_body( $response ), true );
		if ( ! is_array( $data ) ) {
			throw new RuntimeException( 'VK returned an invalid response.' );
		}
		if ( ! empty( $data['error'] ) ) {
			$code = isset( $data['error']['error_code'] ) ? (int) $data['error']['error_code'] : 0;
			$msg  = isset( $data['error']['error_msg'] ) ? (string) $data['error']['error_msg'] : 'Unknown VK API error';
			throw new RuntimeException( sprintf( 'VK API error %d: %s', $code, $msg ) );
		}

		return isset( $data['response'] ) ? (array) $data['response'] : array();
	}

	public static function test_connection(): array {
		$owner_id = self::owner_id();
		if ( '' === $owner_id ) {
			throw new RuntimeException( 'VK owner ID is not configured.' );
		}

		if ( 0 > (int) $owner_id ) {
			$group_id = abs( (int) $owner_id );
			$data     = self::api( 'groups.getById', array( 'group_ids' => (string) $group_id ) );
			$group    = isset( $data['groups'][0] ) ? $data['groups'][0] : ( $data[0] ?? array() );
			return array(
				'ok'       => true,
				'type'     => 'community',
				'owner_id' => $owner_id,
				'name'     => is_array( $group ) ? (string) ( $group['name'] ?? '' ) : '',
			);
		}

		$data = self::api( 'users.get', array( 'user_ids' => $owner_id ) );
		$user = $data[0] ?? array();
		return array(
			'ok'       => true,
			'type'     => 'user',
			'owner_id' => $owner_id,
			'name'     => is_array( $user ) ? trim( (string) ( $user['first_name'] ?? '' ) . ' ' . (string) ( $user['last_name'] ?? '' ) ) : '',
		);
	}

	private static function download_temp( string $url ): string {
		if ( ! wp_http_validate_url( $url ) ) {
			throw new InvalidArgumentException( 'VK photo URL must be a valid public HTTP(S) URL.' );
		}

		require_once ABSPATH . 'wp-admin/includes/file.php';
		$tmp = download_url( $url, 60 );
		if ( is_wp_error( $tmp ) ) {
			throw new RuntimeException( 'Unable to download VK photo: ' . $tmp->get_error_message() );
		}
		return $tmp;
	}

	private static function upload_multipart( string $upload_url, string $path ): array {
		if ( ! function_exists( 'curl_init' ) || ! function_exists( 'curl_file_create' ) ) {
			throw new RuntimeException( 'The server cURL extension is required for VK photo uploads.' );
		}

		$mime = function_exists( 'mime_content_type' ) ? (string) mime_content_type( $path ) : 'image/jpeg';
		$file = curl_file_create( $path, $mime ?: 'image/jpeg', basename( $path ) );

		$ch = curl_init( $upload_url );
		curl_setopt_array(
			$ch,
			array(
				CURLOPT_POST           => true,
				CURLOPT_POSTFIELDS     => array( 'photo' => $file ),
				CURLOPT_RETURNTRANSFER => true,
				CURLOPT_CONNECTTIMEOUT => 20,
				CURLOPT_TIMEOUT        => 90,
			)
		);
		$raw  = curl_exec( $ch );
		$code = (int) curl_getinfo( $ch, CURLINFO_HTTP_CODE );
		$err  = curl_error( $ch );
		curl_close( $ch );

		if ( false === $raw || $code >= 300 ) {
			throw new RuntimeException( 'VK upload server rejected the photo. ' . ( $err ?: 'HTTP ' . $code ) );
		}

		$data = json_decode( (string) $raw, true );
		if ( ! is_array( $data ) || ! isset( $data['photo'], $data['server'], $data['hash'] ) ) {
			throw new RuntimeException( 'VK photo upload returned an invalid response.' );
		}
		return $data;
	}

	private static function upload_wall_photo( string $url ): string {
		$owner_id = (int) self::owner_id();
		$params   = array();
		if ( $owner_id < 0 ) {
			$params['group_id'] = abs( $owner_id );
		}

		$server     = self::api( 'photos.getWallUploadServer', $params );
		$upload_url = (string) ( $server['upload_url'] ?? '' );
		if ( '' === $upload_url ) {
			throw new RuntimeException( 'VK did not return a wall photo upload URL.' );
		}

		$tmp = self::download_temp( $url );
		try {
			$uploaded = self::upload_multipart( $upload_url, $tmp );
		} finally {
			@unlink( $tmp );
		}

		$save_params = array(
			'photo'  => (string) $uploaded['photo'],
			'server' => (string) $uploaded['server'],
			'hash'   => (string) $uploaded['hash'],
		);
		if ( $owner_id < 0 ) {
			$save_params['group_id'] = abs( $owner_id );
		} else {
			$save_params['user_id'] = $owner_id;
		}

		$saved = self::api( 'photos.saveWallPhoto', $save_params );
		$photo = $saved[0] ?? array();
		if ( ! is_array( $photo ) || ! isset( $photo['owner_id'], $photo['id'] ) ) {
			throw new RuntimeException( 'VK did not return the saved wall photo ID.' );
		}

		return 'photo' . (string) $photo['owner_id'] . '_' . (string) $photo['id'];
	}

	public static function publish( string $message = '', array $media = array(), string $link = '' ): array {
		$owner_id = self::owner_id();
		if ( '' === $owner_id ) {
			throw new RuntimeException( 'VK owner ID is not configured.' );
		}

		$message = trim( wp_strip_all_tags( $message ) );
		$link    = esc_url_raw( $link );
		$photos  = array();

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
				throw new InvalidArgumentException( 'VK v0.5 currently accepts photo media in the WordPress publisher. Video publishing is handled in the next channel-media phase.' );
			}
			$photos[] = $url;
		}

		if ( count( $photos ) > self::MAX_PHOTOS ) {
			throw new InvalidArgumentException( 'VK publishing is limited to 10 photos per post in Engagement Core.' );
		}
		if ( '' === $message && empty( $photos ) && '' === $link ) {
			throw new InvalidArgumentException( 'A VK post needs text, a photo, or a link.' );
		}

		$attachments = array();
		foreach ( $photos as $photo_url ) {
			$attachments[] = self::upload_wall_photo( $photo_url );
		}
		if ( '' !== $link ) {
			$attachments[] = $link;
		}

		$params = array(
			'owner_id' => $owner_id,
			'message'  => $message,
		);
		if ( (int) $owner_id < 0 ) {
			$params['from_group'] = 1;
		}
		if ( ! empty( $attachments ) ) {
			$params['attachments'] = implode( ',', $attachments );
		}

		$result = self::api( 'wall.post', $params );
		$post_id = isset( $result['post_id'] ) ? (int) $result['post_id'] : null;

		update_option(
			'grec_vk_last_publish',
			array(
				'at'          => time(),
				'owner_id'    => $owner_id,
				'post_id'     => $post_id,
				'photo_count' => count( $photos ),
				'link'        => $link,
			),
			false
		);

		return array(
			'ok'          => true,
			'owner_id'    => $owner_id,
			'post_id'     => $post_id,
			'photo_count' => count( $photos ),
			'link'        => $link,
		);
	}

	public static function status(): array {
		$app = self::oauth_app();
		$meta = get_option( 'grec_vk_oauth_meta', array() );
		return array(
			'connected'       => self::is_connected(),
			'owner_id'        => self::owner_id(),
			'token_saved'     => ! empty( self::credentials()['token'] ),
			'oauth_configured'=> self::oauth_app_configured(),
			'app_id'          => isset( $app['client_id'] ) ? (string) $app['client_id'] : '',
			'connected_user_id' => is_array( $meta ) ? (int) ( $meta['user_id'] ?? 0 ) : 0,
			'connected_at'    => is_array( $meta ) ? (int) ( $meta['connected_at'] ?? 0 ) : 0,
			'last_publish'    => get_option( 'grec_vk_last_publish', array() ),
		);
	}
}
