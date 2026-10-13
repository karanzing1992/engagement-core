<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

/**
 * Private, opt-in Moksha paid-booking alerts. Existing Engagement Core Telegram
 * community destinations are deliberately never used for guest information.
 */
final class GREC_Booking_Telegram {
    private const CHAT = 'grec_booking_private_telegram_chat';
    private const PROOF = 'grec_booking_private_pair_';
    private const SENT = '_grec_booking_telegram_sent_at';
    private const RETRY = 'grec_booking_telegram_retry';

    public static function init(): void {
        add_action( 'admin_menu', array( __CLASS__, 'menu' ) );
        foreach ( array( 'start', 'verify', 'disconnect', 'recover' ) as $action ) {
            add_action( 'admin_post_grec_booking_tg_' . $action, array( __CLASS__, $action ) );
        }
        add_action( 'woocommerce_payment_complete', array( __CLASS__, 'paid' ), 55 );
        add_action( 'woocommerce_order_status_changed', array( __CLASS__, 'status_changed' ), 55, 4 );
        add_action( self::RETRY, array( __CLASS__, 'paid' ) );
    }

    private static function private_chat(): string {
        $id = (string) get_option( self::CHAT, '' );
        return preg_match( '/^[1-9][0-9]{1,19}$/D', $id ) ? $id : '';
    }

    private static function api( string $method, array $params = array() ): array {
        $cred = GREC_Telegram::credentials();
        if ( empty( $cred['token'] ) ) { throw new RuntimeException( 'Bot unavailable' ); }
        $response = wp_remote_post( 'https://api.telegram.org/bot' . rawurlencode( (string) $cred['token'] ) . '/' . $method, array(
            'timeout' => 15,
            'body' => $params,
        ) );
        if ( is_wp_error( $response ) ) { throw new RuntimeException( 'Telegram transport unavailable' ); }
        $decoded = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( 200 !== (int) wp_remote_retrieve_response_code( $response ) || ! is_array( $decoded ) || empty( $decoded['ok'] ) ) {
            throw new RuntimeException( 'Telegram API unavailable' );
        }
        return $decoded;
    }

    private static function send_dm( string $id, string $html ): int {
        if ( ! preg_match( '/^[1-9][0-9]{1,19}$/D', $id ) ) { throw new RuntimeException( 'Invalid private chat' ); }
        $data = self::api( 'sendMessage', array(
            'chat_id' => $id,
            'text' => $html,
            'parse_mode' => 'HTML',
            'disable_web_page_preview' => 'true',
        ) );
        $message = (int) ( $data['result']['message_id'] ?? 0 );
        if ( ! $message ) { throw new RuntimeException( 'Missing Telegram send receipt' ); }
        return $message;
    }

    private static function guard( string $name ): void {
        if ( ! current_user_can( 'manage_options' ) ) { wp_die( 'Administrator permission required.' ); }
        check_admin_referer( 'grec_booking_tg_' . $name );
    }

    private static function back( string $status ): void {
        wp_safe_redirect( admin_url( 'admin.php?page=grec-booking-telegram&result=' . rawurlencode( $status ) ) );
        exit;
    }

    public static function menu(): void {
        add_submenu_page( 'woocommerce', 'Private Booking Telegram', 'Booking Telegram', 'manage_options', 'grec-booking-telegram', array( __CLASS__, 'page' ) );
    }

    public static function start(): void {
        self::guard( 'start' );
        try {
            $bot = self::api( 'getMe' );
            if ( empty( $bot['result']['username'] ) ) { throw new RuntimeException( 'No username' ); }
            $proof = bin2hex( random_bytes( 18 ) );
            set_transient( self::PROOF . get_current_user_id(), $proof, 20 * MINUTE_IN_SECONDS );
            self::back( 'start_ready' );
        } catch ( Throwable $e ) {
            self::back( 'bot_unavailable' );
        }
    }

