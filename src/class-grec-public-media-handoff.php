<?php
/**
 * Owner-scoped, signed Dell -> WordPress video handoff.
 *
 * Separate from the intentionally private Reel Uploads vault. Disabled until an
 * administrator configures a site-bound Ed25519 public key and enable flag.
 * No password, shared bearer token, or arbitrary server path is accepted.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_Public_Media_Handoff {
    private const NS = 'wp-control/v1';
    private const CHUNK = 4194304;
    private const MAX_BYTES = 67108864;
    private const PREFIX = 'grec_public_handoff_';

    public static function init(): void {
        add_action( 'rest_api_init', array( __CLASS__, 'routes' ), 35 );
        add_action( 'grec_public_media_nonce_cleanup', array( __CLASS__, 'cleanup_nonce' ), 10, 1 );
    }

    public static function cleanup_nonce( $nonce ): void {
        if ( is_string( $nonce ) && preg_match( '/^[a-f0-9]{32}$/D', $nonce ) ) {
            delete_option( self::PREFIX . 'nonce_' . $nonce );
        }
    }

    public static function routes(): void {
        register_rest_route( self::NS, '/media-handoff/health', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'health' ),
            'permission_callback' => '__return_true',
        ) );
        foreach ( array(
            array( '/media-handoff/start', 'start' ),
            array( '/media-handoff/(?P<id>[a-f0-9]{32})/chunk/(?P<part>[0-9]+)', 'chunk' ),
            array( '/media-handoff/(?P<id>[a-f0-9]{32})/finish', 'finish' ),
        ) as $route ) {
            register_rest_route( self::NS, $route[0], array(
                'methods' => 'POST', 'callback' => array( __CLASS__, $route[1] ),
                'permission_callback' => array( __CLASS__, 'authorize' ),
            ) );
        }
    }

    private static function fail( string $code, string $message, int $status = 400 ) {
        return new WP_Error( $code, $message, array( 'status' => $status ) );
    }

    private static function enabled(): bool {
        $host = strtolower( (string) wp_parse_url( home_url(), PHP_URL_HOST ) );
        $approved = strtolower( (string) get_option( 'grec_public_media_site_host', '' ) );
        $key = base64_decode( (string) get_option( 'grec_public_media_ed25519_key', '' ), true );
        return get_option( 'grec_public_media_enabled', '0' ) === '1'
            && $host !== '' && hash_equals( $host, $approved )
            && is_string( $key ) && strlen( $key ) === 32
            && function_exists( 'sodium_crypto_sign_verify_detached' );
    }

    public static function health() {
        return rest_ensure_response( array(
            'ok' => true, 'enabled' => self::enabled(),
            'max_bytes' => self::MAX_BYTES, 'chunk_bytes' => self::CHUNK,
        ) );
    }

    public static function authorize( $request ) {
        if ( ! self::enabled() ) {
            return self::fail( 'grec_handoff_disabled', 'Signed media handoff is not configured.', 503 );
        }
        $ts = (string) $request->get_header( 'X-GREC-Time' );
        $nonce = (string) $request->get_header( 'X-GREC-Nonce' );
        $signature = base64_decode( (string) $request->get_header( 'X-GREC-Signature' ), true );
        $body = (string) $request->get_body();
        if ( ! preg_match( '/^[0-9]{10}$/D', $ts ) || abs( time() - (int) $ts ) > 180
            || ! preg_match( '/^[a-f0-9]{32}$/D', $nonce )
            || ! is_string( $signature ) || strlen( $signature ) !== 64
            || strlen( $body ) > self::CHUNK ) {
            return self::fail( 'grec_handoff_signature', 'Invalid or expired signed request.', 401 );
        }
        $host = strtolower( (string) wp_parse_url( home_url(), PHP_URL_HOST ) );
        $message = $request->get_method() . "\n" . $request->get_route() . "\n"
            . $ts . "\n" . $nonce . "\n" . hash( 'sha256', $body ) . "\n" . $host;
        $key = base64_decode( (string) get_option( 'grec_public_media_ed25519_key' ), true );
        if ( ! sodium_crypto_sign_verify_detached( $signature, $message, $key ) ) {
            return self::fail( 'grec_handoff_signature', 'Signature verification failed.', 401 );
        }
        // add_option uses a unique DB option name: concurrent replays cannot
        // both claim the same nonce, even without a persistent object cache.
        $replay_key = self::PREFIX . 'nonce_' . $nonce;
        if ( ! add_option( $replay_key, time(), '', false ) ) {
            return self::fail( 'grec_handoff_replay', 'Signed request already used.', 409 );
        }
        wp_schedule_single_event( time() + 600, 'grec_public_media_nonce_cleanup', array( $nonce ) );
        return true;
    }

    private static function vault() {
        $webroot = realpath( ABSPATH );
        $docroot = ! empty( $_SERVER['DOCUMENT_ROOT'] )
            ? realpath( (string) $_SERVER['DOCUMENT_ROOT'] ) : $webroot;
        if ( ! $webroot || ! $docroot ) {
            return self::fail( 'grec_handoff_root', 'Document root unavailable.', 503 );
        }
        $path = dirname( $docroot ) . '/.moksha-public-handoff';
        if ( is_link( $path ) || ( ! is_dir( $path ) && ! @mkdir( $path, 0700, true ) ) ) {
            return self::fail( 'grec_handoff_vault', 'Private transfer vault unavailable.', 503 );
        }
        $real = realpath( $path );
        if ( ! $real || $real === $docroot
            || strpos( $real . '/', rtrim( $docroot, '/' ) . '/' ) === 0
            || $real === $webroot
            || strpos( $real . '/', rtrim( $webroot, '/' ) . '/' ) === 0 ) {
            return self::fail( 'grec_handoff_vault', 'Transfer vault must be outside the public web root.', 503 );
        }
        @chmod( $real, 0700 );
        return $real;
    }

    private static function session( string $id ) {
        if ( ! preg_match( '/^[a-f0-9]{32}$/D', $id ) ) {
            return self::fail( 'grec_handoff_id', 'Invalid session identifier.' );
        }
        $record = get_option( self::PREFIX . $id, false );
        if ( ! is_array( $record ) ) {
            return self::fail( 'grec_handoff_missing', 'Upload session not found.', 404 );
        }
        if ( time() - (int) $record['created'] > 3600 && $record['state'] !== 'registered' ) {
            return self::fail( 'grec_handoff_expired', 'Upload session expired.', 410 );
        }
        return $record;
    }

    private static function directory( string $id ) {
        $vault = self::vault();
        if ( is_wp_error( $vault ) ) { return $vault; }
        $dir = $vault . '/' . $id;
        if ( is_link( $dir ) || ( ! is_dir( $dir ) && ! @mkdir( $dir, 0700 ) ) ) {
            return self::fail( 'grec_handoff_folder', 'Cannot prepare transfer directory.', 503 );
        }
        @chmod( $dir, 0700 );
        return $dir;
    }

    public static function start( $request ) {
        $data = $request->get_json_params();
        $size = isset( $data['size'] ) ? filter_var( $data['size'], FILTER_VALIDATE_INT ) : false;
        $digest = strtolower( (string) ( $data['sha256'] ?? '' ) );
        $filename = sanitize_file_name( (string) ( $data['filename'] ?? '' ) );
        if ( false === $size || $size < 1024 || $size > self::MAX_BYTES
            || ! preg_match( '/^[a-f0-9]{64}$/D', $digest )
            || ! preg_match( '/^[a-zA-Z0-9][a-zA-Z0-9._-]{0,126}\.mp4$/D', $filename )
            || ( $data['mime'] ?? '' ) !== 'video/mp4'
            || ( $data['brand'] ?? '' ) !== 'moksha'
            || empty( $data['owner_approved'] ) ) {
            return self::fail( 'grec_handoff_meta', 'Invalid or unauthorized MP4 transfer manifest.' );
        }
        $id = bin2hex( random_bytes( 16 ) );
        $dir = self::directory( $id );
        if ( is_wp_error( $dir ) ) { return $dir; }
        $record = array(
            'created' => time(), 'state' => 'uploading', 'filename' => $filename,
            'size' => $size, 'sha256' => $digest,
            'parts' => (int) ceil( $size / self::CHUNK ),
            'brand' => 'moksha',
        );
        if ( ! add_option( self::PREFIX . $id, $record, '', false ) ) {
            return self::fail( 'grec_handoff_session', 'Unable to persist upload session.', 503 );
        }
        return new WP_REST_Response( array(
            'ok' => true, 'id' => $id, 'parts' => $record['parts'],
            'chunk_bytes' => self::CHUNK, 'private_until_verified' => true,
        ), 201 );
    }

    public static function chunk( $request ) {
        $id = (string) $request['id'];
        $part = absint( $request['part'] );
        $record = self::session( $id );
        if ( is_wp_error( $record ) ) { return $record; }
        if ( $record['state'] !== 'uploading' || $part >= $record['parts'] ) {
            return self::fail( 'grec_handoff_state', 'Chunk not accepted for this session.', 409 );
        }
        $bytes = (string) $request->get_body();
        $wanted = min( self::CHUNK, $record['size'] - $part * self::CHUNK );
        if ( strlen( $bytes ) !== $wanted ) {
            return self::fail( 'grec_handoff_length', 'Unexpected chunk length.', 422 );
        }
        $dir = self::directory( $id );
        if ( is_wp_error( $dir ) ) { return $dir; }
        $path = $dir . '/' . sprintf( '%06d', $part ) . '.part';
        $hash = hash( 'sha256', $bytes );
        if ( is_file( $path ) ) {
            if ( filesize( $path ) === $wanted && hash_equals( hash_file( 'sha256', $path ), $hash ) ) {
                return rest_ensure_response( array( 'ok' => true, 'duplicate' => true, 'part' => $part ) );
            }
            return self::fail( 'grec_handoff_conflict', 'Conflicting chunk exists.', 409 );
        }
        $temp = $path . '.' . bin2hex( random_bytes( 6 ) ) . '.tmp';
        if ( file_put_contents( $temp, $bytes, LOCK_EX ) !== $wanted
            || ! @rename( $temp, $path ) ) {
            @unlink( $temp );
            return self::fail( 'grec_handoff_write', 'Could not write verified chunk.', 507 );
        }
        @chmod( $path, 0600 );
        return rest_ensure_response( array( 'ok' => true, 'part' => $part, 'sha256' => $hash ) );
    }

    public static function finish( $request ) {
        $id = (string) $request['id'];
        $record = self::session( $id );
        if ( is_wp_error( $record ) ) { return $record; }
        if ( $record['state'] === 'registered' ) {
            return rest_ensure_response( array( 'ok' => true, 'duplicate' => true,
                'attachment_id' => $record['attachment_id'], 'url' => $record['url'],
                'sha256' => $record['sha256'] ) );
        }
        if ( $record['state'] !== 'uploading' ) {
            return self::fail( 'grec_handoff_state', 'Transfer not accepting completion.', 409 );
        }
        if ( ! add_option( self::PREFIX . $id . '_lock', time(), '', false ) ) {
            return self::fail( 'grec_handoff_busy', 'Another completion is running.', 409 );
        }
        try {
            $dir = self::directory( $id );
            if ( is_wp_error( $dir ) ) { return $dir; }
            $dest = $dir . '/assembled.mp4';
            $out = @fopen( $dest, 'wb' );
            if ( ! $out ) { return self::fail( 'grec_handoff_assemble', 'Cannot assemble MP4.', 507 ); }
            $ctx = hash_init( 'sha256' );
            $total = 0;
            for ( $i = 0; $i < $record['parts']; $i++ ) {
                $path = $dir . '/' . sprintf( '%06d', $i ) . '.part';
                $input = @fopen( $path, 'rb' );
                if ( ! $input ) { fclose( $out ); return self::fail( 'grec_handoff_missing_part', 'Missing transfer chunk.', 409 ); }
                while ( ! feof( $input ) ) {
                    $bytes = fread( $input, 1048576 );
                    if ( false === $bytes || fwrite( $out, $bytes ) !== strlen( $bytes ) ) {
                        fclose( $input ); fclose( $out );
                        return self::fail( 'grec_handoff_assemble', 'Failed to assemble chunk.', 507 );
                    }
                    hash_update( $ctx, $bytes );
                    $total += strlen( $bytes );
                }
                fclose( $input );
            }
            fclose( $out );
            $digest = hash_final( $ctx );
            if ( $total !== $record['size'] || ! hash_equals( $record['sha256'], $digest ) ) {
                @unlink( $dest );
                return self::fail( 'grec_handoff_integrity', 'Full-file integrity mismatch.', 422 );
            }
            $fh = @fopen( $dest, 'rb' );
            $head = $fh ? fread( $fh, 16 ) : '';
            if ( $fh ) { fclose( $fh ); }
            if ( strlen( $head ) < 12 || substr( $head, 4, 4 ) !== 'ftyp' ) {
                @unlink( $dest );
                return self::fail( 'grec_handoff_format', 'MP4 signature missing.', 422 );
            }
            require_once ABSPATH . 'wp-admin/includes/file.php';
            require_once ABSPATH . 'wp-admin/includes/image.php';
            $sideload = array(
                'name' => $record['filename'], 'type' => 'video/mp4',
                'tmp_name' => $dest, 'size' => $total, 'error' => 0,
            );
            $upload = wp_handle_sideload( $sideload, array(
                'test_form' => false, 'mimes' => array( 'mp4' => 'video/mp4' ),
            ) );
            if ( ! is_array( $upload ) || ! empty( $upload['error'] ) || empty( $upload['file'] ) ) {
                return self::fail( 'grec_handoff_import', 'WordPress Media Library import failed.', 500 );
            }
            if ( ! hash_equals( $record['sha256'], hash_file( 'sha256', $upload['file'] ) ) ) {
                @unlink( $upload['file'] );
                return self::fail( 'grec_handoff_postcopy', 'WordPress copy failed integrity check.', 500 );
            }
            $attachment_id = wp_insert_attachment( array(
                'post_mime_type' => 'video/mp4',
                'post_title' => sanitize_text_field( pathinfo( $record['filename'], PATHINFO_FILENAME ) ),
                'post_status' => 'inherit',
            ), $upload['file'], 0, true );
            if ( is_wp_error( $attachment_id ) || ! $attachment_id ) {
                @unlink( $upload['file'] );
                return self::fail( 'grec_handoff_attachment', 'Could not register media attachment.', 500 );
            }
            wp_update_attachment_metadata( $attachment_id, wp_generate_attachment_metadata( $attachment_id, $upload['file'] ) );
            $url = wp_get_attachment_url( $attachment_id );
            if ( ! is_string( $url ) || strpos( $url, 'https://' ) !== 0 ) {
                wp_delete_attachment( $attachment_id, true );
                return self::fail( 'grec_handoff_url', 'Media URL is not HTTPS.', 500 );
            }
            $record['state'] = 'registered';
            $record['attachment_id'] = $attachment_id;
            $record['url'] = $url;
            update_option( self::PREFIX . $id, $record, false );
            return new WP_REST_Response( array(
                'ok' => true, 'attachment_id' => $attachment_id,
                'url' => $url, 'sha256' => $digest, 'size' => $total,
            ), 201 );
        } finally {
            delete_option( self::PREFIX . $id . '_lock' );
        }
    }
}
