<?php
/** Tabler-powered mobile-first CRM shell. Local assets and WordPress REST only. */
defined( 'ABSPATH' ) || exit;
final class ECCRM_Admin {
    public static function register(): void {
        add_action( 'admin_menu', array( __CLASS__, 'menu' ) );
        add_action( 'admin_enqueue_scripts', array( __CLASS__, 'assets' ) );
    }
    public static function menu(): void {
        add_menu_page( 'Engagement CRM', 'Engagement CRM', ECCRM_CAPABILITY, 'engagement-core-crm', array( __CLASS__, 'page' ), 'dashicons-groups', 26 );
    }
    public static function assets( string $hook ): void {
        if ( 'toplevel_page_engagement-core-crm' !== $hook || ! current_user_can( ECCRM_CAPABILITY ) ) { return; }
        $root = ECCRM_PATH . 'engagement-core-crm.php';
        wp_enqueue_style( 'eccrm-tabler', plugins_url( 'assets/css/tabler.min.css', $root ), array(), '1.7.0' );
        wp_enqueue_style( 'eccrm-workspace', plugins_url( 'assets/css/workspace.css', $root ), array( 'eccrm-tabler' ), '0.2.0' );
        wp_enqueue_script( 'eccrm-workspace', plugins_url( 'assets/js/workspace.js', $root ), array(), '0.2.0', true );
        wp_add_inline_script( 'eccrm-workspace', 'window.ECCRM_CONFIG=' . wp_json_encode( array(
            'api' => esc_url_raw( rest_url( 'eccrm/v1/' ) ), 'nonce' => wp_create_nonce( 'wp_rest' )
        ) ) . ';', 'before' );
    }
    private static function icon( string $name ): void {
        $paths = array(
            'grid' => '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
            'users' => '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
            'activity' => '<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 6-7"/>',
            'menu' => '<path d="M4 7h16M4 12h16M4 17h16"/>',
            'plus' => '<path d="M12 5v14M5 12h14"/>',
            'search' => '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
            'arrow' => '<path d="m9 18 6-6-6-6"/>',
            'close' => '<path d="M18 6 6 18M6 6l12 12"/>',
            'refresh' => '<path d="M20 7v5h-5M4 17v-5h5"/>',
        );
        echo '<svg class="eccrm-icon" viewBox="0 0 24 24" width="21" height="21" stroke="currentColor" fill="none" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' . ( $paths[$name] ?? $paths['grid'] ) . '</svg>'; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
    }
    public static function page(): void {
        if ( ! current_user_can( ECCRM_CAPABILITY ) ) { wp_die( esc_html__( 'CRM access denied.', 'engagement-core-crm' ) ); }
        ?>
        <div id="eccrm-workspace" class="eccrm-app" data-app="engagement-crm">
            <div id="eccrm-backdrop" class="eccrm-backdrop" hidden></div>
            <aside id="eccrm-sidebar" class="eccrm-sidebar" aria-label="CRM navigation">
                <div class="eccrm-brand"><span class="eccrm-mark">e<span>.</span></span><span class="eccrm-brandtext"><strong>engagement</strong><small>CORE CRM</small></span></div>
                <p class="eccrm-sidelabel">WORKSPACE</p>
                <nav class="eccrm-side-nav" aria-label="Main">
                    <button type="button" class="eccrm-nav is-active" data-view="overview"><?php self::icon('grid'); ?><span>Overview</span></button>
                    <button type="button" class="eccrm-nav" data-view="contacts"><?php self::icon('users'); ?><span>Contacts</span></button>
                    <button type="button" class="eccrm-nav" data-view="activity"><?php self::icon('activity'); ?><span>Activity</span></button>
                </nav>
                <div class="eccrm-sidefoot"><span class="eccrm-statusdot"></span><span>WordPress hosted<br><small>Local CRM · AI optional</small></span></div>
            </aside>
            <div class="eccrm-main">
                <header class="eccrm-topbar">
                    <div class="eccrm-top-left">
                        <button type="button" id="eccrm-open-menu" class="eccrm-iconbutton eccrm-menu-btn" aria-label="Open navigation" aria-expanded="false"><?php self::icon('menu'); ?></button>
                        <div><span class="eccrm-eyebrow">YOUR WORKSPACE</span><h1 id="eccrm-page-title">Overview</h1></div>
                    </div>
                    <div class="eccrm-top-actions"><span class="eccrm-pill"><span class="eccrm-statusdot"></span> Development preview</span><button type="button" id="eccrm-refresh" class="eccrm-iconbutton" aria-label="Refresh CRM data"><?php self::icon('refresh'); ?></button><span class="eccrm-avatar" aria-label="Signed-in operator"><?php echo esc_html( strtoupper( substr( wp_get_current_user()->display_name ?: 'U', 0, 1 ) ) ); ?></span></div>
                </header>
                <main id="eccrm-content" class="eccrm-content">
                    <div id="eccrm-notice" class="eccrm-notice" role="status" aria-live="polite" hidden></div>
                    <section id="eccrm-view-overview" class="eccrm-view" aria-label="CRM overview">
                        <div class="eccrm-hero"><div><p class="eccrm-hero-label">ENGAGEMENT CORE / CRM</p><h2>Good to have you here.</h2><p>A clear view of your relationships, without the noise.</p></div><button type="button" class="btn btn-light eccrm-new-btn" data-create><?php self::icon('plus'); ?> New contact</button></div>
                        <div class="eccrm-stat-grid" id="eccrm-stats">
                            <div class="eccrm-stat"><span>Contacts</span><strong id="eccrm-stat-total">—</strong><small>All recorded</small></div>
                            <div class="eccrm-stat"><span>Qualified leads</span><strong id="eccrm-stat-qualified">—</strong><small>Ready for follow-up</small></div>
                            <div class="eccrm-stat"><span>Customers</span><strong id="eccrm-stat-customers">—</strong><small>Active relationships</small></div>
                        </div>
                        <div class="eccrm-home-grid">
                            <article class="eccrm-panel"><div class="eccrm-panelhead"><div><h3>Recent contacts</h3><p>Latest people added to your CRM</p></div><button type="button" class="eccrm-textlink" data-view="contacts">View all <?php self::icon('arrow'); ?></button></div><div id="eccrm-recent-contacts" class="eccrm-recent-list"><p class="eccrm-loading">Loading contacts…</p></div></article>
                            <article class="eccrm-panel"><div class="eccrm-panelhead"><div><h3>Latest activity</h3><p>Recorded changes, not simulated data</p></div><button type="button" class="eccrm-textlink" data-view="activity">View all <?php self::icon('arrow'); ?></button></div><div id="eccrm-recent-activity" class="eccrm-activity-list"><p class="eccrm-loading">Loading activity…</p></div></article>
                        </div>
                        <div class="eccrm-scope-note"><strong>Available now:</strong> Contacts and local activity. Conversations, channels, booking sync and external AI are not yet connected.</div>
                    </section>

                    <section id="eccrm-view-contacts" class="eccrm-view" hidden aria-label="Contacts">
                        <div class="eccrm-sectionhead"><div><p class="eccrm-eyebrow">PEOPLE & RELATIONSHIPS</p><h2>Contacts</h2><p>Manage profiles and lifecycle stages in one place.</p></div><button type="button" class="btn btn-primary eccrm-new-btn" data-create><?php self::icon('plus'); ?> Add contact</button></div>
                        <div class="eccrm-panel eccrm-contacts-panel">
                            <div class="eccrm-filters"><label class="eccrm-search"><span class="visually-hidden">Search contacts</span><?php self::icon('search'); ?><input id="eccrm-search" type="search" placeholder="Search name, email or phone" autocomplete="off"/></label><label class="eccrm-filter"><span class="visually-hidden">Filter lifecycle</span><select id="eccrm-stage" class="form-select"><option value="">All stages</option><option value="lead">Lead</option><option value="qualified">Qualified</option><option value="customer">Customer</option><option value="inactive">Inactive</option></select></label></div>
                            <div id="eccrm-contacts-list" class="eccrm-contacts-list" aria-live="polite"><p class="eccrm-loading">Loading contacts…</p></div>
                            <div class="eccrm-pagination"><span id="eccrm-page-indicator">—</span><div><button id="eccrm-prev" class="btn btn-outline-secondary btn-sm" type="button">Previous</button><button id="eccrm-next" class="btn btn-outline-secondary btn-sm" type="button">Next</button></div></div>
                        </div>
                    </section>
                    <section id="eccrm-view-activity" class="eccrm-view" hidden aria-label="Activity">
                        <div class="eccrm-sectionhead"><div><p class="eccrm-eyebrow">LOCAL EVENT HISTORY</p><h2>Activity</h2><p>An audit-friendly timeline of actual CRM changes.</p></div></div>
                        <div class="eccrm-panel"><div id="eccrm-full-activity" class="eccrm-activity-list"><p class="eccrm-loading">Loading activity…</p></div></div>
                    </section>
                </main>
            </div>
            <nav class="eccrm-bottomnav" aria-label="Mobile CRM navigation"><button class="is-active" data-view="overview" type="button"><?php self::icon('grid'); ?><span>Home</span></button><button data-view="contacts" type="button"><?php self::icon('users'); ?><span>Contacts</span></button><button data-view="activity" type="button"><?php self::icon('activity'); ?><span>Activity</span></button></nav>
            <dialog id="eccrm-editor" class="eccrm-dialog" aria-labelledby="eccrm-editor-title">
                <form id="eccrm-contact-form" class="eccrm-editor-form">
                    <div class="eccrm-dialoghead"><div><p class="eccrm-eyebrow">CONTACT PROFILE</p><h2 id="eccrm-editor-title">New contact</h2></div><button type="button" id="eccrm-close-dialog" class="eccrm-iconbutton" aria-label="Close editor"><?php self::icon('close'); ?></button></div>
                    <div class="eccrm-dialogbody">
                        <label class="form-label" for="eccrm-field-name">Full name <span aria-hidden="true">*</span></label><input id="eccrm-field-name" name="display_name" class="form-control" maxlength="190" required autocomplete="name" placeholder="e.g. Alex Morgan"/>
                        <label class="form-label" for="eccrm-field-email">Email</label><input id="eccrm-field-email" name="email" class="form-control" maxlength="190" type="email" autocomplete="email" placeholder="name@example.com"/>
                        <label class="form-label" for="eccrm-field-phone">Phone</label><input id="eccrm-field-phone" name="phone" class="form-control" maxlength="48" type="tel" autocomplete="tel" placeholder="+91 98765 43210"/>
                        <label class="form-label" for="eccrm-field-lifecycle">Lifecycle stage</label><select id="eccrm-field-lifecycle" name="lifecycle" class="form-select"><option value="lead">Lead</option><option value="qualified">Qualified</option><option value="customer">Customer</option><option value="inactive">Inactive</option></select>
                        <p id="eccrm-form-error" class="eccrm-form-error" role="alert" hidden></p>
                    </div>
                    <div class="eccrm-dialogfooter"><button type="button" class="btn btn-outline-secondary" id="eccrm-cancel-dialog">Cancel</button><button type="submit" id="eccrm-save-contact" class="btn btn-primary">Save contact</button></div>
                </form>
            </dialog>
        </div>
        <?php
    }
}

