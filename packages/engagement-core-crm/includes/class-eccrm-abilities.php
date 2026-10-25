<?php
/** WordPress 6.9+ ability definition. Initially internal-only; no anonymous or external agent exposure. */
defined( 'ABSPATH' ) || exit;

final class ECCRM_Abilities {
    public static function register(): void {
        if ( ! function_exists( 'wp_register_ability' ) || ! function_exists( 'wp_register_ability_category' ) ) {
            return;
        }
        add_action( 'wp_abilities_api_categories_init', array( __CLASS__, 'categories' ) );
        add_action( 'wp_abilities_api_init', array( __CLASS__, 'abilities' ) );
    }

    public static function categories(): void {
        wp_register_ability_category( 'engagement-core-crm', array(
            'label' => __( 'Engagement CRM', 'engagement-core-crm' ),
            'description' => __( 'Locally hosted CRM operations.', 'engagement-core-crm' ),
        ) );
    }

    public static function abilities(): void {
        wp_register_ability( 'engagement-core-crm/list-contacts', array(
            'label' => __( 'List CRM contacts', 'engagement-core-crm' ),
            'description' => __( 'Returns a bounded contact list to an authorized CRM operator.', 'engagement-core-crm' ),
            'category' => 'engagement-core-crm',
            'input_schema' => array( 'type' => 'object', 'properties' => array( 'limit' => array( 'type' => 'integer', 'minimum' => 1, 'maximum' => 100 ) ), 'additionalProperties' => false ),
            'output_schema' => array( 'type' => 'object' ),
            'execute_callback' => static function ( $input ): array {
                $limit = is_array( $input ) ? (int) ( $input['limit'] ?? 25 ) : 25;
                return array( 'items' => ECCRM_Contacts::list( $limit ) );
            },
            'permission_callback' => static function (): bool { return current_user_can( ECCRM_CAPABILITY ); },
            'meta' => array( 'show_in_rest' => false, 'annotations' => array( 'readonly' => true ) ),
        ) );
    }
}
