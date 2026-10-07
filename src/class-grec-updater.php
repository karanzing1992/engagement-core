<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class GREC_Updater {
	private const MANIFEST_URL = 'https://saczglesalubroyaucqe.supabase.co/functions/v1/engagement-core-release/manifest';
	private const RELEASE_HOST = 'saczglesalubroyaucqe.supabase.co';
	private const PUBLIC_KEY_B64 = 'G9U/h3Og/jAenqYfwc/2YSq/owFy7oJp+4Zdph5pFno=';
	private const BACKUP_OPTION = 'grec_update_backup';
	private const LAST_UPDATE_OPTION = 'grec_update_last_result';
	private const CHECK_TRANSIENT = 'grec_update_manifest';

	public static function init(): void {
		// Intentionally no automatic install. Updates are explicit through WP Control.
	}

	private static function error( string $code, string $message, int $status = 400 ): WP_Error {
		return new WP_Error( $code, $message, array( 'status' => $status ) );
	}

	private static function canonical_payload( array $manifest ): string {
		return implode(
			"\n",
			array(
				'engagement-core',
				(string) $manifest['version'],
				strtolower( (string) $manifest['sha256'] ),
				(string) $manifest['package_url'],
				(string) $manifest['released_at'],
				(string) ( $manifest['min_php'] ?? '' ),
				(string) ( $manifest['min_wp'] ?? '' ),
				(string) ( $manifest['commit'] ?? '' ),
			)
		);
	}

	private static function verify_manifest( array $manifest ) {
		foreach ( array( 'version', 'sha256', 'package_url', 'released_at', 'min_php', 'min_wp', 'commit', 'signature' ) as $required ) {
			if ( empty( $manifest[ $required ] ) || ! is_string( $manifest[ $required ] ) ) {
				return self::error( 'grec_update_manifest_invalid', 'Update manifest is missing a required field.' );
			}
		}

		if ( ! preg_match( '/^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9._-]+)?$/', $manifest['version'] ) ) {
			return self::error( 'grec_update_version_invalid', 'Update manifest version is invalid.' );
		}
		if ( ! preg_match( '/^[a-f0-9]{64}$/i', $manifest['sha256'] ) ) {
			return self::error( 'grec_update_hash_invalid', 'Update manifest checksum is invalid.' );
		}
		if ( ! preg_match( '/^[a-f0-9]{40}$/i', $manifest['commit'] ) ) {
			return self::error( 'grec_update_commit_invalid', 'Update manifest commit is invalid.' );
		}

		$parts = wp_parse_url( $manifest['package_url'] );
		if (
			! is_array( $parts ) ||
			'https' !== ( $parts['scheme'] ?? '' ) ||
			self::RELEASE_HOST !== ( $parts['host'] ?? '' ) ||
			false === strpos( (string) ( $parts['path'] ?? '' ), '/functions/v1/engagement-core-release/' )
		) {
			return self::error( 'grec_update_package_url_invalid', 'Update package URL is not an approved Engagement Core release endpoint.' );
		}

		if ( ! function_exists( 'sodium_crypto_sign_verify_detached' ) ) {
			return self::error( 'grec_update_sodium_missing', 'Ed25519 verification is unavailable on this PHP installation.', 501 );
		}

		$signature = base64_decode( $manifest['signature'], true );
		$public    = base64_decode( self::PUBLIC_KEY_B64, true );
		if ( false === $signature || false === $public || SODIUM_CRYPTO_SIGN_BYTES !== strlen( $signature ) || SODIUM_CRYPTO_SIGN_PUBLICKEYBYTES !== strlen( $public ) ) {
			return self::error( 'grec_update_signature_invalid', 'Update manifest signature is malformed.' );
		}

		if ( ! sodium_crypto_sign_verify_detached( $signature, self::canonical_payload( $manifest ), $public ) ) {
			return self::error( 'grec_update_signature_invalid', 'Update manifest signature verification failed.', 403 );
		}

		if ( ! empty( $manifest['min_php'] ) && version_compare( PHP_VERSION, (string) $manifest['min_php'], '<' ) ) {
			return self::error( 'grec_update_php_too_old', 'This release requires a newer PHP version.', 409 );
		}
		$wp_version = get_bloginfo( 'version' );
		if ( ! empty( $manifest['min_wp'] ) && version_compare( $wp_version, (string) $manifest['min_wp'], '<' ) ) {
			return self::error( 'grec_update_wp_too_old', 'This release requires a newer WordPress version.', 409 );
		}

		return true;
	}

	public static function check( bool $force = false ) {
		if ( ! $force ) {
			$cached = get_transient( self::CHECK_TRANSIENT );
			if ( is_array( $cached ) ) {
				return $cached;
			}
		}

		$response = wp_remote_get(
			self::MANIFEST_URL,
			array(
				'timeout'     => 15,
				'redirection' => 2,
				'sslverify'   => true,
				'headers'     => array( 'accept' => 'application/json' ),
			)
		);
		if ( is_wp_error( $response ) ) {
			return self::error( 'grec_update_manifest_unreachable', 'Could not reach the Engagement Core release service.', 503 );
		}

		$status = (int) wp_remote_retrieve_response_code( $response );
		$body   = json_decode( wp_remote_retrieve_body( $response ), true );
		if ( 200 !== $status || ! is_array( $body ) ) {
			return self::error( 'grec_update_manifest_unreachable', 'Release service returned an invalid response.', 503 );
		}

		$verified = self::verify_manifest( $body );
		if ( is_wp_error( $verified ) ) {
			return $verified;
		}

		$result = array(
			'ok'                => true,
			'current_version'   => defined( 'GREC_VERSION' ) ? GREC_VERSION : '0.0.0',
			'available_version' => $body['version'],
			'update_available'  => version_compare( $body['version'], defined( 'GREC_VERSION' ) ? GREC_VERSION : '0.0.0', '>' ),
			'manifest'          => $body,
			'signature_valid'   => true,
		);
		set_transient( self::CHECK_TRANSIENT, $result, 10 * MINUTE_IN_SECONDS );
		return $result;
	}

	private static function plugin_dir(): string {
		return trailingslashit( WP_PLUGIN_DIR ) . 'engagement-core';
	}

	private static function ensure_filesystem() {
		require_once ABSPATH . 'wp-admin/includes/file.php';
		if ( ! function_exists( 'WP_Filesystem' ) || ! WP_Filesystem() ) {
			return self::error( 'grec_update_filesystem_unavailable', 'WordPress filesystem access is unavailable.', 503 );
		}
		return true;
	}

	private static function remove_tree( string $path ): void {
		if ( '' === $path || '/' === $path || ! file_exists( $path ) ) {
			return;
		}
		if ( is_file( $path ) || is_link( $path ) ) {
			@unlink( $path );
			return;
		}
		$items = scandir( $path );
		if ( ! is_array( $items ) ) {
			return;
		}
		foreach ( $items as $item ) {
			if ( '.' === $item || '..' === $item ) {
				continue;
			}
			self::remove_tree( $path . DIRECTORY_SEPARATOR . $item );
		}
		@rmdir( $path );
	}

	private static function package_root( string $stage_dir ): ?string {
		$direct = trailingslashit( $stage_dir ) . 'engagement-core';
		if ( is_file( trailingslashit( $direct ) . 'engagement-core.php' ) ) {
			return $direct;
		}

		$items = scandir( $stage_dir );
		if ( ! is_array( $items ) ) {
			return null;
		}
		foreach ( $items as $item ) {
			if ( '.' === $item || '..' === $item ) {
				continue;
			}
			$path = trailingslashit( $stage_dir ) . $item;
			if ( is_dir( $path ) && is_file( trailingslashit( $path ) . 'engagement-core.php' ) ) {
				return $path;
			}
		}
		return null;
	}

	private static function package_version( string $root ): string {
		require_once ABSPATH . 'wp-admin/includes/plugin.php';
		$data = get_plugin_data( trailingslashit( $root ) . 'engagement-core.php', false, false );
		return isset( $data['Version'] ) ? (string) $data['Version'] : '';
	}

	private static function health_check( string $expected_version ) {
		$url = add_query_arg( 'grec_update_probe', wp_generate_uuid4(), rest_url( 'engagement-core/v1/health' ) );
		$response = wp_remote_get(
			$url,
			array(
				'timeout'     => 20,
				'redirection' => 2,
				'sslverify'   => true,
				'headers'     => array( 'cache-control' => 'no-cache' ),
			)
		);
		if ( is_wp_error( $response ) ) {
			return false;
		}
		$data = json_decode( wp_remote_retrieve_body( $response ), true );
		return 200 === (int) wp_remote_retrieve_response_code( $response )
			&& is_array( $data )
			&& ! empty( $data['ok'] )
			&& isset( $data['version'] )
			&& (string) $data['version'] === $expected_version;
	}

	private static function restore_backup( string $backup_dir, string $current_dir ): bool {
		if ( ! is_dir( $backup_dir ) ) {
			return false;
		}
		$failed = $current_dir . '.failed-' . gmdate( 'YmdHis' );
		if ( is_dir( $current_dir ) && ! @rename( $current_dir, $failed ) ) {
			return false;
		}
		if ( ! @rename( $backup_dir, $current_dir ) ) {
			if ( is_dir( $failed ) ) {
				@rename( $failed, $current_dir );
			}
			return false;
		}
		self::remove_tree( $failed );
		return true;
	}

	public static function apply( $input = array() ) {
		if ( ! current_user_can( 'manage_options' ) ) {
			return self::error( 'grec_update_forbidden', 'Administrator permission is required.', 403 );
		}
		$input = is_array( $input ) ? $input : array();
		if ( ! empty( $input['dry_run'] ) ) {
			$check = self::check( true );
			if ( is_wp_error( $check ) ) {
				return $check;
			}
			return array(
				'ok'                => true,
				'dry_run'           => true,
				'current_version'   => $check['current_version'],
				'available_version' => $check['available_version'],
				'update_available'  => $check['update_available'],
				'signature_valid'   => true,
			);
		}

		$fs = self::ensure_filesystem();
		if ( is_wp_error( $fs ) ) {
			return $fs;
		}

		$check = self::check( true );
		if ( is_wp_error( $check ) ) {
			return $check;
		}
		$manifest = $check['manifest'];
		if ( ! $check['update_available'] && empty( $input['allow_reinstall'] ) ) {
			return array(
				'ok'      => true,
				'updated' => false,
				'version' => $check['current_version'],
				'message' => 'Engagement Core is already current.',
			);
		}

		require_once ABSPATH . 'wp-admin/includes/file.php';
		$tmp_zip = download_url( $manifest['package_url'], 30 );
		if ( is_wp_error( $tmp_zip ) ) {
			return self::error( 'grec_update_download_failed', 'Release package download failed.', 502 );
		}

		$actual_hash = strtolower( (string) hash_file( 'sha256', $tmp_zip ) );
		if ( ! hash_equals( strtolower( $manifest['sha256'] ), $actual_hash ) ) {
			@unlink( $tmp_zip );
			return self::error( 'grec_update_checksum_failed', 'Release package checksum verification failed.', 403 );
		}

		$upgrade_base = trailingslashit( WP_CONTENT_DIR ) . 'upgrade';
		wp_mkdir_p( $upgrade_base );
		$stage_dir = trailingslashit( $upgrade_base ) . 'grec-stage-' . wp_generate_uuid4();
		wp_mkdir_p( $stage_dir );

		$unzipped = unzip_file( $tmp_zip, $stage_dir );
		@unlink( $tmp_zip );
		if ( is_wp_error( $unzipped ) ) {
			self::remove_tree( $stage_dir );
			return self::error( 'grec_update_unpack_failed', 'Release package could not be unpacked.', 500 );
		}

		$source_dir = self::package_root( $stage_dir );
		if ( ! $source_dir ) {
			self::remove_tree( $stage_dir );
			return self::error( 'grec_update_package_invalid', 'Release package does not contain Engagement Core.', 500 );
		}
		if ( self::package_version( $source_dir ) !== (string) $manifest['version'] ) {
			self::remove_tree( $stage_dir );
			return self::error( 'grec_update_version_mismatch', 'Release package version does not match the signed manifest.', 403 );
		}

		$current_dir = self::plugin_dir();
		if ( ! is_dir( $current_dir ) ) {
			self::remove_tree( $stage_dir );
			return self::error( 'grec_update_current_missing', 'Current Engagement Core directory is missing.', 500 );
		}

		$old_backup = get_option( self::BACKUP_OPTION, array() );
		$backup_dir = trailingslashit( $upgrade_base ) . 'grec-backup-' . sanitize_key( defined( 'GREC_VERSION' ) ? GREC_VERSION : 'unknown' ) . '-' . gmdate( 'YmdHis' );

		if ( ! @rename( $current_dir, $backup_dir ) ) {
			self::remove_tree( $stage_dir );
			return self::error( 'grec_update_backup_failed', 'Could not create the rollback backup.', 500 );
		}
		if ( ! @rename( $source_dir, $current_dir ) ) {
			@rename( $backup_dir, $current_dir );
			self::remove_tree( $stage_dir );
			return self::error( 'grec_update_swap_failed', 'Could not install the staged release; the old version was restored.', 500 );
		}

		self::remove_tree( $stage_dir );

		if ( ! self::health_check( (string) $manifest['version'] ) ) {
			self::restore_backup( $backup_dir, $current_dir );
			delete_transient( self::CHECK_TRANSIENT );
			update_option(
				self::LAST_UPDATE_OPTION,
				array(
					'ok'        => false,
					'rolled_back'=> true,
					'at'        => gmdate( DATE_ATOM ),
					'target'    => (string) $manifest['version'],
				),
				false
			);
			return self::error( 'grec_update_health_failed', 'The new release failed its health check and was rolled back automatically.', 500 );
		}

		update_option(
			self::BACKUP_OPTION,
			array(
				'path'    => $backup_dir,
				'version' => defined( 'GREC_VERSION' ) ? GREC_VERSION : '',
				'created' => gmdate( DATE_ATOM ),
			),
			false
		);
		update_option(
			self::LAST_UPDATE_OPTION,
			array(
				'ok'      => true,
				'at'      => gmdate( DATE_ATOM ),
				'from'    => defined( 'GREC_VERSION' ) ? GREC_VERSION : '',
				'to'      => (string) $manifest['version'],
				'sha256'  => strtolower( (string) $manifest['sha256'] ),
			),
			false
		);

		if ( is_array( $old_backup ) && ! empty( $old_backup['path'] ) && $old_backup['path'] !== $backup_dir ) {
			self::remove_tree( (string) $old_backup['path'] );
		}

		delete_transient( self::CHECK_TRANSIENT );
		return array(
			'ok'               => true,
			'updated'          => true,
			'previous_version' => defined( 'GREC_VERSION' ) ? GREC_VERSION : '',
			'version'          => (string) $manifest['version'],
			'health_verified'  => true,
			'rollback_ready'   => true,
		);
	}

	public static function rollback( $input = array() ) {
		if ( ! current_user_can( 'manage_options' ) ) {
			return self::error( 'grec_update_forbidden', 'Administrator permission is required.', 403 );
		}
		$backup = get_option( self::BACKUP_OPTION, array() );
		if ( ! is_array( $backup ) || empty( $backup['path'] ) || empty( $backup['version'] ) || ! is_dir( $backup['path'] ) ) {
			return self::error( 'grec_update_backup_missing', 'No rollback backup is available.', 404 );
		}

		$input = is_array( $input ) ? $input : array();
		if ( ! empty( $input['dry_run'] ) ) {
			return array( 'ok' => true, 'dry_run' => true, 'rollback_version' => (string) $backup['version'] );
		}

		$current_dir = self::plugin_dir();
		$current_tmp = $current_dir . '.rollback-' . gmdate( 'YmdHis' );
		if ( ! @rename( $current_dir, $current_tmp ) ) {
			return self::error( 'grec_update_rollback_swap_failed', 'Could not stage the current release for rollback.', 500 );
		}
		if ( ! @rename( (string) $backup['path'], $current_dir ) ) {
			@rename( $current_tmp, $current_dir );
			return self::error( 'grec_update_rollback_restore_failed', 'Could not restore the rollback release.', 500 );
		}

		if ( ! self::health_check( (string) $backup['version'] ) ) {
			@rename( $current_dir, (string) $backup['path'] );
			@rename( $current_tmp, $current_dir );
			return self::error( 'grec_update_rollback_health_failed', 'Rollback failed its health check; the current release was restored.', 500 );
		}

		self::remove_tree( $current_tmp );
		delete_option( self::BACKUP_OPTION );
		delete_transient( self::CHECK_TRANSIENT );
		update_option(
			self::LAST_UPDATE_OPTION,
			array(
				'ok'          => true,
				'rolled_back' => true,
				'at'          => gmdate( DATE_ATOM ),
				'to'          => (string) $backup['version'],
			),
			false
		);
		return array( 'ok' => true, 'rolled_back' => true, 'version' => (string) $backup['version'], 'health_verified' => true );
	}

	public static function status(): array {
		$backup = get_option( self::BACKUP_OPTION, array() );
		return array(
			'ok'                  => true,
			'version'             => defined( 'GREC_VERSION' ) ? GREC_VERSION : null,
			'engine'              => 'engagement-core-native',
			'manifest_url'        => self::MANIFEST_URL,
			'signature_algorithm' => 'Ed25519',
			'signature_ready'     => function_exists( 'sodium_crypto_sign_verify_detached' ),
			'rollback_available'  => is_array( $backup ) && ! empty( $backup['path'] ) && is_dir( (string) $backup['path'] ),
			'rollback_version'    => is_array( $backup ) && ! empty( $backup['version'] ) ? (string) $backup['version'] : null,
			'last_update'         => get_option( self::LAST_UPDATE_OPTION, null ),
		);
	}
}
