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
