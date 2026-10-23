<?php
/**
 * Engagement Core / Business House Matrix — signed PRIVATE task notifications.
 * Reusable fixed-function WordPress snippet source. NEVER community publishing.
 *
 * Install as an administrator-reviewed WPCode PHP snippet WITHOUT opening <?php tag.
 * This source file itself is not deployed by a Git commit.
 * Signing key owner: Dell. Public key below is safe to publish; private key is not.
 * A per-project second signer requires separate review and explicit key enrollment.
 */
if (!defined('ABSPATH')) { return; }
if (!class_exists('BHM_Private_Event_Notify_V1', false)) {
final class BHM_Private_Event_Notify_V1 {
    private const PUBLIC_KEY_B64 = 'R+8XsrFR+2eLIKdm9k9ITRtDYl5MRuSbbIcN8FXtfgU=';
    private const ROUTE = 'bhm-private-events/v1';
    private const LOCK_PREFIX = 'bhm_private_event_2026_';
    private const REPLAY_WINDOW = 300;
    private const CATEGORIES = array('completed','failed','blocked','stalled','resumed','escalation','approval_required');

    public static function initialize(): void {
        add_action('rest_api_init', static function (): void {
            register_rest_route(self::ROUTE, '/notify', array(
                'methods' => 'POST',
                'permission_callback' => array(__CLASS__, 'authorize'),
                'callback' => array(__CLASS__, 'notify'),
            ));
        });
    }

    public static function authorize(WP_REST_Request $request) {
        if (!function_exists('sodium_crypto_sign_verify_detached')) {
            return new WP_Error('bhm_crypto_unavailable', 'Signed notification verification unavailable', array('status'=>503));
        }
        $id = (string) $request->get_header('x-matrix-event-id');
        $stamp = (string) $request->get_header('x-matrix-timestamp');
        $signature = (string) $request->get_header('x-matrix-signature');
        $body = $request->get_body();
        if (!preg_match('/^[a-f0-9]{64}$/D', $id)
            || !preg_match('/^[0-9]{10,12}$/D', $stamp)
            || abs(time() - (int)$stamp) > self::REPLAY_WINDOW
            || !is_string($body) || strlen($body)>2400 || strlen($body)<50
            || !preg_match('/^[A-Za-z0-9+\/]{86}==$/D', $signature)) {
            return new WP_Error('bhm_invalid_signature_format', 'Invalid signed notification', array('status'=>403));
        }
        $key = base64_decode(self::PUBLIC_KEY_B64, true);
        $sig = base64_decode($signature, true);
        if (!is_string($key) || strlen($key)!==32 || !is_string($sig) || strlen($sig)!==64) {
            return new WP_Error('bhm_invalid_signature', 'Invalid signed notification', array('status'=>403));
        }
        $canonical = "bhm-private-relay-v1\n" . $stamp . "\n" . $id . "\n" . $body;
        if (!sodium_crypto_sign_verify_detached($sig, $canonical, $key)) {
            return new WP_Error('bhm_invalid_signature', 'Invalid signed notification', array('status'=>403));
        }
        $data = json_decode($body, true);
        if (!is_array($data) || !hash_equals($id, (string)($data['event_id']??''))) {
            return new WP_Error('bhm_invalid_payload', 'Invalid event data', array('status'=>422));
        }
        return true;
    }

    private static function validated_event(array $data) {
        if (($data['schema']??null)!==1) { return false; }
        $kind = (string) ($data['kind']??'');
        $task = (string) ($data['task_id']??'');
        $run = (string) ($data['run_id']??'');
        $stage = (string) ($data['stage']??'');
        $summary = (string) ($data['summary']??'');
        $evidence = (string) ($data['evidence_url']??'');
        if (!in_array($kind, self::CATEGORIES, true)
            || !preg_match('/^[A-Za-z0-9][A-Za-z0-9._:-]{1,119}$/D', $task)
            || !preg_match('/^[A-Za-z0-9][A-Za-z0-9._:-]{1,119}$/D', $run)
            || strlen($stage)>120 || strlen($summary)>420 || strlen($summary)<4
            || preg_match('/[<>]/', $summary)
            || preg_match('/(?:api[_ -]?key|token|password|secret|bearer|authorization)\s*[:=]/i', $summary)
            || preg_match('/[\x00-\x08\x0b\x0c\x0e-\x1f]/', $summary)
            || strlen($evidence)>700) { return false; }
        if ($evidence) {
            $parts = wp_parse_url($evidence);
            if (!is_array($parts) || ($parts['scheme']??'')!=='https'
                || empty($parts['host']) || isset($parts['user']) || isset($parts['pass'])
                || isset($parts['fragment'])) { return false; }
        }
        return array('kind'=>$kind,'task'=>$task,'stage'=>$stage,'summary'=>$summary,'evidence'=>$evidence);
    }

    public static function notify(WP_REST_Request $request): WP_REST_Response {
        // Authorization callback is mandatory; never allow anonymous fallback.
        $payload = json_decode($request->get_body(), true);
        if (!is_array($payload)) {
            return new WP_REST_Response(array('ok'=>false,'status'=>'invalid_payload'),422);
        }
        $validated = self::validated_event($payload);
        if (!$validated) {
            return new WP_REST_Response(array('ok'=>false,'status'=>'invalid_event'),422);
        }
        $chat = (string) get_option('grec_booking_private_telegram_chat','');
        if (!preg_match('/^[1-9][0-9]{1,19}$/D', $chat)) {
            return new WP_REST_Response(array('ok'=>false,'status'=>'private_chat_not_paired'),503);
        }
        if (!class_exists('GREC_Telegram', false)) {
            return new WP_REST_Response(array('ok'=>false,'status'=>'engagement_core_not_loaded'),503);
        }
        $cred = GREC_Telegram::credentials();
        if (empty($cred['token'])) {
            return new WP_REST_Response(array('ok'=>false,'status'=>'telegram_bot_not_configured'),503);
        }
        $id = (string) $payload['event_id'];
        $option = self::LOCK_PREFIX . $id;
        // Unique atomic reservation BEFORE outbound network call.
        if (!add_option($option,array('state'=>'reserved','at'=>time()),'','no')) {
            return new WP_REST_Response(array('ok'=>false,'status'=>'duplicate_or_uncertain','event_id'=>$id),409);
        }
        $title = 'Business House Matrix — ' . strtoupper($validated['kind']);
        $text = $title
              . "\nTask: " . $validated['task']
              . "\nStage: " . sanitize_text_field($validated['stage'])
              . "\n" . sanitize_text_field($validated['summary']);
        if ($validated['evidence']) { $text .= "\nEvidence: " . $validated['evidence']; }
        if (!empty($payload['requires_owner_attention'])) { $text .= "\nAction: review evidence and unblock."; }
        $response = wp_remote_post(
            'https://api.telegram.org/bot' . rawurlencode((string)$cred['token']) . '/sendMessage',
            array('timeout'=>12,'redirection'=>0,'body'=>array(
                'chat_id'=>$chat, 'text'=>$text, 'disable_web_page_preview'=>'true'
            ))
        );
        if (is_wp_error($response)) {
            update_option($option,array('state'=>'uncertain','at'=>time()),false);
            return new WP_REST_Response(array('ok'=>false,'status'=>'delivery_uncertain_no_retry'),502);
        }
        $reply = json_decode(wp_remote_retrieve_body($response),true);
        $message_id = is_array($reply) ? (int) ($reply['result']['message_id']??0) : 0;
        $recipient = is_array($reply) ? (string) ($reply['result']['chat']['id']??'') : '';
        if (200!==(int)wp_remote_retrieve_response_code($response)
            || empty($reply['ok']) || $message_id<1 || !hash_equals($chat,$recipient)) {
            update_option($option,array('state'=>'uncertain','at'=>time()),false);
            return new WP_REST_Response(array('ok'=>false,'status'=>'delivery_uncertain_no_retry'),502);
        }
        update_option($option,array('state'=>'delivered','message_id'=>$message_id,'at'=>time()),false);
        return new WP_REST_Response(array(
            'ok'=>true,'status'=>'delivered','recipient'=>'verified_private_booking_chat',
            'event_id'=>$id,'message_id'=>$message_id
        ),200);
    }
}
BHM_Private_Event_Notify_V1::initialize();
}
