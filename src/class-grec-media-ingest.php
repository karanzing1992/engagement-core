<?php
/**
 * Media Studio private chunked upload vault.
 *
 * Browser -> WP admin REST (4 MiB parts) -> private filesystem outside ABSPATH.
 * Cloud worker can read verified completed videos via existing WP Control HMAC.
 * Public URLs, unauthenticated uploads, arbitrary file paths and posting disabled.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_Media_Ingest {
    private const PREFIX = 'grec_mrs_ingest_';
    private const CHUNK = 4194304;
    private const FILE_MAX = 838860800; // 800 MiB per video.
    private const SESSION_MAX = 1610612736; // 1.5 GiB total.
    private const CONTEXT = 'mrs-media-queue-v1';

    public static function init(): void {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 32 );
        add_action( 'admin_menu', array( __CLASS__, 'admin_menu' ), 40 );
    }

    public static function register_routes(): void {
        $ns = 'wp-control/v1';
        foreach ( array(
            array( '/media-studio/ingest/start', 'POST', 'start', 'admin_allowed' ),
            array( '/media-studio/ingest/(?P<id>[a-f0-9]{32})/chunk/(?P<file>[0-9]+)/(?P<part>[0-9]+)', 'POST', 'chunk', 'admin_allowed' ),
            array( '/media-studio/ingest/(?P<id>[a-f0-9]{32})/finish/(?P<file>[0-9]+)', 'POST', 'finish', 'admin_allowed' ),
            array( '/media-studio/ingest/(?P<id>[a-f0-9]{32})/status', 'GET', 'status', 'admin_allowed' ),
            array( '/media-studio/ingest/ready', 'GET', 'ready', 'worker_allowed' ),
            array( '/media-studio/ingest/health', 'GET', 'health', 'worker_allowed' ),
            array( '/media-studio/ingest/(?P<id>[a-f0-9]{32})/source/(?P<file>[0-9]+)', 'GET', 'source', 'worker_allowed' ),
            array( '/media-studio/ingest/(?P<id>[a-f0-9]{32})/source-part/(?P<file>[0-9]+)/(?P<part>[0-9]+)', 'GET', 'source_part', 'worker_allowed' ),
            array( '/media-studio/ingest/(?P<id>[a-f0-9]{32})/render-start', 'POST', 'render_start', 'worker_allowed' ),
            array( '/media-studio/ingest/(?P<id>[a-f0-9]{32})/render-chunk/(?P<part>[0-9]+)', 'POST', 'render_chunk', 'worker_allowed' ),
            array( '/media-studio/ingest/(?P<id>[a-f0-9]{32})/render-finish', 'POST', 'render_finish', 'worker_allowed' ),
            array( '/media-studio/ingest/(?P<id>[a-f0-9]{32})/preview', 'GET', 'preview', 'admin_allowed' ),
        ) as $route ) {
            register_rest_route( $ns, $route[0], array(
                'methods' => $route[1],
                'callback' => array( __CLASS__, $route[2] ),
                'permission_callback' => array( __CLASS__, $route[3] ),
            ) );
        }
    }

    public static function admin_allowed(): bool {
        return current_user_can( 'manage_options' );
    }

    public static function worker_allowed( $request ): bool {
        $secret = (string) get_option( 'deployer_for_git_api_secret', '' );
        $token = is_object( $request ) ? (string) $request->get_header( 'X-WP-Control-Media-Token' ) : '';
        return strlen( $secret ) >= 20 && preg_match( '/^[0-9a-f]{64}$/D', $token ) === 1
            && hash_equals( hash_hmac( 'sha256', self::CONTEXT, $secret ), $token );
    }

    private static function fail( string $code, string $message, int $status = 400 ) {
        return new WP_Error( $code, $message, array( 'status' => $status ) );
    }

    private static function root() {
        $webroot = realpath( ABSPATH );
        if ( ! $webroot ) { return self::fail( 'mrs_vault_webroot', 'WordPress root not accessible', 503 ); }
        // A sibling of public_html, never under wp-content/uploads or other web-served folders.
        $vault = dirname( $webroot ) . '/.moksha-private-media';
        if ( is_link( $vault ) ) { return self::fail( 'mrs_vault_symlink', 'Unsafe vault link', 503 ); }
        if ( ! is_dir( $vault ) && ! @mkdir( $vault, 0700, true ) ) {
            return self::fail( 'mrs_vault_unavailable',
                'Host must permit a private folder outside the WordPress document root.', 503 );
        }
        $real = realpath( $vault );
        if ( ! $real || strpos( $real . '/', rtrim( $webroot, '/' ) . '/' ) === 0 ) {
            return self::fail( 'mrs_vault_public', 'Vault is not outside the public document root', 503 );
        }
        @chmod( $real, 0700 );
        return $real;
    }

    private static function directory( $id ) {
        if ( ! preg_match( '/^[a-f0-9]{32}$/D', (string) $id ) ) {
            return self::fail( 'mrs_invalid_id', 'Invalid upload session ID' );
        }
        $root = self::root();
        if ( is_wp_error( $root ) ) { return $root; }
        $dir = $root . '/' . $id;
        if ( is_link( $dir ) ) { return self::fail( 'mrs_unsafe_dir', 'Unsafe session directory' ); }
        if ( ! is_dir( $dir ) && ! @mkdir( $dir, 0700 ) ) {
            return self::fail( 'mrs_session_dir', 'Unable to create private ingest folder', 503 );
        }
        @chmod( $dir, 0700 );
        return $dir;
    }

    private static function load( $id ) {
        $record = get_option( self::PREFIX . $id, false );
        return is_array( $record ) && ! empty( $record['files'] ) ? $record :
            self::fail( 'mrs_ingest_missing', 'Upload session not found', 404 );
    }

    private static function save( $id, $record ): bool {
        return update_option( self::PREFIX . $id, $record, false );
    }

    public static function start( $request ) {
        $data = $request->get_json_params();
        $files = isset( $data['files'] ) ? $data['files'] : null;
        if ( ! is_array( $files ) || count( $files ) < 1 || count( $files ) > 8 ) {
            return self::fail( 'mrs_ingest_files', 'One to eight clips required.' );
        }
        if ( empty( $data['owner_attests_goa_india'] ) || empty( $data['owner_attests_rights'] ) ) {
            return self::fail( 'mrs_owner_attestation',
                'An administrator must confirm Indian capture location and permission to use the footage.' );
        }
        $normalized = array();
        $sum = 0;
        foreach ( $files as $entry ) {
            $name = sanitize_file_name( isset( $entry['name'] ) ? $entry['name'] : '' );
            $size = filter_var( isset( $entry['size'] ) ? $entry['size'] : 0, FILTER_VALIDATE_INT );
            $ext = strtolower( pathinfo( $name, PATHINFO_EXTENSION ) );
            if ( ! $name || ! in_array( $ext, array( 'mp4', 'mov', 'm4v' ), true ) ||
                false === $size || $size < 1024 || $size > self::FILE_MAX ) {
                return self::fail( 'mrs_ingest_format', 'MP4/MOV clips up to 800 MiB are supported.' );
            }
            $sum += $size;
            $normalized[] = array(
                'name' => $name, 'size' => $size,
                'parts' => (int) ceil( $size / self::CHUNK ), 'complete' => false,
                'sha256' => '',
            );
        }
        if ( $sum > self::SESSION_MAX ) {
            return self::fail( 'mrs_ingest_total', 'Session exceeds private storage limit of 1.5 GiB.' );
        }
        $id = bin2hex( random_bytes( 16 ) );
        $dir = self::directory( $id );
        if ( is_wp_error( $dir ) ) { return $dir; }
        $record = array( 'id' => $id, 'state' => 'uploading', 'files' => $normalized,
            'created_at' => time(), 'owner' => get_current_user_id(), 'target_seconds' => 30,
            'owner_attestation' => array( 'capture_country' => 'India', 'editorial_region' => 'Goa',
                'owner_attests_rights' => true, 'owner_attests_india' => true,
                'verified_at' => time(), 'verified_by_user_id' => get_current_user_id(),
                'independent_editorial_review_required' => true ),
            'output' => array(), 'last_error' => '', 'render_attempts' => 0 );
        if ( ! add_option( self::PREFIX . $id, $record, '', false ) ) {
            return self::fail( 'mrs_ingest_db', 'Could not persist upload session', 503 );
        }
        // Bounded private queue. The remote cloud worker never scans wp_options.
        $pending = (array) get_option( 'grec_mrs_pending_sessions', array() );
        $pending[] = $id;
        update_option( 'grec_mrs_pending_sessions', array_slice( array_values( array_unique( $pending ) ), -25 ), false );
        return new WP_REST_Response( array(
            'ok' => true, 'id' => $id, 'chunk_size' => self::CHUNK,
            'files' => $normalized, 'state' => 'uploading', 'private' => true,
            'publishing_enabled' => false ), 201 );
    }

    private static function part_path( $id, $file, $part, $output = false ) {
        $dir = self::directory( $id );
        if ( is_wp_error( $dir ) ) { return $dir; }
        $path = $dir . ( $output ? '/out' : '/f' . $file );
        if ( ! is_dir( $path ) && ! @mkdir( $path, 0700 ) ) {
            return self::fail( 'mrs_chunk_dir', 'Cannot create private chunks directory', 503 );
        }
        return $path . '/' . sprintf( '%06d', $part ) . '.chunk';
    }

    private static function receive_part( $request, $id, $file, $part, $size, $total, $output = false ) {
        if ( $part < 0 || $part >= $total ) { return self::fail( 'mrs_chunk_bounds', 'Chunk out of range.' ); }
        $want = min( self::CHUNK, $size - $part * self::CHUNK );
        $body = $request->get_body();
        if ( ! is_string( $body ) || strlen( $body ) !== $want ) {
            return self::fail( 'mrs_chunk_size', 'Incorrect chunk size, retry this part.', 400 );
        }
        $hash = strtolower( (string) $request->get_header( 'X-Chunk-SHA256' ) );
        if ( ! preg_match( '/^[0-9a-f]{64}$/D', $hash ) ||
            ! hash_equals( $hash, hash( 'sha256', $body ) ) ) {
            return self::fail( 'mrs_chunk_integrity', 'SHA-256 chunk mismatch; retry.', 422 );
        }
        $path = self::part_path( $id, $file, $part, $output );
        if ( is_wp_error( $path ) ) { return $path; }
        if ( file_exists( $path ) ) {
            if ( filesize( $path ) === $want && hash_equals( hash_file( 'sha256', $path ), $hash ) ) {
                return new WP_REST_Response( array( 'ok' => true, 'duplicate' => true, 'part' => $part ), 200 );
            }
            return self::fail( 'mrs_chunk_conflict', 'A different chunk already exists here.', 409 );
        }
        $temp = $path . '.' . bin2hex( random_bytes( 5 ) ) . '.tmp';
        if ( file_put_contents( $temp, $body, LOCK_EX ) !== $want ) {
            @unlink( $temp );
            return self::fail( 'mrs_chunk_write', 'Could not write private chunk', 507 );
        }
        @chmod( $temp, 0600 );
        if ( ! @rename( $temp, $path ) ) {
            @unlink( $temp );
            return self::fail( 'mrs_chunk_rename', 'Could not finalize private chunk', 507 );
        }
        return new WP_REST_Response( array( 'ok' => true, 'part' => $part,
            'bytes' => $want, 'sha256' => $hash ), 200 );
    }

    public static function chunk( $request ) {
        $id = $request['id']; $file = absint( $request['file'] ); $part = absint( $request['part'] );
        $record = self::load( $id );
        if ( is_wp_error( $record ) ) { return $record; }
        if ( ! isset( $record['files'][$file] ) || $record['state'] !== 'uploading' ) {
            return self::fail( 'mrs_invalid_file', 'Session or file not accepting chunks', 409 );
        }
        $f = $record['files'][$file];
        if ( ! empty( $f['complete'] ) ) { return self::fail( 'mrs_file_done', 'File already finished', 409 ); }
        return self::receive_part( $request, $id, $file, $part, $f['size'], $f['parts'] );
    }

    private static function assemble( $id, $file, $size, $count, $dest, $expected_sha = '' ) {
        $tmp = $dest . '.incomplete';
        $out = @fopen( $tmp, 'wb' );
        if ( ! $out ) { return self::fail( 'mrs_assembly_open', 'Cannot assemble video', 507 ); }
        @chmod( $tmp, 0600 );
        $ctx = hash_init( 'sha256' ); $total = 0;
        for ( $i = 0; $i < $count; $i++ ) {
            $part = self::part_path( $id, $file, $i, $file === 'output' );
            if ( is_wp_error( $part ) || ! is_file( $part ) ) {
                fclose( $out ); @unlink( $tmp );
                return self::fail( 'mrs_missing_chunk', 'Missing chunk ' . $i . '; resume upload.', 409 );
            }
            $in = @fopen( $part, 'rb' );
            if ( ! $in ) {
                fclose( $out ); @unlink( $tmp );
                return self::fail( 'mrs_part_read', 'Cannot read chunk', 500 );
            }
            while ( ! feof( $in ) ) {
                $data = fread( $in, 1024 * 1024 );
                if ( false === $data ) { fclose( $in ); fclose( $out ); @unlink( $tmp );
                    return self::fail( 'mrs_part_corrupt', 'Cannot read chunk data', 500 ); }
                $length = strlen( $data ); $total += $length;
                if ( $total > $size || fwrite( $out, $data ) !== $length ) {
                    fclose( $in ); fclose( $out ); @unlink( $tmp );
                    return self::fail( 'mrs_assemble_overflow', 'Assembly exceeded expected length.', 422 );
                }
                hash_update( $ctx, $data );
            }
            fclose( $in );
        }
        fflush( $out ); fclose( $out );
        $digest = hash_final( $ctx );
        if ( $total !== $size || ( $expected_sha && ! hash_equals( $expected_sha, $digest ) ) ) {
            @unlink( $tmp );
            return self::fail( 'mrs_final_integrity', 'Final media hash/length mismatch.', 422 );
        }
        if ( ! @rename( $tmp, $dest ) ) {
            @unlink( $tmp );
            return self::fail( 'mrs_final_rename', 'Cannot finalize private media.', 507 );
        }
        @chmod( $dest, 0600 );
        return array( 'sha256' => $digest, 'size' => $size, 'path' => $dest );
    }

    public static function finish( $request ) {
        $id = $request['id']; $file = absint( $request['file'] );
        $record = self::load( $id );
        if ( is_wp_error( $record ) ) { return $record; }
        if ( ! isset( $record['files'][$file] ) ) { return self::fail( 'mrs_file_missing', 'Source not found', 404 ); }
        $f = $record['files'][$file];
        if ( ! empty( $f['complete'] ) ) {
            return new WP_REST_Response( array( 'ok' => true, 'file' => $file, 'sha256' => $f['sha256'],
                'state' => $record['state'], 'duplicate' => true ), 200 );
        }
        if ( $record['state'] !== 'uploading' ) {
            return self::fail( 'mrs_ingest_state', 'Not accepting sources', 409 );
        }
        $dir = self::directory( $id );
        if ( is_wp_error( $dir ) ) { return $dir; }
        $dest = $dir . '/source-' . $file . '.' . strtolower( pathinfo( $f['name'], PATHINFO_EXTENSION ) );
        $expected = strtolower( (string) $request->get_param( 'sha256' ) );
        if ( $expected && ! preg_match( '/^[a-f0-9]{64}$/D', $expected ) ) {
            return self::fail( 'mrs_bad_hash', 'Invalid expected SHA-256' );
        }
        $result = self::assemble( $id, $file, $f['size'], $f['parts'], $dest, $expected );
        if ( is_wp_error( $result ) ) { return $result; }
        // Prevent disguised executables being stored, even in the private vault.
        $mime = function_exists( 'mime_content_type' ) ? mime_content_type( $dest ) : '';
        $handle = fopen( $dest, 'rb' ); $head = $handle ? fread( $handle, 16 ) : ''; if ( $handle ) { fclose( $handle ); }
        $mp4_header = strlen( $head ) >= 12 && substr( $head, 4, 4 ) === 'ftyp';
        if ( ! $mp4_header && $mime !== 'video/quicktime' ) {
            @unlink( $dest );
            return self::fail( 'mrs_source_format', 'File is not a recognizable MP4/MOV container.', 422 );
        }
        $record['files'][$file]['sha256'] = $result['sha256'];
        $record['files'][$file]['complete'] = true;
        $complete = true;
        foreach ( $record['files'] as $entry ) {
            if ( empty( $entry['complete'] ) ) { $complete = false; break; }
        }
        if ( $complete ) { $record['state'] = 'ready'; }
        self::save( $id, $record );
        return new WP_REST_Response( array(
            'ok' => true, 'file' => $file, 'sha256' => $result['sha256'],
            'state' => $record['state'], 'private' => true ), 200 );
    }

    public static function status( $request ) {
        $record = self::load( $request['id'] );
        if ( is_wp_error( $record ) ) { return $record; }
        return new WP_REST_Response( array(
            'ok' => true, 'id' => $record['id'], 'state' => $record['state'],
            'files' => $record['files'],
            'rendered' => $record['state'] === 'preview_ready_private',
            'private_preview_url' => $record['state'] === 'preview_ready_private' ?
                rest_url( 'wp-control/v1/media-studio/ingest/' . $record['id'] . '/preview' ) : '',
            'publishing_enabled' => false ), 200 );
    }

    public static function health( $request ) {
        $root = self::root();
        if ( is_wp_error( $root ) ) { return $root; }
        if ( ! is_writable( $root ) ) {
            return self::fail( 'mrs_vault_read_only',
                'Private storage directory is not writable by WordPress.', 503 );
        }
        return new WP_REST_Response( array(
            'ok' => true, 'private_vault' => true, 'writable' => true,
            'chunk_size_bytes' => self::CHUNK,
            'max_file_bytes' => self::FILE_MAX,
            'publishing_enabled' => false ), 200 );
    }

    public static function ready( $request ) {
        $ids = get_option( 'grec_mrs_pending_sessions', array() );
        // This bounded index avoids scanning entire wp_options on each cloud job.
        $records = array();
        foreach ( array_slice( (array) $ids, -25 ) as $id ) {
            $r = self::load( $id );
            if ( is_array( $r ) && $r['state'] === 'ready' ) {
                $records[] = array( 'id' => $id, 'files' => $r['files'],
                    'target_seconds' => $r['target_seconds'], 'state' => $r['state'] );
            }
        }
        return new WP_REST_Response( array( 'ok' => true, 'sessions' => $records,
            'private' => true, 'publishing_enabled' => false ), 200 );
    }

    private static function stream_private( $file, $name = 'private-preview.mp4' ) {
        if ( ! is_file( $file ) ) { return self::fail( 'mrs_private_missing', 'Private video unavailable', 404 ); }
        // WordPress REST validation has already checked the HMAC or administrator.
        // Stream rather than loading 231+ MB into PHP memory.
        if ( headers_sent() ) { return self::fail( 'mrs_header_error', 'Cannot stream media safely', 500 ); }
        header( 'Content-Type: video/mp4' );
        header( 'X-Content-Type-Options: nosniff' );
        header( 'Cache-Control: private, no-store, max-age=0' );
        header( 'Content-Disposition: attachment; filename="' . sanitize_file_name( $name ) . '"' );
        header( 'Content-Length: ' . filesize( $file ) );
        $fp = fopen( $file, 'rb' );
        if ( ! $fp ) { return self::fail( 'mrs_stream_open', 'Private video unavailable', 500 ); }
        fpassthru( $fp ); fclose( $fp );
        exit;
    }

    public static function source( $request ) {
        $record = self::load( $request['id'] );
        if ( is_wp_error( $record ) ) { return $record; }
        $idx = absint( $request['file'] );
        if ( ! isset( $record['files'][$idx] ) || empty( $record['files'][$idx]['complete'] ) ||
            ! in_array( $record['state'], array( 'ready', 'processing' ), true ) ) {
            return self::fail( 'mrs_source_not_ready', 'Source not ready for rendering', 409 );
        }
        $dir = self::directory( $record['id'] );
        if ( is_wp_error( $dir ) ) { return $dir; }
        $path = $dir . '/source-' . $idx . '.' .
            strtolower( pathinfo( $record['files'][$idx]['name'], PATHINFO_EXTENSION ) );
        return self::stream_private( $path, $record['files'][$idx]['name'] );
    }

    public static function source_part( $request ) {
        $record = self::load( $request['id'] );
        if ( is_wp_error( $record ) ) { return $record; }
        $idx=absint( $request['file'] ); $part=absint( $request['part'] );
        if ( ! isset( $record['files'][$idx] ) || empty( $record['files'][$idx]['complete'] ) ||
            ! in_array( $record['state'], array( 'ready', 'processing' ), true ) ||
            $part >= $record['files'][$idx]['parts'] ) {
            return self::fail( 'mrs_source_part_missing', 'Source part not ready', 404 );
        }
        $path = self::part_path( $record['id'], $idx, $part );
        if ( is_wp_error( $path ) ) { return $path; }
        return self::stream_private( $path, 'private-source-' . $idx . '-part-' . $part . '.bin' );
    }

    public static function render_start( $request ) {
        $id=$request['id']; $record=self::load( $id );
        if ( is_wp_error( $record ) ) { return $record; }
        if ( ! in_array( $record['state'], array( 'ready', 'processing' ), true ) ) {
            return self::fail( 'mrs_render_state', 'Only ready private uploads can render', 409 );
        }
        $data = $request->get_json_params();
        $size = filter_var( $data['size'] ?? 0, FILTER_VALIDATE_INT );
        $sha = strtolower( (string) ( $data['sha256'] ?? '' ) );
        if ( false === $size || $size < 1024 || $size > self::FILE_MAX ||
            ! preg_match( '/^[a-f0-9]{64}$/D', $sha ) ) {
            return self::fail( 'mrs_render_meta', 'Output requires exact size and SHA-256.' );
        }
        if ( $record['state'] === 'processing' && ! empty( $record['output'] ) ) {
            if ( $record['output']['sha256'] === $sha && $record['output']['size'] === $size ) {
                return new WP_REST_Response( array( 'ok' => true, 'id' => $id, 'duplicate' => true ), 200 );
            }
            return self::fail( 'mrs_render_conflict', 'Another private render is being uploaded', 409 );
        }
        $record['state'] = 'processing';
        $record['output'] = array( 'size' => $size, 'sha256' => $sha,
            'parts' => (int) ceil( $size / self::CHUNK ), 'complete' => false );
        $record['render_attempts'] = (int) $record['render_attempts'] + 1;
        self::save( $id, $record );
        return new WP_REST_Response( array( 'ok' => true, 'id' => $id,
            'state' => 'processing', 'private' => true ), 200 );
    }

    public static function render_chunk( $request ) {
        $id=$request['id']; $part=absint( $request['part'] ); $r=self::load( $id );
        if ( is_wp_error( $r ) ) { return $r; }
        if ( $r['state'] !== 'processing' || empty( $r['output'] ) ) {
            return self::fail( 'mrs_render_not_started', 'Render transfer not started', 409 );
        }
        return self::receive_part( $request, $id, 'output', $part, $r['output']['size'], $r['output']['parts'], true );
    }

    public static function render_finish( $request ) {
        $id=$request['id']; $r=self::load( $id );
        if ( is_wp_error( $r ) ) { return $r; }
        if ( $r['state'] === 'preview_ready_private' ) {
            return new WP_REST_Response( array( 'ok' => true, 'id' => $id, 'duplicate' => true ), 200 );
        }
        if ( $r['state'] !== 'processing' || empty( $r['output'] ) ) {
            return self::fail( 'mrs_render_not_started', 'Render transfer not started', 409 );
        }
        $dir=self::directory( $id );
        if ( is_wp_error( $dir ) ) { return $dir; }
        $dest=$dir.'/private-final-preview.mp4';
        $o=$r['output'];
        $result=self::assemble( $id, 'output', $o['size'], $o['parts'], $dest, $o['sha256'] );
        if ( is_wp_error( $result ) ) { return $result; }
        $handle=fopen( $dest, 'rb' ); $head=$handle ? fread( $handle, 16 ) : ''; if ( $handle ) { fclose( $handle ); }
        if ( strlen( $head ) < 12 || substr( $head, 4, 4 ) !== 'ftyp' ) {
            @unlink( $dest );
            return self::fail( 'mrs_preview_invalid', 'Rendered output is not MP4', 422 );
        }
        $r['state'] = 'preview_ready_private';
        $r['output']['complete']=true;
        $r['output']['completed_at']=time();
        self::save( $id, $r );
        return new WP_REST_Response( array( 'ok' => true, 'id' => $id,
            'status' => 'preview_ready_private', 'sha256' => $o['sha256'],
            'publishing_enabled' => false, 'schedule_enabled' => false ), 200 );
    }

    public static function preview( $request ) {
        $r=self::load( $request['id'] );
        if ( is_wp_error( $r ) ) { return $r; }
        if ( $r['state'] !== 'preview_ready_private' ) {
            return self::fail( 'mrs_preview_pending', 'Private render not completed', 409 );
        }
        $dir=self::directory( $r['id'] );
        return is_wp_error( $dir ) ? $dir :
            self::stream_private( $dir.'/private-final-preview.mp4', 'moksha-30-second-preview.mp4' );
    }

    public static function admin_menu(): void {
        add_submenu_page( 'tools.php', 'Private Reel Uploads', 'Reel Uploads',
            'manage_options', 'grec-media-ingest', array( __CLASS__, 'admin_page' ) );
    }

    public static function admin_page(): void {
        if ( ! current_user_can( 'manage_options' ) ) { return; }
        $asset=plugins_url( 'assets/media-ingest.js', GREC_FILE );
        $config = array( 'api' => rest_url( 'wp-control/v1/media-studio/ingest/' ),
            'nonce' => wp_create_nonce( 'wp_rest' ), 'chunk' => self::CHUNK,
            'maxFile' => self::FILE_MAX );
        echo '<div class="wrap"><h1>Private Reel Uploads</h1>';
        echo '<p>Upload 1–8 original phone clips directly in 4 MiB chunks, including videos larger than 200 MB. ';
        echo 'Only administrators can see previews. Original files stay outside the public website.</p>';
        echo '<p><input id="mrs-files" type="file" accept="video/mp4,video/quicktime,video/x-m4v" multiple></p>';
        echo '<p><label><input id="mrs-geocheck" type="checkbox"> I confirm these clips were filmed in Goa/India and I hold rights to use them. Independent review still applies before publishing.</label></p>';
        echo '<p><button id="mrs-start" type="button" class="button button-primary">Upload and queue private 30s Reel</button></p>';
        echo '<div id="mrs-upload-feedback" role="status" aria-live="polite"></div>';
        echo '<h2>Recent private uploads</h2><table class="widefat striped"><thead><tr><th>Session</th><th>Clips</th><th>Status</th><th>Private preview</th></tr></thead><tbody>';
        foreach ( array_reverse( (array) array_slice( (array) get_option( 'grec_mrs_pending_sessions', array() ), -15 ) ) as $id ) {
            $record = self::load( $id );
            if ( ! is_array( $record ) ) { continue; }
            echo '<tr><td><code>' . esc_html( substr( $id, 0, 12 ) ) . '</code></td>';
            echo '<td>' . esc_html( implode( ', ', array_map( function( $item ) { return $item['name']; }, $record['files'] ) ) ) . '</td>';
            echo '<td>' . esc_html( $record['state'] ) . '</td><td>';
            if ( $record['state'] === 'preview_ready_private' ) {
                echo '<button type="button" class="button" data-private-preview="' . esc_attr( $id ) . '">Download private 30s MP4</button>';
            } else {
                echo 'Not ready';
            }
            echo '</td></tr>';
        }
        echo '</tbody></table>';
        echo '<p><a href="' . esc_url( admin_url( 'admin.php?page=mrs-studio' ) ) .
            '">Open Media Studio drafts</a></p></div>';
        echo '<script>window.MRSIngest=' . wp_json_encode( $config ) . ';</script>';
        echo '<script src="' . esc_url( $asset ) . '" defer></script>';
    }
}
