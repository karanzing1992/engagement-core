<?php
/**
 * Plugin Name: WP Control
 * Description: Secure WordPress execution bridge for ChatGPT plugins and MCP clients.
 * Version: 0.1.1
 * Author: KaranBiz
 * Requires at least: 7.1
 * Requires PHP: 8.0
 * Requires Plugins: cowboy-mcp
 * Text Domain: wp-control
 */

defined( 'ABSPATH' ) || exit;

define( 'WPCONTROL_VERSION', '0.1.1' )
define( 'WPCONTROL_FILE', __FILE__ );
define( 'WPCONTROL_DIR', plugin_dir_path( __FILE__ ) );

require_once WPCONTROL_DIR . 'src/class-wp-control-bridge.php';

add_action( 'plugins_loaded', array( 'WPControl_Bridge', 'init' ) );
register_activation_hook( __FILE__, array( 'WPControl_Bridge', 'activate' ) );
