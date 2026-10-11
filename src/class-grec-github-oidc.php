<?php
/**
 * Short-lived GitHub Actions identity verification for the private Media Studio worker.
 * Replaces reliance on an old shared webhook URL: GitHub signs a scoped RS256 JWT,
 * WordPress verifies it against token.actions.githubusercontent.com OIDC JWKS.
 *
 * Deliberately accepts only the exact first-party main-branch rendering workflow.
 * No secrets or OAuth tokens are written to wp_options or URLs.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_GitHub_Reel_OIDC {
    private const ISS = 'https://token.actions.githubusercontent.com';
    private const AUD = 'mokshagoa.com/private-reel-ingest-v1';
    private const REPO = 'karanzing1992/engagement-core';
    private const REPO_ID = '1403281267';
    private const WORKFLOW = 'karanzing1992/engagement-core/.github/workflows/media-ingest-worker.yml@refs/heads/main';
    private const JWKS = 'https://token.actions.githubusercontent.com/.well-known/jwks';
    private const JWKS_CACHE_KEY = 'grec_reel_oidc_jwks_v1';

    private static function from_b64url( $input ) {
        if ( ! is_string( $input ) || strlen( $input ) > 12000 ||
            preg_match( '/^[A-Za-z0-9_-]+$/D', $input ) !== 1 ) { return false; }
        return base64_decode( strtr( $input, '-_', '+/' ) . str_repeat( '=', ( 4 - strlen( $input ) % 4 ) % 4 ), true );
    }

    private static function public_keys() {
        $cached = get_transient( self::JWKS_CACHE_KEY );
        if ( is_array( $cached ) && isset( $cached['keys'] ) && is_array( $cached['keys'] ) ) {
            return $cached['keys'];
        }
        // Fixed GitHub HTTPS endpoint, redirects refused to eliminate SSRF.
        $resp = wp_remote_get( self::JWKS, array(
            'timeout' => 8, 'redirection' => 0,
            'headers' => array( 'Accept' => 'application/json' ),
        ) );
        if ( is_wp_error( $resp ) || wp_remote_retrieve_response_code( $resp ) !== 200 ) {
            return array();
        }
        $payload = json_decode( (string) wp_remote_retrieve_body( $resp ), true );
        if ( ! is_array( $payload ) || ! isset( $payload['keys'] ) ||
            ! is_array( $payload['keys'] ) || count( $payload['keys'] ) > 25 ) {
            return array();
        }
        set_transient( self::JWKS_CACHE_KEY, $payload, HOUR_IN_SECONDS );
        return $payload['keys'];
    }

    public static function allowed( $request ): bool {
        if ( ! function_exists( 'openssl_verify' ) ) { return false; }
        $jwt = is_object( $request ) ? (string) $request->get_header( 'X-GitHub-OIDC-Token' ) : '';
        if ( strlen( $jwt ) < 100 || strlen( $jwt ) > 9000 ) { return false; }
        $pieces = explode( '.', $jwt );
        if ( count( $pieces ) !== 3 ) { return false; }
        $header_raw = self::from_b64url( $pieces[0] );
        $claims_raw = self::from_b64url( $pieces[1] );
        $sig = self::from_b64url( $pieces[2] );
        if ( false === $header_raw || false === $claims_raw || false === $sig ||
            strlen( $claims_raw ) > 14000 ) { return false; }
        $header = json_decode( $header_raw, true );
        $claims = json_decode( $claims_raw, true );
        if ( ! is_array( $header ) || ! is_array( $claims ) ||
            ( $header['alg'] ?? '' ) !== 'RS256' ||
            ! isset( $header['kid'] ) || ! is_string( $header['kid'] ) ) { return false; }
        $now = time();
        if ( ( $claims['iss'] ?? '' ) !== self::ISS ||
            ( $claims['aud'] ?? '' ) !== self::AUD ||
            ( $claims['repository'] ?? '' ) !== self::REPO ||
            (string) ( $claims['repository_id'] ?? '' ) !== self::REPO_ID ||
            ( $claims['ref'] ?? '' ) !== 'refs/heads/main' ||
            ( $claims['workflow_ref'] ?? '' ) !== self::WORKFLOW ||
            ! in_array( (string) ( $claims['event_name'] ?? '' ),
                array( 'schedule', 'workflow_dispatch', 'push' ), true ) ||
            (int) ( $claims['exp'] ?? 0 ) <= $now - 20 ||
            (int) ( $claims['exp'] ?? 0 ) > $now + 900 ||
            (int) ( $claims['iat'] ?? 0 ) > $now + 60 ||
            (int) ( $claims['iat'] ?? 0 ) < $now - 900 ||
            (int) ( $claims['nbf'] ?? $now ) > $now + 60 ) {
            return false;
        }
        // New immutable-subject formats are supported: repository_id + workflow_ref
        // provide stronger boundaries than matching mutable sub text alone.
        foreach ( self::public_keys() as $key ) {
            if ( ! is_array( $key ) || (string) ( $key['kid'] ?? '' ) !== $header['kid'] ||
                ( $key['kty'] ?? '' ) !== 'RSA' || ( $key['use'] ?? '' ) !== 'sig' ||
                empty( $key['x5c'][0] ) ) { continue; }
            $der = (string) $key['x5c'][0];
            if ( ! preg_match( '/^[A-Za-z0-9+\\/=]+$/D', $der ) ) { continue; }
            $pem = "-----BEGIN CERTIFICATE-----\n" . chunk_split( $der, 64, "\n" ) .
                "-----END CERTIFICATE-----\n";
            $cert = openssl_x509_read( $pem );
            if ( false === $cert ) { continue; }
            $pub = openssl_pkey_get_public( $cert );
            if ( ! $pub ) { continue; }
            $valid = openssl_verify( $pieces[0] . '.' . $pieces[1], $sig, $pub, OPENSSL_ALGO_SHA256 ) === 1;
            if ( $valid ) { return true; }
        }
        return false;
    }

    public static function audience(): string { return self::AUD; }
}
