<?php
/**
 * Snapchat Public Profile API publisher.
 *
 * This is an optional, allowlisted alternative to the existing Creative Kit Android handoff.
 * OAuth credentials/tokens remain server-side. No Snap password or session cookie is used.
 * @see https://developers.snap.com/marketing-api/Public-Profile-API/GetStarted
 * @see https://developers.snap.com/marketing-api/Public-Profile-API/ProfileAssetManagement
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_Snap_Public_API {
    private const API = 'https://businessapi.snapchat.com';
    private const TOKEN_URL = 'https://accounts.snapchat.com/login/oauth2/access_token';
    private const AUTH_URL = 'https://accounts.snapchat.com/login/oauth2/authorize';
    private const MAX_MEDIA_BYTES = 100663296; // 96 MiB; safeguard for typical WordPress hosts.
    private const PART_BYTES = 33554432; // Snapchat multipart max 32 MiB per part.
    private const CONFIG_OPTION = 'grec_snap_public_config';
    private const SECRET_OPTION = 'grec_snap_public_secret';

    public static function init(): void {
        add_action( 'rest_api_init', array( __CLASS__, 'routes' ) );
        add_action( 'admin_menu', array( __CLASS__, 'menu' ) );
        add_action( 'admin_enqueue_scripts', array( __CLASS__, 'assets' ) );
        add_action( 'admin_post_grec_snap_api_save', array( __CLASS__, 'save' ) );
        add_action( 'admin_post_grec_snap_api_start', array( __CLASS__, 'start' ) );
        add_action( 'admin_post_grec_snap_api_verify', array( __CLASS__, 'verify' ) );
        add_action( 'admin_post_grec_snap_api_publish', array( __CLASS__, 'admin_publish' ) );
        add_action( 'admin_post_grec_snap_api_disconnect', array( __CLASS__, 'disconnect' ) );
    }

    private static function config(): array {
        $value = get_option( self::CONFIG_OPTION, array() );
        return is_array( $value ) ? $value : array();
    }
    private static function secret(): array {
        return GREC_Secrets::open( (string) get_option( self::SECRET_OPTION, '' ) );
    }
    private static function store_secret( array $secret ): void {
        update_option( self::SECRET_OPTION, GREC_Secrets::seal( $secret ), false );
    }
    public static function redirect_uri(): string {
        return rest_url( 'engagement-core/v1/snapchat/api/oauth/callback' );
    }
    private static function uuid( string $value ): string {
        $value = strtolower( trim( $value ) );
        if ( '' !== $value && ! preg_match( '/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/', $value ) ) {
            throw new InvalidArgumentException( 'Snapchat organization/profile ID must be a UUID.' );
        }
        return $value;
    }
    public static function status(): array {
        $c = self::config();
        $s = self::secret();
        return array(
            'mode'                    => 'public-profile-api',
            'requires_allowlisting'   => true,
            'client_id_saved'         => ! empty( $c['client_id'] ),
            'client_secret_saved'     => ! empty( $s['client_secret'] ),
            'organization_id_saved'   => ! empty( $c['organization_id'] ),
            'profile_id_saved'        => ! empty( $c['profile_id'] ),
            'oauth_connected'         => ! empty( $s['refresh_token'] ),
            'api_access_verified'     => ! empty( $c['verified_at'] ),
            'verified_at'             => ! empty( $c['verified_at'] ) ? $c['verified_at'] : null,
            'publish_tested'          => false, // API read verification does not demonstrate write permissions.
            'old_android_handoff'     => GREC_Snapchat::status(),
        );
    }
    public static function routes(): void {
        // The OAuth redirect uses a query-free callback URL. Random, one-use state
        // replaces reliance on admin cookies during Snapchat's cross-site redirect.
        register_rest_route( 'engagement-core/v1', '/snapchat/api/oauth/callback', array(
            'methods' => 'GET',
            'callback' => static function() {
                GREC_Snap_Public_API::callback(); // Redirects to the dashboard and exits.
                return rest_ensure_response( array( 'ok' => false ) );
            },
            'permission_callback' => '__return_true',
        ) );
        register_rest_route( 'engagement-core/v1', '/snapchat/api/status', array(
            'methods' => 'GET',
            'callback' => static function() { return rest_ensure_response( GREC_Snap_Public_API::status() ); },
            'permission_callback' => static function( WP_REST_Request $r ) {
                return GREC_Publisher_REST::machine_auth( $r, 'snapchat.status' );
            },
        ) );
        register_rest_route( 'engagement-core/v1', '/snapchat/api/profiles', array(
            'methods' => 'GET',
            'callback' => static function() {
                try { return rest_ensure_response( GREC_Snap_Public_API::profiles() ); }
                catch ( Throwable $e ) { return new WP_Error( 'snap_api_error', $e->getMessage(), array( 'status' => 502 ) ); }
            },
            'permission_callback' => static function( WP_REST_Request $r ) {
                return GREC_Publisher_REST::machine_auth( $r, 'snapchat.status' );
            },
        ) );
        register_rest_route( 'engagement-core/v1', '/snapchat/api/publish', array(
            'methods' => 'POST',
            'callback' => static function( WP_REST_Request $r ) {
                try {
                    return rest_ensure_response( GREC_Snap_Public_API::publish(
                        absint( $r->get_param( 'attachment_id' ) ),
                        sanitize_key( (string) $r->get_param( 'destination' ) ),
                        array(
                            'description' => sanitize_textarea_field( (string) $r->get_param( 'description' ) ),
                            'locale' => sanitize_text_field( (string) $r->get_param( 'locale' ) ),
                            'ttl' => sanitize_key( (string) $r->get_param( 'ttl' ) ),
                        )
                    ) );
                } catch ( Throwable $e ) {
                    return new WP_Error( 'snap_publish_failed', $e->getMessage(), array( 'status' => 400 ) );
                }
            },
            'permission_callback' => static function( WP_REST_Request $r ) {
                return GREC_Publisher_REST::machine_auth( $r, 'snapchat.publish' );
            },
            'args' => array(
                'attachment_id' => array( 'required' => true, 'type' => 'integer', 'minimum' => 1 ),
                'destination' => array( 'required' => true, 'type' => 'string', 'enum' => array( 'story', 'spotlight' ) ),
                'description' => array( 'required' => false, 'type' => 'string' ),
                'locale' => array( 'required' => false, 'type' => 'string' ),
                'ttl' => array( 'required' => false, 'type' => 'string' ),
            ),
        ) );
    }

    private static function admin_check( string $nonce ): void {
        if ( ! current_user_can( 'manage_options' ) ) { wp_die( 'Administrator access required.' ); }
        check_admin_referer( $nonce );
    }
    private static function back( string $message, bool $failed = false ): void {
        wp_safe_redirect( add_query_arg( array(
            'page' => 'grec-snapchat-api',
            'snap_notice' => rawurlencode( $message ),
            'snap_error' => $failed ? '1' : '0',
        ), admin_url( 'admin.php' ) ) );
        exit;
    }

    public static function save(): void {
        self::admin_check( 'grec_snap_api_save' );
        try {
            $c = self::config();
            $s = self::secret();
            $id = sanitize_text_field( (string) wp_unslash( $_POST['client_id'] ?? '' ) );
            if ( $id !== ( $c['client_id'] ?? '' ) ) {
                // Never carry a token from an old OAuth application into a replacement app.
                unset( $s['access_token'], $s['refresh_token'], $s['expires_at'] );
                unset( $c['verified_at'] );
            }
            $c['client_id'] = $id;
            $c['organization_id'] = self::uuid( (string) wp_unslash( $_POST['organization_id'] ?? '' ) );
            $c['profile_id'] = self::uuid( (string) wp_unslash( $_POST['profile_id'] ?? '' ) );
            $new_secret = trim( (string) wp_unslash( $_POST['client_secret'] ?? '' ) );
            if ( '' !== $new_secret ) {
                $s['client_secret'] = $new_secret;
                unset( $s['access_token'], $s['refresh_token'], $s['expires_at'] );
                unset( $c['verified_at'] );
            }
            update_option( self::CONFIG_OPTION, $c, false );
            self::store_secret( $s );
            self::back( 'Snapchat API credentials saved. OAuth and Snapchat allowlisting still required.' );
        } catch ( Throwable $e ) { self::back( $e->getMessage(), true ); }
    }

    public static function start(): void {
        self::admin_check( 'grec_snap_api_start' );
        $c = self::config();
        $s = self::secret();
        if ( empty( $c['client_id'] ) || empty( $s['client_secret'] ) ) {
            self::back( 'Save the Business Dashboard OAuth Client ID and Client Secret first.', true );
        }
        $state = bin2hex( random_bytes( 32 ) );
        set_transient( 'grec_snap_state_' . hash( 'sha256', $state ), (string) get_current_user_id(), 10 * MINUTE_IN_SECONDS );
        $url = add_query_arg( array(
            'response_type' => 'code',
            'client_id' => $c['client_id'],
            'redirect_uri' => self::redirect_uri(),
            'scope' => 'snapchat-profile-api',
            'state' => $state,
        ), self::AUTH_URL );
        wp_redirect( esc_url_raw( $url ), 302, 'Engagement Core' ); // Fixed Snapchat endpoint.
        exit;
    }

    private static function token_exchange( array $form ): array {
        $response = wp_remote_post( self::TOKEN_URL, array(
            'timeout' => 25,
            'body' => $form,
        ) );
        if ( is_wp_error( $response ) ) { throw new RuntimeException( $response->get_error_message() ); }
        $body = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( wp_remote_retrieve_response_code( $response ) >= 300 || ! is_array( $body ) || empty( $body['access_token'] ) ) {
            throw new RuntimeException( 'Snapchat OAuth exchange failed: ' . sanitize_text_field( (string) ( $body['error_description'] ?? $body['error'] ?? 'HTTP error' ) ) );
        }
        return $body;
    }

    private static function store_tokens( array $tokens ): void {
        $s = self::secret();
        $s['access_token'] = $tokens['access_token'];
        if ( ! empty( $tokens['refresh_token'] ) ) { $s['refresh_token'] = $tokens['refresh_token']; }
        $s['expires_at'] = time() + max( 120, absint( $tokens['expires_in'] ?? 3600 ) ) - 60;
        self::store_secret( $s );
    }

    public static function callback(): void {
        $state = sanitize_text_field( (string) wp_unslash( $_GET['state'] ?? '' ) );
        $state_key = 'grec_snap_state_' . hash( 'sha256', $state );
        $expected_user = get_transient( $state_key );
        delete_transient( $state_key );
        if ( strlen( $state ) !== 64 || ! ctype_xdigit( $state ) || ! $expected_user ) {
            self::back( 'Snapchat OAuth state check failed.', true );
        }
        if ( ! empty( $_GET['error'] ) ) { self::back( 'Snapchat access was denied.', true ); }
        $code = sanitize_text_field( (string) wp_unslash( $_GET['code'] ?? '' ) );
        if ( '' === $code ) { self::back( 'Snapchat did not return an authorization code.', true ); }
        try {
            $c = self::config();
            $s = self::secret();
            self::store_tokens( self::token_exchange( array(
                'grant_type' => 'authorization_code',
                'client_id' => $c['client_id'],
                'client_secret' => $s['client_secret'],
                'redirect_uri' => self::redirect_uri(),
                'code' => $code,
            ) ) );
            self::back( 'Snapchat OAuth connected. Test API access next; allowlisting is separate.' );
        } catch ( Throwable $e ) { self::back( $e->getMessage(), true ); }
    }

    private static function bearer(): string {
        $c = self::config();
        $s = self::secret();
        if ( empty( $s['refresh_token'] ) ) { throw new RuntimeException( 'Connect Snapchat OAuth in Engagement Core first.' ); }
        if ( ! empty( $s['access_token'] ) && (int) ( $s['expires_at'] ?? 0 ) > time() ) {
            return $s['access_token'];
        }
        $tokens = self::token_exchange( array(
            'grant_type' => 'refresh_token',
            'client_id' => $c['client_id'],
            'client_secret' => $s['client_secret'],
            'refresh_token' => $s['refresh_token'],
        ) );
        self::store_tokens( $tokens );
        return $tokens['access_token'];
    }

    private static function request( string $method, string $path, $body = null, string $content_type = 'application/json' ): array {
        // API hosts are fixed; a regional multipart path can never redirect to an arbitrary URL.
        if ( ! preg_match( '#^/(?:[a-z]{2}/)?v1/(?:public_profiles|organizations)/[a-zA-Z0-9/_-]+$#', $path ) ) {
            throw new InvalidArgumentException( 'Unexpected Snapchat API path.' );
        }
        $args = array(
            'method' => $method,
            'timeout' => 90,
            'redirection' => 0,
            'headers' => array( 'Authorization' => 'Bearer ' . self::bearer(), 'Accept' => 'application/json' ),
        );
        if ( null !== $body ) {
            $args['headers']['Content-Type'] = $content_type;
            $args['body'] = 'application/json' === $content_type ? wp_json_encode( $body ) : $body;
        }
        $response = wp_remote_request( self::API . $path, $args );
        if ( is_wp_error( $response ) ) { throw new RuntimeException( $response->get_error_message() ); }
        $data = json_decode( wp_remote_retrieve_body( $response ), true );
        $http = wp_remote_retrieve_response_code( $response );
        if ( $http < 200 || $http >= 300 || ! is_array( $data ) || ( isset( $data['request_status'] ) && 'SUCCESS' !== $data['request_status'] ) ) {
            $error = is_array( $data ) ? ( $data['error_code'] ?? $data['display_message'] ?? $data['debug_message'] ?? 'unknown error' ) : 'invalid JSON response';
            throw new RuntimeException( 'Snapchat API HTTP ' . $http . ': ' . sanitize_text_field( (string) $error ) );
        }
        return $data;
    }

    public static function profiles(): array {
        $id = self::uuid( (string) ( self::config()['organization_id'] ?? '' ) );
        if ( '' === $id ) { throw new RuntimeException( 'Snapchat Organization ID has not been saved.' ); }
        return self::request( 'GET', '/v1/organizations/' . $id . '/public_profiles' );
    }

    public static function verify(): void {
        self::admin_check( 'grec_snap_api_verify' );
        try {
            $data = self::profiles();
            $c = self::config();
            $selected = (string) ( $c['profile_id'] ?? '' );
            if ( '' !== $selected ) {
                $found = false;
                foreach ( (array) ( $data['public_profiles'] ?? array() ) as $item ) {
                    if ( $selected === (string) ( $item['public_profile']['id'] ?? '' ) ) { $found = true; break; }
                }
                if ( ! $found ) { throw new RuntimeException( 'The configured Public Profile ID was not returned for your organization. Check account permissions and the UUID.' ); }
            }
            $c['verified_at'] = gmdate( 'c' );
            update_option( self::CONFIG_OPTION, $c, false );
            self::back( 'Snapchat API read access verified: ' . count( $data['public_profiles'] ?? array() ) . ' profile(s) returned. Publishing remains untested.' );
        } catch ( Throwable $e ) { self::back( $e->getMessage(), true ); }
    }

    private static function media_attachment( int $id, string $destination ): array {
        if ( 'attachment' !== get_post_type( $id ) ) { throw new InvalidArgumentException( 'Select an existing WordPress Media Library attachment.' ); }
        $path = get_attached_file( $id );
        if ( ! is_string( $path ) || ! is_readable( $path ) || ! is_file( $path ) ) {
            throw new RuntimeException( 'The media file is not readable on WordPress.' );
        }
        $size = filesize( $path );
        if ( false === $size || $size <= 0 || $size > self::MAX_MEDIA_BYTES ) {
            throw new RuntimeException( 'Snapchat API media file must be under 96 MiB in this WordPress adapter.' );
        }
        $mime = strtolower( (string) get_post_mime_type( $id ) );
        if ( ! in_array( $mime, array( 'video/mp4', 'image/jpeg', 'image/png' ), true ) ) {
            throw new InvalidArgumentException( 'Use MP4, JPEG or PNG media.' );
        }
        if ( 'spotlight' === $destination && 'video/mp4' !== $mime ) {
            throw new InvalidArgumentException( 'Snapchat Spotlight requires an MP4 video.' );
        }
        $m = wp_get_attachment_metadata( $id );
        $width = absint( $m['width'] ?? 0 );
        $height = absint( $m['height'] ?? 0 );
        if ( $width && $height && ( $width < 540 || $height < 960 ) ) {
            throw new InvalidArgumentException( 'Snapchat requires media at least 540 x 960 pixels. Re-export your 9:16 master.' );
        }
        if ( 'video/mp4' === $mime ) {
            $duration = (float) ( $m['length'] ?? 0 );
            if ( $duration <= 0 ) { throw new InvalidArgumentException( 'Video duration metadata is missing; re-import the MP4 to WordPress.' ); }
            $minimum = 'spotlight' === $destination ? 6 : 5;
            if ( $duration < $minimum || $duration > 60 ) {
                throw new InvalidArgumentException( 'Snapchat ' . $destination . ' requires a ' . $minimum . '–60 second MP4.' );
            }
        }
        return array( 'path' => $path, 'type' => 'video/mp4' === $mime ? 'VIDEO' : 'IMAGE', 'name' => basename( $path ) );
    }

    // Streaming CBC encryption: encrypt full 16-byte blocks and manually PKCS#7-pad the final block.
    // Avoid loading a large video into PHP memory.
    private static function encrypt_media( string $source, string $target, string $key, string $iv ): void {
        $in = fopen( $source, 'rb' );
        $out = fopen( $target, 'wb' );
        if ( false === $in || false === $out ) { throw new RuntimeException( 'Unable to create encrypted media upload.' ); }
        try {
            $pending = '';
            $last_iv = $iv;
            while ( ! feof( $in ) ) {
                $read = fread( $in, 1048576 );
                if ( false === $read || ( '' === $read && ! feof( $in ) ) ) { throw new RuntimeException( 'Cannot read Snapchat media.' ); }
                $pending .= $read;
                $count = strlen( $pending ) - 16; // Reserve at least one block for final padding.
                $count -= $count % 16;
                if ( $count <= 0 ) { continue; }
                $block = substr( $pending, 0, $count );
                $pending = substr( $pending, $count );
                $cipher = openssl_encrypt( $block, 'aes-256-cbc', $key, OPENSSL_RAW_DATA | OPENSSL_ZERO_PADDING, $last_iv );
                if ( false === $cipher ) { throw new RuntimeException( 'Media encryption failed.' ); }
                fwrite( $out, $cipher );
                $last_iv = substr( $cipher, -16 );
            }
            $padding = 16 - ( strlen( $pending ) % 16 );
            $final = openssl_encrypt( $pending . str_repeat( chr( $padding ), $padding ), 'aes-256-cbc', $key, OPENSSL_RAW_DATA | OPENSSL_ZERO_PADDING, $last_iv );
            if ( false === $final || false === fwrite( $out, $final ) ) { throw new RuntimeException( 'Media encryption could not finish.' ); }
        } finally {
            fclose( $in );
            fclose( $out );
        }
    }

    private static function form_part( string $name, string $value, string $boundary ): string {
        return '--' . $boundary . "\r\nContent-Disposition: form-data; name=\"" . $name . "\"\r\n\r\n" . $value . "\r\n";
    }

    private static function upload( array $media, string $profile ): string {
        $key = random_bytes( 32 );
        $iv = random_bytes( 16 );
        $encrypted = wp_tempnam( $media['name'] . '.enc' );
        if ( ! $encrypted ) { throw new RuntimeException( 'Media encryption temporary file could not be created.' ); }
        try {
            self::encrypt_media( $media['path'], $encrypted, $key, $iv );
            $container = self::request( 'POST', '/v1/public_profiles/' . $profile . '/media', array(
                'type' => $media['type'],
                'name' => $media['name'],
                'key' => base64_encode( $key ),
                'iv' => base64_encode( $iv ),
            ) );
            if ( empty( $container['media_id'] ) || empty( $container['add_path'] ) || empty( $container['finalize_path'] ) ) {
                throw new RuntimeException( 'Snapchat did not return media upload paths.' );
            }
            $upload_path = $container['add_path'];
            $finalize_path = $container['finalize_path'];
            $source = fopen( $encrypted, 'rb' );
            if ( false === $source ) { throw new RuntimeException( 'Could not read encrypted media.' ); }
            try {
                $index = 0;
                while ( ! feof( $source ) ) {
                    $bytes = fread( $source, self::PART_BYTES );
                    if ( false === $bytes ) { throw new RuntimeException( 'Could not read encrypted upload chunk.' ); }
                    if ( '' === $bytes ) { break; }
                    ++$index;
                    $boundary = 'SnapMoksha' . bin2hex( random_bytes( 12 ) );
                    $body = self::form_part( 'action', 'ADD', $boundary );
                    $body .= self::form_part( 'part_number', (string) $index, $boundary );
                    $body .= '--' . $boundary . "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"encrypted.bin\"\r\nContent-Type: application/octet-stream\r\n\r\n";
                    $body .= $bytes . "\r\n--" . $boundary . "--\r\n";
                    unset( $bytes );
                    self::request( 'POST', $upload_path, $body, 'multipart/form-data; boundary=' . $boundary );
                    unset( $body );
                }
            } finally { fclose( $source ); }
            $boundary = 'SnapMoksha' . bin2hex( random_bytes( 12 ) );
            $body = self::form_part( 'action', 'FINALIZE', $boundary ) . '--' . $boundary . "--\r\n";
            self::request( 'POST', $finalize_path, $body, 'multipart/form-data; boundary=' . $boundary );
            return sanitize_text_field( (string) $container['media_id'] );
        } finally {
            @unlink( $encrypted );
        }
    }

    public static function publish( int $attachment_id, string $destination, array $options = array() ): array {
        $destination = sanitize_key( $destination );
        if ( ! in_array( $destination, array( 'story', 'spotlight' ), true ) ) {
            throw new InvalidArgumentException( 'Destination must be story or spotlight.' );
        }
        $c = self::config();
        $profile = self::uuid( (string) ( $c['profile_id'] ?? '' ) );
        if ( '' === $profile || empty( self::secret()['refresh_token'] ) ) {
            throw new RuntimeException( 'Save a Public Profile ID and connect OAuth before publishing.' );
        }
        $media = self::media_attachment( $attachment_id, $destination );
        $lock = 'grec_snap_pub_' . md5( $profile . '|' . $destination . '|' . $attachment_id );
        if ( get_transient( $lock ) ) { throw new RuntimeException( 'A publish attempt for this media is already in progress. Check Snapchat before retrying.' ); }
        set_transient( $lock, 1, 5 * MINUTE_IN_SECONDS );
        $submitted = false;
        try {
            $media_id = self::upload( $media, $profile );
            if ( 'story' === $destination ) {
                $body = array( 'media_id' => $media_id );
                $ttl = strtoupper( sanitize_key( (string) ( $options['ttl'] ?? '' ) ) );
                if ( '' !== $ttl ) {
                    if ( ! in_array( $ttl, array( 'ONE_DAY', 'TWO_DAYS', 'THREE_DAYS', 'ONE_WEEK' ), true ) ) {
                        throw new InvalidArgumentException( 'Story TTL must be ONE_DAY, TWO_DAYS, THREE_DAYS or ONE_WEEK.' );
                    }
                    $body['customized_ttl'] = array( 'ttl' => $ttl );
                }
                $result = self::request( 'POST', '/v1/public_profiles/' . $profile . '/stories', $body );
            } else {
                $description = trim( (string) ( $options['description'] ?? '' ) );
                if ( ( function_exists( 'mb_strlen' ) ? mb_strlen( $description ) : strlen( $description ) ) > 160 ) {
                    throw new InvalidArgumentException( 'Spotlight description cannot exceed 160 characters.' );
                }
                $locale = (string) ( $options['locale'] ?? 'en_IN' );
                if ( '' === $locale ) { $locale = 'en_IN'; }
                if ( ! preg_match( '/^[a-z]{2}_[A-Z]{2}$/', $locale ) ) {
                    throw new InvalidArgumentException( 'Locale must look like en_IN or ru_RU.' );
                }
                $result = self::request( 'POST', '/v1/public_profiles/' . $profile . '/spotlights', array(
                    'media_id' => $media_id,
                    'description' => $description,
                    'locale' => $locale,
                ) );
            }
            update_option( 'grec_snap_api_last_submit', array(
                'destination' => $destination,
                'attachment_id' => $attachment_id,
                'request_id' => $result['request_id'] ?? null,
                'spotlight_id' => $result['spotlight_id'] ?? null,
                'submitted_at' => gmdate( 'c' ),
            ), false );
            $submitted = true;
            return array(
                'ok' => true,
                'status' => 'submitted_to_snapchat',
                'destination' => $destination,
                'request_id' => $result['request_id'] ?? null,
                'spotlight_id' => $result['spotlight_id'] ?? null,
                'note' => 'Snapchat accepted the request; check platform visibility/moderation separately.',
            );
        } finally {
            // Preserve the short deduplication window when Snapchat accepted the request.
            if ( ! $submitted ) { delete_transient( $lock ); }
        }
    }

    public static function admin_publish(): void {
        self::admin_check( 'grec_snap_api_publish' );
        try {
            $result = self::publish( absint( $_POST['attachment_id'] ?? 0 ), sanitize_key( (string) wp_unslash( $_POST['destination'] ?? '' ) ), array(
                'description' => sanitize_textarea_field( (string) wp_unslash( $_POST['description'] ?? '' ) ),
                'locale' => sanitize_text_field( (string) wp_unslash( $_POST['locale'] ?? 'en_IN' ) ),
                'ttl' => sanitize_text_field( (string) wp_unslash( $_POST['ttl'] ?? '' ) ),
            ) );
            self::back( 'Submitted to Snapchat. Request ' . ( $result['request_id'] ?? 'accepted' ) . '. Confirm visibility inside Snapchat.' );
        } catch ( Throwable $e ) { self::back( $e->getMessage(), true ); }
    }

    public static function disconnect(): void {
        self::admin_check( 'grec_snap_api_disconnect' );
        $s = self::secret();
        unset( $s['access_token'], $s['refresh_token'], $s['expires_at'] );
        self::store_secret( $s );
        $c = self::config();
        unset( $c['verified_at'] );
        update_option( self::CONFIG_OPTION, $c, false );
        self::back( 'Snapchat OAuth tokens disconnected locally.' );
    }

    public static function menu(): void {
        add_submenu_page( 'engagement-core', 'Snapchat Public Profile API', 'Snapchat API', 'manage_options', 'grec-snapchat-api', array( __CLASS__, 'render' ) );
    }
    public static function assets( string $hook ): void {
        if ( false !== strpos( $hook, 'grec-snapchat-api' ) ) { wp_enqueue_media(); }
    }
    public static function render(): void {
        if ( ! current_user_can( 'manage_options' ) ) { return; }
        $c = self::config();
        $s = self::secret();
        $status = self::status();
        $notice = isset( $_GET['snap_notice'] ) ? sanitize_text_field( wp_unslash( $_GET['snap_notice'] ) ) : '';
        ?>
        <div class="wrap">
            <h1>Snapchat Public Profile API</h1>
            <p>Direct Stories and Spotlight publishing. <strong>Snapchat approval/allowlisting required.</strong> The older Android handoff stays enabled separately.</p>
            <p><a href="https://developers.snap.com/marketing-api/Public-Profile-API/GetStarted" target="_blank" rel="noopener noreferrer">Official Snap setup guide</a></p>
            <?php if ( $notice ) : ?><div class="notice notice-<?php echo ! empty( $_GET['snap_error'] ) ? 'error' : 'success'; ?>"><p><?php echo esc_html( $notice ); ?></p></div><?php endif; ?>
            <p>OAuth: <strong><?php echo $status['oauth_connected'] ? 'Connected' : 'Not connected'; ?></strong> · API read verification: <strong><?php echo $status['api_access_verified'] ? 'Verified' : 'Not verified'; ?></strong> · Publishing: <strong>Not verified until a real post</strong></p>
            <p><strong>Register this query-free redirect URI in Snapchat Business Dashboard:</strong><br><code><?php echo esc_html( self::redirect_uri() ); ?></code></p>
            <p><strong>Important:</strong> Create the Marketing API OAuth app in Snapchat Ads Manager → Business Dashboard → Business Details, <em>not</em> the generic Developer Portal. Send only the Client ID to your Snap contact for Public Profile API allowlisting; never send the Client Secret.</p>
            <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
                <input type="hidden" name="action" value="grec_snap_api_save"><?php wp_nonce_field( 'grec_snap_api_save' ); ?>
                <table class="form-table">
                    <tr><th><label for="snap-client">OAuth Client ID</label></th><td><input id="snap-client" class="regular-text code" name="client_id" value="<?php echo esc_attr( $c['client_id'] ?? '' ); ?>" required></td></tr>
                    <tr><th><label for="snap-secret">OAuth Client Secret</label></th><td><input id="snap-secret" type="password" class="regular-text code" name="client_secret" placeholder="<?php echo empty( $s['client_secret'] ) ? 'Required' : 'Saved (leave blank to keep)'; ?>" autocomplete="new-password"></td></tr>
                    <tr><th><label for="snap-org">Organization UUID</label></th><td><input id="snap-org" class="regular-text code" name="organization_id" value="<?php echo esc_attr( $c['organization_id'] ?? '' ); ?>"></td></tr>
                    <tr><th><label for="snap-profile">Public Profile UUID</label></th><td><input id="snap-profile" class="regular-text code" name="profile_id" value="<?php echo esc_attr( $c['profile_id'] ?? '' ); ?>"></td></tr>
                </table>
                <?php submit_button( 'Save API credentials' ); ?>
            </form>
            <form method="post" style="display:inline-block;margin-right:10px" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>"><input type="hidden" name="action" value="grec_snap_api_start"><?php wp_nonce_field( 'grec_snap_api_start' ); ?><?php submit_button( 'Connect Snapchat OAuth', 'secondary', 'submit', false ); ?></form>
            <form method="post" style="display:inline-block;margin-right:10px" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>"><input type="hidden" name="action" value="grec_snap_api_verify"><?php wp_nonce_field( 'grec_snap_api_verify' ); ?><?php submit_button( 'Verify API access', 'secondary', 'submit', false ); ?></form>
            <form method="post" style="display:inline-block" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>"><input type="hidden" name="action" value="grec_snap_api_disconnect"><?php wp_nonce_field( 'grec_snap_api_disconnect' ); ?><?php submit_button( 'Disconnect OAuth', 'secondary', 'submit', false ); ?></form>

            <h2>Direct publish (after Snapchat approval)</h2>
            <p>Choose an existing Media Library asset. The video must be portrait MP4, 5–60 seconds for Stories, 6–60 seconds for Spotlight and at least 540×960. The adapter rejects unsupported media before upload.</p>
            <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="max-width:850px">
                <input type="hidden" name="action" value="grec_snap_api_publish"><?php wp_nonce_field( 'grec_snap_api_publish' ); ?>
                <p><label>Media attachment ID: <input id="snap-api-media" name="attachment_id" type="number" min="1" required></label> <button id="snap-api-select" class="button" type="button">Select Media Library asset</button> <span id="snap-api-media-name"></span></p>
                <p><label>Destination <select name="destination"><option value="story">Public Story</option><option value="spotlight">Spotlight</option></select></label></p>
                <p><label>Spotlight description (up to 160 characters)<br><textarea class="large-text" rows="2" name="description" maxlength="160"></textarea></label></p>
                <p><label>Spotlight locale <input name="locale" value="en_IN" maxlength="5" style="width:100px"></label> <label>Story lifetime <select name="ttl"><option value="">24 hours (default)</option><option value="TWO_DAYS">2 days</option><option value="THREE_DAYS">3 days</option><option value="ONE_WEEK">1 week</option></select></label></p>
                <?php submit_button( 'Publish via Snapchat API' ); ?>
            </form>
            <p>Machine publishing: authenticated <code>POST /wp-json/engagement-core/v1/snapchat/api/publish</code> with <code>attachment_id</code>, <code>destination</code>, <code>description</code>, <code>locale</code> and/or <code>ttl</code>. Use an explicitly authorized <code>snapchat.publish</code> scope.</p>
            <script>
            (function() {
                var button=document.getElementById('snap-api-select'), input=document.getElementById('snap-api-media'), title=document.getElementById('snap-api-media-name');
                if (!button || !window.wp || !wp.media) return;
                button.addEventListener('click',function() {
                    var picker=wp.media({title:'Select Snapchat media',button:{text:'Use this media'},multiple:false});
                    picker.on('select',function() {
                        var a=picker.state().get('selection').first().toJSON();
                        input.value=a.id || '';
                        title.textContent=a.filename || a.title || '';
                    });
                    picker.open();
                });
            })();
            </script>
        </div>
        <?php
    }
}