    public static function verify(): void {
        self::guard( 'verify' );
        $proof = get_transient( self::PROOF . get_current_user_id() );
        if ( ! is_string( $proof ) || ! preg_match( '/^[0-9a-f]{36}$/D', $proof ) ) { self::back( 'expired' ); }
        try {
            // No offset means no consumption of updates; never change bot webhook.
            $data = self::api( 'getUpdates', array( 'limit' => 100, 'timeout' => 0, 'allowed_updates' => wp_json_encode( array( 'message' ) ) ) );
            foreach ( array_reverse( (array) ( $data['result'] ?? array() ) ) as $update ) {
                $message = (array) ( $update['message'] ?? array() );
                $chat = (array) ( $message['chat'] ?? array() );
                $from = (array) ( $message['from'] ?? array() );
                $id = (string) ( $chat['id'] ?? '' );
                $text = trim( (string) ( $message['text'] ?? '' ) );
                if ( 'private' !== ( $chat['type'] ?? '' ) || ! empty( $from['is_bot'] ) || ! $id ) { continue; }
                if ( ! hash_equals( $id, (string) ( $from['id'] ?? '' ) ) ) { continue; }
                if ( ! preg_match( '/^\/start(?:@[A-Za-z0-9_]+)?\s+' . preg_quote( $proof, '/' ) . '$/D', $text ) ) { continue; }
                self::send_dm( $id, "✅ <b>Moksha booking alerts connected.</b>\nPaid bookings will arrive only in this private chat." );
                update_option( self::CHAT, $id, false );
                delete_transient( self::PROOF . get_current_user_id() );
                self::back( 'connected' );
            }
            self::back( 'start_not_found' );
        } catch ( Throwable $e ) {
            // Fail closed if the existing bot has a webhook or update access fails.
            self::back( 'verification_unavailable' );
        }
    }

    public static function disconnect(): void {
        self::guard( 'disconnect' );
        delete_option( self::CHAT );
        delete_transient( self::PROOF . get_current_user_id() );
        self::back( 'disconnected' );
    }

    public static function page(): void {
        if ( ! current_user_can( 'manage_options' ) ) { return; }
        $chat = self::private_chat();
        $proof = get_transient( self::PROOF . get_current_user_id() );
        $bot_username = '';
        try {
            $bot = self::api( 'getMe' );
            $bot_username = (string) ( $bot['result']['username'] ?? '' );
        } catch ( Throwable $e ) {}
        $messages = array(
            'start_ready' => 'Tap the Telegram link and Start, then Verify.',
            'connected' => 'Private Telegram connection verified and enabled.',
            'bot_unavailable' => 'Existing bot unavailable.',
            'expired' => 'Pairing expired. Start again.',
            'start_not_found' => 'No matching private Start message yet. Tap Start in Telegram, then Verify.',
            'verification_unavailable' => 'Unable to verify; no chat was connected. An existing Telegram webhook can block getUpdates.',
            'disconnected' => 'Private alerts disconnected.',
            'not_eligible' => 'Order not eligible or already notified.',
            'recovery_attempted' => 'Existing paid booking alert attempted; confirm the Telegram message receipt.',
        );
        $notice = sanitize_key( (string) ( $_GET['result'] ?? '' ) );
        echo '<div class="wrap"><h1>Moksha private booking alerts</h1>';
        echo '<p>Guest details are sent only to your paired private DM, never to any community/channel destination.</p>';
        if ( isset( $messages[ $notice ] ) ) { echo '<div class="notice notice-info"><p>' . esc_html( $messages[ $notice ] ) . '</p></div>'; }
        if ( $chat ) {
            echo '<p><strong>Connected.</strong> Private chat ending ' . esc_html( substr( $chat, -4 ) ) . '.</p>';
            self::form( 'disconnect', 'Disconnect private chat' );
            echo '<h2>Recover missed paid booking</h2><form method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '">';
            echo '<input type="hidden" name="action" value="grec_booking_tg_recover" /><input type="number" name="order_id" min="1" required placeholder="WooCommerce order ID" />';
            wp_nonce_field( 'grec_booking_tg_recover' );
            submit_button( 'Send missing booking alert' );
            echo '</form>';
        } else {
            self::form( 'start', 'Start private pairing' );
            if ( is_string( $proof ) && $bot_username && preg_match( '/^[A-Za-z0-9_]{5,}$/D', $bot_username ) ) {
                $link = 'https://t.me/' . $bot_username . '?start=' . rawurlencode( $proof );
                echo '<p><a class="button button-primary" target="_blank" rel="noopener noreferrer" href="' . esc_url( $link ) . '">Open Telegram bot and tap Start</a></p>';
                self::form( 'verify', 'Verify my private chat' );
            }
        }
        echo '</div>';
    }

