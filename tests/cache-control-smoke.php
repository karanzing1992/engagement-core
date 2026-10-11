<?php
/**
 * Run: php tests/cache-control-smoke.php
 * Uses WordPress stubs; never touches a live site.
 */
define('ABSPATH',__DIR__);
define('LSCWP_V','7.9.1');
class WP_Error { private $code; public function __construct($code,$message='',$data=array()){$this->code=$code;} public function get_error_code(){return $this->code;} }
$GLOBALS['cache_admin']=true;
$GLOBALS['cache_url']='https://mokshagoa.com/fire-ice-reset/';
$GLOBALS['purges']=array();
function absint($x){return abs((int)$x);}
function get_post($id){return 12627===$id?(object)array('post_status'=>'publish','post_type'=>'page'):null;}
function get_post_type_object($x){return (object)array('public'=>true,'publicly_queryable'=>false);}
function get_permalink($x){return $GLOBALS['cache_url'];}
function wp_parse_url($s){return parse_url($s);}
function home_url($path){return 'https://mokshagoa.com'.$path;}
function has_action($hook){return 0;}
function current_user_can($cap){return $GLOBALS['cache_admin'];}
function is_wp_error($x){return $x instanceof WP_Error;}
function sanitize_text_field($x){return strip_tags($x);}
function sanitize_key($x){return strtolower(preg_replace('/[^a-z0-9_-]/i','',$x));}
function add_query_arg($key,$value,$url){return $url.'?'.$key.'='.$value;}
function wp_generate_password($length,$special,$extra){return 'testnonce';}
function wp_using_ext_object_cache(){return false;}
function wp_strip_all_tags($html){return strip_tags($html);}
function wp_remote_get($url,$args){return array('code'=>200,'body'=>false!==strpos($url,'_wpcontrol_probe')?'<p>Fire & Ice Reset now includes four answers</p>':'<p>Old page</p>','headers'=>array('etag'=>'test-etag'));}
function wp_remote_retrieve_response_code($r){return $r['code'];}
function wp_remote_retrieve_body($r){return $r['body'];}
function wp_remote_retrieve_header($r,$key){return $r['headers'][$key]??'';}
function do_action($hook,$arg){$GLOBALS['purges'][]=array($hook,$arg);}
require __DIR__.'/../src/class-grec-cache-tools.php';
function check($value,$message){if(!$value){fwrite(STDERR,"FAIL: ".$message."\n");exit(1);}echo "PASS: ".$message."\n";}
$d=GREC_Cache_Tools::diagnose(array('post_id'=>12627,'expected_text'=>'four answers'));
check($d['canonical']['expected_text_found']===false&&$d['cache_busted']['expected_text_found']===true,'Detect old canonical for a built-in page');
check($d['html_differs']===true,'Detect divergent HTML');
$dry=GREC_Cache_Tools::purge_target(array('post_id'=>12627,'dry_run'=>true));
check(!empty($dry['dry_run'])&&!$GLOBALS['purges'],'Dry run does not purge');
$denied=GREC_Cache_Tools::purge_target(array('post_id'=>12627));
check(is_wp_error($denied)&&$denied->get_error_code()==='wp_control_cache_confirmation_required','Require explicit confirmation');
$p=GREC_Cache_Tools::purge_target(array('post_id'=>12627,'confirm'=>true));
check($p['dispatched']&&!$p['verified_cleared']&&$GLOBALS['purges'][0][0]==='litespeed_purge_url','Dispatch URL hook, never claim success');
$GLOBALS['cache_url']='https://malicious.example/secret';
$denied=GREC_Cache_Tools::diagnose(array('post_id'=>12627));
check(is_wp_error($denied)&&$denied->get_error_code()==='wp_control_cache_url_rejected','Reject off-domain target');
$GLOBALS['cache_admin']=false;
$denied=GREC_Cache_Tools::diagnose(array('post_id'=>12627));
check(is_wp_error($denied)&&$denied->get_error_code()==='wp_control_cache_forbidden','Reject non-admin');
echo "ALL CACHE CONTROL SMOKE TESTS PASSED\n";
