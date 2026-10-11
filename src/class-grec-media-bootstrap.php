<?php
/**
 * Narrow, administrator-only bootstrap for Media Studio's first installation.
 * All future application updates belong to a signed, separately versioned updater.
 * Installing this package is opt-in and can never overwrite any existing plugin folder.
 */
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class GREC_Media_Studio_Bootstrap {
    private const PACKAGE = 'mrs-media-studio';
    private const ENTRYPOINT = 'mrs-media-studio.php';
    private const EXPECTED_VERSION = '0.1.0';
    private const SOURCE_SHA = 'caab0df7bbd96b4c4c4f94e968599851e69c8c84';
    private const SOURCE_ARCHIVE = 'https://codeload.github.com/karanzing1992/engagement-core/zip/caab0df7bbd96b4c4c4f94e968599851e69c8c84';

    public static function init(): void {
        if ( function_exists( 'wp_register_ability' ) ) {
            add_action( 'wp_abilities_api_init', array( __CLASS__, 'register_ability' ), 30 );
        }
    }

    public static function register_ability(): void {
        wp_register_ability( 'wp-control/bootstrap-media-studio', array(
            'label'               => __( 'Install Media Studio v0.1.0', 'engagement-core' ),
            'description'         => __( 'One-time installation of the pinned, reviewed Media Studio plugin. Refuses existing directories and does not publish content.', 'engagement-core' ),
            'category'            => 'wp-control',
            'execute_callback'    => array( __CLASS__, 'install' ),
            'permission_callback' => array( __CLASS__, 'authorized' ),
            'input_schema'        => array( 'type' => 'object', 'properties' => array() ),
            'meta'                => array(
                'public' => true, 'show_in_rest' => true,
                'annotations' => array( 'readonly' => false, 'destructive' => false, 'idempotent' => true ),
                'mcp' => array( 'public' => true ),
            ),
        ) );
    }

    public static function authorized(): bool {
        return current_user_can( 'manage_options' ) && current_user_can( 'install_plugins' ) && current_user_can( 'activate_plugins' );
    }

    public static function install( $input = array() ) {
        if ( ! self::authorized() ) {
            return new WP_Error( 'mrs_bootstrap_forbidden', 'Administrator plugin installation permission required.', array( 'status' => 403 ) );
        }

        require_once ABSPATH . 'wp-admin/includes/file.php';
        require_once ABSPATH . 'wp-admin/includes/plugin.php';

        $plugin_file = self::PACKAGE . '/' . self::ENTRYPOINT;
        $destination = trailingslashit( WP_PLUGIN_DIR ) . self::PACKAGE;

        if ( file_exists( $destination ) ) {
            // A pre-existing folder is never overwritten, even if empty or broken.
            if ( is_plugin_active( $plugin_file ) ) {
                return array( 'ok' => true, 'already_installed' => true, 'active' => true,
                    'plugin' => $plugin_file, 'version' => self::EXPECTED_VERSION );
            }
            return new WP_Error( 'mrs_bootstrap_existing_directory', 'An installation already exists. Refusing to overwrite files.', array( 'status' => 409 ) );
        }

        // Use the immutable Git commit, not a moving branch or untrusted URL.
        $archive = download_url( self::SOURCE_ARCHIVE, 45 );
        if ( is_wp_error( $archive ) ) {
            return $archive;
        }
        $scratch = trailingslashit( get_temp_dir() ) . 'mrs-bootstrap-' . wp_generate_uuid4();
        $copied = false;
        try {
            if ( ! wp_mkdir_p( $scratch ) ) {
                return new WP_Error( 'mrs_bootstrap_tmp', 'Could not create a temporary extraction directory.' );
            }
            if ( ! WP_Filesystem() ) {
                return new WP_Error( 'mrs_bootstrap_filesystem', 'WordPress filesystem is not writable.' );
            }
            $expanded = unzip_file( $archive, $scratch );
            if ( is_wp_error( $expanded ) ) {
                return $expanded;
            }
            $directories = glob( $scratch . '/*', GLOB_ONLYDIR );
            if ( ! is_array( $directories ) || count( $directories ) !== 1 ) {
                return new WP_Error( 'mrs_bootstrap_package', 'Unexpected distribution archive layout.' );
            }
            $source = $directories[0];
            $main = $source . '/' . self::ENTRYPOINT;
            if ( ! is_file( $main ) || is_link( $main ) || ! is_file( $source . '/includes/class-mrs-studio.php' ) || ! is_file( $source . '/includes/class-mrs-policy.php' ) ) {
                return new WP_Error( 'mrs_bootstrap_manifest', 'Expected plugin files are missing.' );
            }
            $headers = get_plugin_data( $main, false, false );
            if ( (string) ( $headers['Version'] ?? '' ) !== self::EXPECTED_VERSION ||
                 (string) ( $headers['Name'] ?? '' ) !== 'Media Studio — Private Drafts' ) {
                return new WP_Error( 'mrs_bootstrap_identity', 'Unrecognized Media Studio plugin identity.' );
            }
            // Recheck immediately before installation; do not replace existing files.
            if ( file_exists( $destination ) ) {
                return new WP_Error( 'mrs_bootstrap_race', 'Plugin directory appeared during download.', array( 'status' => 409 ) );
            }
            $copied = true; // Also clean partially extracted files if copy_dir fails.
            $copy = copy_dir( $source, $destination );
            if ( is_wp_error( $copy ) ) {
                return $copy;
            }
            if ( ! is_file( $destination . '/' . self::ENTRYPOINT ) ) {
                return new WP_Error( 'mrs_bootstrap_install_incomplete', 'Plugin entrypoint not found after installation.' );
            }
            // An activation failure is reversed by removing the freshly copied files.
            $activation = activate_plugin( $plugin_file, '', false, true );
            if ( is_wp_error( $activation ) ) {
                return $activation;
            }
            if ( ! is_plugin_active( $plugin_file ) ) {
                return new WP_Error( 'mrs_bootstrap_not_active', 'Plugin activation did not complete.' );
            }
            $copied = false; // Success: retain the installed directory.
            return array( 'ok' => true, 'installed' => true, 'active' => true,
                'plugin' => $plugin_file, 'version' => self::EXPECTED_VERSION, 'source_sha' => self::SOURCE_SHA );
        } finally {
            if ( $copied ) {
                // Only delete the folder we created, never any other WordPress plugin.
                global $wp_filesystem;
                if ( $wp_filesystem ) {
                    $wp_filesystem->delete( $destination, true );
                }
            }
            if ( is_file( $archive ) ) {
                @unlink( $archive );
            }
            global $wp_filesystem;
            if ( $wp_filesystem && is_dir( $scratch ) ) {
                $wp_filesystem->delete( $scratch, true );
            }
        }
    }
}