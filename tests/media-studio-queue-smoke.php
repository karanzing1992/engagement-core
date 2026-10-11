<?php
error_reporting(E_ALL);
define('ABSPATH','/tmp/');
$GLOBALS['opts']=['deployer_for_git_api_secret'=>'0123456789abcdef0123456789abcdef'];
$GLOBALS['posts']=[];$GLOBALS['metas']=[];$GLOBALS['counter']=42;
class WP_Error{public function __construct(public string $code,public string $message,public array $data=[]){}}
class WP_REST_Request implements ArrayAccess {
    public function __construct(public array $data,public array $headers=[],public array $route=[],public array $query=[]){ }
    public function get_header($k){return $this->headers[$k]??'';}
    public function get_json_params(){return $this->data;}
    public function get_param($k){return $this->query[$k]??null;}
    public function offsetGet(mixed $o):mixed{return $this->route[$o]??null;}
    public function offsetExists(mixed $o):bool{return isset($this->route[$o]);}
    public function offsetSet(mixed $o,mixed $v):void{$this->route[$o]=$v;}
    public function offsetUnset(mixed $o):void{unset($this->route[$o]);}
}
class WP_REST_Response{public function __construct(public array $data,public int $status) {}}
class MRS_Studio{}
class MRS_Policy{
 public static function brand_policies():array{return ['moksha'=>['max_duration_seconds'=>180]];}
 public static function validate_creative(string $b,string $s,string $c):array{return str_contains(strtolower($s.$c),'moksha')?['brand not allowed']:[];}
 public static function validate_ledger(array $rows):array{return [];} }
function get_option($key,$def=''){return $GLOBALS['opts'][$key]??$def;}
function add_option($key,$value,$deprecated='',$autoload=false){if(array_key_exists($key,$GLOBALS['opts']))return false;$GLOBALS['opts'][$key]=$value;return true;}
function get_post_type($id){return $GLOBALS['posts'][$id]['post_type']??null;}
function get_post_status($id){return $GLOBALS['posts'][$id]['post_status']??null;}
function post_type_exists($type){return $type==='mrs_reel';}
function sanitize_key($s){return preg_replace('/[^a-z0-9_-]/','',strtolower($s));}
function sanitize_text_field($s){return trim(strip_tags($s));}
function sanitize_textarea_field($s){return trim(strip_tags($s));}
function is_wp_error($o){return $o instanceof WP_Error;}
function wp_json_encode($o){return json_encode($o);}
function wp_insert_post($p,$wp_error){$id=++$GLOBALS['counter'];$GLOBALS['posts'][$id]=$p;return $id;}
function wp_delete_post($id,$force){unset($GLOBALS['posts'][$id]);}
function get_post_meta($id,$key,$single){return $GLOBALS['metas'][$id][$key]??'';}
function update_post_meta($id,$key,$value){$GLOBALS['metas'][$id][$key]=$value;}
function absint($x){return abs((int)$x);}
function esc_url_raw($x){return $x;}
function wp_parse_url($url){return parse_url($url);}
function register_rest_route($namespace,$route,$args){}
function add_action($name,$fn,$priority=10){}
function add_filter($name,$fn,$priority=10,$accepted=1){}
function get_posts($args){return array_keys($GLOBALS['posts']);}
function update_option($key,$value,$autoload=false){$GLOBALS['opts'][$key]=$value;return true;}
require __DIR__.'/../src/class-grec-media-queue.php';
function ok($condition,$message){if(!$condition){fwrite(STDERR,'FAIL: '.$message."\n");exit(1);}echo 'PASS '.$message."\n";}
$key=hash_hmac('sha256','mrs-media-queue-v1',$GLOBALS['opts']['deployer_for_git_api_secret']);
$headers=['X-WP-Control-Media-Token'=>$key];
$data=['job_key'=>'nature-immersive-20261011','brand'=>'moksha','title'=>'Nature Soundscape: 85-second private draft', 'topic'=>'A natural four-sound listening experience','script'=>'Put on headphones. Listen to rain, birds, waves and water.', 'caption'=>'Which natural sound helps you unwind?', 'duration_seconds'=>85,'notes'=>'No narration or music', 'ledger'=>[]];
$bad = new WP_REST_Request($data,[]);
ok(!GREC_Media_Queue::authorized($bad),'anonymous cannot call worker queue');
$r=new WP_REST_Request($data,$headers);
ok(GREC_Media_Queue::authorized($r),'valid HMAC accepted');
$first=GREC_Media_Queue::create_draft($r);
ok($first instanceof WP_REST_Response && $first->status===201, 'draft created with HTTP 201');
$id=$first->data['id'];
ok(get_post_status($id)==='private' && get_post_meta($id,'_mrs_state',true)==='draft','record private and only draft');
$dup=GREC_Media_Queue::create_draft($r);
ok($dup instanceof WP_REST_Response && $dup->status===200 && $dup->data['id']===$id,'repeat request idempotent');
$bad_copy=$data;$bad_copy['job_key']='nature-different-20261011';$bad_copy['script']='Book a Moksha reset';
ok(GREC_Media_Queue::create_draft(new WP_REST_Request($bad_copy,$headers)) instanceof WP_Error,'forbidden copy rejected');
$ledger=[[
 'source_url'=>'https://commons.wikimedia.org/wiki/File:Goa_Coast.webm',
 'license_url'=>'https://creativecommons.org/licenses/by/3.0',
 'creator'=>'Local videographer','license_name'=>'CC BY 3.0','media_type'=>'video',
 'origin'=>'licensed_stock','capture_country'=>'India','capture_region'=>'Goa',
 'verification_status'=>'human_verified','verified_by'=>'Media Studio editor',
 'location_evidence_url'=>'https://commons.wikimedia.org/wiki/File:Goa_Coast.webm'
 ],[
 'source_url'=>'https://commons.wikimedia.org/wiki/File:Ocean_Waves.ogg',
 'license_url'=>'https://creativecommons.org/licenses/by/3.0',
 'creator'=>'Audio Creator','license_name'=>'CC BY 3.0','media_type'=>'audio'
 ]];
