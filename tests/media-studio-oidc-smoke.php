<?php
/* Real local RS256 verification of short-lived GitHub Actions worker identity.
 * Tests are signed with an ephemeral key, not a production GitHub credential.
 */
error_reporting(E_ALL);
define('ABSPATH','/tmp/');
define('HOUR_IN_SECONDS',3600);
$GLOBALS['jwks_cache']=array();
class FakeReq {
    public function __construct(public $jwt){}
    public function get_header($x){return $x==='X-GitHub-OIDC-Token'?$this->jwt:'';}
}
function get_transient($key){return $GLOBALS['jwks_cache'][$key]??false;}
function set_transient($key,$value,$ttl){$GLOBALS['jwks_cache'][$key]=$value;return true;}
function is_wp_error($x){return false;}
function wp_remote_retrieve_response_code($r){return $r['code'];}
function wp_remote_retrieve_body($r){return $r['body'];}
function wp_remote_get($url,$args){
    if ($url!=='https://token.actions.githubusercontent.com/.well-known/jwks') {
        throw new Exception('Unexpected JWKS location');
    }
    return array('code'=>200,'body'=>json_encode($GLOBALS['oidc_jwks']));
}
require __DIR__.'/../src/class-grec-github-oidc.php';
function check($x,$msg) {
    if (!$x) throw new Exception("FAIL: ".$msg);
    echo "PASS: ".$msg.PHP_EOL;
}
$private=openssl_pkey_new(array('private_key_bits'=>2048,'private_key_type'=>OPENSSL_KEYTYPE_RSA));
$csr=openssl_csr_new(array('CN'=>'GitHub mock JWKS local test'),$private);
$cert=openssl_csr_sign($csr,null,$private,2,array('digest_alg'=>'sha256'));
openssl_x509_export($cert,$certpem);
$x5c=preg_replace('/[^A-Za-z0-9+\/=]/','',str_replace(
    array('-----BEGIN CERTIFICATE-----','-----END CERTIFICATE-----'),'', $certpem));
$GLOBALS['oidc_jwks']=array('keys'=>array(array(
    'kid'=>'local-test-key','kty'=>'RSA','use'=>'sig','x5c'=>array($x5c))));
function b64url($value){return rtrim(strtr(base64_encode($value),'+/','-_'),'=');}
$base=array(
 'iss'=>'https://token.actions.githubusercontent.com',
 'aud'=>'mokshagoa.com/private-reel-ingest-v1',
 'repository'=>'karanzing1992/engagement-core',
 'repository_id'=>'1403281267',
 'ref'=>'refs/heads/main',
 'workflow_ref'=>'karanzing1992/engagement-core/.github/workflows/media-ingest-worker.yml@refs/heads/main',
 'event_name'=>'workflow_dispatch',
 'exp'=>time()+300,'iat'=>time(),'nbf'=>time()-10,
);
function issue_token($claims,$private){
    $header=b64url(json_encode(array('alg'=>'RS256','kid'=>'local-test-key','typ'=>'JWT')));
    $body=b64url(json_encode($claims));
    openssl_sign($header.'.'.$body,$sig,$private,OPENSSL_ALGO_SHA256);
    return $header.'.'.$body.'.'.b64url($sig);
}
check(GREC_GitHub_Reel_OIDC::allowed(new FakeReq(issue_token($base,$private))),
      'RS256 signed, scoped GitHub workflow JWT accepted');
$bad=$base;$bad['aud']='other-site';
check(!GREC_GitHub_Reel_OIDC::allowed(new FakeReq(issue_token($bad,$private))),'Wrong audience rejected');
$bad=$base;$bad['repository_id']='999';
check(!GREC_GitHub_Reel_OIDC::allowed(new FakeReq(issue_token($bad,$private))),'Wrong repository id rejected');
$bad=$base;$bad['workflow_ref']='karanzing1992/engagement-core/.github/workflows/ci.yml@refs/heads/main';
check(!GREC_GitHub_Reel_OIDC::allowed(new FakeReq(issue_token($bad,$private))),'Wrong workflow rejected');
$bad=$base;$bad['ref']='refs/heads/feature/reel';
check(!GREC_GitHub_Reel_OIDC::allowed(new FakeReq(issue_token($bad,$private))),'Wrong branch rejected');
$bad=$base;$bad['event_name']='pull_request';
check(!GREC_GitHub_Reel_OIDC::allowed(new FakeReq(issue_token($bad,$private))),'Pull requests rejected');
$bad=$base;$bad['exp']=time()-60;
check(!GREC_GitHub_Reel_OIDC::allowed(new FakeReq(issue_token($bad,$private))),'Expired token rejected');
$bad=$base;$bad['iat']=time()-3600;
check(!GREC_GitHub_Reel_OIDC::allowed(new FakeReq(issue_token($bad,$private))),'Stale token rejected');
$bad=$base;$bad['exp']=time()+40000;
check(!GREC_GitHub_Reel_OIDC::allowed(new FakeReq(issue_token($bad,$private))),'Implausibly long token refused');
$jwt=issue_token($base,$private);
$pieces=explode('.',$jwt);$pieces[2]=b64url(random_bytes(256));
check(!GREC_GitHub_Reel_OIDC::allowed(new FakeReq(implode('.',$pieces))),'Tampered signature rejected');
check(!GREC_GitHub_Reel_OIDC::allowed(new FakeReq('not.a.jwt')),'Malformed JWT rejected');
echo "ALL OIDC TESTS PASSED".PHP_EOL;
