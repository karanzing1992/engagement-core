<?php
/**
 * Plugin Name: Media Studio — Private Drafts
 * Description: Administrator-only, nonpublishing Reel/Shorts draft workspace with source ledgers and approval gates.
 * Version: 0.1.0
 * Requires at least: 6.5
 * Requires PHP: 8.0
 * Author: Studio Engine
 * License: MIT
 * Text Domain: mrs-media-studio
 */

defined( 'ABSPATH' ) || exit;

define( 'MRS_STUDIO_VERSION', '0.1.0' );
define( 'MRS_STUDIO_PATH', plugin_dir_path( __FILE__ ) );
define( 'MRS_STUDIO_URL', plugin_dir_url( __FILE__ ) );

require_once MRS_STUDIO_PATH . 'includes/class-mrs-policy.php';
require_once MRS_STUDIO_PATH . 'includes/class-mrs-studio.php';

MRS_Studio::register();