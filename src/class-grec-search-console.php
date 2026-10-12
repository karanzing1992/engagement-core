<?php
/**
 * Direct Google Search Console integration (read-only).
 *
 * Independent OAuth connection; NEVER reads Site Kit or YouTube tokens.
 * WordPress admin controls credentials; GPT/REST exposes aggregate reports only.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_Search_Console {
    private const CLIENT_ID = 'grec_gsc_client_id';
    private const SECRET = 'grec_gsc_sealed_credentials';
    private const SNAPSHOT = 'grec_gsc_daily_snapshot';
    private const HOOK = 'grec_gsc_daily_sync';
    private const SCOPE = 'https://www.googleapis.com/auth/webmasters.readonly';

    public static function init(): void {
        add_action( 'admin_menu', array( __CLASS__, 'menu' ) );
        add_action( 'admin_post_grec_gsc_save', array( __CLASS__, 'save' ) );
        add_action( 'admin_post_grec_gsc_connect', array( __CLASS__, 'connect' ) );
        add_action( 'admin_post_grec_gsc_callback', array( __CLASS__, 'callback' ) );
        add_action( 'admin_post_grec_gsc_disconnect', array( __CLASS__, 'disconnect' ) );
        add_action( 'admin_post_grec_gsc_sync', array( __CLASS__, 'admin_sync' ) );
        add_action( self::HOOK, array( __CLASS__, 'daily_sync' ) );
        add_action( 'init', array( __CLASS__, 'ensure_schedule' ), 21 );
        add_action( 'wp_abilities_api_init', array( __CLASS__, 'abilities' ), 30 );
    }

    public static function property(): string {
        // Intentional: one WordPress installation and one corresponding GSC property.
        return trailingslashit( home_url( '/' ) );
    }

    public static function callback_url(): string {
        return admin_url( 'admin-post.php?action=grec_gsc_callback' );
    }

    public static function allowed_local_url( string $url ): bool {
        $origin = wp_parse_url( self::property() );
        $parsed = wp_parse_url( $url );
        if ( ! is_array( $origin ) || ! is_array( $parsed ) ) { return false; }
        if ( ! in_array( strtolower( (string) ( $parsed['scheme'] ?? '' ) ), array( 'https' ), true ) ) { return false; }
        if ( ! hash_equals( strtolower( (string) ( $origin['host'] ?? '' ) ), strtolower( (string) ( $parsed['host'] ?? '' ) ) ) ) { return false; }
        if ( ! empty( $parsed['user'] ) || ! empty( $parsed['pass'] ) || ! empty( $parsed['port'] ) ) { return false; }
        return 0 === strpos( (string) ( $parsed['path'] ?? '/' ), (string) ( $origin['path'] ?? '/' ) );
    }

    private static function secret(): array {
        return GREC_Secrets::open( (string) get_option( self::SECRET, '' ) );
    }

    private static function store( array $value ): void {
        update_option( self::SECRET, GREC_Secrets::seal( $value ), false );
    }

    public static function status(): array {
        $s = self::secret();
        $snapshot = get_option( self::SNAPSHOT, array() );
        return array(
            'provider' => 'google-search-console',
            'site_url' => self::property(),
            'scope' => self::SCOPE,
            'oauth_client_configured' => '' !== (string) get_option( self::CLIENT_ID, '' ) && ! empty( $s['client_secret'] ),
            'connected' => ! empty( $s['refresh_token'] ),
            'daily_sync_scheduled' => (bool) wp_next_scheduled( self::HOOK ),
            'last_snapshot' => is_array( $snapshot ) && ! empty( $snapshot['retrieved_at'] ) ? $snapshot : null,
        );
    }

    private static function admin_guard( string $nonce ): void {
        if ( ! current_user_can( 'manage_options' ) ) { wp_die( 'Administrator access required.' ); }
        check_admin_referer( $nonce );
    }

    private static function back( string $message, bool $error = false ): void {
        wp_safe_redirect( add_query_arg( array(
            'page' => 'grec-gsc',
            'gsc_note' => rawurlencode( $message ),
            'gsc_error' => $error ? '1' : '0',
        ), admin_url( 'admin.php' ) ) );
        exit;
    }

    public static function save(): void {
        self::admin_guard( 'grec_gsc_save' );
        $id = trim( sanitize_text_field( (string) wp_unslash( $_POST['client_id'] ?? '' ) ) );
        $new_secret = trim( (string) wp_unslash( $_POST['client_secret'] ?? '' ) );
        if ( ! preg_match( '/^[a-zA-Z0-9._-]+\\.apps\\.googleusercontent\\.com$/', $id ) ) {
            self::back( 'Enter a valid Google OAuth web client ID.', true );
        }
        $old = (string) get_option( self::CLIENT_ID, '' );
        $stored = self::secret();
        if ( $old !== $id ) { $stored = array(); }
        if ( '' !== $new_secret ) { $stored['client_secret'] = $new_secret; }
        if ( empty( $stored['client_secret'] ) ) { self::back( 'Client secret is required.', true ); }
        update_option( self::CLIENT_ID, $id, false );
        self::store( $stored );
        self::back( 'Credentials saved securely. Authorize with Google next.' );
    }

    public static function connect(): void {
        self::admin_guard( 'grec_gsc_connect' );
        $id = (string) get_option( self::CLIENT_ID, '' );
        if ( '' === $id || empty( self::secret()['client_secret'] ) ) {
            self::back( 'Save a dedicated Google OAuth web client first.', true );
        }
        $state = bin2hex( random_bytes( 24 ) );
        set_transient( 'grec_gsc_state_' . get_current_user_id(), $state, 10 * MINUTE_IN_SECONDS );
        $url = add_query_arg( array(
            'client_id' => $id,
            'redirect_uri' => self::callback_url(),
            'response_type' => 'code',
            'scope' => self::SCOPE,
            'access_type' => 'offline',
            'prompt' => 'consent',
            'state' => $state,
        ), 'https://accounts.google.com/o/oauth2/v2/auth' );
        wp_redirect( esc_url_raw( $url ), 302, 'Engagement Core' );
        exit;
    }

    public static function callback(): void {
        if ( ! current_user_can( 'manage_options' ) ) { wp_die( 'Administrator access required.' ); }
        $saved = (string) get_transient( 'grec_gsc_state_' . get_current_user_id() );
        $state = sanitize_text_field( (string) wp_unslash( $_GET['state'] ?? '' ) );
        delete_transient( 'grec_gsc_state_' . get_current_user_id() );
        if ( '' === $saved || '' === $state || ! hash_equals( $saved, $state ) ) {
            self::back( 'Google authorization state mismatch.', true );
        }
        if ( isset( $_GET['error'] ) ) { self::back( 'Google authorization was cancelled or denied.', true ); }
        $code = (string) wp_unslash( $_GET['code'] ?? '' );
        if ( '' === $code || strlen( $code ) > 4096 ) { self::back( 'Missing Google authorization code.', true ); }
        try {
            $old = self::secret();
            $token = self::token_request( array(
                'code' => $code,
                'redirect_uri' => self::callback_url(),
                'grant_type' => 'authorization_code',
            ) );
            if ( empty( $token['refresh_token'] ) ) { throw new RuntimeException( 'No offline refresh token issued; revoke prior access and reconnect.' ); }
            // Validate property access before accepting the new connection.
            self::request_with_access_token( 'GET', 'https://www.googleapis.com/webmasters/v3/sites/' . rawurlencode( self::property() ), $token['access_token'] );
            self::store( array(
                'client_secret' => $old['client_secret'],
                'refresh_token' => $token['refresh_token'],
                'access_token' => $token['access_token'],
                'expires_at' => time() + max( 60, (int) ( $token['expires_in'] ?? 3600 ) ),
            ) );
            self::ensure_schedule();
            self::back( 'Read-only Search Console connected. Daily reporting enabled.' );
        } catch ( Throwable $e ) {
            self::back( 'Connection failed: ' . $e->getMessage(), true );
        }
    }

    private static function token_request( array $params ): array {
        $s = self::secret();
        $params['client_id'] = (string) get_option( self::CLIENT_ID, '' );
        $params['client_secret'] = (string) ( $s['client_secret'] ?? '' );
        $response = wp_remote_post( 'https://oauth2.googleapis.com/token', array(
            'timeout' => 25, 'body' => $params, 'redirection' => 0,
        ) );
        return self::decode_google( $response, 'Google token' );
    }

    private static function decode_google( $response, string $operation ): array {
        if ( is_wp_error( $response ) ) { throw new RuntimeException( $operation . ' transport error.' ); }
        $body = json_decode( wp_remote_retrieve_body( $response ), true );
        $code = (int) wp_remote_retrieve_response_code( $response );
        if ( $code < 200 || $code >= 300 || ! is_array( $body ) ) {
            // Never echo the raw response, which can contain sensitive values.
            throw new RuntimeException( $operation . ' failed (HTTP ' . $code . ').' );
        }
        return $body;
    }

    private static function access_token(): string {
        $s = self::secret();
        if ( empty( $s['refresh_token'] ) ) { throw new RuntimeException( 'Connect Search Console in WordPress admin first.' ); }
        if ( ! empty( $s['access_token'] ) && (int) ( $s['expires_at'] ?? 0 ) > time() + 90 ) {
            return (string) $s['access_token'];
        }
        $fresh = self::token_request( array( 'refresh_token' => $s['refresh_token'], 'grant_type' => 'refresh_token' ) );
        if ( empty( $fresh['access_token'] ) ) { throw new RuntimeException( 'Google token refresh failed.' ); }
        $s['access_token'] = $fresh['access_token'];
        $s['expires_at'] = time() + max( 60, (int) ( $fresh['expires_in'] ?? 3600 ) );
        if ( ! empty( $fresh['refresh_token'] ) ) { $s['refresh_token'] = $fresh['refresh_token']; }
        self::store( $s );
        return $s['access_token'];
    }

    private static function request_with_access_token( string $method, string $url, string $access_token, array $body = array() ): array {
        $args = array(
            'method' => $method, 'timeout' => 25, 'redirection' => 0,
            'headers' => array( 'Authorization' => 'Bearer ' . $access_token, 'Accept' => 'application/json' ),
        );
        if ( 'POST' === $method ) {
            $args['headers']['Content-Type'] = 'application/json';
            $args['body'] = wp_json_encode( $body );
        }
        return self::decode_google( wp_remote_request( $url, $args ), 'Search Console API' );
    }

    private static function request( string $method, string $url, array $body = array() ): array {
        return self::request_with_access_token( $method, $url, self::access_token(), $body );
    }

    public static function report( string $group_by = 'date' ): array {
        if ( ! in_array( $group_by, array( 'date', 'query', 'page', 'device' ), true ) ) {
            throw new InvalidArgumentException( 'Unsupported Search Console dimension.' );
        }
        $key = 'grec_gsc_report_' . $group_by;
        $cached = get_transient( $key );
        if ( is_array( $cached ) ) { return $cached; }
        // Use settled data; Google Search Console typically lags by 2-3 days.
        $start = gmdate( 'Y-m-d', time() - 31 * DAY_IN_SECONDS );
        $end = gmdate( 'Y-m-d', time() - 3 * DAY_IN_SECONDS );
        $data = self::request( 'POST', 'https://www.googleapis.com/webmasters/v3/sites/' . rawurlencode( self::property() ) . '/searchAnalytics/query', array(
            'startDate' => $start, 'endDate' => $end,
            'dimensions' => array( $group_by ), 'type' => 'web', 'rowLimit' => 40,
        ) );
        $rows = array();
        foreach ( array_slice( (array) ( $data['rows'] ?? array() ), 0, 40 ) as $row ) {
            if ( ! is_array( $row ) ) { continue; }
            $rows[] = array(
                'key' => sanitize_text_field( (string) ( $row['keys'][0] ?? '' ) ),
                'clicks' => (int) ( $row['clicks'] ?? 0 ),
                'impressions' => (int) ( $row['impressions'] ?? 0 ),
                'ctr' => round( (float) ( $row['ctr'] ?? 0 ), 5 ),
                'position' => round( (float) ( $row['position'] ?? 0 ), 2 ),
            );
        }
        $report = array( 'site_url' => self::property(), 'dimension' => $group_by, 'start_date' => $start, 'end_date' => $end, 'rows' => $rows, 'retrieved_at' => gmdate( 'c' ) );
        set_transient( $key, $report, 6 * HOUR_IN_SECONDS );
        return $report;
    }

    public static function inspect( int $post_id ): array {
        $post = get_post( $post_id );
        if ( ! $post || 'publish' !== $post->post_status || ! in_array( $post->post_type, array( 'page', 'post' ), true ) ) {
            throw new InvalidArgumentException( 'Inspect a published local page or post.' );
        }
        $url = get_permalink( $post );
        if ( ! is_string( $url ) || ! self::allowed_local_url( $url ) ) {
            throw new InvalidArgumentException( 'Inspection URL is outside this WordPress site.' );
        }
        $data = self::request( 'POST', 'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect', array(
            'inspectionUrl' => $url, 'siteUrl' => self::property(), 'languageCode' => 'en-US',
        ) );
        $result = (array) ( $data['inspectionResult']['indexStatusResult'] ?? array() );
        $fields = array( 'verdict', 'coverageState', 'indexingState', 'lastCrawlTime', 'googleCanonical', 'userCanonical', 'robotsTxtState', 'pageFetchState', 'crawledAs' );
        $clean = array();
        foreach ( $fields as $field ) { $clean[ $field ] = sanitize_text_field( (string) ( $result[ $field ] ?? '' ) ); }
        return array( 'url' => $url, 'property' => self::property(), 'index' => $clean, 'retrieved_at' => gmdate( 'c' ) );
    }

    public static function ensure_schedule(): void {
        if ( empty( self::secret()['refresh_token'] ) ) { return; }
        if ( ! wp_next_scheduled( self::HOOK ) ) {
            wp_schedule_event( time() + HOUR_IN_SECONDS, 'daily', self::HOOK );
        }
    }

    public static function daily_sync(): void {
        if ( empty( self::secret()['refresh_token'] ) ) { return; }
        try {
            delete_transient( 'grec_gsc_report_date' );
            $daily = self::report( 'date' );
            $snapshot = array(
                'retrieved_at' => $daily['retrieved_at'],
                'date_range' => array( $daily['start_date'], $daily['end_date'] ),
                'clicks' => array_sum( array_column( $daily['rows'], 'clicks' ) ),
                'impressions' => array_sum( array_column( $daily['rows'], 'impressions' ) ),
                'last_error' => null,
            );
            // Inspect only Moksha's canonical Mud Bath page once per daily sync.
            $page = get_page_by_path( 'mud-bath-goa' );
            if ( $page && 'publish' === $page->post_status ) {
                $snapshot['mud_bath_inspection'] = self::inspect( (int) $page->ID );
            }
            update_option( self::SNAPSHOT, $snapshot, false );
        } catch ( Throwable $e ) {
            $snapshot = get_option( self::SNAPSHOT, array() );
            if ( ! is_array( $snapshot ) ) { $snapshot = array(); }
            $snapshot['last_error'] = sanitize_text_field( $e->getMessage() );
            $snapshot['last_attempt'] = gmdate( 'c' );
            update_option( self::SNAPSHOT, $snapshot, false );
        }
    }

    public static function disconnect(): void {
        self::admin_guard( 'grec_gsc_disconnect' );
        $s = self::secret();
        self::store( array( 'client_secret' => (string) ( $s['client_secret'] ?? '' ) ) );
        wp_clear_scheduled_hook( self::HOOK );
        foreach ( array( 'date', 'query', 'page', 'device' ) as $d ) { delete_transient( 'grec_gsc_report_' . $d ); }
        delete_option( self::SNAPSHOT );
        self::back( 'Google Search Console tokens disconnected locally. Site Kit is unchanged.' );
    }

    public static function admin_sync(): void {
        self::admin_guard( 'grec_gsc_sync' );
        self::daily_sync();
        $s = self::status();
        self::back( empty( $s['last_snapshot']['last_error'] ) ? 'Search Console snapshot updated.' : 'Sync error; see dashboard details.', ! empty( $s['last_snapshot']['last_error'] ) );
    }

    public static function abilities(): void {
        if ( ! function_exists( 'wp_register_ability' ) ) { return; }
        foreach ( array(
            'wp-control/gsc-status' => array( 'Google Search Console connection status', array(), 'status_ability' ),
            'wp-control/gsc-report' => array( 'Google Search Console performance', array(
                'type' => 'object', 'properties' => array(
                    'dimension' => array( 'type' => 'string', 'enum' => array( 'date', 'query', 'page', 'device' ), 'default' => 'date' ),
                ),
            ), 'report_ability' ),
            'wp-control/gsc-inspect' => array( 'Inspect Google indexing for a published page', array(
                'type' => 'object', 'required' => array( 'post_id' ), 'properties' => array(
                    'post_id' => array( 'type' => 'integer', 'minimum' => 1 ),
                ),
            ), 'inspect_ability' ),
        ) as $name => $meta ) {
            $args = array(
                'label' => $meta[0],
                'description' => 'Moksha WordPress authenticated read-only Search Console operation. Never exposes OAuth credentials.',
                'category' => 'wp-control',
                'execute_callback' => array( __CLASS__, $meta[2] ),
                'permission_callback' => array( __CLASS__, 'can_manage' ),
                'meta' => array(
                    'public' => true, 'show_in_rest' => true,
                    'annotations' => array( 'readonly' => true, 'destructive' => false, 'idempotent' => true ),
                    'mcp' => array( 'public' => true ),
                ),
            );
            if ( $meta[1] ) { $args['input_schema'] = $meta[1]; }
            wp_register_ability( $name, $args );
        }
    }

    public static function can_manage(): bool { return current_user_can( 'manage_options' ); }
    public static function status_ability(): array { return self::status(); }
    public static function report_ability( $input = array() ): array {
        try { return array( 'ok' => true, 'data' => self::report( (string) ( $input['dimension'] ?? 'date' ) ) ); }
        catch ( Throwable $e ) { return array( 'ok' => false, 'error' => $e->getMessage() ); }
    }
    public static function inspect_ability( $input = array() ): array {
        try { return array( 'ok' => true, 'data' => self::inspect( (int) ( $input['post_id'] ?? 0 ) ) ); }
        catch ( Throwable $e ) { return array( 'ok' => false, 'error' => $e->getMessage() ); }
    }

    public static function menu(): void {
        add_submenu_page( 'engagement-core', 'Search Console', 'Search Console', 'manage_options', 'grec-gsc', array( __CLASS__, 'render' ) );
    }

    public static function render(): void {
        if ( ! current_user_can( 'manage_options' ) ) { wp_die( 'Administrator access required.' ); }
        $s = self::status();
        $note = sanitize_text_field( (string) wp_unslash( $_GET['gsc_note'] ?? '' ) );
        ?>
        <div class="wrap"><h1>Moksha · Google Search Console</h1>
        <p>Direct, independent and free read-only Google API integration. Existing Google Site Kit remains untouched.</p>
        <?php if ( $note ) : ?><div class="notice <?php echo ! empty( $_GET['gsc_error'] ) && '1' === $_GET['gsc_error'] ? 'notice-error' : 'notice-success'; ?>"><p><?php echo esc_html( $note ); ?></p></div><?php endif; ?>
        <p><strong>Property:</strong> <?php echo esc_html( $s['site_url'] ); ?> · <strong>Connected:</strong> <?php echo $s['connected'] ? 'Yes' : 'No'; ?> · <strong>Daily sync:</strong> <?php echo $s['daily_sync_scheduled'] ? 'Scheduled' : 'Not scheduled'; ?></p>
        <p>Enable Search Console API in your Google Cloud project; create a Web application OAuth client with redirect URI:<br><code><?php echo esc_html( self::callback_url() ); ?></code></p>
        <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
          <input type="hidden" name="action" value="grec_gsc_save"><?php wp_nonce_field( 'grec_gsc_save' ); ?>
          <table class="form-table">
            <tr><th><label for="grec-gsc-id">OAuth client ID</label></th><td><input class="regular-text" id="grec-gsc-id" name="client_id" value="<?php echo esc_attr( get_option( self::CLIENT_ID, '' ) ); ?>" required></td></tr>
            <tr><th><label for="grec-gsc-secret">OAuth client secret</label></th><td><input class="regular-text" id="grec-gsc-secret" name="client_secret" type="password" autocomplete="new-password" placeholder="Leave blank to retain saved secret"></td></tr>
          </table>
          <?php submit_button( 'Save dedicated Google client' ); ?>
        </form>
        <?php foreach ( array( 'connect' => 'Authorize Google read-only', 'sync' => 'Sync now', 'disconnect' => 'Disconnect tokens' ) as $action => $label ) : ?>
        <form method="post" style="display:inline-block;margin-right:12px" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
          <input type="hidden" name="action" value="grec_gsc_<?php echo esc_attr( $action ); ?>">
          <?php wp_nonce_field( 'grec_gsc_' . $action ); ?>
          <?php submit_button( $label, 'secondary', 'submit', false ); ?>
        </form>
        <?php endforeach; ?>
        <h2>Last daily snapshot</h2>
        <pre><?php echo esc_html( wp_json_encode( $s['last_snapshot'], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) ); ?></pre>
        <p>GPT control abilities (administrator only): <code>wp-control/gsc-status</code>, <code>wp-control/gsc-report</code>, <code>wp-control/gsc-inspect</code>. No bulk submissions or automated Request Indexing.</p>
        </div>
        <?php
    }
}
