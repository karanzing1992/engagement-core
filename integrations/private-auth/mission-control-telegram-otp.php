<?php
/**
 * Mission Control: owner-private Telegram OTP + encrypted task metadata.
 * SOURCE ONLY. Install as a separate administrator-reviewed WPCode PHP snippet
 * after removing the opening PHP tag. Does not replace paid booking alerts
 * or the BHM private event notification relay.
 *
 * Security: single fixed paired private DM, no arbitrary recipient parameter,
 * short-lived one-time challenges, strict send/verify budgets, bearer sessions,
 * encrypted-at-rest task metadata, no secrets committed.
 */
if (!defined('ABSPATH')) { return; }
if (!class_exists('BHM_Mission_Control_OTP_V1', false)) {
final class BHM_Mission_Control_OTP_V1 {
    private const ROUTE = 'mission-control/v1';
    private const PREFIX = 'bhm_mc_otp_v1_';
    private const ORIGIN = 'https://mokshagoa.com';
    private const CHALLENGE_TTL = 300;
    private const SESSION_TTL = 1200;
    private const SEND_LIMIT = 3;
    private const VERIFY_LIMIT = 12;

    public static function initialize(): void {
        add_action('rest_api_init', static function (): void {
            register_rest_route(self::ROUTE, '/health', array(
                'methods'=>'GET','permission_callback'=>'__return_true',
                'callback'=>array(__CLASS__,'health')));
            register_rest_route(self::ROUTE, '/otp/start', array(
                'methods'=>'POST','permission_callback'=>'__return_true',
                'callback'=>array(__CLASS__,'start')));
            register_rest_route(self::ROUTE, '/otp/verify', array(
                'methods'=>'POST','permission_callback'=>'__return_true',
                'callback'=>array(__CLASS__,'verify')));
            register_rest_route(self::ROUTE, '/logout', array(
                'methods'=>'POST','permission_callback'=>array(__CLASS__,'authorize_session'),
                'callback'=>array(__CLASS__,'logout')));
            register_rest_route(self::ROUTE, '/tasks', array(
                array('methods'=>'GET','permission_callback'=>array(__CLASS__,'authorize_session'),
                      'callback'=>array(__CLASS__,'read_tasks')),
                array('methods'=>'PUT','permission_callback'=>array(__CLASS__,'authorize_session'),
                      'callback'=>array(__CLASS__,'write_tasks'))));
        });
        add_filter('rest_pre_serve_request', static function ($served, $result, $request) {
            if (strpos((string)$request->get_route(),'/'.self::ROUTE.'/')!==0) return $served;
            if ((string)($_SERVER['HTTP_ORIGIN']??'')===self::ORIGIN) {
                header('Access-Control-Allow-Origin: '.self::ORIGIN);
                header('Access-Control-Allow-Methods: GET, POST, PUT, OPTIONS');
                header('Access-Control-Allow-Headers: Authorization, Content-Type');
                header('Vary: Origin');
            }
            header('Cache-Control: no-store, private');
            header('X-Content-Type-Options: nosniff');
            return $served;
        },10,3);
    }
    private static function response(array $body, int $code=200): WP_REST_Response {
        $out=new WP_REST_Response($body,$code);
        $out->header('Cache-Control','no-store, private');
        return $out;
    }
    private static function origin_ok(): bool {
        $origin=(string)($_SERVER['HTTP_ORIGIN']??'');
        if ($origin!=='') return hash_equals(self::ORIGIN,$origin);
        // Browser same-origin GET fetches commonly omit the Origin header.
        // Read access still requires the short-lived private bearer session.
        if (strtoupper((string)($_SERVER['REQUEST_METHOD']??''))!=='GET') return false;
        if ((string)($_SERVER['HTTP_SEC_FETCH_SITE']??'')==='same-origin') return true;
        $ref=(string)($_SERVER['HTTP_REFERER']??'');
        return $ref!=='' && strpos($ref,self::ORIGIN.'/mission-control/')===0;
    }
    private static function nonce_key(string $name): string {
        return self::PREFIX . $name;
    }
    private static function secret(): string {
        return wp_salt('auth');
    }
    private static function digest(string $value): string {
        return hash_hmac('sha256',$value,self::secret());
    }
    private static function ip_key(): string {
        $ip=(string)($_SERVER['REMOTE_ADDR']??'unknown');
        return substr(hash_hmac('sha256',$ip,self::secret()),0,24);
    }
    private static function spend(string $scope, int $limit, int $duration): bool {
        // Two budgets protect both the owner DM and the verify endpoint.
        // A per-scope add_option mutex serializes updates across PHP workers.
        $key=self::nonce_key('budget_'.$scope);
        $mutex=self::nonce_key('mutex_'.$scope);
        if (!add_option($mutex,time()+8,'','no')) {
            $until=(int)get_option($mutex,0);
            if ($until>=time()) return false;
            delete_option($mutex);
            if (!add_option($mutex,time()+8,'','no')) return false;
        }
        try {
            $state=get_transient($key);
            $state=is_array($state)?$state:array('start'=>time(),'count'=>0);
            if ((int)$state['start']+$duration<=time()) $state=array('start'=>time(),'count'=>0);
            if ((int)$state['count'] >= $limit) return false;
            $state['count']++;
            set_transient($key,$state,max(1,(int)$state['start']+$duration-time()));
            return true;
        } finally {
            delete_option($mutex);
        }
    }
    private static function send_private(string $code) {
        $chat=(string)get_option('grec_booking_private_telegram_chat','');
        if (!preg_match('/^[1-9][0-9]{1,19}$/D',$chat)) return new WP_Error('private_dm_unavailable','Private Telegram DM not paired',array('status'=>503));
        if (!class_exists('GREC_Telegram',false)) return new WP_Error('engine_unavailable','Engagement Core unavailable',array('status'=>503));
        $creds=GREC_Telegram::credentials();
        if (empty($creds['token'])) return new WP_Error('telegram_unavailable','Private Telegram credentials unavailable',array('status'=>503));
        $message="Mission Control sign-in code: ".$code."\nExpires in 5 minutes. If you didn't request this, ignore it.";
        $response=wp_remote_post('https://api.telegram.org/bot'.rawurlencode((string)$creds['token']).'/sendMessage',
            array('timeout'=>12,'redirection'=>0,'body'=>array(
                'chat_id'=>$chat,'text'=>$message,'disable_web_page_preview'=>'true')));
        if (is_wp_error($response)) return new WP_Error('delivery_uncertain','Telegram delivery uncertain; do not retry automatically',array('status'=>502));
        $reply=json_decode(wp_remote_retrieve_body($response),true);
        $recipient=is_array($reply)?(string)($reply['result']['chat']['id']??''):'';
        $message_id=is_array($reply)?(int)($reply['result']['message_id']??0):0;
        if ((int)wp_remote_retrieve_response_code($response)!==200
            || empty($reply['ok']) || $message_id<1 || !hash_equals($chat,$recipient)) {
            return new WP_Error('delivery_uncertain','Telegram recipient receipt not verified; do not retry automatically',array('status'=>502));
        }
        return true;
    }
    public static function health(): WP_REST_Response {
        return self::response(array('ok'=>true,'service'=>'mission-control-owner-otp','version'=>'0.1.0'));
    }
    public static function start(WP_REST_Request $request) {
        if (!self::origin_ok()) return self::response(array('error'=>'origin_denied'),403);
        $bytes=$request->get_body();
        if (!is_string($bytes)||strlen($bytes)>128) return self::response(array('error'=>'invalid_request'),400);
        if (!self::spend('send_global',self::SEND_LIMIT,900)
            || !self::spend('send_ip_'.self::ip_key(),self::SEND_LIMIT,900)
            || !self::spend('send_day',20,86400)) {
            return self::response(array('error'=>'temporarily_rate_limited'),429);
        }
        $id=bin2hex(random_bytes(16));
        $code=(string)random_int(100000,999999);
        $record=array('hash'=>self::digest($id.':'.$code),'attempts'=>0,'created'=>time());
        set_transient(self::nonce_key('challenge_'.$id),$record,self::CHALLENGE_TTL);
        $delivered=self::send_private($code);
        unset($code);
        if (is_wp_error($delivered)) {
            // An uncertain delivery is not automatically replayed.
            delete_transient(self::nonce_key('challenge_'.$id));
            return $delivered;
        }
        return self::response(array('ok'=>true,'challenge_id'=>$id,'expires_in'=>self::CHALLENGE_TTL));
    }
    public static function verify(WP_REST_Request $request) {
        if (!self::origin_ok()) return self::response(array('error'=>'origin_denied'),403);
        if (strlen((string)$request->get_body())>512) return self::response(array('error'=>'invalid_request'),400);
        if (!self::spend('verify_global',self::VERIFY_LIMIT,900)
            || !self::spend('verify_ip_'.self::ip_key(),self::VERIFY_LIMIT,900)) {
            return self::response(array('error'=>'temporarily_rate_limited'),429);
        }
        $data=$request->get_json_params();
        $id=is_array($data)?(string)($data['challenge_id']??''):'';
        $code=is_array($data)?(string)($data['code']??''):'';
        if (!preg_match('/^[a-f0-9]{32}$/D',$id) || !preg_match('/^[0-9]{6}$/D',$code))
            return self::response(array('error'=>'invalid_code'),401);
        $key=self::nonce_key('challenge_'.$id);
        $mutex=self::nonce_key('challenge_lock_'.$id);
        if (!add_option($mutex,time()+8,'','no')) {
            if ((int)get_option($mutex,0)>=time()) return self::response(array('error'=>'challenge_busy'),429);
            delete_option($mutex);
            if (!add_option($mutex,time()+8,'','no')) return self::response(array('error'=>'challenge_busy'),429);
        }
        try {
            $record=get_transient($key);
            if (!is_array($record)||time()-(int)($record['created']??0)>self::CHALLENGE_TTL)
                return self::response(array('error'=>'expired_or_used'),401);
            if ((int)($record['attempts']??0)>=5) return self::response(array('error'=>'expired_or_used'),401);
            if (!hash_equals((string)$record['hash'],self::digest($id.':'.$code))) {
                $record['attempts']=(int)$record['attempts']+1;
                if ($record['attempts']>=5) delete_transient($key);
                else set_transient($key,$record,max(1,self::CHALLENGE_TTL-(time()-(int)$record['created'])));
                return self::response(array('error'=>'invalid_code'),401);
            }
            delete_transient($key);
            $token=bin2hex(random_bytes(32));
            set_transient(self::nonce_key('session_'.self::digest($token)),array('issued'=>time()),self::SESSION_TTL);
            return self::response(array('ok'=>true,'access_token'=>$token,'expires_in'=>self::SESSION_TTL));
        } finally {
            delete_option($mutex);
        }
    }
    private static function bearer(WP_REST_Request $request): string {
        $header=(string)$request->get_header('authorization');
        return preg_match('/^Bearer ([a-f0-9]{64})$/D',$header,$m)?$m[1]:'';
    }
    public static function authorize_session(WP_REST_Request $request) {
        if (!self::origin_ok()) return new WP_Error('origin_denied','Origin denied',array('status'=>403));
        $token=self::bearer($request);
        if (!$token) return new WP_Error('unauthorized','Session required',array('status'=>401));
        $active=get_transient(self::nonce_key('session_'.self::digest($token)));
        if (!is_array($active)) return new WP_Error('session_expired','Session expired',array('status'=>401));
        return true;
    }
    public static function logout(WP_REST_Request $request): WP_REST_Response {
        $token=self::bearer($request);
        if ($token) delete_transient(self::nonce_key('session_'.self::digest($token)));
        return self::response(array('ok'=>true));
    }
    private static function storage_key(): string {
        return hash_hkdf('sha256',self::secret(),32,'mission-control-task-v1');
    }
    private static function load_store(): array {
        $blob=get_option(self::nonce_key('encrypted_tasks'),array());
        if (!$blob) return array('version'=>0,'entries'=>array());
        if (!is_array($blob)||!isset($blob['ciphertext'],$blob['iv'],$blob['tag'],$blob['version']))
            return array('error'=>'vault_unavailable');
        $plain=openssl_decrypt(base64_decode((string)$blob['ciphertext'],true),'aes-256-gcm',
            self::storage_key(),OPENSSL_RAW_DATA,base64_decode((string)$blob['iv'],true),
            base64_decode((string)$blob['tag'],true));
        if (!is_string($plain)) return array('error'=>'vault_unavailable');
        $value=json_decode($plain,true);
        return is_array($value)&&isset($value['entries'])&&is_array($value['entries'])
            ?$value:array('error'=>'vault_unavailable');
    }
    public static function read_tasks(WP_REST_Request $request): WP_REST_Response {
        $value=self::load_store();
        if (isset($value['error'])) return self::response($value,503);
        return self::response($value);
    }
    private static function normalize_entries($raw) {
        if (!is_array($raw)||count($raw)>5000) return false;
        $output=array();$ids=array();
        foreach ($raw as $item) {
            if (!is_array($item)) return false;
            $id=(string)($item['id']??'');
            if (!preg_match('/^[a-zA-Z0-9_-]{8,100}$/D',$id) || isset($ids[$id])) return false;
            $ids[$id]=true;
            $status=(string)($item['status']??'Working');
            if (!in_array($status,array('Working','Done','On Ice','Deprecated'),true)) return false;
            $url=(string)($item['url']??'');
            if ($url) {
                $parts=wp_parse_url($url);
                if (!is_array($parts)||($parts['scheme']??'')!=='https'||($parts['host']??'')!=='chatgpt.com'
                    || strpos((string)($parts['path']??''),'/c/')!==0
                    || isset($parts['user'])||isset($parts['pass'])) return false;
            }
            $output[]=array(
                'id'=>$id,
                'title'=>sanitize_text_field(substr((string)($item['title']??''),0,180)),
                'project'=>sanitize_text_field(substr((string)($item['project']??'Unfiled Chats'),0,100)),
                'url'=>$url,'status'=>$status,
                'summary'=>sanitize_textarea_field(substr((string)($item['summary']??''),0,1500)),
                'next'=>sanitize_textarea_field(substr((string)($item['next']??''),0,700)),
                'blocker'=>sanitize_textarea_field(substr((string)($item['blocker']??''),0,700)),
                'updated'=>max(0,(int)($item['updated']??time()*1000)),
                'manual'=>!empty($item['manual'])
            );
        }
        return $output;
    }
    public static function write_tasks(WP_REST_Request $request) {
        if (strlen((string)$request->get_body())>1024*1024) return self::response(array('error'=>'payload_too_large'),413);
        $data=$request->get_json_params();
        if (!is_array($data)||!isset($data['version'],$data['entries']))
            return self::response(array('error'=>'invalid_payload'),422);
        $mutex=self::nonce_key('task_write_lock');
        if (!add_option($mutex,time()+8,'','no')) {
            if ((int)get_option($mutex,0)>=time()) return self::response(array('error'=>'write_busy'),429);
            delete_option($mutex);
            if (!add_option($mutex,time()+8,'','no')) return self::response(array('error'=>'write_busy'),429);
        }
        try {
        $existing=self::load_store();
        if (isset($existing['error'])) return self::response($existing,503);
        if ((int)$data['version']!==(int)$existing['version'])
            return self::response(array('error'=>'version_conflict','version'=>(int)$existing['version']),409);
        $entries=self::normalize_entries($data['entries']);
        if ($entries===false) return self::response(array('error'=>'invalid_entries'),422);
        $version=(int)$existing['version']+1;
        $plain=wp_json_encode(array('version'=>$version,'entries'=>$entries));
        if (!is_string($plain)) return self::response(array('error'=>'encode_failed'),500);
        $iv=random_bytes(12);$tag='';
        $cipher=openssl_encrypt($plain,'aes-256-gcm',self::storage_key(),OPENSSL_RAW_DATA,$iv,$tag);
        if (!is_string($cipher)) return self::response(array('error'=>'encryption_failed'),500);
        $blob=array('version'=>$version,'iv'=>base64_encode($iv),'tag'=>base64_encode($tag),'ciphertext'=>base64_encode($cipher));
        update_option(self::nonce_key('encrypted_tasks'),$blob,false);
        return self::response(array('ok'=>true,'version'=>$version,'count'=>count($entries)));
        } finally { delete_option($mutex); }
    }
}
BHM_Mission_Control_OTP_V1::initialize();
}
