<?php
/**
 * Isolated CLI contract smoke tests: NO WordPress instance, NO Telegram send.
 * Run: php tests/mission-control-otp-smoke.php
 */
error_reporting(E_ALL);
define('ABSPATH',__DIR__);
$GLOBALS['opt']=array('grec_booking_private_telegram_chat'=>'123456789');
$GLOBALS['transients']=array();
$GLOBALS['otp_code']=null;
$_SERVER['HTTP_ORIGIN']='https://karanzing1992.github.io';
$_SERVER['REMOTE_ADDR']='127.0.0.1';

class WP_Error {
    private $code; private $data;
    public function __construct($code,$message,$data=array()){$this->code=$code;$this->data=$data;}
    public function get_error_code(){return $this->code;}
    public function get_error_data(){return $this->data;}
}
function is_wp_error($v){return $v instanceof WP_Error;}
class WP_REST_Response {
    private $data; private $status;
    public function __construct($data,$status=200){$this->data=$data;$this->status=$status;}
    public function header($key,$value){}
    public function get_data(){return $this->data;}
    public function get_status(){return $this->status;}
}
class WP_REST_Request {
    private $body; private $headers;
    public function __construct($data=array(),$headers=array()){
        $this->body=json_encode($data);$this->headers=array_change_key_case($headers,CASE_LOWER);
    }
    public function get_body(){return $this->body;}
    public function get_json_params(){return json_decode($this->body,true);}
    public function get_header($key){return $this->headers[strtolower($key)]??'';}
    public function get_route(){return '/mission-control/v1/tasks';}
}
class GREC_Telegram {
    public static function credentials(){return array('token'=>'FAKE_TEST_ONLY');}
}
function add_action($name,$fn){}
function add_filter($name,$fn,$priority=10,$args=1){}
function register_rest_route($ns,$route,$args){}
function __return_true(){return true;}
function wp_salt($kind='auth'){return str_repeat('t',64);}
function add_option($name,$value,$deprecated='',$autoload='yes'){
    if(array_key_exists($name,$GLOBALS['opt']))return false;
    $GLOBALS['opt'][$name]=$value;return true;
}
function get_option($name,$default=false){return $GLOBALS['opt'][$name]??$default;}
function update_option($name,$value,$autoload=null){$GLOBALS['opt'][$name]=$value;return true;}
function delete_option($name){unset($GLOBALS['opt'][$name]);return true;}
function set_transient($name,$value,$ttl){$GLOBALS['transients'][$name]=array($value,time()+$ttl);return true;}
function get_transient($name){$row=$GLOBALS['transients'][$name]??null;return $row&&$row[1]>time()?$row[0]:false;}
function delete_transient($name){unset($GLOBALS['transients'][$name]);return true;}
function wp_remote_post($url,$args){
    if(strpos($url,'https://api.telegram.org/bot')!==0)throw new RuntimeException('wrong Telegram endpoint');
    $b=$args['body'];if((string)$b['chat_id']!==(string)get_option('grec_booking_private_telegram_chat'))throw new RuntimeException('wrong recipient');
    if(preg_match('/sign-in code: ([0-9]{6})/',$b['text'],$m))$GLOBALS['otp_code']=$m[1];
    return array('response'=>array('code'=>200),'body'=>json_encode(array('ok'=>true,'result'=>array('chat'=>array('id'=>$b['chat_id']),'message_id'=>42))));
}
function wp_remote_retrieve_body($response){return $response['body'];}
function wp_remote_retrieve_response_code($response){return $response['response']['code'];}
function wp_json_encode($v){return json_encode($v);}
function wp_parse_url($v){return parse_url($v);}
function sanitize_text_field($v){return trim(strip_tags($v));}
function sanitize_textarea_field($v){return trim(strip_tags($v));}
require __DIR__.'/../integrations/private-auth/mission-control-telegram-otp.php';

function check($ok,$why){if(!$ok){fwrite(STDERR,"FAIL ".$why."\n");exit(1);}}
function status($res){return $res instanceof WP_REST_Response?$res->get_status():($res instanceof WP_Error?(int)($res->get_error_data()['status']??500):0);}
function data($res){return $res instanceof WP_REST_Response?$res->get_data():array();}

$auth='BHM_Mission_Control_OTP_V1';
check(status($auth::health())===200,'health');
$_SERVER['HTTP_ORIGIN']='https://malicious.example';
check(status($auth::start(new WP_REST_Request()))===403,'origin denied');
$_SERVER['HTTP_ORIGIN']='https://karanzing1992.github.io';
$start=$auth::start(new WP_REST_Request());
check(status($start)===200&&preg_match('/^[a-f0-9]{32}$/',data($start)['challenge_id']??''),'OTP start');
check((bool)preg_match('/^[0-9]{6}$/',(string)$GLOBALS['otp_code']),'code is six digits');
$id=data($start)['challenge_id'];
check(status($auth::verify(new WP_REST_Request(array('challenge_id'=>$id,'code'=>'000000'))))===401,'wrong OTP denied');
$good=$auth::verify(new WP_REST_Request(array('challenge_id'=>$id,'code'=>$GLOBALS['otp_code'])));
check(status($good)===200&&strlen((string)(data($good)['access_token']??''))===64,'OTP verify');
check(status($auth::verify(new WP_REST_Request(array('challenge_id'=>$id,'code'=>$GLOBALS['otp_code'])))===401,'replay denied');
$bearer='Bearer '.data($good)['access_token'];
check($auth::authorize_session(new WP_REST_Request(array(),array('authorization'=>$bearer)))===true,'session valid');
check(status($auth::authorize_session(new WP_REST_Request()))===401,'missing session denied');
$read=$auth::read_tasks(new WP_REST_Request(array(),array('authorization'=>$bearer)));
check(status($read)===200&&data($read)['version']===0,'empty vault');
$tasks=array(array('id'=>'test-task-123','title'=>'Private test task','project'=>'Demo','url'=>'https://chatgpt.com/c/12345678-aaaa-bbbb-cccc-dddddddddddd','status'=>'Working','summary'=>'Metadata only','next'=>'QA','blocker'=>'','updated'=>time()*1000,'manual'=>true));
$write=$auth::write_tasks(new WP_REST_Request(array('version'=>0,'entries'=>$tasks),array('authorization'=>$bearer)));
check(status($write)===200&&data($write)['version']===1,'encrypted write');
$raw=json_encode(get_option('bhm_mc_otp_v1_encrypted_tasks'));
check(strpos($raw,'Private test task')===false,'no plaintext stored');
$read=$auth::read_tasks(new WP_REST_Request(array(),array('authorization'=>$bearer)));
check(status($read)===200&&data($read)['entries'][0]['title']==='Private test task','encrypted read');
check(status($auth::write_tasks(new WP_REST_Request(array('version'=>0,'entries'=>$tasks))))===409,'revision conflict');
$tasks[0]['url']='https://chatgpt.com/share/public-id';
check(status($auth::write_tasks(new WP_REST_Request(array('version'=>1,'entries'=>$tasks))))===422,'shared-public URL denied');
$logout=$auth::logout(new WP_REST_Request(array(),array('authorization'=>$bearer)));
check(status($logout)===200,'logout');
check(status($auth::authorize_session(new WP_REST_Request(array(),array('authorization'=>$bearer))))===401,'token revoked');
$GLOBALS['opt']['grec_booking_private_telegram_chat']='-1000000000000';
check(status($auth::start(new WP_REST_Request()))===503,'group recipient forbidden');
echo "Mission Control OTP smoke PASS (no real network)\n";
