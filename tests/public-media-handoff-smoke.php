<?php
/* Narrow offline signature / scope regression tests; no live WordPress or secrets. */
define( 'ABSPATH', '/nonexistent-wordpress-test/' );
class WP_Error {
    public $code;
    public function __construct($code, $message, $data = array()) { $this->code = $code; }
}
class WP_REST_Response {
    public $data;
    public function __construct($data, $status = 200) { $this->data = $data; }
}
function rest_ensure_response($value) { return new WP_REST_Response($value); }
function add_action() {}
function register_rest_route() {}
function home_url() { return 'https://mokshagoa.com/'; }
function wp_parse_url($url, $part = -1) { return parse_url($url, $part); }
$GLOBALS['opts'] = array();
$GLOBALS['transients'] = array();
function get_option($name, $default = false) { return $GLOBALS['opts'][$name] ?? $default; }
function add_option($name, $value, $deprecated = '', $autoload = false) {
    if (array_key_exists($name, $GLOBALS['opts'])) { return false; }
    $GLOBALS['opts'][$name] = $value; return true;
}
function delete_option($name) { unset($GLOBALS['opts'][$name]); return true; }
function wp_schedule_single_event($when, $hook, $args = array()) { return true; }
require dirname(__DIR__) . '/src/class-grec-public-media-handoff.php';
function check($truth, $label) {
    if (!$truth) { fwrite(STDERR, 'FAIL: ' . $label . PHP_EOL); exit(1); }
    echo 'PASS: ' . $label . PHP_EOL;
}
class StubRequest {
    private $body;
    private $route;
    private $headers;
    public function __construct($body, $route, $headers) {
        $this->body = $body; $this->route = $route; $this->headers = $headers;
    }
    public function get_body() { return $this->body; }
    public function get_method() { return 'POST'; }
    public function get_route() { return $this->route; }
    public function get_header($name) { return $this->headers[$name] ?? ''; }
}
$path = '/wp-control/v1/media-handoff/start';
$request = new StubRequest('{}', $path, array());
check(GREC_Public_Media_Handoff::authorize($request) instanceof WP_Error, 'disabled by default');
if (!function_exists('sodium_crypto_sign_keypair')) {
    echo 'SKIP: sodium not installed in isolated PHP runtime' . PHP_EOL;
    exit(0);
}
$keypair = sodium_crypto_sign_keypair();
$private = sodium_crypto_sign_secretkey($keypair);
$public = sodium_crypto_sign_publickey($keypair);
$GLOBALS['opts']['grec_public_media_enabled'] = '1';
$GLOBALS['opts']['grec_public_media_ed25519_key'] = base64_encode($public);
$GLOBALS['opts']['grec_public_media_site_host'] = 'another-domain.com';
check(GREC_Public_Media_Handoff::authorize($request) instanceof WP_Error, 'site host binding enforced');
$GLOBALS['opts']['grec_public_media_site_host'] = 'mokshagoa.com';
function signed_request($private, $path, $body, $timestamp, $nonce) {
    $canonical = "POST\n" . $path . "\n" . $timestamp . "\n" . $nonce . "\n"
        . hash('sha256', $body) . "\nmokshagoa.com";
    return new StubRequest($body, $path, array(
        'X-GREC-Time' => $timestamp,
        'X-GREC-Nonce' => $nonce,
        'X-GREC-Signature' => base64_encode(sodium_crypto_sign_detached($canonical, $private)),
    ));
}
$ts = (string) time();
$valid = signed_request($private, $path, '{"one":1}', $ts, str_repeat('a', 32));
check(GREC_Public_Media_Handoff::authorize($valid) === true, 'valid Ed25519 manifest accepted');
$replay = GREC_Public_Media_Handoff::authorize($valid);
check($replay instanceof WP_Error && $replay->code === 'grec_handoff_replay', 'signed replay rejected');
$tampered = signed_request($private, $path, '{"one":1}', $ts, str_repeat('b', 32));
$tampered = new StubRequest('{"one":2}', $path, array(
    'X-GREC-Time' => $ts, 'X-GREC-Nonce' => str_repeat('b', 32),
    'X-GREC-Signature' => $tampered->get_header('X-GREC-Signature'),
));
check(GREC_Public_Media_Handoff::authorize($tampered) instanceof WP_Error, 'payload mutation rejected');
$expired = signed_request($private, $path, '{}', (string)(time() - 400), str_repeat('c', 32));
check(GREC_Public_Media_Handoff::authorize($expired) instanceof WP_Error, 'expired signature rejected');
$oversize = signed_request($private, $path, str_repeat('z', 4194305), $ts, str_repeat('d', 32));
check(GREC_Public_Media_Handoff::authorize($oversize) instanceof WP_Error, 'overlarge chunk rejected');
check(GREC_Public_Media_Handoff::health()->data['enabled'] === true, 'enabled health is read-only');
