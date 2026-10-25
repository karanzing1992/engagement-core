<?php
/** Contact persistence and strictly local audit events. */
defined( 'ABSPATH' ) || exit;

final class ECCRM_Contacts {
    public static function normalize( array $input, bool $create = true ): array {
        $allowed = array( 'display_name', 'email', 'phone', 'lifecycle', 'source', 'external_id' );
        $data = array_intersect_key( $input, array_flip( $allowed ) );
        foreach ( $data as $field => $value ) {
            if ( null !== $value && ! is_scalar( $value ) ) {
                return array( 'error' => 'Invalid field type: ' . $field );
            }
        }
        if ( array_key_exists( 'display_name', $data ) ) {
            $data['display_name'] = sanitize_text_field( (string) $data['display_name'] );
            if ( '' === $data['display_name'] ) {
                return array( 'error' => 'Contact name must not be empty.' );
            }
            $data['display_name'] = function_exists( 'mb_substr' ) ? mb_substr( $data['display_name'], 0, 190 ) : substr( $data['display_name'], 0, 190 );
        } elseif ( $create ) {
            return array( 'error' => 'Contact name is required.' );
        }
        if ( array_key_exists( 'email', $data ) ) {
            $raw_email = trim( (string) $data['email'] );
            $data['email'] = sanitize_email( $raw_email );
            if ( '' !== $raw_email && ! is_email( $data['email'] ) ) {
                return array( 'error' => 'Invalid contact email.' );
            }
            $data['email'] = substr( $data['email'], 0, 190 );
        }
        if ( array_key_exists( 'phone', $data ) ) {
            $data['phone'] = substr( sanitize_text_field( (string) $data['phone'] ), 0, 48 );
        }
        if ( array_key_exists( 'lifecycle', $data ) ) {
            $data['lifecycle'] = sanitize_key( (string) $data['lifecycle'] );
            if ( ! in_array( $data['lifecycle'], array( 'lead', 'qualified', 'customer', 'inactive' ), true ) ) {
                return array( 'error' => 'Unsupported lifecycle value.' );
            }
        }
        if ( array_key_exists( 'source', $data ) ) {
            $data['source'] = sanitize_key( (string) $data['source'] );
            if ( ! preg_match( '/^[a-z0-9_-]{2,48}$/', $data['source'] ) ) {
                return array( 'error' => 'Invalid source.' );
            }
        }
        if ( array_key_exists( 'external_id', $data ) ) {
            $data['external_id'] = sanitize_text_field( (string) $data['external_id'] );
            if ( '' === $data['external_id'] ) {
                $data['external_id'] = null;
            } elseif ( strlen( $data['external_id'] ) > 128 ) {
                return array( 'error' => 'External identifier too long.' );
            }
        }
        return $data;
    }

    public static function list( int $limit = 25, int $offset = 0, string $search = '', string $lifecycle = '' ): array {
        global $wpdb;
        $table = ECCRM_Schema::table( 'contacts' );
        $limit = min( max( $limit, 1 ), 100 );
        $offset = max( $offset, 0 );
        $where = array();
        $args = array();
        $search = substr( sanitize_text_field( $search ), 0, 100 );
        if ( '' !== $search ) {
            $like = '%' . $wpdb->esc_like( $search ) . '%';
            $where[] = '(display_name LIKE %s OR email LIKE %s OR phone LIKE %s)';
            array_push( $args, $like, $like, $like );
        }
        if ( in_array( $lifecycle, array( 'lead', 'qualified', 'customer', 'inactive' ), true ) ) {
            $where[] = 'lifecycle = %s';
            $args[] = $lifecycle;
        }
        $filter = $where ? ' WHERE ' . implode( ' AND ', $where ) : '';
        $sql = "SELECT id, display_name, email, phone, lifecycle, source, created_at, updated_at
                FROM {$table}{$filter} ORDER BY id DESC LIMIT %d OFFSET %d";
        $args[] = $limit;
        $args[] = $offset;
        return (array) $wpdb->get_results( $wpdb->prepare( $sql, $args ), ARRAY_A );
    }

