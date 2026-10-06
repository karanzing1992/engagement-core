<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_Snapchat {
	private const MAX_QUEUE = 50;
	private const CLAIM_TTL = 600;

	public static function client_id(): string {
		return trim( (string) get_option( 'grec_snapchat_client_id', '' ) );
	}

	public static function save_client_id( string $client_id ): void {
		update_option( 'grec_snapchat_client_id', sanitize_text_field( trim( $client_id ) ), false );
	}

	public static function device_key(): string {
		$data = GREC_Secrets::open( (string) get_option( 'grec_snapchat_device_key', '' ) );
		return isset( $data['key'] ) ? (string) $data['key'] : '';
	}

	public static function save_device_key( string $key ): void {
		$key = trim( $key );
		if ( strlen( $key ) < 24 ) {
			throw new InvalidArgumentException( 'Snapchat device key must be at least 24 characters.' );
		}
		update_option( 'grec_snapchat_device_key', GREC_Secrets::seal( array( 'key' => $key ) ), false );
	}

	public static function ensure_device_key(): string {
		$key = self::device_key();
		if ( '' !== $key ) {
			return $key;
		}
		$key = bin2hex( random_bytes( 24 ) );
		self::save_device_key( $key );
		return $key;
	}

	public static function is_configured(): bool {
		return '' !== self::client_id() && '' !== self::device_key();
	}

	private static function queue(): array {
		$queue = get_option( 'grec_snapchat_handoffs', array() );
		return is_array( $queue ) ? array_values( $queue ) : array();
	}

	private static function save_queue( array $queue ): void {
		$queue = array_slice( array_values( $queue ), -self::MAX_QUEUE );
		update_option( 'grec_snapchat_handoffs', $queue, false );
	}

	private static function id(): string {
		return wp_generate_uuid4();
	}

	public static function queue_handoff( string $caption, string $media_url, string $media_type ): array {
		$caption    = sanitize_textarea_field( $caption );
		$media_url  = esc_url_raw( $media_url );
		$media_type = sanitize_key( $media_type );

		if ( ! in_array( $media_type, array( 'image', 'video' ), true ) ) {
			throw new InvalidArgumentException( 'Snapchat media type must be image or video.' );
		}
		if ( '' === $media_url || ! wp_http_validate_url( $media_url ) ) {
			throw new InvalidArgumentException( 'Snapchat needs a valid public media URL.' );
		}

		$task = array(
			'id'         => self::id(),
			'status'     => 'pending',
			'caption'    => $caption,
			'media_url'  => $media_url,
			'media_type' => $media_type,
			'created_at' => time(),
			'claimed_at' => null,
			'finished_at'=> null,
			'error'      => '',
		);

		$queue   = self::queue();
		$queue[] = $task;
		self::save_queue( $queue );
		return $task;
	}

	private static function release_stale_claims( array $queue ): array {
		$now = time();
		foreach ( $queue as &$task ) {
			if ( 'claimed' === ( $task['status'] ?? '' )
				&& ! empty( $task['claimed_at'] )
				&& $now - (int) $task['claimed_at'] > self::CLAIM_TTL ) {
				$task['status']     = 'pending';
				$task['claimed_at'] = null;
			}
		}
		unset( $task );
		return $queue;
	}

	public static function claim_next(): ?array {
		$queue = self::release_stale_claims( self::queue() );

		foreach ( $queue as $index => $task ) {
			if ( 'pending' !== ( $task['status'] ?? '' ) ) {
				continue;
			}
			$queue[ $index ]['status']     = 'claimed';
			$queue[ $index ]['claimed_at'] = time();
			self::save_queue( $queue );

			return array(
				'id'         => $queue[ $index ]['id'],
				'caption'    => $queue[ $index ]['caption'],
				'media_url'  => $queue[ $index ]['media_url'],
				'media_type' => $queue[ $index ]['media_type'],
				'client_id'  => self::client_id(),
				'mode'       => 'creative-kit-lite-preview',
			);
		}

		self::save_queue( $queue );
		return null;
	}

	public static function complete( string $id, string $status, string $error = '' ): array {
		$status = sanitize_key( $status );
		if ( ! in_array( $status, array( 'opened', 'failed', 'cancelled' ), true ) ) {
			throw new InvalidArgumentException( 'Snapchat completion status must be opened, failed, or cancelled.' );
		}

		$queue = self::queue();
		foreach ( $queue as $index => $task ) {
			if ( (string) ( $task['id'] ?? '' ) !== $id ) {
				continue;
			}
			$queue[ $index ]['status']      = $status;
			$queue[ $index ]['finished_at'] = time();
			$queue[ $index ]['error']       = sanitize_text_field( $error );
			self::save_queue( $queue );
			return $queue[ $index ];
		}

		throw new RuntimeException( 'Snapchat handoff task was not found.' );
	}

	public static function recent( int $limit = 20 ): array {
		$queue = array_reverse( self::queue() );
		return array_slice( $queue, 0, max( 1, min( 50, $limit ) ) );
	}

	public static function pending_count(): int {
		$count = 0;
		foreach ( self::queue() as $task ) {
			if ( in_array( (string) ( $task['status'] ?? '' ), array( 'pending', 'claimed' ), true ) ) {
				$count++;
			}
		}
		return $count;
	}

	public static function status(): array {
		return array(
			'configured'      => self::is_configured(),
			'client_id_saved' => '' !== self::client_id(),
			'device_key_saved'=> '' !== self::device_key(),
			'mode'            => 'creative-kit-lite-preview',
			'pending_count'   => self::pending_count(),
			'requires_device_confirmation' => true,
			'recent'          => self::recent( 10 ),
		);
	}
}
