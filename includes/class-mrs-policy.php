<?php
/** Business-specific content policy is isolated from WordPress I/O and rendering. */
defined( 'ABSPATH' ) || exit;

final class MRS_Policy {
    public const STATES = array( 'draft', 'preview_ready', 'approved', 'needs_revision' );
    public const TRANSITIONS = array(
        'draft'          => array( 'preview_ready' ),
        'preview_ready'  => array( 'approved', 'needs_revision', 'draft' ),
        'approved'       => array( 'needs_revision' ),
        'needs_revision' => array( 'draft', 'preview_ready' ),
    );

    /** This map is deliberately independent of the engine: add more brands here. */
    public static function brand_policies(): array {
        return array(
            'moksha' => array(
                'label'                 => 'Wellness editorial',
                'forbidden_copy_terms'  => array( 'moksha', 'мокша' ),
                'max_duration_seconds'  => 180,
                'allow_promotional_cta' => false,
                'allow_mentions'        => false,
            ),
            'generic' => array(
                'label'                 => 'Generic editorial',
                'forbidden_copy_terms'  => array(),
                'max_duration_seconds'  => 180,
                'allow_promotional_cta' => false,
                'allow_mentions'        => true,
            ),
        );
    }

    public static function validate_creative( string $brand, string $script, string $caption ): array {
        $policies = self::brand_policies();
        if ( ! isset( $policies[ $brand ] ) ) {
            return array( 'Unknown configured brand.' );
        }
        $errors = array();
        foreach ( $policies[ $brand ]['forbidden_copy_terms'] as $term ) {
            $regex = '/(?<![\p{L}\p{N}])' . preg_quote( $term, '/' ) . '(?![\p{L}\p{N}])/iu';
            if ( preg_match( $regex, $script ) || preg_match( $regex, $caption ) ) {
                $errors[] = 'A forbidden brand word appears in on-screen creative text or caption.';
                break;
            }
        }
        // Engagement-only profiles must never silently turn into sales creatives.
        $combined_copy = $script . "\n" . $caption;
        if ( ! $policies[ $brand ]['allow_promotional_cta'] && preg_match( '/(?:book\s+now|reserve\s+now|buy\s+now|dm\s+to\s+book|limited\s+(?:offer|deal)|discount|\x{20B9}\s*\d+)/iu', $combined_copy ) ) {
            $errors[] = 'Promotional calls to action or prices are not allowed in engagement-only creative.';
        }
        if ( empty( $policies[ $brand ]['allow_mentions'] ) && preg_match( '/(?<![\p{L}\p{N}\w.])@[A-Za-z][A-Za-z0-9_.]+/u', $combined_copy ) ) {
            $errors[] = 'Social account mentions require separate editorial relevance review; omit them from this profile.';
        }
        if ( ( function_exists( 'mb_strlen' ) ? mb_strlen( $script, 'UTF-8' ) : strlen( $script ) ) > 6000 || ( function_exists( 'mb_strlen' ) ? mb_strlen( $caption, 'UTF-8' ) : strlen( $caption ) ) > 2200 ) {
            $errors[] = 'Creative copy exceeds the permitted length.';
        }
        return $errors;
    }

    public static function can_transition( string $from, string $to ): bool {
        return in_array( $to, self::TRANSITIONS[ $from ] ?? array(), true );
    }

    /** Source ledger: source and licence URLs must be explicitly present; nothing is fetched. */
    public static function validate_ledger( array $assets ): array {
        $errors = array();
        if ( count( $assets ) > 20 ) {
            return array( 'Source ledger has more than 20 entries.' );
        }
        foreach ( $assets as $index => $asset ) {
            if ( ! is_array( $asset ) ) {
                $errors[] = 'Ledger entry is not an object.';
                continue;
            }
            foreach ( array( 'source_url', 'license_url', 'license_name', 'creator' ) as $key ) {
                if ( empty( $asset[ $key ] ) || ! is_string( $asset[ $key ] ) ) {
                    $errors[] = 'Asset ' . ( $index + 1 ) . ' lacks ' . $key . '.';
                }
            }
            foreach ( array( 'source_url', 'license_url' ) as $key ) {
                $url = $asset[ $key ] ?? '';
                $pieces = is_string( $url ) ? parse_url( $url ) : false;
                if ( ! $pieces || strtolower( $pieces['scheme'] ?? '' ) !== 'https' || empty( $pieces['host'] ) || isset( $pieces['user'] ) ) {
                    $errors[] = 'Asset ' . ( $index + 1 ) . ' has an invalid HTTPS ' . $key . '.';
                }
            }
        }
        return $errors;
    }

    /** Renderer handoff always remains private. This plugin does not publish or schedule. */
    public static function manifest( array $job ): array {
        return array(
            'schema_version'    => 1,
            'job_id'            => (int) $job['id'],
            'status'            => 'draft',
            'publishing_enabled'=> false,
            'scheduling_enabled'=> false,
            'brand'             => $job['brand'],
            'topic'             => $job['topic'],
            'title'             => $job['title'],
            'aspect_ratio'      => '9:16',
            'duration_seconds'  => (int) $job['duration_seconds'],
            'creative_text'     => $job['script'],
            'caption'           => $job['caption'],
            'license_ledger'    => $job['ledger'],
            'logo_attachment_id'=> (int) $job['logo_attachment_id'],
            'logo_verified'     => (bool) $job['logo_verified'],
            'private_preview_url'=> $job['private_preview_url'],
            'natural_audio_only'=> (bool) $job['natural_audio_only'],
            'no_voiceover'      => (bool) $job['no_voiceover'],
            'review_status'     => $job['state'],
        );
    }
}