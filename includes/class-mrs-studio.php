<?php
/** WordPress admin workspace; intentionally contains no publishing/scheduling operations. */
defined( 'ABSPATH' ) || exit;

final class MRS_Studio {
    private const POST_TYPE = 'mrs_reel';
    private const META = '_mrs_';
    private const PAGE = 'mrs-studio';

    public static function register(): void {
        add_action( 'init', array( __CLASS__, 'register_post_type' ) );
        add_action( 'admin_menu', array( __CLASS__, 'admin_menu' ) );
        add_action( 'admin_enqueue_scripts', array( __CLASS__, 'enqueue_admin' ) );
        add_action( 'admin_post_mrs_save', array( __CLASS__, 'admin_save' ) );
        add_action( 'admin_post_mrs_transition', array( __CLASS__, 'admin_transition' ) );
        add_action( 'rest_api_init', array( __CLASS__, 'register_rest' ) );
    }

    public static function register_post_type(): void {
        register_post_type( self::POST_TYPE, array(
            'label'               => 'Private Reel Drafts',
            'public'              => false,
            'publicly_queryable'  => false,
            'exclude_from_search' => true,
            'show_ui'             => false,
            'show_in_rest'        => false,
            'supports'            => array( 'title' ),
            'rewrite'             => false,
            'query_var'           => false,
            'can_export'          => true,
        ) );
    }

    public static function admin_menu(): void {
        add_menu_page(
            'Media Studio', 'Media Studio', 'manage_options', self::PAGE,
            array( __CLASS__, 'admin_page' ), 'dashicons-format-video', 59
        );
    }

    public static function enqueue_admin( string $hook ): void {
        if ( 'toplevel_page_' . self::PAGE !== $hook || ! current_user_can( 'manage_options' ) ) {
            return;
        }
        wp_enqueue_style( 'mrs-media-studio', MRS_STUDIO_URL . 'assets/admin.css', array(), MRS_STUDIO_VERSION );
        wp_enqueue_media();
        wp_enqueue_script( 'mrs-media-studio', MRS_STUDIO_URL . 'assets/admin.js', array( 'jquery', 'media-views' ), MRS_STUDIO_VERSION, true );
    }

    /** Restrict every operation to an administrator. No public or unauthenticated REST. */
    public static function permission(): bool {
        return current_user_can( 'manage_options' );
    }

