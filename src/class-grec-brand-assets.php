<?php
/**
 * Verified brand-asset resolver for Media Studio and in-house WordPress Control.
 * Source of truth: specific approved Google Drive file, mirrored byte-for-byte in this plugin.
 * No fuzzy logo search, AI generation, substitutions, remote arbitrary URLs, or publishing.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_Brand_Assets {
    private const DRIVE_ID = '1XwmlYRfjfkcnbEOlJLNJc8bGHm9uxkyv';
    private const DRIVE_PARENT = '1vfbteCPWk_-JscgYk2WhW9rT9yU9yEYt';
    private const DRIVE_MODIFIED_AT = '2026-09-14T06:46:05.135Z';
    private const SHA256 = '76e89b83667827da4b5d89143fb267f4000a9392eff685129c838c3d0b24748c';
    private const FILENAME = 'moksha-logo-source.jpg';
    private const WIDTH = 737;
    private const HEIGHT = 681;
    private const SIZE_BYTES = 81501;
    private const WP_OPTION = 'grec_brand_logo_moksha_official_v1';
    private const TOKEN_CONTEXT = 'mrs-brand-assets-v1';
    private const META_SHA = '_grec_brand_sha256';
    private const META_DRIVE_ID = '_grec_brand_drive_file_id';

    public static function init(): void {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ), 30 );
        // Existing Media Studio plugin does not expose a custom asset filter.
        // Apply the verified logo after its final logo_verified post meta is saved.
        add_action( 'added_post_meta', array( __CLASS__, 'maybe_autofill_logo' ), 20, 4 );
        add_action( 'updated_post_meta', array( __CLASS__, 'maybe_autofill_logo' ), 20, 4 );
    }

    public static function register_routes(): void {
        register_rest_route( 'wp-control/v1', '/brand-assets/moksha/sync', array(
            'methods' => 'POST',
            'callback' => array( __CLASS__, 'rest_sync' ),
            'permission_callback' => array( __CLASS__, 'authorized' ),
        ) );
        register_rest_route( 'wp-control/v1', '/brand-assets/moksha/resolve', array(
            'methods' => 'GET',
            'callback' => array( __CLASS__, 'rest_resolve' ),
            'permission_callback' => array( __CLASS__, 'authorized' ),
        ) );
        register_rest_route( 'wp-control/v1', '/brand-assets/moksha/status', array(
            'methods' => 'GET',
            'callback' => array( __CLASS__, 'rest_status' ),
            'permission_callback' => array( __CLASS__, 'authorized' ),
        ) );
    }

    public static function authorized( $request ): bool {
        // Administrators may use normal nonce-authenticated WordPress REST calls.
        if ( function_exists( 'current_user_can' ) && current_user_can( 'manage_options' ) ) {
            return true;
        }
        $secret = (string) get_option( 'deployer_for_git_api_secret', '' );
        $token = is_object( $request ) ? (string) $request->get_header( 'X-WP-Control-Brand-Token' ) : '';
        if ( strlen( $secret ) < 20 || ! preg_match( '/^[0-9a-f]{64}$/D', $token ) ) { return false; }
        return hash_equals( hash_hmac( 'sha256', self::TOKEN_CONTEXT, $secret ), $token );
    }

    private static function error( string $code, string $message, int $status = 400 ) {
        return new WP_Error( $code, $message, array( 'status' => $status ) );
    }

    private static function original_file(): string {
        return GREC_DIR . 'assets/brand/' . self::FILENAME;
    }

    public static function validate_source() {
        $source = self::original_file();
        if ( ! is_file( $source ) || is_link( $source ) || filesize( $source ) !== self::SIZE_BYTES ) {
            return self::error( 'brand_source_unavailable', 'Exact approved master logo is missing or has an unexpected size.', 409 );
        }
        $sha = hash_file( 'sha256', $source );
        if ( ! is_string( $sha ) || ! hash_equals( self::SHA256, $sha ) ) {
            return self::error( 'brand_source_changed', 'Cached logo differs from the approved Drive original. Manual reapproval required.', 409 );
        }
        $dimensions = @getimagesize( $source );
        if ( ! is_array( $dimensions ) || (int) $dimensions[0] !== self::WIDTH ||
            (int) $dimensions[1] !== self::HEIGHT || (int) ($dimensions[2] ?? 0) !== IMAGETYPE_JPEG ) {
            return self::error( 'brand_source_invalid', 'Official master image properties differ from the approved source.', 409 );
        }
        return true;
    }

    /** Trust only an attachment whose actual physical file matches the approved master checksum. */
    public static function verified_attachment( int $id ): bool {
        if ( $id < 1 || get_post_type( $id ) !== 'attachment' ) { return false; }
        if ( (string) get_post_meta( $id, self::META_SHA, true ) !== self::SHA256 ||
             (string) get_post_meta( $id, self::META_DRIVE_ID, true ) !== self::DRIVE_ID ) { return false; }
        $file = get_attached_file( $id );
        return is_string( $file ) && is_file( $file ) && ! is_link( $file ) &&
            filesize( $file ) === self::SIZE_BYTES &&
            hash_equals( self::SHA256, (string) hash_file( 'sha256', $file ) );
    }

    public static function saved_attachment_id(): int {
        $id = (int) get_option( self::WP_OPTION, 0 );
        return $id > 0 && self::verified_attachment( $id ) ? $id : 0;
    }

    public static function import_master() {
        $source_ok = self::validate_source();
        if ( is_wp_error( $source_ok ) ) { return $source_ok; }
        $registered = (int) get_option( self::WP_OPTION, 0 );
        if ( $registered > 0 ) {
            if ( ! self::verified_attachment( $registered ) ) {
                // A changed or deleted registered attachment is not silently replaced.
                return self::error( 'brand_registered_asset_changed', 'Previously registered official logo failed checksum verification. Intervention required.', 409 );
            }
            return array( 'id' => $registered, 'imported' => false );
        }
        // Recover from a partial prior import only if bytes AND provenance metadata match.
        $candidates = get_posts( array(
            'post_type' => 'attachment', 'post_status' => 'inherit', 'posts_per_page' => 20,
            'meta_key' => self::META_DRIVE_ID, 'meta_value' => self::DRIVE_ID,
            'fields' => 'ids',
        ) );
        foreach ( $candidates as $candidate ) {
            $candidate = (int) $candidate;
            if ( self::verified_attachment( $candidate ) ) {
                update_option( self::WP_OPTION, $candidate, false );
                return array( 'id' => $candidate, 'imported' => false );
            }
        }
        $data = file_get_contents( self::original_file() );
        if ( ! is_string( $data ) || ! hash_equals( self::SHA256, hash( 'sha256', $data ) ) ) {
            return self::error( 'brand_source_read_failed', 'Official logo cannot be read reliably.', 500 );
        }
        // Import a copy, never modify/reprocess the Drive or repository master.
        $filename = 'moksha-wellness-official-logo-' . substr( self::SHA256, 0, 12 ) . '.jpg';
        $up = wp_upload_bits( $filename, null, $data );
        if ( ! is_array( $up ) || ! empty( $up['error'] ) || empty( $up['file'] ) || ! is_file( $up['file'] ) ) {
            return self::error( 'brand_upload_failed', 'Could not import official logo into WordPress Media Library.', 500 );
        }
        if ( ! hash_equals( self::SHA256, (string) hash_file( 'sha256', $up['file'] ) ) ) {
            @unlink( $up['file'] );
            return self::error( 'brand_import_corrupt', 'Imported copy does not match Drive master checksum.', 500 );
        }
        require_once ABSPATH . 'wp-admin/includes/image.php';
        $id = wp_insert_attachment( array(
            'post_mime_type' => 'image/jpeg',
            'post_title' => 'Moksha Wellness – Verified Official Master Logo',
            'post_content' => '',
            'post_status' => 'inherit',
        ), $up['file'], 0, true );
        if ( is_wp_error( $id ) || ! $id ) {
            @unlink( $up['file'] );
            return self::error( 'brand_import_register_failed', 'Official copy could not be registered as a WordPress attachment.', 500 );
        }
        $id = (int) $id;
        // Canonical file remains untouched. WordPress derivatives may be generated for previews.
        $meta = wp_generate_attachment_metadata( $id, $up['file'] );
        if ( is_array( $meta ) ) { wp_update_attachment_metadata( $id, $meta ); }
        update_post_meta( $id, self::META_SHA, self::SHA256 );
        update_post_meta( $id, self::META_DRIVE_ID, self::DRIVE_ID );
        update_post_meta( $id, '_grec_brand_source', 'approved-google-drive-master' );
        update_post_meta( $id, '_wp_attachment_image_alt', 'Official gold Moksha Wellness floral emblem and wordmark on black' );
        if ( ! self::verified_attachment( $id ) ) {
            return self::error( 'brand_import_verification_failed', 'Imported logo could not be reverified after registration.', 500 );
        }
        update_option( self::WP_OPTION, $id, false );
        return array( 'id' => $id, 'imported' => true );
    }

    /** For server-to-server jobs and assistant tools: do not guess files based on name. */
    public static function choose( string $brand, string $placement ) {
        if ( 'moksha' !== $brand ) { return self::error( 'brand_not_approved', 'No verified source of truth is registered for this brand.', 404 ); }
        $modes = array(
            'reel' => array( 'display' => 'closing_logo', 'not_before_seconds' => 1.5, 'width_px_1080' => 300, 'exclude_first_hook' => true ),
            'short' => array( 'display' => 'closing_logo', 'not_before_seconds' => 1.5, 'width_px_1080' => 300, 'exclude_first_hook' => true ),
            'story' => array( 'display' => 'corner_card', 'safe_top_px' => 230, 'safe_bottom_px' => 320, 'width_px_1080' => 190 ),
            'feed' => array( 'display' => 'corner_card', 'width_px_1080' => 220 ),
            'google-business' => array( 'display' => 'corner_card', 'width_px_1080' => 220 ),
            'whatsapp' => array( 'display' => 'corner_card', 'width_px_1080' => 220 ),
            'pinterest' => array( 'display' => 'corner_card', 'width_px_1080' => 220 ),
            'website' => array( 'display' => 'full_original', 'width_px_1080' => 320 ),
            'print' => array( 'display' => 'full_original', 'width_px_1080' => 320 ),
        );
        if ( ! isset( $modes[ $placement ] ) ) {
            return self::error( 'brand_placement_unsupported', 'No approved logo placement exists for this output.', 400 );
        }
        $source_ok = self::validate_source();
        if ( is_wp_error( $source_ok ) ) { return $source_ok; }
        $id = self::saved_attachment_id();
        if ( ! $id ) {
            return self::error( 'brand_logo_not_synced', 'Approved logo has not been imported into WordPress. Run the trusted sync first.', 409 );
        }
        return array(
            'brand' => 'moksha', 'role' => 'official_full_logo', 'variant' => 'original_gold_on_black',
            'attachment_id' => $id, 'asset_url' => (string) wp_get_attachment_url( $id ),
            // Immutable mirror of the identical approved Drive bytes; use ONLY after verifying SHA-256.
            'verified_original_mirror_url' => 'https://raw.githubusercontent.com/karanzing1992/engagement-core/e7224f224ffa17bfa56bea7c946c2f7f8af45b8f/assets/brand/moksha-logo-source.jpg',
            'drive_file_id' => self::DRIVE_ID,
            'drive_url' => 'https://drive.google.com/file/d/' . self::DRIVE_ID . '/view',
            'source_name' => 'Moksha_Logo_Source_01.jpeg',
            'approved_sha256' => self::SHA256,
            'source_modified_at' => self::DRIVE_MODIFIED_AT,
            'width' => self::WIDTH, 'height' => self::HEIGHT, 'format' => 'image/jpeg',
            'placement' => $placement, 'placement_policy' => $modes[ $placement ],
            'allow_ai_recreation' => false, 'allow_synthetic_substitute' => false,
            'allow_recolor' => false, 'allow_unapproved_cutout' => false,
            'preserve_aspect' => true, 'preserve_black_background' => true,
            'ready' => true,
        );
    }

    /** Assign only to private unapproved Moksha drafts with no pre-selected logo. */
    public static function assign_to_draft( int $job_id, int $logo_id ): string {
        if ( $logo_id < 1 || ! self::verified_attachment( $logo_id ) ) { return 'missing_verified_logo'; }
        if ( get_post_type( $job_id ) !== 'mrs_reel' || get_post_status( $job_id ) !== 'private' ||
             (string) get_post_meta( $job_id, '_mrs_brand', true ) !== 'moksha' ) { return 'not_applicable'; }
        if ( (string) get_post_meta( $job_id, '_mrs_state', true ) === 'approved' ) { return 'requires_review'; }
        $existing = (int) get_post_meta( $job_id, '_mrs_logo_attachment_id', true );
        if ( $existing !== 0 && $existing !== $logo_id ) { return 'conflicting_asset_requires_review'; }
        if ( $existing === $logo_id && (bool) get_post_meta( $job_id, '_mrs_logo_verified', true ) ) { return 'already_linked'; }
        update_post_meta( $job_id, '_mrs_logo_attachment_id', $logo_id );
        update_post_meta( $job_id, '_mrs_logo_verified', true );
        update_post_meta( $job_id, '_mrs_logo_drive_file_id', self::DRIVE_ID );
        update_post_meta( $job_id, '_mrs_logo_sha256', self::SHA256 );
        update_post_meta( $job_id, '_mrs_logo_variant', 'original_gold_on_black' );
        $old_state = (string) get_post_meta( $job_id, '_mrs_state', true );
        if ( $old_state === 'preview_ready' ) {
            // The existing rendered MP4 may not contain the approved official logo.
            // Keep the preview URL as a technical reference, but revoke ready-to-approve.
            update_post_meta( $job_id, '_mrs_state', 'draft' );
            update_post_meta( $job_id, '_mrs_worker_state', 'rebranding_required' );
        }
        $audit = get_post_meta( $job_id, '_mrs_audit', true );
        $audit = is_array( $audit ) ? array_slice( $audit, -49 ) : array();
        $audit[] = array( 'at' => gmdate( 'c' ), 'action' => 'approved_drive_logo_linked_sha256_verified' );
        update_post_meta( $job_id, '_mrs_audit', $audit );
        return 'linked';
    }

    public static function apply_to_private_drafts( int $logo_id ): array {
        $report = array( 'linked' => 0, 'already_linked' => 0, 'requires_review' => 0,
            'conflicting_asset_requires_review' => 0, 'not_applicable' => 0 );
        if ( ! post_type_exists( 'mrs_reel' ) ) { return $report; }
        $ids = get_posts( array( 'post_type' => 'mrs_reel', 'post_status' => 'private',
            'posts_per_page' => 300, 'fields' => 'ids', 'orderby' => 'ID', 'order' => 'DESC' ) );
        foreach ( $ids as $id ) {
            $status = self::assign_to_draft( (int) $id, $logo_id );
            if ( ! isset( $report[ $status ] ) ) { $report[ $status ] = 0; }
            $report[ $status ]++;
        }
        return $report;
    }

    public static function maybe_autofill_logo( $mid, $object_id, $meta_key, $meta_value ): void {
        static $busy = false;
        if ( $busy || $meta_key !== '_mrs_logo_verified' ) { return; }
        $id = self::saved_attachment_id();
        if ( ! $id ) { return; }
        $busy = true;
        try { self::assign_to_draft( (int) $object_id, $id ); }
        finally { $busy = false; }
    }

    public static function rest_sync( $request ) {
        $result = self::import_master();
        if ( is_wp_error( $result ) ) { return $result; }
        $report = self::apply_to_private_drafts( (int) $result['id'] );
        return new WP_REST_Response( array( 'ok' => true, 'asset_verified' => true,
            'attachment_id' => (int) $result['id'], 'imported' => (bool) $result['imported'],
            'sha256' => self::SHA256, 'drive_file_id' => self::DRIVE_ID,
            'drafts' => $report, 'publishing_enabled' => false ), 200 );
    }

    public static function rest_resolve( $request ) {
        $placement = sanitize_key( (string) ( is_object( $request ) ? $request->get_param( 'placement' ) : '' ) );
        $result = self::choose( 'moksha', $placement );
        return is_wp_error( $result ) ? $result : new WP_REST_Response( $result, 200 );
    }

    public static function rest_status( $request ) {
        $asset = self::validate_source();
        $id = self::saved_attachment_id();
        return new WP_REST_Response( array(
            'ok' => ! is_wp_error( $asset ) && $id > 0,
            'brand' => 'moksha', 'drive_file_id' => self::DRIVE_ID,
            'source_hash_verified' => ! is_wp_error( $asset ),
            'attachment_hash_verified' => $id > 0, 'attachment_id' => $id,
            'approval_required_for_changed_master' => true,
            'publishing_enabled' => false,
        ), 200 );
    }
}