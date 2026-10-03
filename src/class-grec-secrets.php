<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class GREC_Secrets {
	private const CIPHER = 'aes-256-gcm';

	private static function key(): string {
		$material = ( defined( 'AUTH_KEY' ) ? AUTH_KEY : '' ) . '|' . ( defined( 'SECURE_AUTH_KEY' ) ? SECURE_AUTH_KEY : '' );
		return hash( 'sha256', $material, true );
	}

	public static function seal( array $value ): string {
		if ( ! function_exists( 'openssl_encrypt' ) ) {
			throw new RuntimeException( 'OpenSSL is required to encrypt OAuth credentials.' );
		}
		$iv = random_bytes( 12 );
		$tag = '';
		$plain = wp_json_encode( $value );
		$cipher = openssl_encrypt( $plain, self::CIPHER, self::key(), OPENSSL_RAW_DATA, $iv, $tag );
		if ( false === $cipher ) {
			throw new RuntimeException( 'Unable to encrypt OAuth credentials.' );
		}
		return base64_encode( wp_json_encode( array(
			'v' => 1,
			'iv' => base64_encode( $iv ),
			'tag' => base64_encode( $tag ),
			'data' => base64_encode( $cipher ),
		) ) );
	}

	public static function open( string $sealed ): array {
		if ( '' === $sealed ) {
			return array();
		}
		$payload = json_decode( base64_decode( $sealed, true ) ?: '', true );
		if ( ! is_array( $payload ) || empty( $payload['iv'] ) || empty( $payload['tag'] ) || empty( $payload['data'] ) ) {
			return array();
		}
		$plain = openssl_decrypt(
			base64_decode( $payload['data'], true ),
			self::CIPHER,
			self::key(),
			OPENSSL_RAW_DATA,
			base64_decode( $payload['iv'], true ),
			base64_decode( $payload['tag'], true )
		);
		if ( false === $plain ) {
			return array();
		}
		$data = json_decode( $plain, true );
		return is_array( $data ) ? $data : array();
	}
}
