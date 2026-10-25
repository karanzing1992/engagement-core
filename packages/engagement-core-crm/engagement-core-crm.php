<?php
/**
 * Plugin Name: Engagement Core CRM
 * Description: Locally hosted customer records and integration-ready CRM foundation. External AI is optional.
 * Version: 0.1.0-dev
 * Requires at least: 6.9
 * Requires PHP: 8.1
 * Author: Engagement Core
 * License: GPL-2.0-or-later
 * Text Domain: engagement-core-crm
 */

defined( 'ABSPATH' ) || exit;

if ( ! defined( 'ECCRM_VERSION' ) ) {
    define( 'ECCRM_VERSION', '0.1.0-dev' );
    define( 'ECCRM_PATH', plugin_dir_path( __FILE__ ) );
    define( 'ECCRM_CAPABILITY', 'manage_eccrm' );
}

require_once ECCRM_PATH . 'includes/class-eccrm-schema.php';
require_once ECCRM_PATH . 'includes/class-eccrm-contacts.php';
require_once ECCRM_PATH . 'includes/class-eccrm-rest.php';
require_once ECCRM_PATH . 'includes/class-eccrm-admin.php';
require_once ECCRM_PATH . 'includes/class-eccrm-abilities.php';

register_activation_hook( __FILE__, array( 'ECCRM_Schema', 'activate' ) );

add_action( 'plugins_loaded', static function (): void {
    if ( version_compare( get_bloginfo( 'version' ), '6.9', '<' ) ) {
        return;
    }
    ECCRM_REST::register();
    ECCRM_Admin::register();
    ECCRM_Abilities::register();
} );
