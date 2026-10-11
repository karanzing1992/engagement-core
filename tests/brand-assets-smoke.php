<?php
error_reporting(E_ALL);
$root = sys_get_temp_dir() . '/grec-brand-registry-' . bin2hex(random_bytes(3));
mkdir($root.'/assets/brand',0777,true);
mkdir($root.'/wp/wp-admin/includes',0777,true);
mkdir($root.'/uploads',0777,true);
file_put_contents($root.'/wp/wp-admin/includes/image.php','<?php');
copy(dirname(__DIR__) . '/assets/brand/moksha-logo-source.jpg', $root.'/assets/brand/moksha-logo-source.jpg');
define('ABSPATH',$root.'/wp/');
define('GREC_DIR',$root.'/');
$GLOBALS['state']=['options'=>['deployer_for_git_api_secret'=>str_repeat('1',32)],'posts'=>[], 'meta'=>[], 'files'=>[], 'next'=>40000];
class WP_Error {
    public $code,$message,$data;
    public function __construct($code='',$message='',$data=[]) {$this->code=$code;$this->message=$message;$this->data=$data;}
}
class WP_REST_Response {public $data,$status; public function __construct($data,$status=200){$this->data=$data;$this->status=$status;}}
class RequestFake {
    public $param=[], $headers=[];
    public function get_header($name){return $this->headers[strtolower($name)]??'';}
    public function get_param($name){return $this->param[$name]??null;}
}
function is_wp_error($x){return $x instanceof WP_Error;}
function get_option($key,$fallback=''){return $GLOBALS['state']['options'][$key]??$fallback;}
function update_option($key,$val,$unused=false){$GLOBALS['state']['options'][$key]=$val;return true;}
function current_user_can($cap){return false;}
function wp_get_attachment_url($id){return 'https://mokshagoa.com/wp-content/uploads/official-'.(int)$id.'.jpg';}
function get_post_type($id){return $GLOBALS['state']['posts'][$id]['type']??null;}
function get_post_status($id){return $GLOBALS['state']['posts'][$id]['status']??null;}
function get_post_meta($id,$key,$single=false){return $GLOBALS['state']['meta'][$id][$key]??'';}
function update_post_meta($id,$key,$value){$GLOBALS['state']['meta'][$id][$key]=$value; return true;}
function get_attached_file($id){return $GLOBALS['state']['files'][$id]??null;}
function get_posts($query){
    $found=[];
    foreach($GLOBALS['state']['posts'] as $id=>$p){
        if(($query['post_type']??'')!==$p['type'] || ($query['post_status']??'')!==$p['status'])continue;
        if(isset($query['meta_key']) && (get_post_meta($id,$query['meta_key'],true)!==($query['meta_value']??null)))continue;
        $found[]=$id;
    }
    return $found;
}
function wp_upload_bits($filename,$deprecation,$data){$file=dirname(GREC_DIR).'/unused';$file=$GLOBALS['fake_upload_dir'].'/'.$filename;file_put_contents($file,$data);return ['file'=>$file,'url'=>'https://mokshagoa.com/'.$filename,'error'=>false];}
$GLOBALS['fake_upload_dir']=$root.'/uploads';
function wp_insert_attachment($fields,$file,$parent=0,$wp_error=false){$id=++$GLOBALS['state']['next'];$GLOBALS['state']['posts'][$id]=['type'=>'attachment','status'=>'inherit'];$GLOBALS['state']['files'][$id]=$file;return $id;}
function wp_generate_attachment_metadata($id,$file){return ['width'=>737,'height'=>681];}
function wp_update_attachment_metadata($id,$data){return true;}
function post_type_exists($type){return $type==='mrs_reel';}
function sanitize_key($value){return preg_replace('/[^a-z0-9_\-]/','',strtolower($value));}
function add_action($event,$callable,$priority=10,$accepted=1){return true;}
function register_rest_route($namespace,$route,$args){return true;}
function check($test,$name){if(!$test)throw new RuntimeException('FAIL '+$name);echo 'PASS '.$name."\n";}
require dirname(__DIR__).'/src/class-grec-brand-assets.php';
$checksum='76e89b83667827da4b5d89143fb267f4000a9392eff685129c838c3d0b24748c';
check(GREC_Brand_Assets::validate_source()===true,'byte-identical approved Drive source');
check(GREC_Brand_Assets::saved_attachment_id()===0,'no arbitrary WordPress logo accepted before sync');
check(is_wp_error(GREC_Brand_Assets::choose('moksha','reel')),'renderer fails closed before sync');
$bad=new RequestFake();$bad->headers['x-wp-control-brand-token']=str_repeat('0',64);
check(!GREC_Brand_Assets::authorized($bad),'invalid HMAC refused');
$good=new RequestFake();$good->headers['x-wp-control-brand-token']=hash_hmac('sha256','mrs-brand-assets-v1',str_repeat('1',32));
check(GREC_Brand_Assets::authorized($good),'correct scoped HMAC accepted');
$import=GREC_Brand_Assets::import_master();
check(is_array($import)&&$import['imported']===true,'master imported');
$id=$import['id'];
check(GREC_Brand_Assets::verified_attachment($id),'imported attachment SHA validated');
check(GREC_Brand_Assets::import_master()['id']===$id && !GREC_Brand_Assets::import_master()['imported'],'sync is idempotent');
$reel=GREC_Brand_Assets::choose('moksha','reel');
check(is_array($reel)&&$reel['drive_file_id']==='1XwmlYRfjfkcnbEOlJLNJc8bGHm9uxkyv'&&$reel['approved_sha256']===$checksum,'unambiguous canonical origin');
check($reel['placement_policy']['not_before_seconds']>=1.5&&$reel['placement_policy']['exclude_first_hook']===true,'no opening logo card');
check(is_wp_error(GREC_Brand_Assets::choose('moksha','unknown')),'unknown variant refused');
check(is_wp_error(GREC_Brand_Assets::choose('andaz','reel')),'unapproved brand refused');
$GLOBALS['state']['posts'][13098]=['type'=>'mrs_reel','status'=>'private'];
$GLOBALS['state']['meta'][13098]=['_mrs_brand'=>'moksha','_mrs_state'=>'preview_ready','_mrs_logo_attachment_id'=>0];
$GLOBALS['state']['posts'][13099]=['type'=>'mrs_reel','status'=>'private'];
$GLOBALS['state']['meta'][13099]=['_mrs_brand'=>'moksha','_mrs_state'=>'draft','_mrs_logo_attachment_id'=>0];
$GLOBALS['state']['posts'][13101]=['type'=>'mrs_reel','status'=>'private'];
$GLOBALS['state']['meta'][13101]=['_mrs_brand'=>'moksha','_mrs_state'=>'approved','_mrs_logo_attachment_id'=>0];
$GLOBALS['state']['posts'][13102]=['type'=>'mrs_reel','status'=>'private'];
$GLOBALS['state']['meta'][13102]=['_mrs_brand'=>'moksha','_mrs_state'=>'draft','_mrs_logo_attachment_id'=>12570];
$report=GREC_Brand_Assets::apply_to_private_drafts($id);
check($report['linked']===2,'only unapproved drafts without logo linked');
check(get_post_meta(13098,'_mrs_state',true)==='draft' && get_post_meta(13098,'_mrs_worker_state',true)==='rebranding_required','unbranded preview approval revoked');
check($report['requires_review']===1,'approved output not silently changed');
check($report['conflicting_asset_requires_review']===1,'unknown existing WordPress logo not replaced silently');
check(GREC_Brand_Assets::apply_to_private_drafts($id)['already_linked']===2,'draft logo sync idempotent');
$GLOBALS['state']['posts'][13103]=['type'=>'mrs_reel','status'=>'private'];
$GLOBALS['state']['meta'][13103]=['_mrs_brand'=>'moksha','_mrs_state'=>'draft','_mrs_logo_attachment_id'=>0,'_mrs_logo_verified'=>false];
GREC_Brand_Assets::maybe_autofill_logo(1,13103,'_mrs_logo_verified',false);
check((int)get_post_meta(13103,'_mrs_logo_attachment_id',true)===$id,'new Media Studio draft receives verified canonical automatically');
$file=$GLOBALS['state']['files'][$id];file_put_contents($file,'damaged');
check(!GREC_Brand_Assets::verified_attachment($id),'tampered cached attachment fails checksum');
check(is_wp_error(GREC_Brand_Assets::import_master()),'tampered registered copy requires intervention');
copy(dirname(__DIR__).'/assets/brand/moksha-logo-source.jpg',$file);
file_put_contents(GREC_DIR.'assets/brand/moksha-logo-source.jpg','damaged');
check(is_wp_error(GREC_Brand_Assets::validate_source()),'modified mirrored master rejected');
echo "PASS ALL 20 canonical brand-asset tests\n";