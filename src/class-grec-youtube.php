<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class GREC_YouTube {
	private const API = 'https://www.googleapis.com/youtube/v3';
	private const OAUTH_AUTH = 'https://accounts.google.com/o/oauth2/v2/auth';
	private const OAUTH_TOKEN = 'https://oauth2.googleapis.com/token';
	private const SCOPE = 'https://www.googleapis.com/auth/youtube.force-ssl';

	public function redirect_uri(): string {
		return admin_url( 'admin-post.php?action=grec_youtube_oauth' );
	}

	public function credentials(): array {
		$client_id = trim( (string) get_option( 'grec_youtube_client_id', '' ) );
		$sealed = (string) get_option( 'grec_youtube_client_secret', '' );
		$secret = GREC_Secrets::open( $sealed );
		return array(
			'client_id' => $client_id,
			'client_secret' => isset( $secret['client_secret'] ) ? (string) $secret['client_secret'] : '',
		);
	}

	public function save_credentials( string $client_id, string $client_secret ): void {
		update_option( 'grec_youtube_client_id', sanitize_text_field( $client_id ), false );
		if ( '' !== trim( $client_secret ) ) {
			update_option( 'grec_youtube_client_secret', GREC_Secrets::seal( array( 'client_secret' => trim( $client_secret ) ) ), false );
		}
	}

	public function token(): array {
		return GREC_Secrets::open( (string) get_option( 'grec_youtube_token', '' ) );
	}

	private function save_token( array $token ): void {
		if ( isset( $token['expires_in'] ) ) {
			$token['expires_at'] = time() + max( 60, absint( $token['expires_in'] ) - 60 );
		}
		$current = $this->token();
		if ( empty( $token['refresh_token'] ) && ! empty( $current['refresh_token'] ) ) {
			$token['refresh_token'] = $current['refresh_token'];
		}
		update_option( 'grec_youtube_token', GREC_Secrets::seal( $token ), false );
	}

	public function disconnect(): void {
		delete_option( 'grec_youtube_token' );
		delete_option( 'grec_youtube_connected_channel_id' );
		delete_option( 'grec_youtube_connected_channel_title' );
	}

	public function is_connected(): bool {
		$token = $this->token();
		return ! empty( $token['access_token'] ) || ! empty( $token['refresh_token'] );
	}

	public function authorization_url(): string {
		$creds = $this->credentials();
		if ( empty( $creds['client_id'] ) ) {
			return '';
		}

		return add_query_arg(
			array(
				'client_id' => $creds['client_id'],
				'redirect_uri' => $this->redirect_uri(),
				'response_type' => 'code',
				'scope' => self::SCOPE,
				'access_type' => 'offline',
				'include_granted_scopes' => 'true',
				'prompt' => 'consent',
				'state' => wp_create_nonce( 'grec-youtube-oauth' ),
			),
			self::OAUTH_AUTH
		);
	}

	public function exchange_code( string $code ): array {
		$creds = $this->credentials();
		if ( empty( $creds['client_id'] ) || empty( $creds['client_secret'] ) ) {
			throw new RuntimeException( 'Google OAuth credentials are incomplete.' );
		}

		$response = wp_remote_post(
			self::OAUTH_TOKEN,
			array(
				'timeout' => 20,
				'body' => array(
					'code' => $code,
					'client_id' => $creds['client_id'],
					'client_secret' => $creds['client_secret'],
					'redirect_uri' => $this->redirect_uri(),
					'grant_type' => 'authorization_code',
				),
			)
		);
		$data = $this->decode_response( $response );
		$this->save_token( $data );
		$this->capture_connected_channel();
		return $data;
	}

	private function access_token(): string {
		$token = $this->token();
		if ( empty( $token['access_token'] ) || ( ! empty( $token['expires_at'] ) && time() >= absint( $token['expires_at'] ) ) ) {
			$token = $this->refresh_access_token( $token );
		}
		return (string) ( $token['access_token'] ?? '' );
	}

	private function refresh_access_token( array $token ): array {
		if ( empty( $token['refresh_token'] ) ) {
			throw new RuntimeException( 'YouTube authorization expired. Reconnect the channel.' );
		}
		$creds = $this->credentials();
		$response = wp_remote_post(
			self::OAUTH_TOKEN,
			array(
				'timeout' => 20,
				'body' => array(
					'client_id' => $creds['client_id'],
					'client_secret' => $creds['client_secret'],
					'refresh_token' => $token['refresh_token'],
					'grant_type' => 'refresh_token',
				),
			)
		);
		$fresh = $this->decode_response( $response );
		$fresh['refresh_token'] = $token['refresh_token'];
		$this->save_token( $fresh );
		return $this->token();
	}

	private function headers(): array {
		$token = $this->access_token();
		if ( '' === $token ) {
			throw new RuntimeException( 'YouTube is not connected.' );
		}
		return array(
			'Authorization' => 'Bearer ' . $token,
			'Accept' => 'application/json',
		);
	}

	private function decode_response( $response ): array {
		if ( is_wp_error( $response ) ) {
			throw new RuntimeException( $response->get_error_message() );
		}
		$code = wp_remote_retrieve_response_code( $response );
		$body = wp_remote_retrieve_body( $response );
		$data = json_decode( $body, true );
		if ( $code < 200 || $code >= 300 ) {
			$message = 'YouTube API request failed.';
			if ( is_array( $data ) ) {
				$message = $data['error']['message'] ?? $data['error_description'] ?? $message;
			}
			throw new RuntimeException( sanitize_text_field( $message ) );
		}
		return is_array( $data ) ? $data : array();
	}

	private function get( string $path, array $query ): array {
		$url = add_query_arg( $query, self::API . $path );
		return $this->decode_response(
			wp_remote_get(
				$url,
				array(
					'timeout' => 20,
					'headers' => $this->headers(),
				)
			)
		);
	}

	private function post( string $path, array $query = array(), ?array $json = null ): array {
		$url = add_query_arg( $query, self::API . $path );
		$args = array(
			'timeout' => 20,
			'headers' => $this->headers(),
		);
		if ( null !== $json ) {
			$args['headers']['Content-Type'] = 'application/json';
			$args['body'] = wp_json_encode( $json );
		}
		return $this->decode_response( wp_remote_post( $url, $args ) );
	}

	public function capture_connected_channel(): array {
		$data = $this->get(
			'/channels',
			array(
				'part' => 'snippet',
				'mine' => 'true',
				'maxResults' => 10,
			)
		);
		$expected = trim( (string) get_option( 'grec_youtube_channel_id', '' ) );
		$chosen = array();

		foreach ( (array) ( $data['items'] ?? array() ) as $item ) {
			if ( empty( $chosen ) ) {
				$chosen = $item;
			}
			if ( $expected && ( $item['id'] ?? '' ) === $expected ) {
				$chosen = $item;
				break;
			}
		}

		if ( empty( $chosen['id'] ) ) {
			throw new RuntimeException( 'No YouTube channel was returned for this Google account.' );
		}

		if ( $expected && $chosen['id'] !== $expected ) {
			throw new RuntimeException( 'The connected Google account does not expose the configured YouTube channel.' );
		}

		update_option( 'grec_youtube_connected_channel_id', sanitize_text_field( $chosen['id'] ), false );
		update_option( 'grec_youtube_connected_channel_title', sanitize_text_field( $chosen['snippet']['title'] ?? '' ), false );
		return $chosen;
	}

	public function sync_recent_comments(): int {
		$channel_id = trim( (string) get_option( 'grec_youtube_channel_id', '' ) );
		if ( '' === $channel_id ) {
			throw new RuntimeException( 'YouTube channel ID is not configured.' );
		}

		$count = 0;
		$page = '';
		for ( $i = 0; $i < 3; $i++ ) {
			$query = array(
				'part' => 'snippet,replies',
				'allThreadsRelatedToChannelId' => $channel_id,
				'maxResults' => 100,
				'order' => 'time',
				'textFormat' => 'plainText',
			);
			if ( $page ) {
				$query['pageToken'] = $page;
			}
			$data = $this->get( '/commentThreads', $query );
			foreach ( (array) ( $data['items'] ?? array() ) as $thread ) {
				GREC_Repository::upsert_youtube_thread( $thread );
				$count++;
			}
			$page = (string) ( $data['nextPageToken'] ?? '' );
			if ( '' === $page ) {
				break;
			}
		}

		update_option( 'grec_last_sync_at', current_time( 'mysql', true ), false );
		return $count;
	}

	public function reply( string $parent_id, string $text ): array {
		$text = trim( wp_strip_all_tags( $text ) );
		if ( '' === $parent_id ) {
			throw new InvalidArgumentException( 'Comment ID is required.' );
		}
		if ( '' === $text ) {
			throw new InvalidArgumentException( 'Reply cannot be empty.' );
		}

		$data = $this->post(
			'/comments',
			array( 'part' => 'snippet' ),
			array(
				'snippet' => array(
					'parentId' => $parent_id,
					'textOriginal' => $text,
				),
			)
		);
		GREC_Repository::mark_replied( $parent_id, (string) ( $data['id'] ?? '' ), $text );
		return $data;
	}

	public function moderate( string $comment_id, string $status, bool $ban_author = false ): void {
		$allowed = array( 'published', 'heldForReview', 'rejected' );
		if ( '' === $comment_id ) {
			throw new InvalidArgumentException( 'Comment ID is required.' );
		}
		if ( ! in_array( $status, $allowed, true ) ) {
			throw new InvalidArgumentException( 'Unsupported moderation status.' );
		}

		$query = array(
			'id' => $comment_id,
			'moderationStatus' => $status,
		);
		if ( 'rejected' === $status && $ban_author ) {
			$query['banAuthor'] = 'true';
		}
		$this->post( '/comments/setModerationStatus', $query, null );
		GREC_Repository::mark_status( $comment_id, $status );
	}
}
