<?php
defined( 'ABSPATH' ) || exit;

/**
 * Bounded single-page cache diagnostics and invalidation for WP Control.
 *
 * Only published, publicly queryable WordPress content is eligible. The caller
 * never supplies a URL; permalink and host are resolved locally to avoid SSRF.
 * All methods require the administrator capability and the existing WP Control
 * OAuth + paired-site checks when invoked through the gateway.
 */
final class GREC_Cache_Tools {
	private static function target( $input ) {
		$id   = is_array( $input ) ? absint( $input['post_id'] ?? 0 ) : 0;
		$post = $id ? get_post( $id ) : null;
		$type = $post ? get_post_type_object( $post->post_type ) : null;

		if ( ! $post || 'publish' !== $post->post_status || ! $type || ! $type->public ||
			( 'page' !== $post->post_type && ! $type->publicly_queryable ) ) {
			return new WP_Error( 'wp_control_invalid_cache_target', 'Choose an existing published public post or page.', array( 'status' => 400 ) );
		}
		$url = get_permalink( $id );
		$origin = wp_parse_url( home_url( '/' ) );
		$target = is_string( $url ) ? wp_parse_url( $url ) : false;
		if ( ! is_array( $origin ) || ! is_array( $target ) ||
			( $target['scheme'] ?? '' ) !== 'https' ||
			strtolower( (string) ( $target['host'] ?? '' ) ) !== strtolower( (string) ( $origin['host'] ?? '' ) ) ||
			( $target['port'] ?? 443 ) !== ( $origin['port'] ?? 443 ) ||
			! empty( $target['user'] ) || ! empty( $target['pass'] ) ||
			! empty( $target['query'] ) || ! empty( $target['fragment'] ) ) {
			return new WP_Error( 'wp_control_cache_url_rejected', 'The public permalink must be a plain same-site HTTPS URL.', array( 'status' => 400 ) );
		}
		return array( 'post_id' => $id, 'url' => $url, 'post_type' => $post->post_type );
	}

	private static function litespeed_available(): bool {
		return defined( 'LSCWP_V' ) || has_action( 'litespeed_purge_url' ) || has_action( 'litespeed_purge_post' );
	}

	private static function probe( string $url, string $expected ): array {
		$response = wp_remote_get( $url, array(
			'timeout' => 12,
			'redirection' => 0,
			'limit_response_size' => 262144,
			'reject_unsafe_urls' => true,
			'cookies' => array(),
			'headers' => array( 'Accept' => 'text/html' ),
			'user-agent' => 'WPControl-Cache-Check/0.1',
		) );
		if ( is_wp_error( $response ) ) {
			return array( 'ok' => false, 'error' => sanitize_key( $response->get_error_code() ) );
		}
		$headers = array();
		foreach ( array( 'age', 'cache-control', 'cf-cache-status', 'etag', 'last-modified', 'server', 'vary', 'x-cache', 'x-hostinger-cache', 'x-litespeed-cache', 'x-litespeed-cache-control', 'x-proxy-cache' ) as $key ) {
			$value = wp_remote_retrieve_header( $response, $key );
			if ( is_string( $value ) && '' !== $value ) {
				$headers[ $key ] = substr( sanitize_text_field( $value ), 0, 180 );
			}
		}
		$html = (string) wp_remote_retrieve_body( $response );
		return array(
			'ok' => true,
			'http_status' => (int) wp_remote_retrieve_response_code( $response ),
			'bytes_read' => strlen( $html ),
			'sha256' => hash( 'sha256', $html ),
			'expected_text_found' => '' === $expected ? null : false !== stripos(
				html_entity_decode( wp_strip_all_tags( $html ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ),
				$expected
			),
			'headers' => $headers,
		);
	}

	public static function diagnose( $input ) {
		if ( ! current_user_can( 'manage_options' ) ) {
			return new WP_Error( 'wp_control_cache_forbidden', 'Administrator access is required.', array( 'status' => 403 ) );
		}
		$target = self::target( $input );
		if ( is_wp_error( $target ) ) return $target;
		$expected = is_array( $input ) && isset( $input['expected_text'] )
			? substr( sanitize_text_field( (string) $input['expected_text'] ), 0, 160 ) : '';
		$uncached_url = add_query_arg( '_wpcontrol_probe', wp_generate_password( 12, false, false ), $target['url'] );
		$normal = self::probe( $target['url'], $expected );
		$busted = self::probe( $uncached_url, $expected );

		return array(
			'ok' => true,
			'target' => $target,
			'provider' => array(
				'litespeed' => self::litespeed_available(),
				'external_object_cache' => wp_using_ext_object_cache(),
			),
			'canonical' => $normal,
			'cache_busted' => $busted,
			'html_differs' => ! empty( $normal['ok'] ) && ! empty( $busted['ok'] )
				? $normal['sha256'] !== $busted['sha256'] : null,
			'note' => 'Differences alone do not prove stale content. Compare expected_text_found and cache headers. Host/CDN cache may be outside WordPress control.',
		);
	}

	public static function purge_target( $input ) {
		if ( ! current_user_can( 'manage_options' ) ) {
			return new WP_Error( 'wp_control_cache_forbidden', 'Administrator access is required.', array( 'status' => 403 ) );
		}
		$target = self::target( $input );
		if ( is_wp_error( $target ) ) return $target;
		$mode = is_array( $input ) && isset( $input['mode'] ) ? sanitize_key( $input['mode'] ) : 'url';
		if ( ! in_array( $mode, array( 'url', 'post' ), true ) ) {
			return new WP_Error( 'wp_control_cache_mode_invalid', 'Choose url or post mode.', array( 'status' => 400 ) );
		}
		if ( ! self::litespeed_available() ) {
			return new WP_Error( 'wp_control_cache_provider_missing', 'LiteSpeed purge integration is not available; no cache was purged.', array( 'status' => 501 ) );
		}
		if ( ! empty( $input['dry_run'] ) ) {
			return array( 'ok' => true, 'dry_run' => true, 'target' => $target, 'mode' => $mode );
		}
		if ( ! is_array( $input ) || true !== ( $input['confirm'] ?? false ) ) {
			return new WP_Error( 'wp_control_cache_confirmation_required', 'Explicit confirm: true is required.', array( 'status' => 400 ) );
		}

		if ( 'post' === $mode ) {
			// Also invalidates caches tagged with this post, including related archives.
			do_action( 'litespeed_purge_post', $target['post_id'] );
		} else {
			do_action( 'litespeed_purge_url', $target['url'] );
		}
		return array(
			'ok' => true,
			'dispatched' => true,
			'verified_cleared' => false,
			'provider' => 'LiteSpeed Cache',
			'mode' => $mode,
			'target' => $target,
			'note' => 'The WordPress hook was dispatched. Verify canonical URL separately after this HTTP request finishes. Host/CDN layers may persist.',
		);
	}
}