    public static function summary(): array {
        global $wpdb;
        $table = ECCRM_Schema::table( 'contacts' );
        $rows = (array) $wpdb->get_results(
            "SELECT lifecycle, COUNT(*) AS total FROM {$table} GROUP BY lifecycle",
            ARRAY_A
        );
        $counts = array( 'total' => 0, 'lead' => 0, 'qualified' => 0, 'customer' => 0, 'inactive' => 0 );
        foreach ( $rows as $row ) {
            $count = (int) $row['total'];
            $counts['total'] += $count;
            if ( array_key_exists( $row['lifecycle'], $counts ) && 'total' !== $row['lifecycle'] ) {
                $counts[ $row['lifecycle'] ] += $count;
            }
        }
        return $counts;
    }

    public static function activity( int $limit = 20 ): array {
        global $wpdb;
        $table = ECCRM_Schema::table( 'events' );
        $limit = min( max( $limit, 1 ), 50 );
        return (array) $wpdb->get_results(
            $wpdb->prepare(
                "SELECT id, event_type, entity_id, created_at FROM {$table} ORDER BY id DESC LIMIT %d",
                $limit
            ),
            ARRAY_A
        );
    }

    public static function find( int $id ): ?array {
        global $wpdb;
        if ( $id <= 0 ) {
            return null;
        }
        $table = ECCRM_Schema::table( 'contacts' );
        $record = $wpdb->get_row( $wpdb->prepare( "SELECT id, display_name, email, phone, lifecycle, source, external_id, created_at, updated_at FROM {$table} WHERE id = %d", $id ), ARRAY_A );
        return $record ? (array) $record : null;
    }

    public static function create( array $input ) {
        global $wpdb;
        $data = self::normalize( $input );
        if ( isset( $data['error'] ) ) {
            return new WP_Error( 'eccrm_invalid_contact', $data['error'], array( 'status' => 400 ) );
        }
        $data['created_at'] = current_time( 'mysql', true );
        $data['updated_at'] = $data['created_at'];
        $ok = $wpdb->insert( ECCRM_Schema::table( 'contacts' ), $data );
        if ( false === $ok ) {
            return new WP_Error( 'eccrm_conflict', 'Unable to create contact; possible duplicate external identity.', array( 'status' => 409 ) );
        }
        $id = (int) $wpdb->insert_id;
        self::record_local_event( 'contact.created', $id, $data );
        return self::find( $id );
    }

    public static function update( int $id, array $input ) {
        global $wpdb;
        if ( ! self::find( $id ) ) {
            return new WP_Error( 'eccrm_not_found', 'Contact not found.', array( 'status' => 404 ) );
        }
        // Source-bound identifiers cannot be changed by generic contact edits.
        unset( $input['source'], $input['external_id'] );
        $data = self::normalize( $input, false );
        if ( isset( $data['error'] ) ) {
            return new WP_Error( 'eccrm_invalid_contact', $data['error'], array( 'status' => 400 ) );
        }
        if ( ! $data ) {
            return new WP_Error( 'eccrm_invalid_contact', 'No editable fields supplied.', array( 'status' => 400 ) );
        }
        $data['updated_at'] = current_time( 'mysql', true );
        $ok = $wpdb->update( ECCRM_Schema::table( 'contacts' ), $data, array( 'id' => $id ) );
        if ( false === $ok ) {
            return new WP_Error( 'eccrm_update_failed', 'Unable to update contact.', array( 'status' => 500 ) );
        }
        if ( $ok > 0 ) {
            self::record_local_event( 'contact.updated', $id, $data );
        }
        return self::find( $id );
    }

    private static function record_local_event( string $event, int $contact_id, array $data ): void {
        global $wpdb;
        // Only metadata here. Never replicate email, phone or raw customer details into an event payload.
        $wpdb->insert( ECCRM_Schema::table( 'events' ), array(
            'event_uuid' => wp_generate_uuid4(),
            'event_type' => $event,
            'entity_id' => $contact_id,
            'actor_id' => get_current_user_id(),
            'payload_json' => wp_json_encode( array( 'changed_fields' => array_keys( $data ) ) ),
            'delivery_state' => 'local_only',
            'created_at' => current_time( 'mysql', true ),
        ) );
        // Deliberately NO webhook dispatch. External delivery requires a separate outbox/consent release gate.
    }
}