    private static function form( string $action, string $label ): void {
        echo '<form method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '"><input type="hidden" name="action" value="grec_booking_tg_' . esc_attr( $action ) . '" />';
        wp_nonce_field( 'grec_booking_tg_' . $action );
        submit_button( $label, 'secondary' );
        echo '</form>';
    }

    private static function bookable( $order ): bool {
        return $order && $order->is_paid() && $order->get_date_paid() && $order->get_meta( '_moksha_visit_date' );
    }

    public static function status_changed( $order_id, $before, $after, $order ): void {
        if ( in_array( $after, array( 'processing', 'completed' ), true ) ) { self::paid( $order_id ); }
    }

    public static function paid( $order_id ): void {
        $chat = self::private_chat();
        if ( ! $chat || ! function_exists( 'wc_get_order' ) ) { return; }
        $order = wc_get_order( $order_id );
        if ( ! self::bookable( $order ) || $order->get_meta( self::SENT ) ) { return; }
        $lock = 'grec_booking_tg_lock_' . (int) $order_id;
        if ( (int) get_option( $lock, 0 ) && (int) get_option( $lock, 0 ) < time() ) { delete_option( $lock ); }
        if ( ! add_option( $lock, time() + 120, '', false ) ) { return; }
        try {
            $items = array();
            foreach ( $order->get_items() as $item ) {
                $items[] = (int) $item->get_quantity() . ' × ' . wp_strip_all_tags( $item->get_name() );
            }
            $html = "<b>💰 PAID MOKSHA BOOKING</b>\n"
                . '<b>Order #' . (int) $order_id . "</b>\n"
                . 'Guest: ' . esc_html( $order->get_formatted_billing_full_name() ) . "\n"
                . 'Phone: ' . esc_html( $order->get_billing_phone() ) . "\n"
                . 'Experience: ' . esc_html( implode( ', ', $items ) ) . "\n"
                . 'Visit: ' . esc_html( $order->get_meta( '_moksha_visit_date' ) . ' ' . $order->get_meta( '_moksha_visit_time' ) ) . " IST\n"
                . 'Paid: <b>' . esc_html( $order->get_currency() . ' ' . $order->get_total() ) . "</b>\n"
                . 'Admin order: ' . esc_url( admin_url( 'admin.php?page=wc-orders&action=edit&id=' . (int) $order_id ) ) . "\n"
                . 'Guest WhatsApp: confirm delivery separately.';
            $message_id = self::send_dm( $chat, $html );
            $order->update_meta_data( self::SENT, current_time( 'mysql' ) );
            $order->update_meta_data( '_grec_booking_telegram_message_id', $message_id );
            $order->delete_meta_data( '_grec_booking_telegram_attempts' );
            $order->save();
        } catch ( Throwable $e ) {
            $attempt = (int) $order->get_meta( '_grec_booking_telegram_attempts' ) + 1;
            $order->update_meta_data( '_grec_booking_telegram_attempts', $attempt );
            $order->save();
            if ( $attempt <= 3 ) {
                $at = time() + 5 * MINUTE_IN_SECONDS * $attempt;
                if ( function_exists( 'as_schedule_single_action' ) ) {
                    as_schedule_single_action( $at, self::RETRY, array( (int) $order_id ), 'grec-private-bookings', true );
                } elseif ( ! wp_next_scheduled( self::RETRY, array( (int) $order_id ) ) ) {
                    wp_schedule_single_event( $at, self::RETRY, array( (int) $order_id ) );
                }
            }
        } finally {
            delete_option( $lock );
        }
    }

    public static function recover(): void {
        self::guard( 'recover' );
        $id = absint( $_POST['order_id'] ?? 0 );
        $order = function_exists( 'wc_get_order' ) ? wc_get_order( $id ) : false;
        if ( ! self::private_chat() || ! self::bookable( $order ) || $order->get_meta( self::SENT ) ) { self::back( 'not_eligible' ); }
        self::paid( $id );
        self::back( 'recovery_attempted' );
    }
}
