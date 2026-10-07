<?php
/**
 * Plugin Name: Engagement Core
 * Description: Brand-agnostic social engagement, publishing and WordPress AI control core.
 * Version: 0.8.6
 * Author: KaranBiz
 * Requires at least: 6.9
 * Requires PHP: 7.4
 * Text Domain: engagement-core
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'GREC_VERSION', '0.8.6' )
define( 'GREC_FILE', __FILE__ );
define( 'GREC_DIR', plugin_dir_path( __FILE__ ) );

require_once GREC_DIR . 'src/class-grec-secrets.php';
require_once GREC_DIR . 'src/class-grec-repository.php';
require_once GREC_DIR . 'src/class-grec-youtube.php';
require_once GREC_DIR . 'src/class-grec-scheduler.php';
require_once GREC_DIR . 'src/class-grec-admin.php';
require_once GREC_DIR . 'src/class-grec-telegram.php';
require_once GREC_DIR . 'src/class-grec-vk.php';
require_once GREC_DIR . 'src/class-grec-ok.php';
require_once GREC_DIR . 'src/class-grec-snapchat.php';
require_once GREC_DIR . 'src/class-grec-publisher-rest.php';
require_once GREC_DIR . 'src/class-grec-wp-control.php';

final class GREC_Plugin {
	public static function init(): void {
		GREC_Scheduler::init();
		GREC_Admin::init();
		GREC_Publisher_REST::init();
		GREC_WordPress_Control::init();
	}

	public static function activate(): void {
		GREC_Repository::install();
		add_option( 'grec_brand_name', 'Goa Reset' );
		add_option( 'grec_youtube_channel_id', 'UCSYkzC8ctGKzMK1fhvy6FcA' );
		add_option( 'grec_auto_sync', '1' );
		add_option( 'grec_sync_interval_minutes', '10' );
	}

	public static function deactivate(): void {
		GREC_Scheduler::clear();
	}
}

register_activation_hook( __FILE__, array( 'GREC_Plugin', 'activate' ) );
register_deactivation_hook( __FILE__, array( 'GREC_Plugin', 'deactivate' ) );
add_action( 'plugins_loaded', array( 'GREC_Plugin', 'init' ) );
