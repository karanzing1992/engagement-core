<?php
/** Conservative first-cut WP admin UI, no public pages or customer data exports. */
defined( 'ABSPATH' ) || exit;

final class ECCRM_Admin {
    public static function register(): void {
        add_action( 'admin_menu', array( __CLASS__, 'menu' ) );
        add_action( 'admin_post_eccrm_create_contact', array( __CLASS__, 'post_create' ) );
    }

    public static function menu(): void {
        add_menu_page( 'Engagement CRM', 'Engagement CRM', ECCRM_CAPABILITY, 'engagement-core-crm', array( __CLASS__, 'page' ), 'dashicons-groups', 26 );
    }

    public static function post_create(): void {
        if ( ! current_user_can( ECCRM_CAPABILITY ) ) {
            wp_die( esc_html__( 'CRM access denied.', 'engagement-core-crm' ), '', array( 'response' => 403 ) );
        }
        check_admin_referer( 'eccrm_create_contact' );
        $post = wp_unslash( $_POST );
        $result = ECCRM_Contacts::create( array(
            'display_name' => $post['display_name'] ?? '',
            'email' => $post['email'] ?? '',
            'phone' => $post['phone'] ?? '',
        ) );
        $status = is_wp_error( $result ) ? 'invalid' : 'created';
        wp_safe_redirect( add_query_arg( array( 'page' => 'engagement-core-crm', 'eccrm_notice' => $status ), admin_url( 'admin.php' ) ) );
        exit;
    }

    public static function page(): void {
        if ( ! current_user_can( ECCRM_CAPABILITY ) ) {
            wp_die( esc_html__( 'CRM access denied.', 'engagement-core-crm' ), '', array( 'response' => 403 ) );
        }
        $contacts = ECCRM_Contacts::list( 25 );
        $notice = isset( $_GET['eccrm_notice'] ) ? sanitize_key( wp_unslash( $_GET['eccrm_notice'] ) ) : '';
        ?>
        <div class="wrap">
            <h1><?php esc_html_e( 'Engagement Core CRM', 'engagement-core-crm' ); ?> <small style="font-weight:normal">0.1.0-dev</small></h1>
            <p><?php esc_html_e( 'Local CRM foundation. No AI calls, external broadcasts or channel messages are enabled.', 'engagement-core-crm' ); ?></p>
            <?php if ( 'created' === $notice ) : ?><div class="notice notice-success"><p><?php esc_html_e( 'Contact created.', 'engagement-core-crm' ); ?></p></div><?php endif; ?>
            <?php if ( 'invalid' === $notice ) : ?><div class="notice notice-error"><p><?php esc_html_e( 'Could not create contact; check required fields or external identity.', 'engagement-core-crm' ); ?></p></div><?php endif; ?>
            <div style="max-width:750px">
                <h2><?php esc_html_e( 'Add contact', 'engagement-core-crm' ); ?></h2>
                <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
                    <input type="hidden" name="action" value="eccrm_create_contact" />
                    <?php wp_nonce_field( 'eccrm_create_contact' ); ?>
                    <p><label><?php esc_html_e( 'Name', 'engagement-core-crm' ); ?> <input name="display_name" required maxlength="190" class="regular-text" /></label></p>
                    <p><label><?php esc_html_e( 'Email', 'engagement-core-crm' ); ?> <input name="email" type="email" maxlength="190" class="regular-text" /></label></p>
                    <p><label><?php esc_html_e( 'Phone', 'engagement-core-crm' ); ?> <input name="phone" maxlength="48" class="regular-text" /></label></p>
                    <?php submit_button( __( 'Add contact', 'engagement-core-crm' ) ); ?>
                </form>
            </div>
            <h2><?php esc_html_e( 'Recent contacts', 'engagement-core-crm' ); ?></h2>
            <div style="overflow-x:auto"><table class="widefat striped">
                <thead><tr><th>ID</th><th><?php esc_html_e( 'Name', 'engagement-core-crm' ); ?></th><th><?php esc_html_e( 'Email', 'engagement-core-crm' ); ?></th><th><?php esc_html_e( 'Phone', 'engagement-core-crm' ); ?></th><th><?php esc_html_e( 'Stage', 'engagement-core-crm' ); ?></th><th><?php esc_html_e( 'Source', 'engagement-core-crm' ); ?></th></tr></thead>
                <tbody><?php foreach ( $contacts as $contact ) : ?><tr>
                    <td><?php echo esc_html( $contact['id'] ); ?></td>
                    <td><?php echo esc_html( $contact['display_name'] ); ?></td>
                    <td><?php echo esc_html( $contact['email'] ); ?></td>
                    <td><?php echo esc_html( $contact['phone'] ); ?></td>
                    <td><?php echo esc_html( $contact['lifecycle'] ); ?></td>
                    <td><?php echo esc_html( $contact['source'] ); ?></td>
                </tr><?php endforeach; ?></tbody>
            </table></div>
        </div>
        <?php
    }
}