$bad_preview=GREC_Media_Queue::attach_preview(new WP_REST_Request(['job_key'=>$data['job_key'],'private_preview_url'=>'https://github.com/evil/public/actions/runs/123/artifacts/12','ledger'=>$ledger],$headers,['id'=>$id]));
ok($bad_preview instanceof WP_Error,'non-allowlisted preview link rejected');
$good='https://github.com/karanzing1992/moksha_wordpress/actions/runs/38108426717/artifacts/11691350006';
$good_preview=GREC_Media_Queue::attach_preview(new WP_REST_Request(['job_key'=>$data['job_key'],'private_preview_url'=>$good,'ledger'=>$ledger],$headers,['id'=>$id]));
ok($good_preview instanceof WP_REST_Response && $good_preview->status===200,'allowlisted private artifact accepted');
ok(get_post_meta($id,'_mrs_state',true)==='preview_ready','preview only, no publishing');
ok($good_preview->data['publish_enabled']===false && $good_preview->data['schedule_enabled']===false,'publishing and scheduling always disabled');
ok(GREC_Media_Queue::geo_ledger_errors($ledger)===[], 'verified Goa visual source accepted');
$nonlocal=$ledger;
$nonlocal[0]['capture_country']='Iceland';
ok(count(GREC_Media_Queue::geo_ledger_errors($nonlocal))>0,'Iceland footage rejected even if title or copy suggests Goa');
$remote=GREC_Media_Queue::attach_preview(new WP_REST_Request(
 ['job_key'=>$data['job_key'],'private_preview_url'=>$good,'ledger'=>$nonlocal],
 $headers,['id'=>$id]));
ok($remote instanceof WP_Error && $remote->code==='mrs_queue_geo_policy','preview callback rejects foreign source');
ok(get_post_meta($id,'_mrs_state',true)==='preview_ready','rejected callback does not overwrite prior approved candidate');

update_post_meta($id,'_mrs_ledger',$nonlocal);
GREC_Media_Queue::quarantine_legacy_previews();
ok(get_post_meta($id,'_mrs_state',true)==='needs_revision','prior nonlocal preview quarantined for revision');
ok(get_post_meta($id,'_mrs_worker_state',true)==='blocked_nonlocal_footage','legacy worker marked blocked');
ok(get_post_meta($id,'_mrs_geo_review_status',true)==='regional_replacement_required','regional replacement required');
ok(get_option('mrs_india_geo_audit_20261011')===1,'legacy migration marked complete');
