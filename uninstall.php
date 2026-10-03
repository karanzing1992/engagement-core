<?php
if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
	exit;
}

// Keep data by default to prevent accidental loss. Define GREC_PURGE_ON_UNINSTALL=true in wp-config.php to fully purge.
if ( ! defined( 'GREC_PURGE_ON_UNINSTALL' ) || true !== GREC_PURGE_ON_UNINSTALL ) {
	return;
}

global $wpdb;
$wpdb->query( 'DROP TABLE IF EXISTS ' . $wpdb->prefix . 'grec_comments' );
foreach ( array(
	'grec_brand_name','grec_youtube_channel_id','grec_auto_sync','grec_sync_interval_minutes','grec_youtube_client_id','grec_youtube_client_secret','grec_youtube_token','grec_youtube_connected_channel_id','grec_youtube_connected_channel_title','grec_last_sync_at','grec_last_error'
) as $option ) {
	delete_option( $option );
}
