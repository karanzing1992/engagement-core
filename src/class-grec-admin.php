<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class GREC_Admin {
	public static function init(): void {
		add_action( 'admin_menu', array( __CLASS__, 'menu' ) );
		add_action( 'admin_post_grec_save_settings', array( __CLASS__, 'save_settings' ) );
		add_action( 'admin_post_grec_youtube_oauth', array( __CLASS__, 'oauth_callback' ) );
		add_action( 'admin_post_grec_youtube_disconnect', array( __CLASS__, 'disconnect' ) );
		add_action( 'admin_post_grec_sync_now', array( __CLASS__, 'sync_now' ) );
		add_action( 'admin_post_grec_reply', array( __CLASS__, 'reply' ) );
		add_action( 'admin_post_grec_moderate', array( __CLASS__, 'moderate' ) );
	}

	private static function guard(): void {
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_die( esc_html__( 'You do not have permission to manage Engagement Core.', 'engagement-core' ) );
		}
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
		<div class="wrap">
			<h1>Engagement Core</h1>
			<p>Unified engagement inbox. V1 uses the official YouTube Data API for comment sync, replies and moderation.</p>
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
		</div>
		<?php
	}
}
