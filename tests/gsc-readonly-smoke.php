<?php
/**
 * GSC native direct API regression/security smoke test.
 * Runs without WordPress or any live Google credentials.
 */
define('ABSPATH', __DIR__);
define('AUTH_KEY', 'test-auth-key');
define('SECURE_AUTH_KEY', 'test-secure-auth-key');
define('DAY_IN_SECONDS', 86400);
define('HOUR_IN_SECONDS', 3600);
define('MINUTE_IN_SECONDS', 60);
$GLOBALS['gsc_options'] = array();
$GLOBALS['gsc_calls'] = array();
$GLOBALS['gsc_schedule'] = false;
class WP_Error {
    private $code;
    public function __construct($code, $message = '', $data = array()) { $this->code = $code; }
    public function get_error_code() { return $this->code; }
}
function is_wp_error($x) { return $x instanceof WP_Error; }
function wp_json_encode($x) { return json_encode($x); }
function get_option($key,$default='') {return array_key_exists($key,$GLOBALS['gsc_options'])?$GLOBALS['gsc_options'][$key]:$default;}
function update_option($key,$value,$autoload=false) {$GLOBALS['gsc_options'][$key]=$value;return true;}
function delete_option($key) {unset($GLOBALS['gsc_options'][$key]);return true;}
function home_url($path='/') {return 'https://mokshagoa.com'.$path;}
function trailingslashit($x) {return rtrim($x,'/').'/';}
function wp_parse_url($x) {return parse_url($x);}
function admin_url($p='') {return 'https://mokshagoa.com/wp-admin/'.$p;}
function absint($n) {return abs((int)$n);}
function wp_next_scheduled($hook) {return $GLOBALS['gsc_schedule'];}
function wp_schedule_event($time,$interval,$hook) {$GLOBALS['gsc_schedule']=true;return true;}
function wp_remote_request($url,$args) {
    $GLOBALS['gsc_calls'][]=array('url'=>$url,'method'=>$args['method']??'GET');
    if(strpos($url,'searchAnalytics/query')!==false) {
       return array('code'=>200,'body'=>json_encode(array('rows'=>array(array('keys'=>array('2026-10-07'),'clicks'=>2,'impressions'=>50,'ctr'=>.04,'position'=>5.3)))));
    }
    if(strpos($url,'urlInspection/index:inspect')!==false) {
       return array('code'=>200,'body'=>json_encode(array('inspectionResult'=>array('indexStatusResult'=>array('verdict'=>'PASS','googleCanonical'=>'https://mokshagoa.com/mud-bath-goa/')))));
    }
    if(strpos($url,'/sitemaps')!==false) {
       return array('code'=>200,'body'=>json_encode(array('sitemap'=>array(array('path'=>'https://mokshagoa.com/sitemap.xml')))));
    }
    return array('code'=>500,'body'=>'{}');
}
function wp_remote_retrieve_response_code($r) {return $r['code'];}
function wp_remote_retrieve_body($r) {return $r['body'];}
function current_user_can($cap) {return true;}
function check($value,$description) {
    if(!$value) {fwrite(STDERR,'FAIL: '.$description."\n");exit(1);}
    echo 'PASS: '.$description."\n";
}
require __DIR__.'/../src/class-grec-secrets.php';
require __DIR__.'/../src/class-grec-gsc.php';
$no=GREC_GSC::status();
check($no['configured']===false && $no['connected']===false, 'Unconfigured by default');
check(GREC_GSC::property()==='https://mokshagoa.com/', 'Locked to WordPress Search Console property');
check(GREC_GSC::allowed_url('https://mokshagoa.com/mud-bath-goa/'), 'Allows canonical own-site HTTPS URL');
foreach(array('https://evil.example/mud-bath-goa/','http://mokshagoa.com/mud-bath-goa/','https://mokshagoa.com.evil.com/','https://mokshagoa.com@evil.example/','https://mokshagoa.com:444/','https://mokshagoa.com/mud-bath-goa/?token=secret','https://mokshagoa.com/mud-bath-goa/#bad') as $url) {
    check(!GREC_GSC::allowed_url($url), 'Rejects invalid, offsite, redirected or decorated URL');
}
$unconnected=GREC_GSC::search(array('start_date'=>'2026-10-01','end_date'=>'2026-10-08'));
check(is_wp_error($unconnected)&&$unconnected->get_error_code()==='grec_gsc_not_connected', 'Disconnected access fails closed');
$GLOBALS['gsc_options']['grec_gsc_credentials']=GREC_Secrets::seal(array('client_id'=>'test.apps.googleusercontent.com','client_secret'=>'local-only-test-secret'));
$GLOBALS['gsc_options']['grec_gsc_token']=GREC_Secrets::seal(array('access_token'=>'ephemeral-test-access','refresh_token'=>'ephemeral-test-refresh','expires_at'=>time()+3500));
$status=GREC_GSC::status();
check($status['configured']&&$status['connected'], 'Encrypted OAuth credentials recognized');
check(!strpos(json_encode($status),'test-secret')&&!strpos(json_encode($status),'test-refresh')&&!strpos(json_encode($status),'ephemeral-test-access'), 'Status never exposes OAuth secrets');
$report=GREC_GSC::search(array('start_date'=>'2026-10-01','end_date'=>'2026-10-08','dimensions'=>array('date'),'limit'=>20,'page_url'=>'https://mokshagoa.com/mud-bath-goa/'));
check(!is_wp_error($report)&&count($report['rows'])===1, 'Calls Google Search Analytics from readonly connection');
check($GLOBALS['gsc_calls'][0]['method']==='POST'&&strpos($GLOBALS['gsc_calls'][0]['url'],'www.googleapis.com/webmasters/v3/sites/')!==false,'Fixed Search Analytics endpoint and POST');
$denied=GREC_GSC::search(array('page_url'=>'https://evil.example/mud-bath-goa/'));
check(is_wp_error($denied)&&$denied->get_error_code()==='grec_gsc_bad_url', 'Rejects cross-site page filter');
$badDates=GREC_GSC::search(array('start_date'=>'2026-02-30','end_date'=>'2026-10-08'));
check(is_wp_error($badDates)&&$badDates->get_error_code()==='grec_gsc_bad_dates', 'Rejects impossible date');
$badDimension=GREC_GSC::search(array('dimensions'=>array('query','secret')));
check(is_wp_error($badDimension)&&$badDimension->get_error_code()==='grec_gsc_bad_dimensions', 'Rejects arbitrary Google API dimensions');
$inspection=GREC_GSC::inspect(array('url'=>'https://mokshagoa.com/mud-bath-goa/'));
check(!is_wp_error($inspection)&&$inspection['verdict']==='PASS', 'Search Console URL Inspection is read-only');
$invalid=GREC_GSC::inspect(array('url'=>'https://evil.example/'));
check(is_wp_error($invalid)&&$invalid->get_error_code()==='grec_gsc_bad_url', 'URL inspection cannot target external host');
$sitemaps=GREC_GSC::sitemaps();
check(!is_wp_error($sitemaps)&&count($sitemaps['sitemaps'])===1, 'Fetches sitemap inventory');
GREC_GSC::daily_job();
$summary=GREC_GSC::status();
check($summary['last_snapshot']['clicks']===2 && $summary['last_snapshot']['impressions']===50, 'Daily job persists aggregates, not tokens');
GREC_GSC::schedule();
check($GLOBALS['gsc_schedule']===true, 'WP Cron daily job scheduled when connected');
echo "ALL GSC READONLY TESTS PASSED\n";
