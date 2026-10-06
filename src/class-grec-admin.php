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
		add_action( 'admin_post_grec_save_telegram', array( __CLASS__, 'save_telegram' ) );
		add_action( 'admin_post_grec_test_telegram', array( __CLASS__, 'test_telegram' ) );
		add_action( 'admin_post_grec_publish_telegram', array( __CLASS__, 'publish_telegram' ) );
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

		$text      = sanitize_textarea_field( (string) wp_unslash( $_POST['telegram_publish_text'] ?? '' ) );
		$media_url = esc_url_raw( (string) wp_unslash( $_POST['telegram_publish_media_url'] ?? '' ) );
		$targets   = isset( $_POST['telegram_publish_targets'] ) && is_array( $_POST['telegram_publish_targets'] )
			? array_map( 'sanitize_text_field', wp_unslash( $_POST['telegram_publish_targets'] ) )
			: array();

		if ( '' === $text ) {
			self::redirect( 'Telegram publish text is required.', 'error' );
		}

		try {
			$data   = GREC_Telegram::send( $text, $media_url, $targets );
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
			<h2>Telegram Publisher</h2>
			<p>One encrypted bot can publish to multiple Telegram groups/channels. Use levels such as <code>primary</code>, <code>community</code>, <code>partner</code>, or <code>promo</code>.</p>
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

				<h3>Quick publish</h3>
				<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="max-width:900px">
					<input type="hidden" name="action" value="grec_publish_telegram">
					<?php wp_nonce_field( 'grec_publish_telegram' ); ?>
					<p><textarea name="telegram_publish_text" rows="5" class="large-text" placeholder="Message / caption"></textarea></p>
					<p><input name="telegram_publish_media_url" type="url" class="large-text code" placeholder="Optional public video URL"></p>
					<fieldset>
						<legend><strong>Destinations</strong> <span class="description">(leave all unchecked to publish to all enabled destinations)</span></legend>
						<?php foreach ( GREC_Telegram::enabled_destinations() as $destination ) : ?>
							<label style="display:block;margin:6px 0">
								<input type="checkbox" name="telegram_publish_targets[]" value="<?php echo esc_attr( $destination['key'] ); ?>">
								<?php echo esc_html( $destination['name'] ); ?> — <code><?php echo esc_html( $destination['level'] ); ?></code> — <code><?php echo esc_html( $destination['chat_id'] ); ?></code>
							</label>
						<?php endforeach; ?>
					</fieldset>
					<?php submit_button( 'Publish to Telegram' ); ?>
				</form>
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
