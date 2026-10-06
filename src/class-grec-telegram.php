<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_Telegram {
	public static function credentials(): array {
		return GREC_Secrets::open( (string) get_option( 'grec_telegram_credentials', '' ) );
	}

	public static function save_token( string $token ): void {
		update_option( 'grec_telegram_credentials', GREC_Secrets::seal( array( 'token' => trim( $token ) ) ), false );
	}

	public static function normalize_chat_id( string $chat_id ): string {
		$chat_id = trim( $chat_id );
		if ( preg_match( '/^-?\\d+$/', $chat_id ) ) {
			return $chat_id;
		}
		if ( preg_match( '/^@[A-Za-z0-9_]{5,}$/', $chat_id ) ) {
			return $chat_id;
		}
		return '';
	}

	private static function destination_key( string $name, string $chat_id, array $used ): string {
		$base = sanitize_key( $name );
		if ( '' === $base ) {
			$base = 'telegram-' . substr( sha1( $chat_id ), 0, 8 );
		}
		$key = $base;
		$i   = 2;
		while ( isset( $used[ $key ] ) ) {
			$key = $base . '-' . $i;
			$i++;
		}
		return $key;
	}

	public static function destinations(): array {
		$stored = get_option( 'grec_telegram_destinations', array() );
		if ( is_array( $stored ) && ! empty( $stored ) ) {
			return array_values( $stored );
		}

		$legacy = self::normalize_chat_id( (string) get_option( 'grec_telegram_chat_id', '' ) );
		if ( '' === $legacy ) {
			return array();
		}

		return array(
			array(
				'key'     => 'primary',
				'name'    => 'Primary',
				'chat_id' => $legacy,
				'level'   => 'primary',
				'enabled' => true,
			),
		);
	}

	public static function save_destinations( array $rows ): array {
		$clean = array();
		$used  = array();

		foreach ( $rows as $row ) {
			if ( ! is_array( $row ) ) {
				continue;
			}

			$chat_id = self::normalize_chat_id( (string) ( $row['chat_id'] ?? '' ) );
			$name    = sanitize_text_field( (string) ( $row['name'] ?? '' ) );

			if ( '' === $chat_id && '' === $name ) {
				continue;
			}
			if ( '' === $chat_id ) {
				throw new InvalidArgumentException( sprintf( 'Invalid Telegram chat ID for "%s". Use @channel or the full numeric ID such as -1001234567890.', $name ?: 'destination' ) );
			}

			$level = sanitize_key( (string) ( $row['level'] ?? 'primary' ) );
			if ( '' === $level ) {
				$level = 'primary';
			}
			if ( '' === $name ) {
				$name = $chat_id;
			}

			$key          = self::destination_key( $name, $chat_id, $used );
			$used[ $key ] = true;
			$clean[]      = array(
				'key'     => $key,
				'name'    => $name,
				'chat_id' => $chat_id,
				'level'   => $level,
				'enabled' => ! empty( $row['enabled'] ),
			);
		}

		update_option( 'grec_telegram_destinations', $clean, false );

		$first_enabled = '';
		foreach ( $clean as $destination ) {
			if ( ! empty( $destination['enabled'] ) ) {
				$first_enabled = (string) $destination['chat_id'];
				break;
			}
		}
		update_option( 'grec_telegram_chat_id', $first_enabled, false );

		return $clean;
	}

	public static function enabled_destinations( array $targets = array(), array $levels = array() ): array {
		$targets = array_values( array_filter( array_map( 'strval', $targets ) ) );
		$levels  = array_values( array_filter( array_map( 'sanitize_key', $levels ) ) );

		return array_values(
			array_filter(
				self::destinations(),
				static function ( $destination ) use ( $targets, $levels ) {
					if ( empty( $destination['enabled'] ) ) {
						return false;
					}
					if ( ! empty( $targets ) && ! in_array( (string) $destination['key'], $targets, true ) && ! in_array( (string) $destination['chat_id'], $targets, true ) ) {
						return false;
					}
					if ( ! empty( $levels ) && ! in_array( (string) $destination['level'], $levels, true ) ) {
						return false;
					}
					return true;
				}
			)
		);
	}

	public static function is_connected(): bool {
		$c = self::credentials();
		return ! empty( $c['token'] ) && ! empty( self::enabled_destinations() );
	}

	private static function send_one( string $token, array $destination, string $text, string $media_url = '' ): array {
		$method = $media_url ? 'sendVideo' : 'sendMessage';
		$body   = array( 'chat_id' => (string) $destination['chat_id'] );

		if ( $media_url ) {
			$body['video']              = $media_url;
			$body['caption']            = mb_substr( $text, 0, 1024 );
			$body['supports_streaming'] = 'true';
		} else {
			$body['text'] = mb_substr( $text, 0, 4096 );
		}

		$response = wp_remote_post(
			'https://api.telegram.org/bot' . rawurlencode( $token ) . '/' . $method,
			array(
				'timeout' => 60,
				'body'    => $body,
			)
		);

		if ( is_wp_error( $response ) ) {
			throw new RuntimeException( $response->get_error_message() );
		}

		$data        = json_decode( wp_remote_retrieve_body( $response ), true );
		$status_code = wp_remote_retrieve_response_code( $response );

		if ( $status_code >= 300 || empty( $data['ok'] ) ) {
			$description = is_array( $data ) && ! empty( $data['description'] ) ? (string) $data['description'] : 'Unknown Telegram API error';
			throw new RuntimeException( $description );
		}

		return $data;
	}

	public static function send( string $text, string $media_url = '', array $targets = array(), array $levels = array() ): array {
		$credentials  = self::credentials();
		$destinations = self::enabled_destinations( $targets, $levels );

		if ( empty( $credentials['token'] ) ) {
			throw new RuntimeException( 'Telegram bot token is not configured.' );
		}
		if ( empty( $destinations ) ) {
			throw new RuntimeException( 'No enabled Telegram destinations matched this publish.' );
		}

		$sent    = array();
		$failed  = array();

		foreach ( $destinations as $destination ) {
			try {
				$data   = self::send_one( (string) $credentials['token'], $destination, $text, $media_url );
				$sent[] = array(
					'key'        => $destination['key'],
					'name'       => $destination['name'],
					'chat_id'    => $destination['chat_id'],
					'level'      => $destination['level'],
					'message_id' => $data['result']['message_id'] ?? null,
				);
			} catch ( Throwable $e ) {
				$failed[] = array(
					'key'     => $destination['key'],
					'name'    => $destination['name'],
					'chat_id' => $destination['chat_id'],
					'level'   => $destination['level'],
					'error'   => $e->getMessage(),
				);
			}
		}

		$result = array(
			'ok'     => empty( $failed ),
			'sent'   => $sent,
			'failed' => $failed,
		);

		update_option(
			'grec_telegram_last_publish',
			array(
				'at'           => time(),
				'sent_count'   => count( $sent ),
				'failed_count' => count( $failed ),
				'sent'         => $sent,
				'failed'       => $failed,
			),
			false
		);

		if ( empty( $sent ) ) {
			$errors = array_map(
				static function ( $failure ) {
					return $failure['name'] . ': ' . $failure['error'];
				},
				$failed
			);
			throw new RuntimeException( 'Telegram publish failed for all destinations. ' . implode( ' | ', $errors ) );
		}

		return $result;
	}
}
