<?php
/**
 * Independent, strictly read-only Google Search Console integration.
 * No Site Kit, Windsor, GSC Wizard, or other plugin credentials are reused.
 * All OAuth tokens stay encrypted within this WordPress installation.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_GSC {
    private const SCOPE = 'https://www.googleapis.com/auth/webmasters.readonly';
    private const TOKEN_URL = 'https://oauth2.googleapis.com/token';
    private const AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth';
    private const OPT_CREDENTIALS = 'grec_gsc_credentials';
    private const OPT_TOKEN = 'grec_gsc_token';
    private const OPT_SNAPSHOT = 'grec_gsc_daily_snapshot';
    private const CRON = 'grec_gsc_daily_readonly';

    public static function init(): void {
        add_action( 'admin_menu', array( __CLASS__, 'menu' ) );
        add_action( 'admin_post_grec_gsc_settings', array( __CLASS__, 'save_settings' ) );
        add_action( 'admin_post_grec_gsc_authorize', array( __CLASS__, 'authorize' ) );
        add_action( 'admin_post_grec_gsc_oauth', array( __CLASS__, 'oauth_callback' ) );
        add_action( 'admin_post_grec_gsc_disconnect', array( __CLASS__, 'disconnect' ) );
        add_action( 'wp_abilities_api_init', array( __CLASS__, 'register_abilities' ), 30 );
        add_action( self::CRON, array( __CLASS__, 'daily_job' ) );
        add_action( 'init', array( __CLASS__, 'schedule' ), 30 );
    }

    public static function property(): string {
        // Exact WordPress origin property: never forward arbitrary user-supplied URLs to Google.
        return trailingslashit( home_url( '/' ) );
    }

    public static function redirect_uri(): string {
        return admin_url( 'admin-post.php?action=grec_gsc_oauth' );
    }

    private static function creds(): array {
        return GREC_Secrets::open( (string) get_option( self::OPT_CREDENTIALS, '' ) );
    }

    private static function token(): array {
        return GREC_Secrets::open( (string) get_option( self::OPT_TOKEN, '' ) );
    }

    public static function status( $input = array() ): array {
        $creds = self::creds();
        $token = self::token();
        $snapshot = get_option( self::OPT_SNAPSHOT, array() );
        return array(
            'provider' => 'google-search-console',
            'mode' => 'independent-readonly-oauth',
            'property' => self::property(),
            'configured' => ! empty( $creds['client_id'] ) && ! empty( $creds['client_secret'] ),
            'connected' => ! empty( $token['refresh_token'] ),
            'scheduled' => (bool) wp_next_scheduled( self::CRON ),
            'last_sync' => is_array( $snapshot ) ? ( $snapshot['fetched_at'] ?? null ) : null,
            'last_snapshot' => is_array( $snapshot ) ? ( $snapshot['totals'] ?? null ) : null,
            'scope' => self::SCOPE,
            'note' => 'URL Inspection is read only; Request Indexing is not available through this API.',
        );
    }

    private static function guard(): void {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( 'Administrator access required.', '', array( 'response' => 403 ) );
        }
    }

    private static function notice( string $message ): void {
        wp_safe_redirect( add_query_arg( 'gsc_notice', $message, admin_url( 'admin.php?page=grec-search-console' ) ) );
        exit;
    }

    public static function menu(): void {
        add_submenu_page(
            'engagement-core', 'Search Console', 'Search Console',
            'manage_options', 'grec-search-console', array( __CLASS__, 'render' )
        );
    }

    public static function render(): void {
        self::guard();
        $status = self::status();
        $notice = isset( $_GET['gsc_notice'] ) ? sanitize_text_field( wp_unslash( $_GET['gsc_notice'] ) ) : '';
        echo '<div class="wrap"><h1>Engagement Core — Google Search Console</h1>';
        if ( $notice ) { echo '<div class="notice notice-info"><p>' . esc_html( $notice ) . '</p></div>'; }
        echo '<p>Independent Google Search Console read-only integration. Does not alter Site Kit, AIOSEO or indexing.</p>';
        echo '<p><strong>Property:</strong> ' . esc_html( self::property() ) . '</p>';
        echo '<p><strong>Connection:</strong> ' . ( $status['connected'] ? 'Connected (read only)' : 'Not connected' ) . '</p>';
        echo '<p><strong>Last daily snapshot:</strong> ' . esc_html( (string) ( $status['last_sync'] ?: 'None' ) ) . '</p>';
        echo '<p>Enable Search Console API in your Google Cloud project, then create a Web Application OAuth client with this exact authorized redirect URI:</p>';
        echo '<p><code>' . esc_html( self::redirect_uri() ) . '</code></p>';
        echo '<form method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '">';
        echo '<input type="hidden" name="action" value="grec_gsc_settings">';
        wp_nonce_field( 'grec_gsc_settings' );
        echo '<p><label>Google OAuth Client ID<br><input type="text" name="client_id" size="65" autocomplete="off" value="' . esc_attr( (string) ( self::creds()['client_id'] ?? '' ) ) . '"></label></p>';
        echo '<p><label>Google OAuth Client Secret (leave blank to retain saved value)<br><input type="password" name="client_secret" autocomplete="new-password" size="65" value=""></label></p>';
        submit_button( 'Save Google API credentials' );
        echo '</form>';
        if ( $status['configured'] ) {
            echo '<p><a class="button button-primary" href="' . esc_url( wp_nonce_url( admin_url( 'admin-post.php?action=grec_gsc_authorize' ), 'grec_gsc_authorize' ) ) . '">Connect Google (read-only)</a></p>';
        }
        if ( $status['connected'] ) {
            echo '<form method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '">';
            echo '<input type="hidden" name="action" value="grec_gsc_disconnect">';
            wp_nonce_field( 'grec_gsc_disconnect' );
            submit_button( 'Disconnect Search Console', 'secondary' );
            echo '</form>';
        }
        echo '<p>Use the existing WP Control / GPT connection to inspect URLs, read search performance, sitemaps and connection status. No secrets are returned to GPT.</p></div>';
    }

    public static function save_settings(): void {
        self::guard();
        check_admin_referer( 'grec_gsc_settings' );
        $client_id = trim( (string) wp_unslash( $_POST['client_id'] ?? '' ) );
        $client_secret = trim( (string) wp_unslash( $_POST['client_secret'] ?? '' ) );
        if ( '' !== $client_id && ! preg_match( '/^[a-zA-Z0-9._-]+\\.apps\\.googleusercontent\\.com$/', $client_id ) ) {
            self::notice( 'Invalid Google OAuth client ID.' );
        }
        $prior = self::creds();
        $previous_id = (string) ( $prior['client_id'] ?? '' );
        if ( '' === $client_id ) { $client_id = $previous_id; }
        if ( '' === $client_secret ) { $client_secret = (string) ( $prior['client_secret'] ?? '' ); }
        if ( '' === $client_id || '' === $client_secret ) { self::notice( 'Provide both Google OAuth credentials.' ); }
        update_option( self::OPT_CREDENTIALS, GREC_Secrets::seal( array( 'client_id' => $client_id, 'client_secret' => $client_secret ) ), false );
        if ( $previous_id !== $client_id ) { delete_option( self::OPT_TOKEN ); }
        self::notice( 'API credentials saved securely. Connect Google to authorize read-only access.' );
    }

    public static function authorize(): void {
        self::guard();
        check_admin_referer( 'grec_gsc_authorize' );
        $creds = self::creds();
        if ( empty( $creds['client_id'] ) || empty( $creds['client_secret'] ) ) { self::notice( 'Save API credentials first.' ); }
        $state = wp_generate_password( 40, false, false );
        set_transient( 'grec_gsc_state_' . hash( 'sha256', $state ), get_current_user_id(), 10 * MINUTE_IN_SECONDS );
        $url = add_query_arg( array(
            'client_id' => $creds['client_id'],
            'redirect_uri' => self::redirect_uri(),
            'response_type' => 'code',
            'scope' => self::SCOPE,
            'access_type' => 'offline',
            'prompt' => 'consent',
            'state' => $state,
        ), self::AUTH_URL );
        wp_redirect( $url, 302, 'Engagement Core' ); // fixed Google OAuth endpoint.
        exit;
    }

    public static function oauth_callback(): void {
        self::guard();
        $state = sanitize_text_field( wp_unslash( $_GET['state'] ?? '' ) );
        if ( ! preg_match( '/^[a-zA-Z0-9]{40}$/', $state ) ) { self::notice( 'OAuth state invalid.' ); }
        $key = 'grec_gsc_state_' . hash( 'sha256', $state );
        $owner = (int) get_transient( $key );
        delete_transient( $key ); // single-use, even for failed callbacks.
        if ( ! $owner || $owner !== get_current_user_id() ) { self::notice( 'OAuth session expired or does not match.' ); }
        $code = sanitize_text_field( wp_unslash( $_GET['code'] ?? '' ) );
        if ( '' === $code || isset( $_GET['error'] ) ) { self::notice( 'Google authorization was cancelled.' ); }
        $creds = self::creds();
        $response = wp_remote_post( self::TOKEN_URL, array(
            'timeout' => 20, 'redirection' => 0,
            'body' => array(
                'code' => $code, 'client_id' => $creds['client_id'],
                'client_secret' => $creds['client_secret'],
                'redirect_uri' => self::redirect_uri(),
                'grant_type' => 'authorization_code',
            ),
        ) );
        if ( is_wp_error( $response ) || 200 !== wp_remote_retrieve_response_code( $response ) ) {
            self::notice( 'Google token exchange failed. Check OAuth client, redirect URI and permissions.' );
        }
        $body = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( ! is_array( $body ) || empty( $body['refresh_token'] ) || empty( $body['access_token'] ) ) {
            self::notice( 'No offline refresh token returned. Reauthorize with consent.' );
        }
        // Do not accept token grants without the exact readonly Google scope.
        if ( isset( $body['scope'] ) && ! in_array( self::SCOPE, preg_split( '/\\s+/', (string) $body['scope'] ), true ) ) {
            self::notice( 'Google did not grant Search Console read-only permission.' );
        }
        $token = array(
            'refresh_token' => (string) $body['refresh_token'],
            'access_token' => (string) $body['access_token'],
            'expires_at' => time() + max( 60, (int) ( $body['expires_in'] ?? 3600 ) - 60 ),
        );
        update_option( self::OPT_TOKEN, GREC_Secrets::seal( $token ), false );
        self::schedule();
        self::notice( 'Search Console connected with read-only permission.' );
    }

    public static function disconnect(): void {
        self::guard();
        check_admin_referer( 'grec_gsc_disconnect' );
        delete_option( self::OPT_TOKEN );
        delete_option( self::OPT_SNAPSHOT );
        wp_clear_scheduled_hook( self::CRON );
        self::notice( 'Disconnected and removed local credentials for Google access.' );
    }

    private static function access_token() {
        $creds = self::creds();
        $token = self::token();
        if ( empty( $creds['client_id'] ) || empty( $creds['client_secret'] ) || empty( $token['refresh_token'] ) ) {
            return new WP_Error( 'grec_gsc_not_connected', 'Connect Google Search Console in Engagement Core settings first.' );
        }
        if ( ! empty( $token['access_token'] ) && (int) ( $token['expires_at'] ?? 0 ) > time() + 30 ) {
            return $token['access_token'];
        }
        $response = wp_remote_post( self::TOKEN_URL, array(
            'timeout' => 20, 'redirection' => 0,
            'body' => array(
                'client_id' => $creds['client_id'],
                'client_secret' => $creds['client_secret'],
                'refresh_token' => $token['refresh_token'],
                'grant_type' => 'refresh_token',
            ),
        ) );
        if ( is_wp_error( $response ) || 200 !== wp_remote_retrieve_response_code( $response ) ) {
            return new WP_Error( 'grec_gsc_refresh_failed', 'Google Search Console token refresh failed. Reconnect in Engagement Core.' );
        }
        $body = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( empty( $body['access_token'] ) ) { return new WP_Error( 'grec_gsc_refresh_failed', 'Google did not issue an access token.' ); }
        $token['access_token'] = (string) $body['access_token'];
        $token['expires_at'] = time() + max( 60, (int) ( $body['expires_in'] ?? 3600 ) - 60 );
        update_option( self::OPT_TOKEN, GREC_Secrets::seal( $token ), false );
        return $token['access_token'];
    }

    private static function api( string $url, $body = null ) {
        $access = self::access_token();
        if ( is_wp_error( $access ) ) { return $access; }
        // All endpoints passed by this class are hardcoded Google HTTPS origins.
        $args = array(
            'timeout' => 20, 'redirection' => 0,
            'headers' => array( 'Authorization' => 'Bearer ' . $access, 'Accept' => 'application/json' ),
        );
        if ( null !== $body ) {
            $args['method'] = 'POST';
            $args['headers']['Content-Type'] = 'application/json';
            $args['body'] = wp_json_encode( $body );
        }
        $response = wp_remote_request( $url, $args );
        if ( is_wp_error( $response ) ) { return new WP_Error( 'grec_gsc_network', 'Google API request failed.' ); }
        $code = (int) wp_remote_retrieve_response_code( $response );
        if ( $code < 200 || $code >= 300 ) {
            return new WP_Error( 'grec_gsc_google_http_' . $code, 'Google Search Console API error (HTTP ' . $code . ').', array( 'status' => 502 ) );
        }
        $data = json_decode( wp_remote_retrieve_body( $response ), true );
        return is_array( $data ) ? $data : array();
    }

    public static function allowed_url( $url ): bool {
        if ( ! is_string( $url ) || strlen( $url ) > 2048 || false !== strpos( $url, '#' ) ) { return false; }
        $parts = wp_parse_url( $url );
        $home = wp_parse_url( home_url( '/' ) );
        return is_array( $parts ) && is_array( $home )
            && ( $parts['scheme'] ?? '' ) === 'https'
            && ( $parts['host'] ?? '' ) === ( $home['host'] ?? '' )
            && ! isset( $parts['user'] ) && ! isset( $parts['pass'] ) && ! isset( $parts['port'] )
            && empty( $parts['query'] );
    }

    public static function search( $input = array() ) {
        $input = is_array( $input ) ? $input : array();
        $end = isset( $input['end_date'] ) ? (string) $input['end_date'] : gmdate( 'Y-m-d', time() - 3 * DAY_IN_SECONDS );
        $start = isset( $input['start_date'] ) ? (string) $input['start_date'] : gmdate( 'Y-m-d', time() - 31 * DAY_IN_SECONDS );
        foreach ( array( $start, $end ) as $date ) {
            if ( ! preg_match( '/^\\d{4}-\\d{2}-\\d{2}$/', $date ) || gmdate( 'Y-m-d', strtotime( $date ) ) !== $date ) {
                return new WP_Error( 'grec_gsc_bad_dates', 'Use valid YYYY-MM-DD dates.' );
            }
        }
        if ( $start > $end || ( strtotime( $end ) - strtotime( $start ) ) > 90 * DAY_IN_SECONDS ) {
            return new WP_Error( 'grec_gsc_date_range', 'Date range must be ordered and at most 90 days.' );
        }
        $dimensions = $input['dimensions'] ?? array( 'query' );
        if ( ! is_array( $dimensions ) || count( $dimensions ) > 3 ||
            array_diff( $dimensions, array( 'date', 'query', 'page', 'device', 'country' ) ) ||
            count( array_unique( $dimensions ) ) !== count( $dimensions ) ) {
            return new WP_Error( 'grec_gsc_bad_dimensions', 'Unsupported or duplicate Search Console dimension.' );
        }
        $payload = array(
            'startDate' => $start, 'endDate' => $end,
            'dimensions' => array_values( $dimensions ),
            'rowLimit' => max( 1, min( 250, absint( $input['limit'] ?? 50 ) ) ),
        );
        if ( ! empty( $input['page_url'] ) ) {
            if ( ! self::allowed_url( $input['page_url'] ) ) { return new WP_Error( 'grec_gsc_bad_url', 'Only pages on this site can be filtered.' ); }
            $payload['dimensionFilterGroups'] = array( array(
                'filters' => array( array( 'dimension' => 'page', 'operator' => 'equals', 'expression' => $input['page_url'] ) ),
            ) );
        }
        $url = 'https://www.googleapis.com/webmasters/v3/sites/' . rawurlencode( self::property() ) . '/searchAnalytics/query';
        $data = self::api( $url, $payload );
        if ( is_wp_error( $data ) ) { return $data; }
        return array( 'property' => self::property(), 'start_date' => $start, 'end_date' => $end, 'dimensions' => $dimensions, 'rows' => $data['rows'] ?? array(), 'source' => 'google-search-console-direct' );
    }

    public static function inspect( $input = array() ) {
        $url = is_array( $input ) ? (string) ( $input['url'] ?? '' ) : '';
        if ( ! self::allowed_url( $url ) ) {
            return new WP_Error( 'grec_gsc_bad_url', 'Only canonical HTTPS URLs on the connected WordPress host can be inspected.' );
        }
        $data = self::api( 'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect', array(
            'inspectionUrl' => $url, 'siteUrl' => self::property(),
        ) );
        if ( is_wp_error( $data ) ) { return $data; }
        $result = $data['inspectionResult']['indexStatusResult'] ?? array();
        return array(
            'url' => $url, 'property' => self::property(),
            'verdict' => $result['verdict'] ?? null,
            'coverage_state' => $result['coverageState'] ?? null,
            'indexing_state' => $result['indexingState'] ?? null,
            'robots_txt_state' => $result['robotsTxtState'] ?? null,
            'last_crawl_time' => $result['lastCrawlTime'] ?? null,
            'google_canonical' => $result['googleCanonical'] ?? null,
            'user_canonical' => $result['userCanonical'] ?? null,
            'inspection_result_link' => $data['inspectionResult']['inspectionResultLink'] ?? null,
            'note' => 'Read-only inspection; no Request Indexing action exists for ordinary pages.',
        );
    }

    public static function sitemaps( $input = array() ) {
        $url = 'https://www.googleapis.com/webmasters/v3/sites/' . rawurlencode( self::property() ) . '/sitemaps';
        $data = self::api( $url );
        if ( is_wp_error( $data ) ) { return $data; }
        return array( 'property' => self::property(), 'sitemaps' => $data['sitemap'] ?? array() );
    }

    public static function schedule(): void {
        if ( ! empty( self::token()['refresh_token'] ) && ! wp_next_scheduled( self::CRON ) ) {
            wp_schedule_event( time() + HOUR_IN_SECONDS, 'daily', self::CRON );
        }
    }

    public static function daily_job(): void {
        if ( empty( self::token()['refresh_token'] ) ) { return; }
        $report = self::search( array( 'dimensions' => array( 'date' ), 'limit' => 45 ) );
        if ( is_wp_error( $report ) ) { return; }
        $totals = array( 'clicks' => 0, 'impressions' => 0 );
        foreach ( $report['rows'] as $row ) {
            $totals['clicks'] += (float) ( $row['clicks'] ?? 0 );
            $totals['impressions'] += (int) ( $row['impressions'] ?? 0 );
        }
        update_option( self::OPT_SNAPSHOT, array(
            'fetched_at' => gmdate( 'c' ),
            'through' => $report['end_date'], 'totals' => $totals,
        ), false );
        // No Telegram publishing, sharing, indexing writes, or unsolicited external notifications.
    }

    public static function register_abilities(): void {
        if ( ! function_exists( 'wp_register_ability' ) ) { return; }
        $abilities = array(
            'gsc-status' => array( 'Search Console connection status', 'Return readonly OAuth connection and daily snapshot status; never return credentials.', 'status', array() ),
            'gsc-search' => array( 'Search Console performance', 'Read settled impressions, clicks, CTR and rankings directly from Google.', 'search', array( 'type'=>'object','properties'=>array(
                'start_date'=>array('type'=>'string'), 'end_date'=>array('type'=>'string'),
                'dimensions'=>array('type'=>'array','items'=>array('type'=>'string')),
                'page_url'=>array('type'=>'string'), 'limit'=>array('type'=>'integer','minimum'=>1,'maximum'=>250),
            ) ) ),
            'gsc-inspect' => array( 'Inspect Google indexing', 'Read Google indexed/canonical state of one same-site URL. Cannot request indexing.', 'inspect', array( 'type'=>'object','required'=>array('url'),'properties'=>array('url'=>array('type'=>'string')) ) ),
            'gsc-sitemaps' => array( 'List Google sitemaps', 'Read submitted Search Console sitemaps and their download/errors.', 'sitemaps', array() ),
        );
        foreach ( $abilities as $slug => $info ) {
            $args = array(
                'label' => $info[0], 'description' => $info[1], 'category' => 'wp-control',
                'execute_callback' => array( __CLASS__, $info[2] ),
                'permission_callback' => array( __CLASS__, 'can_manage_options' ),
                'meta' => array( 'public'=>true, 'show_in_rest'=>true,
                    'mcp'=>array('public'=>true),
                    'annotations'=>array('readonly'=>true,'destructive'=>false,'idempotent'=>true) ),
            );
            if ( $info[3] ) { $args['input_schema'] = $info[3]; }
            wp_register_ability( 'wp-control/' . $slug, $args );
        }
    }

    public static function can_manage_options(): bool {
        return current_user_can( 'manage_options' );
    }
}
