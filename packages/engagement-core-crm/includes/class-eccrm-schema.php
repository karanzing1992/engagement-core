<?php
/** Database schema, explicitly local to the WordPress installation. */
defined( 'ABSPATH' ) || exit;

final class ECCRM_Schema {
    public const VERSION = '0.1.0';

    public static function table( string $name ): string {
        global $wpdb;
        $allowed = array( 'contacts', 'events', 'identities' );
        if ( ! in_array( $name, $allowed, true ) ) {
            throw new InvalidArgumentException( 'Unknown CRM table' );
        }
        return $wpdb->prefix . 'eccrm_' . $name;
    }

    public static function activate(): void {
        global $wpdb;
        require_once ABSPATH . 'wp-admin/includes/upgrade.php';
        $collation = $wpdb->get_charset_collate();
        $contacts = self::table( 'contacts' );
        $identities = self::table( 'identities' );
        $events = self::table( 'events' );

        dbDelta( "CREATE TABLE {$contacts} (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            display_name varchar(190) NOT NULL,
            email varchar(190) NOT NULL DEFAULT '',
            phone varchar(48) NOT NULL DEFAULT '',
            lifecycle varchar(24) NOT NULL DEFAULT 'lead',
            source varchar(48) NOT NULL DEFAULT 'manual',
            external_id varchar(128) DEFAULT NULL,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (id),
            UNIQUE KEY external_identity (source,external_id),
            KEY email (email),
            KEY updated_at (updated_at)
        ) {$collation};" );
        dbDelta( "CREATE TABLE {$identities} (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            contact_id bigint(20) unsigned NOT NULL,
            system_key varchar(48) NOT NULL,
            subject_key varchar(128) NOT NULL,
            verified_at datetime DEFAULT NULL,
            created_at datetime NOT NULL,
            PRIMARY KEY  (id),
            UNIQUE KEY source_subject (system_key,subject_key),
            KEY contact_id (contact_id)
        ) {$collation};" );
        dbDelta( "CREATE TABLE {$events} (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            event_uuid char(36) NOT NULL,
            event_type varchar(80) NOT NULL,
            entity_id bigint(20) unsigned NOT NULL,
            actor_id bigint(20) unsigned NOT NULL DEFAULT 0,
            payload_json longtext NOT NULL,
            delivery_state varchar(24) NOT NULL DEFAULT 'local_only',
            created_at datetime NOT NULL,
            PRIMARY KEY  (id),
            UNIQUE KEY event_uuid (event_uuid),
            KEY entity_id (entity_id),
            KEY delivery_state (delivery_state)
        ) {$collation};" );

        // Database creation must precede granting access. No customer data is removed on deactivation.
        update_option( 'eccrm_schema_version', self::VERSION, false );
        $admin = get_role( 'administrator' );
        if ( $admin ) {
            $admin->add_cap( ECCRM_CAPABILITY );
        }
    }
}