    public static function register_rest(): void {
        register_rest_route( 'mrs/v1', '/jobs', array(
            array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_list' ), 'permission_callback' => array( __CLASS__, 'permission' ) ),
            array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_create' ), 'permission_callback' => array( __CLASS__, 'permission' ) ),
        ) );
        register_rest_route( 'mrs/v1', '/jobs/(?P<id>\d+)', array(
            array( 'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_get' ), 'permission_callback' => array( __CLASS__, 'permission' ) ),
            array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_edit' ), 'permission_callback' => array( __CLASS__, 'permission' ) ),
        ) );
        register_rest_route( 'mrs/v1', '/jobs/(?P<id>\d+)/manifest', array(
            'methods' => 'GET', 'callback' => array( __CLASS__, 'rest_manifest' ), 'permission_callback' => array( __CLASS__, 'permission' ),
        ) );
        register_rest_route( 'mrs/v1', '/jobs/(?P<id>\d+)/transition', array(
            'methods' => 'POST', 'callback' => array( __CLASS__, 'rest_transition' ), 'permission_callback' => array( __CLASS__, 'permission' ),
        ) );
    }

    private static function error( string $message, int $status = 400 ): WP_Error {
        return new WP_Error( 'mrs_invalid', $message, array( 'status' => $status ) );
    }

    private static function valid_job( int $id ) {
        $post = get_post( $id );
        if ( ! $post || $post->post_type !== self::POST_TYPE || $post->post_status !== 'private' ) {
            return self::error( 'Private Reel job not found.', 404 );
        }
        return $post;
    }

    private static function collect( array $data ) {
        $brand = sanitize_key( (string) ( $data['brand'] ?? 'moksha' ) );
        $policies = MRS_Policy::brand_policies();
        if ( ! isset( $policies[ $brand ] ) ) {
            return self::error( 'Unsupported brand profile.' );
        }
        $title = sanitize_text_field( (string) ( $data['title'] ?? '' ) );
        $topic = sanitize_text_field( (string) ( $data['topic'] ?? '' ) );
        $script = sanitize_textarea_field( (string) ( $data['script'] ?? '' ) );
        $caption = sanitize_textarea_field( (string) ( $data['caption'] ?? '' ) );
        $notes = sanitize_textarea_field( (string) ( $data['notes'] ?? '' ) );
        if ( $title === '' || $topic === '' || strlen( $title ) > 180 || strlen( $topic ) > 240 ) {
            return self::error( 'A short title and topic are required.' );
        }
        $errors = MRS_Policy::validate_creative( $brand, $script, $caption );
        if ( $errors ) {
            return self::error( implode( ' ', $errors ) );
        }
        $duration = filter_var( $data['duration_seconds'] ?? 85, FILTER_VALIDATE_INT );
        if ( false === $duration || $duration < 10 || $duration > (int) $policies[ $brand ]['max_duration_seconds'] ) {
            return self::error( 'Duration must be 10–180 seconds.' );
        }
        $ledger_input = $data['ledger'] ?? array();
        if ( is_string( $ledger_input ) ) {
            $ledger_input = trim( $ledger_input );
            $ledger_input = $ledger_input === '' ? array() : json_decode( $ledger_input, true );
        }
        if ( ! is_array( $ledger_input ) || ( $ledger_input !== array() && array_keys( $ledger_input ) !== range( 0, count( $ledger_input ) - 1 ) ) ) {
            return self::error( 'License ledger must be a JSON array.' );
        }
        if ( strlen( wp_json_encode( $ledger_input ) ) > 24000 ) {
            return self::error( 'License ledger is too large.' );
        }
        $ledger_errors = MRS_Policy::validate_ledger( $ledger_input );
        if ( $ledger_errors ) {
            return self::error( implode( ' ', $ledger_errors ) );
        }
        $logo_id = absint( $data['logo_attachment_id'] ?? 0 );
        $verified = ! empty( $data['logo_verified'] );
        if ( $logo_id && ( get_post_type( $logo_id ) !== 'attachment' || ! wp_attachment_is_image( $logo_id ) ) ) {
            return self::error( 'Logo must be an existing WordPress image attachment.' );
        }
        if ( $logo_id && ! $verified ) {
            return self::error( 'Confirm that the logo is an official approved asset.' );
        }
        // Do not use WordPress Media Library for unreleased previews: its attachment URLs
        // are ordinarily publicly accessible, even when the related draft is private.
        $preview = esc_url_raw( (string) ( $data['private_preview_url'] ?? '' ) );
        if ( $preview !== '' && ! self::is_private_artifact_link( $preview ) ) {
            return self::error( 'Use a GitHub Actions artifact link from an access-controlled repository.' );
        }
        return array(
            'brand'                  => $brand,
            'title'                  => $title,
            'topic'                  => $topic,
            'script'                 => $script,
            'caption'                => $caption,
            'notes'                  => $notes,
            'duration_seconds'       => $duration,
            'ledger'                 => $ledger_input,
            'logo_attachment_id'     => $logo_id,
            'logo_verified'          => $logo_id > 0 && $verified,
            'private_preview_url'   => $preview,
            'natural_audio_only'     => $brand === 'moksha' || ! empty( $data['natural_audio_only'] ),
            'no_voiceover'           => $brand === 'moksha' || ! empty( $data['no_voiceover'] ),
        );
    }

    private static function is_private_artifact_link( string $url ): bool {
        $parts = wp_parse_url( $url );
        if ( ! is_array( $parts ) || strtolower( $parts['scheme'] ?? '' ) !== 'https' || strtolower( $parts['host'] ?? '' ) !== 'github.com' || isset( $parts['user'] ) || isset( $parts['query'] ) || isset( $parts['fragment'] ) ) {
            return false;
        }
        return preg_match( '#^/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[0-9]+/artifacts/[0-9]+/?$#', $parts['path'] ?? '' ) === 1;
    }

    private static function audit( int $id, string $action ): void {
        $events = get_post_meta( $id, self::META . 'audit', true );
        $events = is_array( $events ) ? array_slice( $events, -49 ) : array();
        $events[] = array( 'at' => gmdate( 'c' ), 'admin_id' => get_current_user_id(), 'action' => $action );
        update_post_meta( $id, self::META . 'audit', $events );
    }

    private static function persist( int $id, array $data ): void {
        foreach ( $data as $key => $value ) {
            update_post_meta( $id, self::META . $key, $value );
        }
        self::audit( $id, 'saved_private_draft' );
    }

    public static function save( array $payload, int $existing_id = 0 ) {
        if ( ! self::permission() ) {
            return self::error( 'Administrator permission required.', 403 );
        }
        $values = self::collect( $payload );
        if ( is_wp_error( $values ) ) {
            return $values;
        }
        if ( $existing_id ) {
            $job = self::valid_job( $existing_id );
            if ( is_wp_error( $job ) ) {
                return $job;
            }
            $post_id = wp_update_post( array( 'ID' => $existing_id, 'post_title' => $values['title'], 'post_status' => 'private' ), true );
        } else {
            $post_id = wp_insert_post( array(
                'post_type' => self::POST_TYPE, 'post_status' => 'private',
                'post_title' => $values['title'], 'post_author' => get_current_user_id(),
            ), true );
        }
        if ( is_wp_error( $post_id ) || ! $post_id ) {
            return is_wp_error( $post_id ) ? $post_id : self::error( 'Could not save private draft.' );
        }
        if ( ! $existing_id ) {
            update_post_meta( $post_id, self::META . 'state', 'draft' );
        } else {
            $prior_preview = (string) get_post_meta( $post_id, self::META . 'private_preview_url', true );
            $state = get_post_meta( $post_id, self::META . 'state', true );
            // A changed preview or changed creative copy invalidates prior approval.
            $changed = $prior_preview !== $values['private_preview_url'] ||
                get_post_meta( $post_id, self::META . 'script', true ) !== $values['script'] ||
                get_post_meta( $post_id, self::META . 'caption', true ) !== $values['caption'] ||
                get_post_meta( $post_id, self::META . 'ledger', true ) !== $values['ledger'];
            if ( $changed && ( $state === 'approved' || $state === 'preview_ready' ) ) {
                update_post_meta( $post_id, self::META . 'state', 'draft' );
            }
        }
        self::persist( (int) $post_id, $values );
        return (int) $post_id;
    }

    public static function transition( int $id, string $to ) {
        if ( ! self::permission() ) {
            return self::error( 'Administrator permission required.', 403 );
        }
        $post = self::valid_job( $id );
        if ( is_wp_error( $post ) ) {
            return $post;
        }
        $from = get_post_meta( $id, self::META . 'state', true ) ?: 'draft';
        if ( ! MRS_Policy::can_transition( $from, $to ) ) {
            return self::error( 'Invalid approval transition.' );
        }
        if ( $to === 'preview_ready' || $to === 'approved' ) {
            $preview = (string) get_post_meta( $id, self::META . 'private_preview_url', true );
            $ledger = get_post_meta( $id, self::META . 'ledger', true );
            if ( ! self::is_private_artifact_link( $preview ) || ! is_array( $ledger ) || empty( $ledger ) || MRS_Policy::validate_ledger( $ledger ) ) {
                return self::error( 'An access-controlled GitHub artifact link and complete source ledger are required for review.' );
            }
        }
        update_post_meta( $id, self::META . 'state', $to );
        self::audit( $id, 'review_state:' . $from . '>' . $to );
        return self::job_data( $id );
    }

    public static function job_data( int $id ): array {
        $post = get_post( $id );
        $fields = array(
            'brand', 'topic', 'script', 'caption', 'notes', 'duration_seconds', 'ledger',
            'logo_attachment_id', 'logo_verified', 'private_preview_url', 'natural_audio_only', 'no_voiceover', 'state',
        );
        $out = array( 'id' => $id, 'title' => $post->post_title, 'created_at' => $post->post_date_gmt );
        foreach ( $fields as $key ) {
            $out[ $key ] = get_post_meta( $id, self::META . $key, true );
        }
        $out['state'] = $out['state'] ?: 'draft';
        $out['ledger'] = is_array( $out['ledger'] ) ? $out['ledger'] : array();
        $out['preview_url'] = ! empty( $out['private_preview_url'] ) ? $out['private_preview_url'] : null;
        return $out;
    }

    public static function rest_list( WP_REST_Request $request ): WP_REST_Response {
        $limit = min( 40, max( 1, absint( $request->get_param( 'per_page' ) ?: 20 ) ) );
        $posts = get_posts( array( 'post_type' => self::POST_TYPE, 'post_status' => 'private', 'numberposts' => $limit, 'orderby' => 'date', 'order' => 'DESC' ) );
        return new WP_REST_Response( array_map( static function( $post ) { return self::job_data( $post->ID ); }, $posts ), 200 );
    }

    public static function rest_create( WP_REST_Request $request ) {
        $id = self::save( (array) $request->get_json_params() );
        return is_wp_error( $id ) ? $id : new WP_REST_Response( self::job_data( $id ), 201 );
    }

    public static function rest_get( WP_REST_Request $request ) {
        $post = self::valid_job( absint( $request['id'] ) );
        return is_wp_error( $post ) ? $post : new WP_REST_Response( self::job_data( $post->ID ), 200 );
    }

    public static function rest_edit( WP_REST_Request $request ) {
        $id = self::save( (array) $request->get_json_params(), absint( $request['id'] ) );
        return is_wp_error( $id ) ? $id : new WP_REST_Response( self::job_data( $id ), 200 );
    }

    public static function rest_manifest( WP_REST_Request $request ) {
        $post = self::valid_job( absint( $request['id'] ) );
        return is_wp_error( $post ) ? $post : new WP_REST_Response( MRS_Policy::manifest( self::job_data( $post->ID ) ), 200 );
    }

    public static function rest_transition( WP_REST_Request $request ) {
        $to = sanitize_key( (string) ( $request->get_param( 'to' ) ?? '' ) );
        $data = self::transition( absint( $request['id'] ), $to );
        return is_wp_error( $data ) ? $data : new WP_REST_Response( $data, 200 );
    }

    private static function safe_redirect( int $id = 0, string $status = 'saved' ): void {
        wp_safe_redirect( add_query_arg( array( 'page' => self::PAGE, 'edit' => $id, 'mrs_notice' => $status ), admin_url( 'admin.php' ) ) );
        exit;
    }

    public static function admin_save(): void {
        if ( ! self::permission() ) {
            wp_die( esc_html__( 'Administrator permission required.', 'mrs-media-studio' ), '', array( 'response' => 403 ) );
        }
        check_admin_referer( 'mrs_save' );
        $data = wp_unslash( $_POST );
        $id = self::save( $data, absint( $data['job_id'] ?? 0 ) );
        if ( is_wp_error( $id ) ) {
            wp_die( esc_html( $id->get_error_message() ), 'Unable to save private draft', array( 'response' => 400, 'back_link' => true ) );
        }
        self::safe_redirect( $id, 'saved' );
    }

    public static function admin_transition(): void {
        if ( ! self::permission() ) {
            wp_die( esc_html__( 'Administrator permission required.', 'mrs-media-studio' ), '', array( 'response' => 403 ) );
        }
        check_admin_referer( 'mrs_transition' );
        $id = absint( $_POST['job_id'] ?? 0 );
        $to = sanitize_key( wp_unslash( $_POST['to'] ?? '' ) );
        $result = self::transition( $id, $to );
        if ( is_wp_error( $result ) ) {
            wp_die( esc_html( $result->get_error_message() ), 'Review blocked', array( 'response' => 400, 'back_link' => true ) );
        }
        self::safe_redirect( $id, 'reviewed' );
    }

    public static function admin_page(): void {
        if ( ! self::permission() ) {
            wp_die( esc_html__( 'Administrator permission required.', 'mrs-media-studio' ), '', array( 'response' => 403 ) );
        }
        $edit_id = absint( $_GET['edit'] ?? 0 );
        $job = null;
        if ( $edit_id ) {
            $post = self::valid_job( $edit_id );
            if ( is_wp_error( $post ) ) {
                wp_die( 'Private draft not found', '', array( 'response' => 404 ) );
            }
            $job = self::job_data( $edit_id );
        }
        $jobs = get_posts( array( 'post_type' => self::POST_TYPE, 'post_status' => 'private', 'numberposts' => 30, 'orderby' => 'date', 'order' => 'DESC' ) );
        $policy = MRS_Policy::brand_policies();
        ?>
        <div class="wrap mrs-workspace">
            <div class="mrs-heading"><div><p class="mrs-eyebrow">Private workspace · No publishing</p><h1>Media Studio</h1><p>Draft, source, render externally, and review editorial Reels. No social publishing or scheduling code exists in this plugin.</p></div><span class="mrs-safety">Approval-gated</span></div>
            <?php if ( isset( $_GET['mrs_notice'] ) ) : ?><div class="notice notice-success is-dismissible"><p>Private draft updated. No social activity was triggered.</p></div><?php endif; ?>
            <div class="mrs-layout">
                <section class="mrs-panel"><h2><?php echo $job ? 'Edit private draft #' . (int) $edit_id : 'Create a private Reel'; ?></h2>
                    <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
                        <?php wp_nonce_field( 'mrs_save' ); ?>
                        <input type="hidden" name="action" value="mrs_save">
                        <input type="hidden" name="job_id" value="<?php echo (int) $edit_id; ?>">
                        <label for="mrs-title">Internal project name</label><input id="mrs-title" class="widefat" type="text" name="title" maxlength="180" required value="<?php echo esc_attr( $job['title'] ?? '' ); ?>">
                        <label for="mrs-brand">Editorial profile</label><select id="mrs-brand" name="brand" class="widefat">
                            <?php foreach ( $policy as $id => $settings ) : ?><option value="<?php echo esc_attr( $id ); ?>" <?php selected( $job['brand'] ?? 'moksha', $id ); ?>><?php echo esc_html( $settings['label'] ); ?></option><?php endforeach; ?>
                        </select>
                        <label for="mrs-topic">Subject / research topic</label><input id="mrs-topic" class="widefat" name="topic" maxlength="240" required value="<?php echo esc_attr( $job['topic'] ?? '' ); ?>" placeholder="What does calm sound like?">
                        <label for="mrs-length">Duration (seconds)</label><input id="mrs-length" class="small-text" type="number" name="duration_seconds" min="10" max="180" value="<?php echo (int) ( $job['duration_seconds'] ?? 85 ); ?>">
                        <label for="mrs-script">On-screen copy / script</label><textarea id="mrs-script" class="widefat" name="script" rows="5" maxlength="6000" placeholder="Put on headphones. Listen to the rain, birds, waves…"><?php echo esc_textarea( $job['script'] ?? '' ); ?></textarea>
                        <label for="mrs-caption">Draft caption (never published automatically)</label><textarea id="mrs-caption" class="widefat" name="caption" rows="3" maxlength="2200"><?php echo esc_textarea( $job['caption'] ?? '' ); ?></textarea>
                        <label for="mrs-ledger">Media sources and licenses · JSON array</label><textarea id="mrs-ledger" class="widefat mrs-code" name="ledger" rows="5" spellcheck="false" placeholder='[{"source_url":"https://…","license_url":"https://…","license_name":"CC BY 3.0","creator":"Creator name"}]'><?php echo esc_textarea( $job ? wp_json_encode( $job['ledger'], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) : '[]' ); ?></textarea>
                        <p class="description">Source/license details are mandatory before marking a preview ready or approved.</p>
                        <div class="mrs-checks"><label><input type="checkbox" name="natural_audio_only" value="1" <?php checked( $job['natural_audio_only'] ?? true ); ?>> Authentic nature sounds, no music (required for wellness profile)</label><label><input type="checkbox" name="no_voiceover" value="1" <?php checked( $job['no_voiceover'] ?? true ); ?>> No narration (required for wellness profile)</label></div>
                        <label for="mrs-preview">Private preview · GitHub Actions artifact link</label>
                        <input class="widefat" type="url" id="mrs-preview" name="private_preview_url" placeholder="https://github.com/OWNER/REPO/actions/runs/123/artifacts/456" value="<?php echo esc_attr( $job['private_preview_url'] ?? '' ); ?>">
                        <p class="description">Use a private repository artifact. WordPress Media Library videos can be publicly accessible, so we never upload unreleased preview MP4s there.</p>
                        <label for="mrs-logo">Optional verified official logo attachment</label>
                        <div class="mrs-media-picker"><input type="number" id="mrs-logo" class="small-text" name="logo_attachment_id" min="0" value="<?php echo (int) ( $job['logo_attachment_id'] ?? 0 ); ?>" placeholder="Image ID"><button type="button" class="button mrs-select-media" data-type="image" data-input="#mrs-logo">Select verified image</button></div>
                        <label><input type="checkbox" name="logo_verified" value="1" <?php checked( $job['logo_verified'] ?? false ); ?>> I confirm any selected logo is the approved, original brand asset</label>
                        <label for="mrs-notes">Internal production notes (not creative copy)</label><textarea id="mrs-notes" class="widefat" name="notes" rows="2"><?php echo esc_textarea( $job['notes'] ?? '' ); ?></textarea>
                        <p><button type="submit" class="button button-primary button-hero">Save private draft</button> <?php if ( $job ) : ?><a class="button" href="<?php echo esc_url( admin_url( 'admin.php?page=mrs-studio' ) ); ?>">New draft</a><?php endif; ?></p>
                    </form>
                    <?php if ( $job ) : self::render_review( $job ); endif; ?>
                </section>
                <section class="mrs-panel"><h2>Draft queue</h2><p class="description">Admin-only records. Approval is for creative review, not for publishing.</p>
                    <?php if ( empty( $jobs ) ) : ?><p>No drafts yet. Create the first Reel on the left.</p><?php endif; ?>
                    <?php foreach ( $jobs as $item ) : $entry = self::job_data( $item->ID ); ?>
                        <div class="mrs-job"><div><span class="mrs-job-title"><?php echo esc_html( $entry['title'] ); ?></span><p><?php echo esc_html( $entry['topic'] ); ?></p><small><?php echo esc_html( $entry['duration_seconds'] ); ?> sec · #<?php echo (int) $entry['id']; ?></small></div><div><span class="mrs-state"><?php echo esc_html( str_replace( '_', ' ', $entry['state'] ) ); ?></span><p><a href="<?php echo esc_url( add_query_arg( array( 'page' => self::PAGE, 'edit' => $entry['id'] ), admin_url( 'admin.php' ) ) ); ?>">Edit & review</a></p></div></div>
                    <?php endforeach; ?>
                </section>
            </div>
            <p class="mrs-footnote">Production: WordPress remains lightweight; video rendering belongs on an isolated worker. Publishing/scheduling integrations intentionally do not exist in v0.1.0.</p>
        </div>
        <?php
    }

    private static function render_review( array $job ): void {
        $state = $job['state'];
        $next = MRS_Policy::TRANSITIONS[ $state ] ?? array();
        echo '<div class="mrs-review"><h3>Private review</h3><p>Current status: <strong>' . esc_html( str_replace( '_', ' ', $state ) ) . '</strong></p>';
        if ( ! empty( $job['preview_url'] ) ) {
            echo '<p><a class="button" href="' . esc_url( $job['preview_url'] ) . '" target="_blank" rel="noopener noreferrer">Open private preview artifact in GitHub ↗</a></p>';
        } else {
            echo '<p class="description">Link a draft video artifact from an access-controlled GitHub repository above and save. No preview has been attached.</p>';
        }
        foreach ( $next as $to ) {
            $labels = array( 'preview_ready' => 'Mark ready for review', 'approved' => 'Approve creative ONLY', 'needs_revision' => 'Request revisions', 'draft' => 'Return to draft' );
            echo '<form method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '" class="mrs-inline">';
            echo '<input type="hidden" name="action" value="mrs_transition"><input type="hidden" name="job_id" value="' . (int) $job['id'] . '"><input type="hidden" name="to" value="' . esc_attr( $to ) . '">';
            wp_nonce_field( 'mrs_transition' );
            echo '<button class="button" type="submit">' . esc_html( $labels[ $to ] ?? $to ) . '</button></form> ';
        }
        echo '<p class="description">Approved creatives remain private. There is no Publish, Schedule or Send action.</p></div>';
    }
}