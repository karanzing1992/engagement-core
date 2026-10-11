<?php
/**
 * Media Studio cloud-worker handoff for our own WordPress control bridge.
 * All API writes use the existing deployment secret with a different HMAC context.
 * No social publishing/scheduling or arbitrary HTTP downloader exists here.
 */
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class GREC_Media_Queue {
    private const NONCE_CONTEXT = 'mrs-media-queue-v1';
    private const MEDIA_POST_TYPE = 'mrs_reel';
    private const PREFIX = '_mrs_';
    private const ALLOWED_PRIVATE_REPO = 'karanzing1992/moksha_wordpress';

    public static function init(): void {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 30 );
    }

    public static function register_routes(): void {
        register_rest_route( 'wp-control/v1', '/media-studio/queue', array(
            'methods' => 'POST',
            'callback' => array( __CLASS__, 'create_draft' ),
            'permission_callback' => array( __CLASS__, 'authorized' ),
        ) );
        register_rest_route( 'wp-control/v1', '/media-studio/queue/(?P<id>\d+)/preview', array(
            'methods' => 'POST',
            'callback' => array( __CLASS__, 'attach_preview' ),
            'permission_callback' => array( __CLASS__, 'authorized' ),
        ) );
        register_rest_route( 'wp-control/v1', '/media-studio/queue/(?P<id>\d+)', array(
            'methods' => 'GET',
            'callback' => array( __CLASS__, 'get_status' ),
            'permission_callback' => array( __CLASS__, 'authorized' ),
        ) );
    }

    public static function authorized( $request ): bool {
        $secret = (string) get_option( 'deployer_for_git_api_secret', '' );
        $token  = is_object( $request ) ? (string) $request->get_header( 'X-WP-Control-Media-Token' ) : '';
        if ( strlen( $secret ) < 20 || ! preg_match( '/^[0-9a-f]{64}$/D', $token ) ) {
            return false;
        }
        return hash_equals( hash_hmac( 'sha256', self::NONCE_CONTEXT, $secret ), $token );
    }

    private static function error( string $code, string $message, int $status = 400 ): WP_Error {
        return new WP_Error( $code, $message, array( 'status' => $status ) );
    }

    private static function ready() {
        if ( ! class_exists( 'MRS_Studio' ) || ! class_exists( 'MRS_Policy' ) || ! post_type_exists( self::MEDIA_POST_TYPE ) ) {
            return self::error( 'mrs_queue_not_installed', 'Private Media Studio is not active.', 503 );
        }
        return true;
    }

    private static function serializable_job( int $id ): array {
        return array(
            'ok' => true,
            'id' => $id,
            'job_key' => (string) get_post_meta( $id, self::PREFIX . 'job_key', true ),
            'status' => (string) ( get_post_meta( $id, self::PREFIX . 'state', true ) ?: 'draft' ),
            'worker_state' => (string) ( get_post_meta( $id, self::PREFIX . 'worker_state', true ) ?: 'queued' ),
            'private_preview_url' => (string) get_post_meta( $id, self::PREFIX . 'private_preview_url', true ),
            'publish_enabled' => false,
            'schedule_enabled' => false,
        );
    }

    public static function create_draft( WP_REST_Request $request ) {
        $ready = self::ready();
        if ( is_wp_error( $ready ) ) { return $ready; }
        $data = $request->get_json_params();
        if ( ! is_array( $data ) ) { return self::error( 'mrs_queue_invalid', 'Expected JSON object.' ); }
        $job_key = sanitize_key( (string) ( $data['job_key'] ?? '' ) );
        if ( ! preg_match( '/^[a-z0-9_-]{12,100}$/D', $job_key ) ) {
            return self::error( 'mrs_queue_job_key', 'Invalid idempotency key.' );
        }
        $option = 'mrs_queue_id_' . sha1( $job_key );
        $existing = (int) get_option( $option, 0 );
        if ( $existing && get_post_type( $existing ) === self::MEDIA_POST_TYPE && get_post_status( $existing ) === 'private' ) {
            return new WP_REST_Response( self::serializable_job( $existing ), 200 );
        }
        $brand = sanitize_key( (string) ( $data['brand'] ?? 'moksha' ) );
        $policies = MRS_Policy::brand_policies();
        if ( ! isset( $policies[ $brand ] ) ) { return self::error( 'mrs_queue_brand', 'Unsupported brand profile.' ); }
        $title   = sanitize_text_field( (string) ( $data['title'] ?? '' ) );
        $topic   = sanitize_text_field( (string) ( $data['topic'] ?? '' ) );
        $script  = sanitize_textarea_field( (string) ( $data['script'] ?? '' ) );
        $caption = sanitize_textarea_field( (string) ( $data['caption'] ?? '' ) );
        $notes   = sanitize_textarea_field( (string) ( $data['notes'] ?? '' ) );
        if ( '' === $title || '' === $topic || strlen( $title ) > 180 || strlen( $topic ) > 240 ) {
            return self::error( 'mrs_queue_fields', 'Title and topic are required.' );
        }
        $copy_issues = MRS_Policy::validate_creative( $brand, $script, $caption );
        if ( $copy_issues ) { return self::error( 'mrs_queue_copy', implode( ' ', $copy_issues ) ); }
        $duration = filter_var( $data['duration_seconds'] ?? 85, FILTER_VALIDATE_INT );
        if ( false === $duration || $duration < 10 || $duration > (int) $policies[ $brand ]['max_duration_seconds'] ) {
            return self::error( 'mrs_queue_duration', 'Duration outside allowed range.' );
        }
        $ledger = $data['ledger'] ?? array();
        if ( ! is_array( $ledger ) || strlen( wp_json_encode( $ledger ) ) > 24000 ) {
            return self::error( 'mrs_queue_ledger', 'Ledger must be a small JSON array.' );
        }
        $ledger_errors = MRS_Policy::validate_ledger( $ledger );
        if ( $ledger_errors ) { return self::error( 'mrs_queue_ledger', implode( ' ', $ledger_errors ) ); }
        $id = wp_insert_post( array(
            'post_type' => self::MEDIA_POST_TYPE,
            'post_status' => 'private',
            'post_title' => $title,
            'post_author' => 0,
        ), true );
        if ( is_wp_error( $id ) || ! $id ) {
            return self::error( 'mrs_queue_insert', 'Unable to create private WordPress draft.', 500 );
        }
        $fields = array(
            'brand' => $brand, 'topic' => $topic, 'script' => $script,
            'caption' => $caption, 'notes' => $notes,
            'duration_seconds' => (int) $duration, 'ledger' => $ledger,
            'logo_attachment_id' => 0, 'logo_verified' => false,
            'private_preview_url' => '', 'natural_audio_only' => true,
            'no_voiceover' => true, 'state' => 'draft',
            'worker_state' => 'queued', 'job_key' => $job_key,
            'audit' => array( array( 'at' => gmdate( 'c' ), 'action' => 'private_draft_queued_via_wp_control' ) ),
        );
        foreach ( $fields as $key => $value ) { update_post_meta( (int) $id, self::PREFIX . $key, $value ); }
        if ( ! add_option( $option, (int) $id, '', false ) ) {
            // Fail closed rather than creating a second job under a racing request.
            wp_delete_post( (int) $id, true );
            $known = (int) get_option( $option, 0 );
            if ( $known ) { return new WP_REST_Response( self::serializable_job( $known ), 200 ); }
            return self::error( 'mrs_queue_race', 'Concurrent job creation. Retry the same idempotency key.', 409 );
        }
        return new WP_REST_Response( self::serializable_job( (int) $id ), 201 );
    }

    private static function job_matches( int $id, string $key ) {
        if ( get_post_type( $id ) !== self::MEDIA_POST_TYPE || get_post_status( $id ) !== 'private' ||
            ! hash_equals( (string) get_post_meta( $id, self::PREFIX . 'job_key', true ), $key ) ) {
            return self::error( 'mrs_queue_not_found', 'Private job not found.', 404 );
        }
        return true;
    }

    private static function valid_private_preview( string $url ): bool {
        $parts = wp_parse_url( $url );
        if ( ! is_array( $parts ) || strtolower( (string) ( $parts['scheme'] ?? '' ) ) !== 'https' ||
             strtolower( (string) ( $parts['host'] ?? '' ) ) !== 'github.com' ||
             isset( $parts['user'] ) || isset( $parts['pass'] ) || isset( $parts['query'] ) || isset( $parts['fragment'] ) ) { return false; }
        return (bool) preg_match( '#^/' . preg_quote( self::ALLOWED_PRIVATE_REPO, '#' ) . '/actions/runs/[0-9]+/artifacts/[0-9]+/?$#iD', (string) ( $parts['path'] ?? '' ) );
    }

    public static function attach_preview( WP_REST_Request $request ) {
        $ready = self::ready();
        if ( is_wp_error( $ready ) ) { return $ready; }
        $data = $request->get_json_params();
        if ( ! is_array( $data ) ) { return self::error( 'mrs_queue_json', 'Expected JSON object.' ); }
        $id = absint( $request['id'] );
        $key = sanitize_key( (string) ( $data['job_key'] ?? '' ) );
        $match = self::job_matches( $id, $key );
        if ( is_wp_error( $match ) ) { return $match; }
        $state = (string) get_post_meta( $id, self::PREFIX . 'state', true );
        if ( $state === 'approved' ) { return self::error( 'mrs_queue_approved', 'Worker cannot modify an approved creative.', 409 ); }
        $url = esc_url_raw( (string) ( $data['private_preview_url'] ?? '' ) );
        if ( ! self::valid_private_preview( $url ) ) { return self::error( 'mrs_queue_preview', 'Preview must belong to the designated private GitHub repository.' ); }
        $ledger = $data['ledger'] ?? array();
        if ( ! is_array( $ledger ) || empty( $ledger ) || strlen( wp_json_encode( $ledger ) ) > 24000 ) {
            return self::error( 'mrs_queue_ledger', 'Complete license ledger required.' );
        }
        $ledger_errors = MRS_Policy::validate_ledger( $ledger );
        if ( $ledger_errors ) { return self::error( 'mrs_queue_ledger', implode( ' ', $ledger_errors ) ); }
        update_post_meta( $id, self::PREFIX . 'ledger', $ledger );
        update_post_meta( $id, self::PREFIX . 'private_preview_url', $url );
        update_post_meta( $id, self::PREFIX . 'worker_state', 'rendered' );
        update_post_meta( $id, self::PREFIX . 'state', 'preview_ready' );
        $audit = get_post_meta( $id, self::PREFIX . 'audit', true );
        $audit = is_array( $audit ) ? array_slice( $audit, -49 ) : array();
        $audit[] = array( 'at' => gmdate( 'c' ), 'action' => 'private_preview_attached_from_worker' );
        update_post_meta( $id, self::PREFIX . 'audit', $audit );
        return new WP_REST_Response( self::serializable_job( $id ), 200 );
    }

    public static function get_status( WP_REST_Request $request ) {
        $id = absint( $request['id'] );
        $key = sanitize_key( (string) ( $request->get_param( 'job_key' ) ?? '' ) );
        $matched = self::job_matches( $id, $key );
        return is_wp_error( $matched ) ? $matched : new WP_REST_Response( self::serializable_job( $id ), 200 );
    }
}