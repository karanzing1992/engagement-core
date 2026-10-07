<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class GREC_Admin {
	public static function init(): void {
		add_action( 'admin_menu', array( __CLASS__, 'menu' ) );
		add_action( 'admin_enqueue_scripts', array( __CLASS__, 'enqueue_assets' ) );
		add_action( 'admin_post_grec_save_settings', array( __CLASS__, 'save_settings' ) );
		add_action( 'admin_post_grec_youtube_oauth', array( __CLASS__, 'oauth_callback' ) );
		add_action( 'admin_post_grec_youtube_disconnect', array( __CLASS__, 'disconnect' ) );
		add_action( 'admin_post_grec_sync_now', array( __CLASS__, 'sync_now' ) );
		add_action( 'admin_post_grec_reply', array( __CLASS__, 'reply' ) );
		add_action( 'admin_post_grec_moderate', array( __CLASS__, 'moderate' ) );
		add_action( 'admin_post_grec_save_telegram', array( __CLASS__, 'save_telegram' ) );
		add_action( 'admin_post_grec_test_telegram', array( __CLASS__, 'test_telegram' ) );
		add_action( 'admin_post_grec_publish_telegram', array( __CLASS__, 'publish_telegram' ) );
		add_action( 'admin_post_grec_generate_publish_key', array( __CLASS__, 'generate_publish_key' ) );
		add_action( 'admin_post_grec_revoke_publish_key', array( __CLASS__, 'revoke_publish_key' ) );
		add_action( 'admin_post_grec_save_vk', array( __CLASS__, 'save_vk' ) );
		add_action( 'admin_post_grec_test_vk', array( __CLASS__, 'test_vk' ) );
		add_action( 'admin_post_grec_publish_vk', array( __CLASS__, 'publish_vk' ) );
		add_action( 'admin_post_grec_save_ok', array( __CLASS__, 'save_ok' ) );
		add_action( 'admin_post_grec_test_ok', array( __CLASS__, 'test_ok' ) );
		add_action( 'admin_post_grec_publish_ok', array( __CLASS__, 'publish_ok' ) );
		add_action( 'admin_post_grec_save_snapchat', array( __CLASS__, 'save_snapchat' ) );
		add_action( 'admin_post_grec_queue_snapchat', array( __CLASS__, 'queue_snapchat' ) );
	}

	private static function guard(): void {
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_die( esc_html__( 'You do not have permission to manage Engagement Core.', 'engagement-core' ) );
		}
	}

	public static function enqueue_assets( string $hook ): void {
		if ( 'toplevel_page_engagement-core' !== $hook ) {
			return;
		}
		wp_enqueue_media();
		wp_enqueue_style(
			'grec-admin',
			plugin_dir_url( GREC_FILE ) . 'assets/admin.css',
			array(),
			GREC_VERSION
		);
		wp_enqueue_script(
			'grec-admin',
			plugin_dir_url( GREC_FILE ) . 'assets/admin.js',
			array(),
			GREC_VERSION,
			true
		);
	}

	public static function menu(): void {
		add_menu_page(
			'Engagement Core',
			'Engagement',
			'manage_options',
			'engagement-core',
			array( __CLASS__, 'render' ),
			'dashicons-format-chat',
			58
		);
	}

	private static function redirect( string $notice = '', string $type = 'success' ): void {
		$url = admin_url( 'admin.php?page=engagement-core' );
		if ( $notice ) {
			$url = add_query_arg(
				array(
					'grec_notice' => $notice,
					'grec_type' => sanitize_key( $type ),
				),
				$url
			);
		}
		wp_safe_redirect( $url );
		exit;
	}

	public static function save_settings(): void {
		self::guard();
		check_admin_referer( 'grec_save_settings' );

		$youtube = new GREC_YouTube();
		$youtube->save_credentials(
			sanitize_text_field( wp_unslash( $_POST['client_id'] ?? '' ) ),
			trim( (string) wp_unslash( $_POST['client_secret'] ?? '' ) )
		);
		update_option( 'grec_brand_name', sanitize_text_field( wp_unslash( $_POST['brand_name'] ?? 'Goa Reset' ) ), false );
		update_option( 'grec_youtube_channel_id', sanitize_text_field( wp_unslash( $_POST['channel_id'] ?? '' ) ), false );
		update_option( 'grec_auto_sync', isset( $_POST['auto_sync'] ) ? '1' : '0', false );
		update_option( 'grec_sync_interval_minutes', (string) max( 5, min( 60, absint( $_POST['sync_interval'] ?? 10 ) ) ), false );

		GREC_Scheduler::clear();
		GREC_Scheduler::ensure_scheduled();
		GREC_Scheduler::ensure_fallback_scheduled();

		self::redirect( 'Settings saved.' );
	}

	public static function save_telegram(): void {
		self::guard();
		check_admin_referer( 'grec_save_telegram' );

		$token    = trim( (string) wp_unslash( $_POST['telegram_token'] ?? '' ) );
		$names    = isset( $_POST['telegram_dest_name'] ) && is_array( $_POST['telegram_dest_name'] ) ? wp_unslash( $_POST['telegram_dest_name'] ) : array();
		$chat_ids = isset( $_POST['telegram_dest_chat_id'] ) && is_array( $_POST['telegram_dest_chat_id'] ) ? wp_unslash( $_POST['telegram_dest_chat_id'] ) : array();
		$levels   = isset( $_POST['telegram_dest_level'] ) && is_array( $_POST['telegram_dest_level'] ) ? wp_unslash( $_POST['telegram_dest_level'] ) : array();
		$enabled  = isset( $_POST['telegram_dest_enabled'] ) && is_array( $_POST['telegram_dest_enabled'] ) ? wp_unslash( $_POST['telegram_dest_enabled'] ) : array();
		$rows     = array();
		$count    = max( count( $names ), count( $chat_ids ), count( $levels ), count( $enabled ) );

		for ( $i = 0; $i < $count; $i++ ) {
			$rows[] = array(
				'name'    => sanitize_text_field( (string) ( $names[ $i ] ?? '' ) ),
				'chat_id' => sanitize_text_field( (string) ( $chat_ids[ $i ] ?? '' ) ),
				'level'   => sanitize_key( (string) ( $levels[ $i ] ?? 'primary' ) ),
				'enabled' => '1' === (string) ( $enabled[ $i ] ?? '0' ),
			);
		}

		try {
			if ( '' !== $token ) {
				GREC_Telegram::save_token( $token );
			}
			$destinations = GREC_Telegram::save_destinations( $rows );
			self::redirect(
				GREC_Telegram::is_connected()
					? sprintf( 'Telegram settings saved. %d destination(s) configured.', count( $destinations ) )
					: 'Telegram settings saved, but connection is incomplete.',
				GREC_Telegram::is_connected() ? 'success' : 'error'
			);
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}

	public static function test_telegram(): void {
		self::guard();
		check_admin_referer( 'grec_test_telegram' );

		try {
			$data   = GREC_Telegram::send( 'Moksha publishing connection test ✓' );
			$sent   = count( $data['sent'] ?? array() );
			$failed = count( $data['failed'] ?? array() );
			self::redirect(
				$failed ? sprintf( 'Telegram test reached %d destination(s); %d failed.', $sent, $failed ) : sprintf( 'Telegram test sent to %d destination(s).', $sent ),
				$failed ? 'error' : 'success'
			);
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}

	public static function publish_telegram(): void {
		self::guard();
		check_admin_referer( 'grec_publish_telegram' );

		$text       = GREC_Telegram::sanitize_message_html( (string) wp_unslash( $_POST['telegram_publish_text'] ?? '' ) );
		$media_json = (string) wp_unslash( $_POST['telegram_publish_media_json'] ?? '[]' );
		$decoded    = json_decode( $media_json, true );
		$media      = is_array( $decoded ) ? $decoded : array();
		$targets    = isset( $_POST['telegram_publish_targets'] ) && is_array( $_POST['telegram_publish_targets'] )
			? array_map( 'sanitize_text_field', wp_unslash( $_POST['telegram_publish_targets'] ) )
			: array();
		$levels     = isset( $_POST['telegram_publish_levels'] ) && is_array( $_POST['telegram_publish_levels'] )
			? array_map( 'sanitize_key', wp_unslash( $_POST['telegram_publish_levels'] ) )
			: array();

		try {
			$data   = GREC_Telegram::send_post( $text, $media, $targets, $levels );
			$sent   = count( $data['sent'] ?? array() );
			$failed = count( $data['failed'] ?? array() );
			self::redirect(
				$failed ? sprintf( 'Telegram published to %d destination(s); %d failed.', $sent, $failed ) : sprintf( 'Telegram published to %d destination(s).', $sent ),
				$failed ? 'error' : 'success'
			);
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}


	public static function generate_publish_key(): void {
		self::guard();
		check_admin_referer( 'grec_generate_publish_key' );
		$key = 'grec_' . bin2hex( random_bytes( 32 ) );
		update_option( 'grec_publish_key_hash', hash( 'sha256', $key ), false );
		delete_option( 'grec_publish_key' );
		set_transient( 'grec_publish_key_once_' . get_current_user_id(), $key, 5 * MINUTE_IN_SECONDS );
		self::redirect( 'Publisher key generated. Copy it now; it will only be shown once.' );
	}

	public static function revoke_publish_key(): void {
		self::guard();
		check_admin_referer( 'grec_revoke_publish_key' );
		delete_option( 'grec_publish_key_hash' );
		delete_option( 'grec_publish_key' );
		delete_transient( 'grec_publish_key_once_' . get_current_user_id() );
		self::redirect( 'Publisher key revoked.' );
	}

	public static function save_vk(): void {
		self::guard();
		check_admin_referer( 'grec_save_vk' );

		$token    = trim( (string) wp_unslash( $_POST['vk_token'] ?? '' ) );
		$owner_id = sanitize_text_field( (string) wp_unslash( $_POST['vk_owner_id'] ?? '' ) );

		try {
			if ( '' !== $token ) {
				GREC_VK::save_token( $token );
			}
			if ( '' !== $owner_id ) {
				GREC_VK::save_owner_id( $owner_id );
			}
			self::redirect(
				GREC_VK::is_connected() ? 'VK settings saved.' : 'VK settings saved, but connection is incomplete.',
				GREC_VK::is_connected() ? 'success' : 'error'
			);
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}

	public static function test_vk(): void {
		self::guard();
		check_admin_referer( 'grec_test_vk' );

		try {
			$data = GREC_VK::test_connection();
			self::redirect( sprintf( 'VK connected: %s (%s).', $data['name'] ?: $data['owner_id'], $data['type'] ) );
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}

	public static function publish_vk(): void {
		self::guard();
		check_admin_referer( 'grec_publish_vk' );

		$text       = sanitize_textarea_field( (string) wp_unslash( $_POST['vk_publish_text'] ?? '' ) );
		$link       = esc_url_raw( (string) wp_unslash( $_POST['vk_publish_link'] ?? '' ) );
		$media_json = (string) wp_unslash( $_POST['vk_publish_media_json'] ?? '[]' );
		$media      = json_decode( $media_json, true );
		$media      = is_array( $media ) ? $media : array();

		try {
			$data = GREC_VK::publish( $text, $media, $link );
			self::redirect( sprintf( 'Published to VK. Post ID %s.', $data['post_id'] ?: 'created' ) );
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}


	public static function save_ok(): void {
		self::guard();
		check_admin_referer( 'grec_save_ok' );

		try {
			GREC_OK::save_credentials(
				array(
					'application_id'     => sanitize_text_field( (string) wp_unslash( $_POST['ok_application_id'] ?? '' ) ),
					'application_key'    => sanitize_text_field( (string) wp_unslash( $_POST['ok_application_key'] ?? '' ) ),
					'application_secret' => trim( (string) wp_unslash( $_POST['ok_application_secret'] ?? '' ) ),
					'access_token'       => trim( (string) wp_unslash( $_POST['ok_access_token'] ?? '' ) ),
				)
			);
			$group_id = sanitize_text_field( (string) wp_unslash( $_POST['ok_group_id'] ?? '' ) );
			if ( '' !== $group_id ) {
				GREC_OK::save_group_id( $group_id );
			}
			self::redirect(
				GREC_OK::is_connected() ? 'Odnoklassniki settings saved.' : 'Odnoklassniki settings saved, but connection is incomplete.',
				GREC_OK::is_connected() ? 'success' : 'error'
			);
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}

	public static function test_ok(): void {
		self::guard();
		check_admin_referer( 'grec_test_ok' );
		try {
			$data = GREC_OK::test_connection();
			self::redirect( sprintf( 'Odnoklassniki API connected%s. App approval is still required for publishing.', $data['user_name'] ? ' as ' . $data['user_name'] : '' ) );
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}

	public static function publish_ok(): void {
		self::guard();
		check_admin_referer( 'grec_publish_ok' );

		$text       = sanitize_textarea_field( (string) wp_unslash( $_POST['ok_publish_text'] ?? '' ) );
		$link       = esc_url_raw( (string) wp_unslash( $_POST['ok_publish_link'] ?? '' ) );
		$media_json = (string) wp_unslash( $_POST['ok_publish_media_json'] ?? '[]' );
		$media      = json_decode( $media_json, true );
		$media      = is_array( $media ) ? $media : array();

		try {
			$data = GREC_OK::publish( $text, $media, $link );
			self::redirect( sprintf( 'Published to Odnoklassniki. Topic ID %s.', $data['topic_id'] ?: 'created' ) );
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}


	public static function save_snapchat(): void {
		self::guard();
		check_admin_referer( 'grec_save_snapchat' );

		try {
			$client_id = sanitize_text_field( (string) wp_unslash( $_POST['snapchat_client_id'] ?? '' ) );
			$device_key = trim( (string) wp_unslash( $_POST['snapchat_device_key'] ?? '' ) );
			if ( '' !== $client_id ) {
				GREC_Snapchat::save_client_id( $client_id );
			}
			if ( '' !== $device_key ) {
				GREC_Snapchat::save_device_key( $device_key );
			} elseif ( '' === GREC_Snapchat::device_key() ) {
				GREC_Snapchat::ensure_device_key();
			}
			self::redirect(
				GREC_Snapchat::is_configured() ? 'Snapchat handoff settings saved.' : 'Snapchat settings saved, but Client ID is still required.',
				GREC_Snapchat::is_configured() ? 'success' : 'error'
			);
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}

	public static function queue_snapchat(): void {
		self::guard();
		check_admin_referer( 'grec_queue_snapchat' );
		try {
			$task = GREC_Snapchat::queue_handoff(
				sanitize_textarea_field( (string) wp_unslash( $_POST['snapchat_caption'] ?? '' ) ),
				esc_url_raw( (string) wp_unslash( $_POST['snapchat_media_url'] ?? '' ) ),
				sanitize_key( (string) wp_unslash( $_POST['snapchat_media_type'] ?? '' ) )
			);
			self::redirect( sprintf( 'Snapchat handoff queued. Task %s.', $task['id'] ) );
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}

	public static function oauth_callback(): void {
		self::guard();
		if ( empty( $_GET['state'] ) || ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_GET['state'] ) ), 'grec-youtube-oauth' ) ) {
			self::redirect( 'OAuth state check failed.', 'error' );
		}
		if ( ! empty( $_GET['error'] ) ) {
			self::redirect( 'YouTube connection was cancelled or denied.', 'error' );
		}
		$code = sanitize_text_field( wp_unslash( $_GET['code'] ?? '' ) );
		if ( '' === $code ) {
			self::redirect( 'No authorization code was returned by Google.', 'error' );
		}

		try {
			( new GREC_YouTube() )->exchange_code( $code );
			self::redirect( 'YouTube connected.' );
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}

	public static function disconnect(): void {
		self::guard();
		check_admin_referer( 'grec_disconnect' );
		( new GREC_YouTube() )->disconnect();
		self::redirect( 'YouTube disconnected.' );
	}

	public static function sync_now(): void {
		self::guard();
		check_admin_referer( 'grec_sync_now' );
		try {
			$count = ( new GREC_YouTube() )->sync_recent_comments();
			self::redirect( sprintf( 'Synced %d comment threads.', $count ) );
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}

	public static function reply(): void {
		self::guard();
		check_admin_referer( 'grec_reply' );
		$id = sanitize_text_field( wp_unslash( $_POST['comment_id'] ?? '' ) );
		$text = sanitize_textarea_field( wp_unslash( $_POST['reply_text'] ?? '' ) );
		try {
			( new GREC_YouTube() )->reply( $id, $text );
			self::redirect( 'Reply posted.' );
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}

	public static function moderate(): void {
		self::guard();
		check_admin_referer( 'grec_moderate' );
		$id = sanitize_text_field( wp_unslash( $_POST['comment_id'] ?? '' ) );
		$status = sanitize_text_field( wp_unslash( $_POST['status'] ?? '' ) );
		$ban = isset( $_POST['ban_author'] );
		try {
			( new GREC_YouTube() )->moderate( $id, $status, $ban );
			self::redirect( 'Comment moderation updated.' );
		} catch ( Throwable $e ) {
			self::redirect( $e->getMessage(), 'error' );
		}
	}

	public static function render(): void {
		self::guard();
		$youtube = new GREC_YouTube();
		$connected = $youtube->is_connected();
		$comments = GREC_Repository::recent( 100 );
		$notice = isset( $_GET['grec_notice'] ) ? sanitize_text_field( wp_unslash( $_GET['grec_notice'] ) ) : '';
		$type = isset( $_GET['grec_type'] ) && 'error' === $_GET['grec_type'] ? 'error' : 'success';
		?>
		<div id="grec-loading-overlay" class="grec-loading-overlay" aria-hidden="true">
			<div class="grec-loading-card" role="status" aria-live="polite">
				<span class="grec-loading-spinner" aria-hidden="true"></span>
				<strong id="grec-loading-message">Working…</strong>
				<span>Please don’t press the button again.</span>
			</div>
		</div>
		<style>
			.grec-loading-overlay{position:fixed;inset:0;z-index:100000;background:rgba(15,23,42,.42);backdrop-filter:blur(2px);display:none;align-items:center;justify-content:center;cursor:progress}
			.grec-loading-overlay.is-active{display:flex}
			.grec-loading-card{min-width:240px;max-width:85vw;background:#fff;border-radius:12px;padding:22px 26px;box-shadow:0 18px 55px rgba(0,0,0,.24);display:flex;flex-direction:column;align-items:center;gap:8px;text-align:center;color:#1d2327}
			.grec-loading-card span:last-child{font-size:12px;color:#646970;font-weight:400}
			.grec-loading-spinner{width:30px;height:30px;border:3px solid #dcdcde;border-top-color:#2271b1;border-radius:50%;animation:grec-spin .75s linear infinite}
			body.grec-ui-busy{overflow:hidden}
			body.grec-ui-busy #wpwrap{pointer-events:none;user-select:none}
			body.grec-ui-busy #grec-loading-overlay{pointer-events:all;user-select:auto}
			@keyframes grec-spin{to{transform:rotate(360deg)}}
			@media (prefers-reduced-motion:reduce){.grec-loading-spinner{animation-duration:1.5s}}
		</style>
		<div class="wrap grec-shell">
			<div class="grec-shell-header">
				<div class="grec-shell-title-row">
					<div>
						<h1>Engagement Core</h1>
						<p class="grec-shell-intro">Publish, monitor and manage social channels from one mobile-first workspace.</p>
					</div>
				</div>
			</div>
			<div class="grec-status-grid" aria-label="Channel connection status">
				<div class="grec-status-card">
					<div class="grec-status-card-top"><strong>YouTube</strong><span class="grec-status-pill <?php echo $connected ? 'is-connected' : 'is-off'; ?>"><?php echo $connected ? 'Connected' : 'Setup'; ?></span></div>
					<p>Comments, replies and moderation.</p>
				</div>
				<div class="grec-status-card">
					<div class="grec-status-card-top"><strong>Telegram</strong><span class="grec-status-pill <?php echo GREC_Telegram::is_connected() ? 'is-connected' : 'is-off'; ?>"><?php echo GREC_Telegram::is_connected() ? 'Connected' : 'Setup'; ?></span></div>
					<p><?php echo esc_html( count( GREC_Telegram::enabled_destinations() ) ); ?> enabled destination(s).</p>
				</div>
				<div class="grec-status-card">
					<div class="grec-status-card-top"><strong>VK</strong><span class="grec-status-pill <?php echo GREC_VK::is_connected() ? 'is-connected' : 'is-off'; ?>"><?php echo GREC_VK::is_connected() ? 'Configured' : 'Setup'; ?></span></div>
					<p>Russian community wall publishing.</p>
				</div>
				<div class="grec-status-card">
					<div class="grec-status-card-top"><strong>Odnoklassniki</strong><span class="grec-status-pill <?php echo GREC_OK::is_connected() ? 'is-pending' : 'is-off'; ?>"><?php echo GREC_OK::is_connected() ? 'Approval needed' : 'Setup'; ?></span></div>
					<p>Group media topics; approved OK app required.</p>
				</div>
				<div class="grec-status-card">
					<div class="grec-status-card-top"><strong>Snapchat</strong><span class="grec-status-pill <?php echo GREC_Snapchat::is_configured() ? 'is-connected' : 'is-off'; ?>"><?php echo GREC_Snapchat::is_configured() ? 'Configured' : 'Setup'; ?></span></div>
					<p><?php echo esc_html( GREC_Snapchat::pending_count() ); ?> pending device handoff(s).</p>
				</div>
			</div>
			<?php if ( $notice ) : ?>
				<div class="notice notice-<?php echo esc_attr( $type ); ?> is-dismissible"><p><?php echo esc_html( $notice ); ?></p></div>
			<?php endif; ?>

			<h2>Goa Reset / YouTube</h2>
			<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
				<input type="hidden" name="action" value="grec_save_settings">
				<?php wp_nonce_field( 'grec_save_settings' ); ?>
				<table class="form-table" role="presentation">
					<tr>
						<th><label for="grec_brand">Brand</label></th>
						<td><input id="grec_brand" class="regular-text" name="brand_name" value="<?php echo esc_attr( get_option( 'grec_brand_name', 'Goa Reset' ) ); ?>"></td>
					</tr>
					<tr>
						<th><label for="grec_channel">YouTube channel ID</label></th>
						<td><input id="grec_channel" class="regular-text code" name="channel_id" value="<?php echo esc_attr( get_option( 'grec_youtube_channel_id', 'UCSYkzC8ctGKzMK1fhvy6FcA' ) ); ?>"></td>
					</tr>
					<tr>
						<th><label for="grec_client_id">Google OAuth Client ID</label></th>
						<td><input id="grec_client_id" class="large-text code" name="client_id" value="<?php echo esc_attr( get_option( 'grec_youtube_client_id', '' ) ); ?>"></td>
					</tr>
					<tr>
						<th><label for="grec_client_secret">Google OAuth Client Secret</label></th>
						<td>
							<input id="grec_client_secret" class="regular-text" type="password" name="client_secret" value="" placeholder="Leave blank to keep existing secret">
							<p class="description">Stored encrypted using WordPress salts.</p>
						</td>
					</tr>
					<tr>
						<th>OAuth redirect URI</th>
						<td><code><?php echo esc_html( $youtube->redirect_uri() ); ?></code></td>
					</tr>
					<tr>
						<th><label for="grec_interval">Sync interval</label></th>
						<td><input id="grec_interval" type="number" min="5" max="60" name="sync_interval" value="<?php echo esc_attr( get_option( 'grec_sync_interval_minutes', '10' ) ); ?>"> minutes</td>
					</tr>
					<tr>
						<th>Automatic sync</th>
						<td><label><input type="checkbox" name="auto_sync" value="1" <?php checked( '1', get_option( 'grec_auto_sync', '1' ) ); ?>> Enable</label></td>
					</tr>
				</table>
				<?php submit_button( 'Save settings' ); ?>
			</form>

			<?php if ( $connected ) : ?>
				<p>
					<strong>Connected:</strong>
					<?php echo esc_html( get_option( 'grec_youtube_connected_channel_title', 'YouTube' ) ); ?>
					<code><?php echo esc_html( get_option( 'grec_youtube_connected_channel_id', '' ) ); ?></code>
				</p>
				<form style="display:inline-block;margin-right:8px" method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
					<input type="hidden" name="action" value="grec_sync_now">
					<?php wp_nonce_field( 'grec_sync_now' ); ?>
					<?php submit_button( 'Sync now', 'secondary', 'submit', false ); ?>
				</form>
				<form style="display:inline-block" method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
					<input type="hidden" name="action" value="grec_youtube_disconnect">
					<?php wp_nonce_field( 'grec_disconnect' ); ?>
					<?php submit_button( 'Disconnect', 'delete', 'submit', false ); ?>
				</form>
			<?php else : ?>
				<?php $auth = $youtube->authorization_url(); ?>
				<?php if ( $auth ) : ?>
					<p><a class="button button-primary" href="<?php echo esc_url( $auth ); ?>">Connect YouTube</a></p>
				<?php else : ?>
					<p>Save a Google OAuth Client ID and secret first.</p>
				<?php endif; ?>
			<?php endif; ?>


			<hr>
			<h2>Telegram Publisher</h2>
			<p>One encrypted bot can publish to multiple Telegram groups/channels. Use levels such as <code>primary</code>, <code>community</code>, <code>partner</code>, or <code>promo</code>.</p>
			<?php
			$publisher_key_once = get_transient( 'grec_publish_key_once_' . get_current_user_id() );
			$publisher_key_ready = defined( 'GREC_PUBLISH_KEY' ) || '' !== (string) get_option( 'grec_publish_key_hash', '' );
			if ( $publisher_key_once ) { delete_transient( 'grec_publish_key_once_' . get_current_user_id() ); }
			?>
			<div style="background:#fff;border:1px solid #dcdcde;border-radius:8px;padding:14px 16px;margin:12px 0;max-width:1000px">
				<h3 style="margin-top:0">Private publishing API</h3>
				<p><strong>Status:</strong> <?php echo $publisher_key_ready ? 'Key active' : 'No key'; ?>. This key only authorizes Telegram status and publishing endpoints.</p>
				<?php if ( $publisher_key_once ) : ?><p><strong>Copy now — shown once:</strong><br><input class="large-text code" readonly onclick="this.select()" value="<?php echo esc_attr( $publisher_key_once ); ?>"></p><?php endif; ?>
				<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="display:inline-block;margin-right:8px"><input type="hidden" name="action" value="grec_generate_publish_key"><?php wp_nonce_field( 'grec_generate_publish_key' ); ?><?php submit_button( $publisher_key_ready ? 'Rotate publishing key' : 'Generate publishing key', 'primary', 'submit', false ); ?></form>
				<?php if ( $publisher_key_ready && ! defined( 'GREC_PUBLISH_KEY' ) ) : ?><form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="display:inline-block"><input type="hidden" name="action" value="grec_revoke_publish_key"><?php wp_nonce_field( 'grec_revoke_publish_key' ); ?><?php submit_button( 'Revoke key', 'delete', 'submit', false ); ?></form><?php endif; ?>
				<p class="description">Only a SHA-256 hash is retained by WordPress. The plaintext key is displayed once after generation and is never committed to Git.</p>
			</div>
			<?php
			$telegram_destinations = GREC_Telegram::destinations();
			$telegram_rows = $telegram_destinations;
			$telegram_rows[] = array( 'key' => '', 'name' => '', 'chat_id' => '', 'level' => 'community', 'enabled' => true );
			?>
			<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
				<input type="hidden" name="action" value="grec_save_telegram">
				<?php wp_nonce_field( 'grec_save_telegram' ); ?>
				<table class="widefat striped" style="max-width:1100px;margin:12px 0">
					<thead><tr><th>Name</th><th>Chat / channel ID</th><th>Level</th><th>Status</th></tr></thead>
					<tbody id="grec-telegram-destinations">
					<?php foreach ( $telegram_rows as $destination ) : ?>
						<tr>
							<td><input class="regular-text" name="telegram_dest_name[]" value="<?php echo esc_attr( $destination['name'] ?? '' ); ?>" placeholder="e.g. Arambol Community"></td>
							<td><input class="regular-text code" name="telegram_dest_chat_id[]" value="<?php echo esc_attr( $destination['chat_id'] ?? '' ); ?>" placeholder="-1001234567890 or @channel"></td>
							<td><input class="regular-text code" name="telegram_dest_level[]" value="<?php echo esc_attr( $destination['level'] ?? 'community' ); ?>" placeholder="community"></td>
							<td>
								<select name="telegram_dest_enabled[]">
									<option value="1" <?php selected( ! isset( $destination['enabled'] ) || ! empty( $destination['enabled'] ) ); ?>>Enabled</option>
									<option value="0" <?php selected( isset( $destination['enabled'] ) && empty( $destination['enabled'] ) ); ?>>Disabled</option>
								</select>
							</td>
						</tr>
					<?php endforeach; ?>
					</tbody>
				</table>
				<p><button type="button" class="button" id="grec-add-telegram-destination">Add destination</button></p>
				<table class="form-table" role="presentation">
					<tr>
						<th><label for="grec_telegram_token">Bot token</label></th>
						<td>
							<input id="grec_telegram_token" class="regular-text" type="password" name="telegram_token" value="" autocomplete="new-password" placeholder="Leave blank to keep existing token">
							<p class="description">Stored encrypted using WordPress salts; never committed to Git.</p>
						</td>
					</tr>
				</table>
				<?php submit_button( 'Save Telegram destinations' ); ?>
			</form>
			<script>
			(function(){
				var button = document.getElementById('grec-add-telegram-destination');
				var body = document.getElementById('grec-telegram-destinations');
				if (!button || !body) return;
				button.addEventListener('click', function(){
					var rows = body.querySelectorAll('tr');
					var row = rows[rows.length - 1].cloneNode(true);
					row.querySelectorAll('input').forEach(function(input){ input.value = ''; });
					var level = row.querySelector('input[name="telegram_dest_level[]"]');
					if (level) level.value = 'community';
					var status = row.querySelector('select');
					if (status) status.value = '1';
					body.appendChild(row);
				});
			})();
			</script>
			<p><strong>Status:</strong> <?php echo GREC_Telegram::is_connected() ? 'Connected' : 'Not connected'; ?> · <?php echo esc_html( count( GREC_Telegram::enabled_destinations() ) ); ?> enabled destination(s)</p>
			<?php if ( GREC_Telegram::is_connected() ) : ?>
				<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="margin-bottom:20px">
					<input type="hidden" name="action" value="grec_test_telegram">
					<?php wp_nonce_field( 'grec_test_telegram' ); ?>
					<?php submit_button( 'Test all enabled Telegram destinations', 'secondary', 'submit', false ); ?>
				</form>

				<h3>Telegram Post Composer</h3>
				<p class="description">Emoji works natively. Formatting uses Telegram HTML: <code>&lt;b&gt;</code>, <code>&lt;i&gt;</code>, <code>&lt;u&gt;</code>, <code>&lt;s&gt;</code>, links, code and spoilers.</p>
				<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="max-width:1000px">
					<input type="hidden" name="action" value="grec_publish_telegram">
					<input type="hidden" id="grec-telegram-media-json" name="telegram_publish_media_json" value="[]">
					<?php wp_nonce_field( 'grec_publish_telegram' ); ?>

					<div style="display:flex;gap:6px;flex-wrap:wrap;margin:8px 0">
						<button type="button" class="button grec-tg-format" data-open="&lt;b&gt;" data-close="&lt;/b&gt;"><strong>B</strong></button>
						<button type="button" class="button grec-tg-format" data-open="&lt;i&gt;" data-close="&lt;/i&gt;"><em>I</em></button>
						<button type="button" class="button grec-tg-format" data-open="&lt;u&gt;" data-close="&lt;/u&gt;"><u>U</u></button>
						<button type="button" class="button grec-tg-format" data-open="&lt;s&gt;" data-close="&lt;/s&gt;"><s>S</s></button>
						<button type="button" class="button grec-tg-format" data-open="&lt;tg-spoiler&gt;" data-close="&lt;/tg-spoiler&gt;">Spoiler</button>
						<button type="button" class="button grec-tg-format" data-open="&lt;code&gt;" data-close="&lt;/code&gt;">Code</button>
						<button type="button" class="button grec-tg-link">Link</button>
						<span style="margin-left:6px">
							<button type="button" class="button grec-tg-emoji">🔥</button>
							<button type="button" class="button grec-tg-emoji">🌿</button>
							<button type="button" class="button grec-tg-emoji">❄️</button>
							<button type="button" class="button grec-tg-emoji">🧖‍♂️</button>
							<button type="button" class="button grec-tg-emoji">✨</button>
							<button type="button" class="button grec-tg-emoji">❤️</button>
						</span>
					</div>
					<p><textarea id="grec-telegram-message" name="telegram_publish_text" rows="7" class="large-text" placeholder="Message / caption — emoji welcome 🔥"></textarea></p>

					<div style="border:1px solid #dcdcde;background:#fff;padding:14px;margin:14px 0">
						<strong>Media</strong>
						<p class="description">Choose up to 10 items. Photo + video can be mixed in an album. Audio albums must be audio-only; document albums document-only; GIF/animation must be sent alone.</p>
						<p>
							<button type="button" class="button button-secondary" id="grec-tg-media-library">Choose from Media Library</button>
							<button type="button" class="button" id="grec-tg-clear-media">Clear</button>
						</p>
						<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
							<select id="grec-tg-manual-type">
								<option value="photo">Photo</option>
								<option value="video">Video</option>
								<option value="animation">GIF / Animation</option>
								<option value="audio">Audio</option>
								<option value="document">Document / PDF</option>
							</select>
							<input id="grec-tg-manual-url" type="url" class="regular-text code" placeholder="https://...">
							<button type="button" class="button" id="grec-tg-add-url">Add URL</button>
						</div>
						<ol id="grec-tg-media-list" style="margin-top:12px"></ol>
					</div>

					<fieldset style="margin:16px 0">
						<legend><strong>Destination levels</strong> <span class="description">(optional)</span></legend>
						<?php
						$telegram_levels = array_values( array_unique( array_map( static function ( $destination ) { return $destination['level']; }, GREC_Telegram::enabled_destinations() ) ) );
						foreach ( $telegram_levels as $level ) :
						?>
							<label style="display:inline-block;margin:6px 14px 6px 0">
								<input type="checkbox" name="telegram_publish_levels[]" value="<?php echo esc_attr( $level ); ?>"> <?php echo esc_html( $level ); ?>
							</label>
						<?php endforeach; ?>
					</fieldset>

					<fieldset>
						<legend><strong>Specific destinations</strong> <span class="description">(leave all level and destination boxes unchecked to publish to all enabled destinations)</span></legend>
						<?php foreach ( GREC_Telegram::enabled_destinations() as $destination ) : ?>
							<label style="display:block;margin:6px 0">
								<input type="checkbox" name="telegram_publish_targets[]" value="<?php echo esc_attr( $destination['key'] ); ?>">
								<?php echo esc_html( $destination['name'] ); ?> — <code><?php echo esc_html( $destination['level'] ); ?></code> — <code><?php echo esc_html( $destination['chat_id'] ); ?></code>
							</label>
						<?php endforeach; ?>
					</fieldset>
					<?php submit_button( 'Publish to Telegram' ); ?>
				</form>

				<script>
				(function(){
					var media = [];
					var hidden = document.getElementById('grec-telegram-media-json');
					var list = document.getElementById('grec-tg-media-list');
					var textarea = document.getElementById('grec-telegram-message');

					function inferType(attachment) {
						var mime = (attachment.mime || '').toLowerCase();
						var filename = (attachment.filename || '').toLowerCase();
						if (mime === 'image/gif' || filename.endsWith('.gif')) return 'animation';
						if (mime.indexOf('image/') === 0) return 'photo';
						if (mime.indexOf('video/') === 0) return 'video';
						if (mime.indexOf('audio/') === 0) return 'audio';
						return 'document';
					}
					function sync() {
						hidden.value = JSON.stringify(media);
						list.innerHTML = '';
						media.forEach(function(item,index){
							var li = document.createElement('li');
							li.style.marginBottom = '8px';
							li.innerHTML = '<code>' + item.type + '</code> ' + (item.name || item.url) +
								' <button type="button" class="button-link" data-action="up" data-index="'+index+'">↑</button>' +
								' <button type="button" class="button-link" data-action="down" data-index="'+index+'">↓</button>' +
								' <button type="button" class="button-link-delete" data-action="remove" data-index="'+index+'">Remove</button>';
							list.appendChild(li);
						});
					}
					function addItems(items) {
						items.forEach(function(item){
							if (media.length < 10 && item.url) media.push(item);
						});
						sync();
						if (media.length >= 10) alert('Telegram albums support a maximum of 10 media items.');
					}
					function insert(open, close) {
						var start = textarea.selectionStart, end = textarea.selectionEnd;
						var selected = textarea.value.slice(start,end);
						textarea.setRangeText(open + selected + close,start,end,'end');
						textarea.focus();
					}

					document.querySelectorAll('.grec-tg-format').forEach(function(button){
						button.addEventListener('click',function(){ insert(this.dataset.open,this.dataset.close); });
					});
					document.querySelectorAll('.grec-tg-emoji').forEach(function(button){
						button.addEventListener('click',function(){ insert(this.textContent,''); });
					});
					document.querySelector('.grec-tg-link').addEventListener('click',function(){
						var href = window.prompt('Link URL (https://...)');
						if (href) insert('<a href="'+href.replace(/"/g,'&quot;')+'">','</a>');
					});

					document.getElementById('grec-tg-media-library').addEventListener('click',function(){
						var frame = wp.media({title:'Choose Telegram media',button:{text:'Add to Telegram post'},multiple:true});
						frame.on('select',function(){
							var picked = frame.state().get('selection').toJSON().map(function(a){
								return {type:inferType(a),url:a.url,name:a.filename || a.title || ''};
							});
							addItems(picked);
						});
						frame.open();
					});

					document.getElementById('grec-tg-add-url').addEventListener('click',function(){
						var url = document.getElementById('grec-tg-manual-url').value.trim();
						var type = document.getElementById('grec-tg-manual-type').value;
						if (!url) return;
						addItems([{type:type,url:url,name:url.split('/').pop()}]);
						document.getElementById('grec-tg-manual-url').value = '';
					});
					document.getElementById('grec-tg-clear-media').addEventListener('click',function(){ media=[]; sync(); });
					list.addEventListener('click',function(e){
						var button=e.target.closest('button[data-action]');
						if(!button) return;
						var index=parseInt(button.dataset.index,10), action=button.dataset.action;
						if(action==='remove') media.splice(index,1);
						if(action==='up' && index>0){ var t=media[index-1]; media[index-1]=media[index]; media[index]=t; }
						if(action==='down' && index<media.length-1){ var t2=media[index+1]; media[index+1]=media[index]; media[index]=t2; }
						sync();
					});
					sync();
				})();
				</script>

			<?php endif; ?>

			<hr>
			<h2>VK Publisher</h2>
			<p>Publish Russian-language Moksha updates to a VK community wall. Community owner IDs use a leading minus sign, for example <code>-123456789</code>.</p>
			<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="max-width:900px">
				<input type="hidden" name="action" value="grec_save_vk">
				<?php wp_nonce_field( 'grec_save_vk' ); ?>
				<table class="form-table" role="presentation">
					<tr>
						<th><label for="grec_vk_owner_id">VK owner ID</label></th>
						<td><input id="grec_vk_owner_id" class="regular-text code" name="vk_owner_id" value="<?php echo esc_attr( GREC_VK::owner_id() ); ?>" placeholder="-123456789"></td>
					</tr>
					<tr>
						<th><label for="grec_vk_token">VK access token</label></th>
						<td>
							<input id="grec_vk_token" class="regular-text" type="password" name="vk_token" value="" autocomplete="new-password" placeholder="Leave blank to keep existing token">
							<p class="description">Stored encrypted. Text posts can use a suitable community token; photo-wall upload may require a user token with wall/photos access.</p>
						</td>
					</tr>
				</table>
				<?php submit_button( 'Save VK settings' ); ?>
			</form>
			<p><strong>Status:</strong> <?php echo GREC_VK::is_connected() ? 'Configured' : 'Not configured'; ?></p>

			<?php if ( GREC_VK::is_connected() ) : ?>
				<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="margin-bottom:18px">
					<input type="hidden" name="action" value="grec_test_vk">
					<?php wp_nonce_field( 'grec_test_vk' ); ?>
					<?php submit_button( 'Test VK connection', 'secondary', 'submit', false ); ?>
				</form>

				<h3>VK Post Composer</h3>
				<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="max-width:1000px">
					<input type="hidden" name="action" value="grec_publish_vk">
					<input type="hidden" id="grec-vk-media-json" name="vk_publish_media_json" value="[]">
					<?php wp_nonce_field( 'grec_publish_vk' ); ?>
					<p><textarea name="vk_publish_text" rows="6" class="large-text" placeholder="Russian VK copy — emoji supported 🔥"></textarea></p>
					<p><input name="vk_publish_link" type="url" class="large-text code" placeholder="Optional link, e.g. https://mokshagoa.com/#choose-and-pay"></p>

					<div style="border:1px solid #dcdcde;background:#fff;padding:14px;margin:14px 0">
						<strong>Photos</strong>
						<p class="description">Choose up to 10 images. They are uploaded to the VK wall before the post is created.</p>
						<p>
							<button type="button" class="button button-secondary" id="grec-vk-media-library">Choose photos</button>
							<button type="button" class="button" id="grec-vk-clear-media">Clear</button>
						</p>
						<ol id="grec-vk-media-list"></ol>
					</div>
					<?php submit_button( 'Publish to VK' ); ?>
				</form>
				<script>
				(function(){
					var media=[];
					var hidden=document.getElementById('grec-vk-media-json');
					var list=document.getElementById('grec-vk-media-list');
					var choose=document.getElementById('grec-vk-media-library');
					var clear=document.getElementById('grec-vk-clear-media');
					if(!hidden || !list || !choose || !clear || typeof wp === 'undefined' || !wp.media) return;

					function sync(){
						hidden.value=JSON.stringify(media);
						list.innerHTML='';
						media.forEach(function(item,index){
							var li=document.createElement('li');
							li.style.marginBottom='7px';
							li.textContent=item.name || item.url;
							var remove=document.createElement('button');
							remove.type='button';
							remove.className='button-link-delete';
							remove.style.marginLeft='8px';
							remove.textContent='Remove';
							remove.addEventListener('click',function(){ media.splice(index,1); sync(); });
							li.appendChild(remove);
							list.appendChild(li);
						});
					}

					choose.addEventListener('click',function(){
						var frame=wp.media({title:'Choose VK photos',button:{text:'Add photos'},multiple:true,library:{type:'image'}});
						frame.on('select',function(){
							frame.state().get('selection').toJSON().forEach(function(a){
								if(media.length<10 && a.url) media.push({type:'photo',url:a.url,name:a.filename || a.title || ''});
							});
							sync();
						});
						frame.open();
					});
					clear.addEventListener('click',function(){media=[];sync();});
					sync();
				})();
				</script>
			<?php endif; ?>
			<hr>
			<h2>Odnoklassniki Publisher</h2>
			<p>Publish Russian-language Moksha media topics to an OK group. The OK application must be approved and have <code>GROUP_CONTENT</code> and <code>PHOTO_CONTENT</code> permissions.</p>
			<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="max-width:950px">
				<input type="hidden" name="action" value="grec_save_ok">
				<?php wp_nonce_field( 'grec_save_ok' ); ?>
				<?php $ok_status = GREC_OK::status(); ?>
				<table class="form-table" role="presentation">
					<tr>
						<th><label for="grec_ok_application_id">Application ID</label></th>
						<td><input id="grec_ok_application_id" class="regular-text code" name="ok_application_id" value="<?php echo esc_attr( $ok_status['application_id'] ); ?>"></td>
					</tr>
					<tr>
						<th><label for="grec_ok_application_key">Application public key</label></th>
						<td><input id="grec_ok_application_key" class="regular-text code" name="ok_application_key" value="" placeholder="<?php echo $ok_status['application_key_saved'] ? 'Saved — enter only to replace' : 'Required'; ?>"></td>
					</tr>
					<tr>
						<th><label for="grec_ok_application_secret">Application secret</label></th>
						<td><input id="grec_ok_application_secret" class="regular-text" type="password" name="ok_application_secret" value="" autocomplete="new-password" placeholder="Leave blank to keep existing secret"></td>
					</tr>
					<tr>
						<th><label for="grec_ok_access_token">Access token</label></th>
						<td><input id="grec_ok_access_token" class="regular-text" type="password" name="ok_access_token" value="" autocomplete="new-password" placeholder="Leave blank to keep existing token"></td>
					</tr>
					<tr>
						<th><label for="grec_ok_group_id">Group ID</label></th>
						<td><input id="grec_ok_group_id" class="regular-text code" name="ok_group_id" value="<?php echo esc_attr( GREC_OK::group_id() ); ?>" placeholder="123456789"></td>
					</tr>
				</table>
				<p class="description"><strong>Approval required:</strong> OK documents that non-approved apps will not successfully create media topics. Credentials are encrypted and never exposed through status endpoints.</p>
				<?php submit_button( 'Save Odnoklassniki settings' ); ?>
			</form>

			<p><strong>Status:</strong> <?php echo GREC_OK::is_connected() ? 'Configured' : 'Not configured'; ?> · App approval required</p>
			<?php if ( GREC_OK::is_connected() ) : ?>
				<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="margin-bottom:18px">
					<input type="hidden" name="action" value="grec_test_ok">
					<?php wp_nonce_field( 'grec_test_ok' ); ?>
					<?php submit_button( 'Test Odnoklassniki API', 'secondary', 'submit', false ); ?>
				</form>

				<h3>Odnoklassniki Post Composer</h3>
				<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="max-width:1000px">
					<input type="hidden" name="action" value="grec_publish_ok">
					<input type="hidden" id="grec-ok-media-json" name="ok_publish_media_json" value="[]">
					<?php wp_nonce_field( 'grec_publish_ok' ); ?>
					<p><textarea name="ok_publish_text" rows="6" class="large-text" placeholder="Russian OK copy — emoji supported 🌿"></textarea></p>
					<p><input name="ok_publish_link" type="url" class="large-text code" placeholder="Optional link"></p>
					<div style="border:1px solid #dcdcde;background:#fff;padding:14px;margin:14px 0">
						<strong>Photos</strong>
						<p class="description">Choose up to 10 images. They are uploaded using the OK photo-token workflow and attached directly to the group media topic.</p>
						<p>
							<button type="button" class="button button-secondary" id="grec-ok-media-library">Choose photos</button>
							<button type="button" class="button" id="grec-ok-clear-media">Clear</button>
						</p>
						<ol id="grec-ok-media-list"></ol>
					</div>
					<?php submit_button( 'Publish to Odnoklassniki' ); ?>
				</form>
				<script>
				(function(){
					var media=[];
					var hidden=document.getElementById('grec-ok-media-json');
					var list=document.getElementById('grec-ok-media-list');
					var choose=document.getElementById('grec-ok-media-library');
					var clear=document.getElementById('grec-ok-clear-media');
					if(!hidden || !list || !choose || !clear || typeof wp === 'undefined' || !wp.media) return;
					function sync(){
						hidden.value=JSON.stringify(media);
						list.innerHTML='';
						media.forEach(function(item,index){
							var li=document.createElement('li');
							li.style.marginBottom='7px';
							li.textContent=item.name || item.url;
							var remove=document.createElement('button');
							remove.type='button';
							remove.className='button-link-delete';
							remove.style.marginLeft='8px';
							remove.textContent='Remove';
							remove.addEventListener('click',function(){media.splice(index,1);sync();});
							li.appendChild(remove);
							list.appendChild(li);
						});
					}
					choose.addEventListener('click',function(){
						var frame=wp.media({title:'Choose Odnoklassniki photos',button:{text:'Add photos'},multiple:true,library:{type:'image'}});
						frame.on('select',function(){
							frame.state().get('selection').toJSON().forEach(function(a){
								if(media.length<10 && a.url) media.push({type:'photo',url:a.url,name:a.filename || a.title || ''});
							});
							sync();
						});
						frame.open();
					});
					clear.addEventListener('click',function(){media=[];sync();});
					sync();
				})();
				</script>
			<?php endif; ?>

			<hr>
			<h2>Snapchat Handoff</h2>
			<p>Prepare Moksha Story/Snap media in WordPress and hand it to the paired Android device. Snapchat opens directly on the Preview screen; the final Story/send confirmation happens in Snapchat.</p>
			<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="max-width:950px">
				<input type="hidden" name="action" value="grec_save_snapchat">
				<?php wp_nonce_field( 'grec_save_snapchat' ); ?>
				<table class="form-table" role="presentation">
					<tr>
						<th><label for="grec_snapchat_client_id">Snap Client ID</label></th>
						<td>
							<input id="grec_snapchat_client_id" class="regular-text code" name="snapchat_client_id" value="<?php echo esc_attr( GREC_Snapchat::client_id() ); ?>">
							<p class="description">From the approved Snap Developer Portal application.</p>
						</td>
					</tr>
					<tr>
						<th><label for="grec_snapchat_device_key">Android pairing key</label></th>
						<td>
							<input id="grec_snapchat_device_key" class="large-text code" type="password" name="snapchat_device_key" value="<?php echo esc_attr( GREC_Snapchat::device_key() ); ?>" autocomplete="off">
							<p class="description">Generated locally by Engagement Core when empty. Keep this private; the Android companion uses it to claim handoff jobs.</p>
						</td>
					</tr>
				</table>
				<?php submit_button( 'Save Snapchat settings' ); ?>
			</form>
			<p><strong>Status:</strong> <?php echo GREC_Snapchat::is_configured() ? 'Configured' : 'Not configured'; ?> · <?php echo esc_html( GREC_Snapchat::pending_count() ); ?> pending handoff(s) · Final confirmation required on device</p>

			<?php if ( GREC_Snapchat::is_configured() ) : ?>
				<h3>Snapchat Story / Snap Composer</h3>
				<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="max-width:1000px">
					<input type="hidden" name="action" value="grec_queue_snapchat">
					<input type="hidden" id="grec-snap-media-url" name="snapchat_media_url" value="">
					<input type="hidden" id="grec-snap-media-type" name="snapchat_media_type" value="">
					<?php wp_nonce_field( 'grec_queue_snapchat' ); ?>
					<p><textarea name="snapchat_caption" rows="5" class="large-text" placeholder="Caption / on-Snap text — Russian or English, emoji supported 🔥"></textarea></p>
					<div style="border:1px solid #dcdcde;background:#fff;padding:14px;margin:14px 0">
						<strong>Full-screen media</strong>
						<p class="description">Choose one 9:16 photo or video. The Android companion downloads it and opens Snapchat Creative Kit Lite Preview.</p>
						<p><button type="button" class="button button-secondary" id="grec-snap-media-library">Choose photo/video</button> <button type="button" class="button" id="grec-snap-clear-media">Clear</button></p>
						<div id="grec-snap-media-label">No media selected.</div>
					</div>
					<?php submit_button( 'Queue for Snapchat' ); ?>
				</form>

				<script>
				(function(){
					var choose=document.getElementById('grec-snap-media-library');
					var clear=document.getElementById('grec-snap-clear-media');
					var url=document.getElementById('grec-snap-media-url');
					var type=document.getElementById('grec-snap-media-type');
					var label=document.getElementById('grec-snap-media-label');
					if(!choose || !clear || !url || !type || !label || typeof wp === 'undefined' || !wp.media) return;
					choose.addEventListener('click',function(){
						var frame=wp.media({title:'Choose Snapchat media',button:{text:'Use for Snapchat'},multiple:false});
						frame.on('select',function(){
							var a=frame.state().get('selection').first().toJSON();
							var mime=(a.mime || '').toLowerCase();
							var kind=mime.indexOf('video/')===0 ? 'video' : (mime.indexOf('image/')===0 ? 'image' : '');
							if(!kind){ window.alert('Choose an image or video.'); return; }
							url.value=a.url || '';
							type.value=kind;
							label.textContent=(a.filename || a.title || a.url) + ' (' + kind + ')';
						});
						frame.open();
					});
					clear.addEventListener('click',function(){url.value='';type.value='';label.textContent='No media selected.';});
				})();
				</script>
			<?php endif; ?>

			<?php $snap_recent = GREC_Snapchat::recent( 10 ); ?>
			<?php if ( $snap_recent ) : ?>
				<h3>Recent Snapchat handoffs</h3>
				<table class="widefat striped" style="max-width:1000px">
					<thead><tr><th>Created</th><th>Media</th><th>Status</th><th>Task</th></tr></thead>
					<tbody>
					<?php foreach ( $snap_recent as $task ) : ?>
						<tr>
							<td><?php echo esc_html( ! empty( $task['created_at'] ) ? wp_date( 'Y-m-d H:i:s', (int) $task['created_at'] ) : '' ); ?></td>
							<td><?php echo esc_html( $task['media_type'] ?? '' ); ?></td>
							<td><strong><?php echo esc_html( $task['status'] ?? '' ); ?></strong><?php if ( ! empty( $task['error'] ) ) : ?><br><small><?php echo esc_html( $task['error'] ); ?></small><?php endif; ?></td>
							<td><code><?php echo esc_html( $task['id'] ?? '' ); ?></code></td>
						</tr>
					<?php endforeach; ?>
					</tbody>
				</table>
			<?php endif; ?>

			<hr>
			<h2>Inbox</h2>
			<?php if ( ! $comments ) : ?>
				<p>No comments synced yet.</p>
			<?php endif; ?>
			<?php foreach ( $comments as $comment ) : ?>
				<div style="background:#fff;border:1px solid #dcdcde;border-radius:8px;padding:14px 16px;margin:12px 0;max-width:1000px">
					<div>
						<strong><?php echo esc_html( $comment['author_name'] ); ?></strong>
						· <?php echo esc_html( $comment['published_at'] ?: $comment['synced_at'] ); ?>
						· <?php echo esc_html( $comment['like_count'] ); ?> likes
					</div>
					<p style="font-size:14px"><?php echo esc_html( wp_strip_all_tags( $comment['comment_text'] ) ); ?></p>
					<?php if ( $comment['our_reply_text'] ) : ?>
						<p><strong>Replied:</strong> <?php echo esc_html( $comment['our_reply_text'] ); ?></p>
					<?php endif; ?>
					<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="display:flex;gap:8px;align-items:flex-start;margin-bottom:8px">
						<input type="hidden" name="action" value="grec_reply">
						<input type="hidden" name="comment_id" value="<?php echo esc_attr( $comment['external_id'] ); ?>">
						<?php wp_nonce_field( 'grec_reply' ); ?>
						<textarea name="reply_text" rows="2" style="width:70%;max-width:650px" placeholder="Write a human reply…"></textarea>
						<button class="button button-primary">Reply</button>
					</form>
					<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="display:inline-block;margin-right:6px">
						<input type="hidden" name="action" value="grec_moderate">
						<input type="hidden" name="comment_id" value="<?php echo esc_attr( $comment['external_id'] ); ?>">
						<input type="hidden" name="status" value="heldForReview">
						<?php wp_nonce_field( 'grec_moderate' ); ?>
						<button class="button">Hold</button>
					</form>
					<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="display:inline-block">
						<input type="hidden" name="action" value="grec_moderate">
						<input type="hidden" name="comment_id" value="<?php echo esc_attr( $comment['external_id'] ); ?>">
						<input type="hidden" name="status" value="rejected">
						<?php wp_nonce_field( 'grec_moderate' ); ?>
						<button class="button">Reject</button>
					</form>
				</div>
			<?php endforeach; ?>
			<script>
			(function(){
				var overlay = document.getElementById('grec-loading-overlay');
				var message = document.getElementById('grec-loading-message');
				if (!overlay || !message) return;

				var labels = {
					grec_save_settings: 'Saving settings…',
					grec_sync_now: 'Syncing comments…',
					grec_youtube_disconnect: 'Disconnecting YouTube…',
					grec_reply: 'Posting reply…',
					grec_moderate: 'Updating moderation…',
					grec_save_telegram: 'Saving Telegram destinations…',
					grec_test_telegram: 'Testing Telegram destinations…',
					grec_publish_telegram: 'Publishing to Telegram…',
					grec_generate_publish_key: 'Generating publishing key…',
					grec_revoke_publish_key: 'Revoking publishing key…',
					grec_save_vk: 'Saving VK settings…',
					grec_test_vk: 'Testing VK connection…',
					grec_publish_vk: 'Publishing to VK…',
					grec_save_ok: 'Saving Odnoklassniki settings…',
					grec_test_ok: 'Testing Odnoklassniki API…',
					grec_publish_ok: 'Publishing to Odnoklassniki…',
					grec_save_snapchat: 'Saving Snapchat settings…',
					grec_queue_snapchat: 'Queueing Snapchat handoff…'
				};

				function setBusy(form) {
					if (document.body.classList.contains('grec-ui-busy')) return false;
					var actionField = form.querySelector('input[name="action"]');
					var action = actionField ? actionField.value : '';
					message.textContent = labels[action] || 'Saving…';
					document.body.classList.add('grec-ui-busy');
					overlay.classList.add('is-active');
					overlay.setAttribute('aria-hidden','false');
					form.setAttribute('aria-busy','true');
					form.querySelectorAll('button[type="submit"],input[type="submit"]').forEach(function(button){
						button.disabled = true;
					});
					return true;
				}

				function resetBusy() {
					document.body.classList.remove('grec-ui-busy');
					overlay.classList.remove('is-active');
					overlay.setAttribute('aria-hidden','true');
					document.querySelectorAll('form[aria-busy="true"]').forEach(function(form){
						form.removeAttribute('aria-busy');
						form.querySelectorAll('button[type="submit"],input[type="submit"]').forEach(function(button){
							button.disabled = false;
						});
					});
				}

				document.querySelectorAll('form[action*="admin-post.php"]').forEach(function(form){
					form.addEventListener('submit',function(event){
						if (!setBusy(form)) event.preventDefault();
					});
				});
				window.addEventListener('pageshow', resetBusy);
			})();
			</script>
		</div>
		<?php
	}
}
