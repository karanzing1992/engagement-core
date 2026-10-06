<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_Telegram {
	private const MEDIA_TYPES = array( 'photo', 'video', 'animation', 'audio', 'document' );

	public static function credentials(): array {
		return GREC_Secrets::open( (string) get_option( 'grec_telegram_credentials', '' ) );
	}

	public static function save_token( string $token ): void {
		update_option( 'grec_telegram_credentials', GREC_Secrets::seal( array( 'token' => trim( $token ) ) ), false );
	}

	public static function media_types(): array {
		return self::MEDIA_TYPES;
	}

	public static function sanitize_message_html( string $text ): string {
		$allowed = array(
			'b'           => array(),
			'strong'      => array(),
			'i'           => array(),
			'em'          => array(),
			'u'           => array(),
			'ins'         => array(),
			's'           => array(),
			'strike'      => array(),
			'del'         => array(),
			'span'        => array( 'class' => true ),
			'tg-spoiler'  => array(),
			'a'           => array( 'href' => true ),
			'code'        => array(),
			'pre'         => array(),
			'blockquote'  => array( 'expandable' => true ),
			'tg-emoji'    => array( 'emoji-id' => true ),
		);
		return trim( (string) wp_kses( $text, $allowed ) );
	}

	private static function text_length( string $text ): int {
		return mb_strlen( html_entity_decode( wp_strip_all_tags( $text ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
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

	public static function normalize_media( array $media ): array {
		$clean = array();

		foreach ( $media as $item ) {
			if ( ! is_array( $item ) ) {
				continue;
			}
			$type = sanitize_key( (string) ( $item['type'] ?? '' ) );
			$url  = esc_url_raw( (string) ( $item['url'] ?? '' ) );
			$name = sanitize_text_field( (string) ( $item['name'] ?? '' ) );

			if ( '' === $url && '' === $type ) {
				continue;
			}
			if ( ! in_array( $type, self::MEDIA_TYPES, true ) ) {
				throw new InvalidArgumentException( 'Unsupported Telegram media type: ' . ( $type ?: 'unknown' ) . '.' );
			}
			if ( '' === $url || ! wp_http_validate_url( $url ) ) {
				throw new InvalidArgumentException( 'Every Telegram media item needs a valid public HTTPS/HTTP URL.' );
			}
			$clean[] = array(
				'type' => $type,
				'url'  => $url,
				'name' => $name,
			);
		}

		if ( count( $clean ) > 10 ) {
			throw new InvalidArgumentException( 'Telegram albums support a maximum of 10 media items.' );
		}

		if ( count( $clean ) > 1 ) {
			$types = array_values( array_unique( array_column( $clean, 'type' ) ) );
			if ( in_array( 'animation', $types, true ) ) {
				throw new InvalidArgumentException( 'GIF/animation cannot be included in a Telegram media album. Send it as a single item.' );
			}
			if ( in_array( 'audio', $types, true ) && array( 'audio' ) !== $types ) {
				throw new InvalidArgumentException( 'Telegram audio albums can contain audio files only.' );
			}
			if ( in_array( 'document', $types, true ) && array( 'document' ) !== $types ) {
				throw new InvalidArgumentException( 'Telegram document albums can contain documents only.' );
			}
			foreach ( $types as $type ) {
				if ( ! in_array( $type, array( 'photo', 'video', 'audio', 'document' ), true ) ) {
					throw new InvalidArgumentException( 'Unsupported Telegram album media combination.' );
				}
			}
		}

		return $clean;
	}

	private static function api_post( string $token, string $method, array $body ): array {
		$response = wp_remote_post(
			'https://api.telegram.org/bot' . rawurlencode( $token ) . '/' . $method,
			array(
				'timeout' => 90,
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

	private static function send_text( string $token, string $chat_id, string $text ): array {
		if ( '' === $text ) {
			return array();
		}
		if ( self::text_length( $text ) > 4096 ) {
			throw new InvalidArgumentException( 'Telegram text messages are limited to 4096 visible characters per message.' );
		}
		return self::api_post(
			$token,
			'sendMessage',
			array(
				'chat_id'    => $chat_id,
				'text'       => $text,
				'parse_mode' => 'HTML',
			)
		);
	}

	private static function single_method( string $type ): array {
		$map = array(
			'photo'     => array( 'sendPhoto', 'photo' ),
			'video'     => array( 'sendVideo', 'video' ),
			'animation' => array( 'sendAnimation', 'animation' ),
			'audio'     => array( 'sendAudio', 'audio' ),
			'document'  => array( 'sendDocument', 'document' ),
		);
		return $map[ $type ];
	}

	private static function send_single_media( string $token, string $chat_id, array $media, string $text ): array {
		list( $method, $field ) = self::single_method( $media['type'] );
		$body                   = array(
			'chat_id' => $chat_id,
			$field     => $media['url'],
		);
		$caption_fits = '' !== $text && self::text_length( $text ) <= 1024;

		if ( $caption_fits ) {
			$body['caption']    = $text;
			$body['parse_mode'] = 'HTML';
		}
		if ( 'video' === $media['type'] ) {
			$body['supports_streaming'] = 'true';
		}

		$data        = self::api_post( $token, $method, $body );
		$message_ids = array( $data['result']['message_id'] ?? null );

		if ( '' !== $text && ! $caption_fits ) {
			$text_data      = self::send_text( $token, $chat_id, $text );
			$message_ids[] = $text_data['result']['message_id'] ?? null;
		}

		return array(
			'message_ids' => array_values( array_filter( $message_ids, static fn( $id ) => null !== $id ) ),
			'mode'        => 'single-' . $media['type'],
		);
	}

	private static function send_album( string $token, string $chat_id, array $media, string $text ): array {
		$caption_fits = '' !== $text && self::text_length( $text ) <= 1024;
		$input_media  = array();

		foreach ( $media as $index => $item ) {
			$entry = array(
				'type'  => $item['type'],
				'media' => $item['url'],
			);
			if ( 0 === $index && $caption_fits ) {
				$entry['caption']    = $text;
				$entry['parse_mode'] = 'HTML';
			}
			if ( 'video' === $item['type'] ) {
				$entry['supports_streaming'] = true;
			}
			$input_media[] = $entry;
		}

		$data = self::api_post(
			$token,
			'sendMediaGroup',
			array(
				'chat_id' => $chat_id,
				'media'   => wp_json_encode( $input_media ),
			)
		);

		$message_ids = array();
		foreach ( (array) ( $data['result'] ?? array() ) as $message ) {
			if ( isset( $message['message_id'] ) ) {
				$message_ids[] = $message['message_id'];
			}
		}

		if ( '' !== $text && ! $caption_fits ) {
			$text_data     = self::send_text( $token, $chat_id, $text );
			$message_ids[] = $text_data['result']['message_id'] ?? null;
		}

		return array(
			'message_ids' => array_values( array_filter( $message_ids, static fn( $id ) => null !== $id ) ),
			'mode'        => 'album',
		);
	}

	private static function send_post_one( string $token, array $destination, string $text, array $media ): array {
		$chat_id = (string) $destination['chat_id'];

		if ( empty( $media ) ) {
			if ( '' === $text ) {
				throw new InvalidArgumentException( 'A Telegram post needs text or media.' );
			}
			$data = self::send_text( $token, $chat_id, $text );
			return array(
				'message_ids' => array( $data['result']['message_id'] ?? null ),
				'mode'        => 'text',
			);
		}

		if ( 1 === count( $media ) ) {
			return self::send_single_media( $token, $chat_id, $media[0], $text );
		}

		return self::send_album( $token, $chat_id, $media, $text );
	}

	public static function send_post( string $text = '', array $media = array(), array $targets = array(), array $levels = array() ): array {
		$credentials  = self::credentials();
		$destinations = self::enabled_destinations( $targets, $levels );
		$text         = self::sanitize_message_html( $text );
		$media        = self::normalize_media( $media );

		if ( empty( $credentials['token'] ) ) {
			throw new RuntimeException( 'Telegram bot token is not configured.' );
		}
		if ( empty( $destinations ) ) {
			throw new RuntimeException( 'No enabled Telegram destinations matched this publish.' );
		}
		if ( '' === $text && empty( $media ) ) {
			throw new InvalidArgumentException( 'A Telegram post needs text or media.' );
		}

		$sent   = array();
		$failed = array();

		foreach ( $destinations as $destination ) {
			try {
				$result = self::send_post_one( (string) $credentials['token'], $destination, $text, $media );
				$sent[] = array(
					'key'         => $destination['key'],
					'name'        => $destination['name'],
					'chat_id'     => $destination['chat_id'],
					'level'       => $destination['level'],
					'mode'        => $result['mode'],
					'message_ids' => $result['message_ids'],
					'message_id'  => $result['message_ids'][0] ?? null,
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
				'media_count'  => count( $media ),
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

	public static function send( string $text, string $media_url = '', array $targets = array(), array $levels = array() ): array {
		$media = array();
		if ( '' !== $media_url ) {
			$media[] = array(
				'type' => 'video',
				'url'  => $media_url,
				'name' => '',
			);
		}
		return self::send_post( $text, $media, $targets, $levels );
	}
}
