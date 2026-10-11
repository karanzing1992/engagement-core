<?php
/* Independent smoke test for private 4MiB chunked WordPress uploads.
 * The large-file test exercises declared size WITHOUT allocating 231 MB.
 */
error_reporting(E_ALL);
$site = sys_get_temp_dir() . '/mrs-upload-tests-' . bin2hex(random_bytes(4));
@mkdir($site . '/public_html', 0700, true);
define('ABSPATH', $site . '/public_html/');
$GLOBALS['opts'] = array('deployer_for_git_api_secret'=>'0123456789abcdef0123456789abcdef');
$GLOBALS['uid'] = 21;
class WP_Error {
    public function __construct(public $code,public $message,public $data=array()){}
}
class WP_REST_Response {
    public function __construct(public $data,public $status=200){}
}
class WP_REST_Request implements ArrayAccess {
    public function __construct(public $data=array(),public $headers=array(),
                                public $route=array(),public $body=''){}
    public function get_json_params(){return $this->data;}
    public function get_header($key){return $this->headers[$key]??'';}
    public function get_body(){return $this->body;}
    public function get_param($key){return $this->data[$key]??null;}
    public function offsetExists(mixed $offset):bool{return isset($this->route[$offset]);}
    public function offsetGet(mixed $offset):mixed{return $this->route[$offset]??null;}
    public function offsetSet(mixed $offset,mixed $v):void{$this->route[$offset]=$v;}
    public function offsetUnset(mixed $offset):void{unset($this->route[$offset]);}
}
function is_wp_error($x){return $x instanceof WP_Error;}
function get_option($k,$default=false){return $GLOBALS['opts'][$k]??$default;}
function add_option($k,$value,$a='',$b=false){if(isset($GLOBALS['opts'][$k]))return false;$GLOBALS['opts'][$k]=$value;return true;}
function update_option($k,$value,$a=false){$GLOBALS['opts'][$k]=$value;return true;}
function get_current_user_id(){return $GLOBALS['uid'];}
function current_user_can($x){return $x==='manage_options';}
function absint($n){return abs((int)$n);}
function sanitize_file_name($n){return basename(preg_replace('/[^A-Za-z0-9._-]/','_', (string) $n));}
function rest_url($s){return 'https://mokshagoa.com/wp-json/'.$s;}
function add_action(){}
function register_rest_route(){}
function add_submenu_page(){}
function plugins_url($p,$x){return 'https://mokshagoa.com/wp-content/plugins/engagement-core/'.$p;}
function esc_url($x){return $x;}
function admin_url($x){return $x;}
function wp_create_nonce($a){return 'nonce';}
function wp_json_encode($x){return json_encode($x);}
function wp_die(){throw new Exception('blocked');}
require __DIR__ . '/../src/class-grec-media-ingest.php';
$tests=0;
function check($value,$name){global $tests;$tests++;if(!$value)throw new Exception("FAIL: ".$name);echo "PASS: ".$name.PHP_EOL;}
function req($data=array(),$route=array(),$body='',$headers=array()){
    return new WP_REST_Request($data,$headers,$route,$body);
}
function part_request($id,$file,$part,$data){
    return req(array(),array('id'=>$id,'file'=>$file,'part'=>$part),$data,
               array('X-Chunk-SHA256'=>hash('sha256',$data)));
}
$r=GREC_Media_Ingest::start(req(array('files'=>array(
    array('name'=>'phone-large.mp4','size'=>230924113),
    array('name'=>'phone-short.mp4','size'=>20442820)))));
check($r instanceof WP_REST_Response && $r->status===201,'231MB + 20MB phone sources accepted');
$large=$r->data;
check($large['files'][0]['parts']===56,'231MB source split into 4MiB resumable parts');
check($large['private']===true && $large['publishing_enabled']===false,'No public publishing');
$root=realpath(dirname(ABSPATH).'/.moksha-private-media');
check($root && !str_starts_with($root,realpath(ABSPATH)),'Upload vault is outside public document root');
$bad=GREC_Media_Ingest::start(req(array('files'=>array(
    array('name'=>'shell.php','size'=>4096)))));
check($bad instanceof WP_Error,'Executable extension rejected');

$sample=4*1024*1024+1013;
$r=GREC_Media_Ingest::start(req(array('files'=>array(
    array('name'=>'clip1.mp4','size'=>$sample),
    array('name'=>'clip2.mp4','size'=>$sample)))));
$id=$r->data['id'];
$video='0000ftypisom'.str_repeat('A',$sample-12);
$p0=substr($video,0,4194304);
$p1=substr($video,4194304);
$x=GREC_Media_Ingest::chunk(part_request($id,0,0,$p0));
check($x instanceof WP_REST_Response && $x->data['ok'],'First 4MiB part accepted');
$dup=GREC_Media_Ingest::chunk(part_request($id,0,0,$p0));
check($dup instanceof WP_REST_Response && $dup->data['duplicate'],'Identical part is idempotent');
$bad=GREC_Media_Ingest::chunk(req(array(),array('id'=>$id,'file'=>0,'part'=>1),$p1,
                              array('X-Chunk-SHA256'=>str_repeat('a',64))));
check($bad instanceof WP_Error && $bad->code==='mrs_chunk_integrity','Bad SHA-256 part refused');
$bad=GREC_Media_Ingest::finish(req(array(),array('id'=>$id,'file'=>0)));
check($bad instanceof WP_Error && $bad->code==='mrs_missing_chunk','Incomplete upload cannot finalize');
GREC_Media_Ingest::chunk(part_request($id,0,1,$p1));
$f=GREC_Media_Ingest::finish(req(array(),array('id'=>$id,'file'=>0)));
check($f instanceof WP_REST_Response && $f->data['sha256']===hash('sha256',$video),'Final file rebuilt byte-identically with streamed SHA-256');
check($f->data['state']==='uploading','Session waits for all clips');
GREC_Media_Ingest::chunk(part_request($id,1,0,$p0));
GREC_Media_Ingest::chunk(part_request($id,1,1,$p1));
$f=GREC_Media_Ingest::finish(req(array(),array('id'=>$id,'file'=>1)));
check($f->data['state']==='ready','Two source clips queued together');
$list=GREC_Media_Ingest::ready(req());
check(count($list->data['sessions'])===1 && $list->data['sessions'][0]['id']===$id,'Private queue exposes only ready source sessions');
$auth=req(array(),array(),'',
          array('X-WP-Control-Media-Token'=>hash_hmac('sha256','mrs-media-queue-v1',$GLOBALS['opts']['deployer_for_git_api_secret'])));
check(GREC_Media_Ingest::worker_allowed($auth),'Existing in-house HMAC authorizes worker');
check(!GREC_Media_Ingest::worker_allowed(req()),'Anonymous worker blocked');
$output='0000ftypisom'.str_repeat('B',2048);
$hash=hash('sha256',$output);
$start=GREC_Media_Ingest::render_start(req(array('size'=>strlen($output),'sha256'=>$hash),array('id'=>$id)));
check($start->data['state']==='processing','Worker may begin private result upload');
$p=GREC_Media_Ingest::render_chunk(part_request($id,0,0,$output));
check($p->data['ok'],'Output chunk stored privately');
$done=GREC_Media_Ingest::render_finish(req(array(),array('id'=>$id)));
check($done->data['status']==='preview_ready_private','Final MP4 saved privately without publishing');
$info=GREC_Media_Ingest::status(req(array(),array('id'=>$id)));
check($info->data['rendered'] && $info->data['private_preview_url'],'Admin sees private preview only');
echo "TOTAL TESTS ".$tests.PHP_EOL;
