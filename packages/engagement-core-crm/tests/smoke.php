<?php
/** Synthetic, dependency-free smoke tests. Not an actual WordPress integration test. */
declare(strict_types=1);

define('ABSPATH', '/tmp/wp/');
define('ECCRM_CAPABILITY', 'manage_eccrm');
const ARRAY_A = 'ARRAY_A';
function sanitize_text_field($v) { return trim(strip_tags($v)); }
function sanitize_email($v) { return filter_var($v, FILTER_SANITIZE_EMAIL); }
function is_email($v) { return filter_var($v, FILTER_VALIDATE_EMAIL) !== false; }
function sanitize_key($v) { return preg_replace('/[^a-z0-9_-]/', '', strtolower($v)); }
function current_time($type, $gmt=false) { return '2026-10-25 13:30:00'; }
function wp_generate_uuid4() { static $n=0; return '11111111-1111-4111-8111-' . str_pad((string)++$n,12,'0',STR_PAD_LEFT); }
function get_current_user_id() { return 1; }
function wp_json_encode($x) { return json_encode($x); }
function current_user_can($cap) { return $GLOBALS['allowed'] ?? false; }
function is_wp_error($x) { return $x instanceof WP_Error; }
function rest_ensure_response($x) { return $x; }
function register_rest_route($namespace,$route,$routes) { $GLOBALS['routes'][$namespace.$route]=$routes; }
class WP_Error { public $code, $message, $data; public function __construct($c,$m,$d=[]) {$this->code=$c;$this->message=$m;$this->data=$d;} }
class WP_REST_Server { const READABLE='GET', CREATABLE='POST'; }
class WP_REST_Response { public $data,$status; public function __construct($data,$status=200) {$this->data=$data;$this->status=$status;} }
class WP_REST_Request implements ArrayAccess {
    private $values,$json,$body;
    public function __construct($values=[],$json=null,$body=[]) {$this->values=$values;$this->json=$json;$this->body=$body;}
    public function get_param($key) {return $this->values[$key]??null;}
    public function get_json_params() {return $this->json;}
    public function get_body_params() {return $this->body;}
    public function offsetExists($offset): bool {return isset($this->values[$offset]);}
    public function offsetGet($offset): mixed {return $this->values[$offset]??null;}
    public function offsetSet($offset,$value): void {$this->values[$offset]=$value;}
    public function offsetUnset($offset): void {unset($this->values[$offset]);}
}
class FakeWPDB {
    public $prefix='wp_', $insert_id=0, $records=[], $events=[], $last_error='';
    public function prepare($sql,...$args) {
        foreach($args as $x){$sql=preg_replace('/%d/',(string)(int)$x,$sql,1);}return $sql;
    }
    public function insert($table,$row) {
        if (str_ends_with($table,'_contacts')) {
            foreach ($this->records as $r){if($r['external_id']!==null && ($row['external_id']??null)!==null && $r['source']===$row['source'] && $r['external_id']===$row['external_id']){return false;}}
            $row += ['source'=>'manual','external_id'=>null,'lifecycle'=>'lead','email'=>'','phone'=>''];
            $row['id']=++$this->insert_id;
            $this->records[$row['id']]=$row;return 1;
        }
        $this->events[]=$row;return 1;
    }
    public function get_row($sql,$format) { preg_match('/id = (\d+)/',$sql,$m);return $this->records[(int)($m[1]??0)]??null; }
    public function get_results($sql,$format) {return array_values(array_reverse($this->records));}
    public function update($table,$data,$where) {$id=$where['id'];$this->records[$id]=array_merge($this->records[$id],$data);return 1;}
}
$wpdb = new FakeWPDB();
require dirname(__DIR__).'/includes/class-eccrm-schema.php';
require dirname(__DIR__).'/includes/class-eccrm-contacts.php';
require dirname(__DIR__).'/includes/class-eccrm-rest.php';
function verify($condition,$message){if(!$condition){fwrite(STDERR,"FAIL: $message\n");exit(1);}echo "PASS: $message\n";}
verify(ECCRM_Contacts::normalize(['display_name'=>'<script>A</script>'])['display_name']==='A','sanitize user-visible name');
verify(isset(ECCRM_Contacts::normalize(['display_name'=>[]])['error']),'reject array-valued untrusted contact');
verify(isset(ECCRM_Contacts::normalize(['display_name'=>''])['error']),'reject empty contact');
verify(isset(ECCRM_Contacts::normalize(['display_name'=>'Test','email'=>'no-at'])['error']),'reject malformed email');
verify(isset(ECCRM_Contacts::normalize(['display_name'=>'Test','lifecycle'=>'secretadmin'])['error']),'reject invalid lifecycle');
verify(ECCRM_Contacts::normalize(['display_name'=>'Test','external_id'=>''])['external_id']===null,'empty external identifier nullable');
$GLOBALS['allowed']=false;
verify(is_wp_error(ECCRM_REST::authorize()),'deny unauthorized CRM access');
$GLOBALS['allowed']=true;
verify(ECCRM_REST::authorize()===true,'allow authorized CRM operator');
ECCRM_REST::routes();
verify(count($GLOBALS['routes'])===4,'register contacts, record, overview and activity routes');
verify(is_wp_error(ECCRM_REST::create(new WP_REST_Request([], 'bad-json-type'))),'reject malformed JSON object');
$response=ECCRM_REST::create(new WP_REST_Request([],['display_name'=>'Synthetic','source'=>'staycore','external_id'=>'guest-1']));
verify($response instanceof WP_REST_Response && $response->status===201,'create contact via API');
verify(count($wpdb->events)===1 && $wpdb->events[0]['delivery_state']==='local_only','write private local-only event');
verify(strpos($wpdb->events[0]['payload_json'],'Synthetic')===false,'avoid customer PII in local event payload');
verify(is_wp_error(ECCRM_REST::create(new WP_REST_Request([],['display_name'=>'Duplicate','source'=>'staycore','external_id'=>'guest-1']))),'deduplicate source identity');
$patch=ECCRM_REST::update(new WP_REST_Request(['id'=>1],['lifecycle'=>'qualified','external_id'=>'attack']));
verify($patch['lifecycle']==='qualified' && $wpdb->records[1]['external_id']==='guest-1','PATCH preserves immutable source identity');
verify(count($wpdb->events)===2,'contact update emits local audit event');
echo "SMOKE SUITE PASSED\n";
