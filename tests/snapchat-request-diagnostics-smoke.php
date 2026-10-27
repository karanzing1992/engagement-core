<?php
// Standalone safe-response and stage-context smoke tests. No Snap token or real network.
define( 'ABSPATH', __DIR__ );
final class GREC_Secrets {
    public static function open( $cipher ) {
        return array(
            'access_token' => 'FAKE_TEST_ACCESS_TOKEN_NOT_A_REAL_SECRET',
            'refresh_token' => 'FAKE_TEST_REFRESH_TOKEN',
            'expires_at' => time() + 3600,
        );
    }
}
function get_option( $key, $fallback = null ) {
    return 'grec_snap_public_secret' === $key ? 'encrypted_test_fixture' : $fallback;
}
function sanitize_key( $value ) {
    return preg_replace( '/[^a-z0-9_-]/', '', strtolower( (string) $value ) );
}
function sanitize_text_field( $value ) { return trim( strip_tags( (string) $value ) ); }
function wp_json_encode( $value ) { return json_encode( $value ); }
function is_wp_error( $value ) { return false; }
function wp_remote_request( $url, $args ) {
    $GLOBALS['snap_test_requests']++;
    return $GLOBALS['snap_test_response'];
}
function wp_remote_retrieve_response_code( $response ) { return $response['status']; }
function wp_remote_retrieve_body( $response ) { return $response['body']; }
function wp_remote_retrieve_header( $response, $name ) {
    return $response['headers'][strtolower( $name )] ?? '';
}
require_once dirname( __DIR__ ) . '/src/class-grec-snap-public-api.php';
$method = new ReflectionMethod( 'GREC_Snap_Public_API', 'request' );
$method->setAccessible( true );
$GLOBALS['snap_test_requests'] = 0;
$failures = array();
$tests = 0;
function prepare_snap_response( $status, $body, $content_type, $headers = array() ) {
    $GLOBALS['snap_test_response'] = array(
        'status' => $status,
        'body' => $body,
        'headers' => array_merge( array( 'content-type' => $content_type ), $headers ),
    );
}
function snap_call( $method, $stage, $path = '/v1/public_profiles/profileid/media', $body = array( 'type' => 'VIDEO' ), $content_type = 'application/json' ) {
    return $method->invoke( null, 'POST', $path, $body, $content_type, $stage );
}
function expect_snap_error( $method, $stage, $required, $forbidden = array(), $path = '/v1/public_profiles/profileid/media', $body = array( 'type' => 'VIDEO' ), $content_type = 'application/json' ) {
    global $failures, $tests;
    ++$tests;
    try {
        snap_call( $method, $stage, $path, $body, $content_type );
        $failures[] = $stage . ': should have thrown';
    } catch ( RuntimeException $e ) {
        $message = $e->getMessage();
        foreach ( $required as $fragment ) {
            if ( false === strpos( $message, $fragment ) ) {
                $failures[] = $stage . ': missing ' . $fragment . ' in ' . $message;
            }
        }
        foreach ( $forbidden as $fragment ) {
            if ( false !== strpos( $message, $fragment ) ) {
                $failures[] = $stage . ': leaked a prohibited response fragment';
            }
        }
    }
}
prepare_snap_response( 403, '<html>PRIVATE_RESPONSE_BODY_DO_NOT_LOG</html>', 'text/html; charset=utf-8', array( 'x-request-id' => 'req-test-123' ) );
expect_snap_error( $method, 'media_create', array( 'media_create', 'HTTP 403', 'non-JSON response', 'text/html', 'req-test-123' ), array( 'PRIVATE_RESPONSE_BODY_DO_NOT_LOG', 'FAKE_TEST_ACCESS_TOKEN' ) );

prepare_snap_response( 403, json_encode( array( 'request_status' => 'ERROR', 'error_code' => 'AUTHORIZATION_PERMISSION_DENIED', 'request_id' => 'snap-ref-22' ) ), 'application/json' );
expect_snap_error( $method, 'story_submit', array( 'story_submit', 'HTTP 403', 'AUTHORIZATION_PERMISSION_DENIED', 'snap-ref-22' ), array( 'FAKE_TEST_REFRESH_TOKEN' ) );

prepare_snap_response( 200, json_encode( array( 'request_status' => 'ERROR', 'error_code' => 'UPSTREAM_PARTIAL_FAILURE' ) ), 'application/json' );
expect_snap_error( $method, 'media_finalize', array( 'media_finalize', 'HTTP 200', 'UPSTREAM_PARTIAL_FAILURE' ) );

prepare_snap_response( 503, 'gateway upstream not ready', 'text/plain' );
expect_snap_error( $method, 'media_add', array( 'media_add', 'HTTP 503', 'non-JSON response' ), array( 'gateway upstream not ready' ), '/us/v1/public_profiles/pid/media/mid/multipart-upload', 'encrypted bytes fixture', 'multipart/form-data; boundary=TEST' );

prepare_snap_response( 200, 'not JSON', 'text/plain' );
expect_snap_error( $method, 'spotlight_submit', array( 'spotlight_submit', 'HTTP 200', 'non-JSON response' ), array( 'not JSON' ) );

prepare_snap_response( 201, json_encode( array( 'request_status' => 'SUCCESS', 'media_id' => 'test-media-id' ) ), 'application/json' );
++$tests;
try {
    $data = snap_call( $method, 'media_create' );
    if ( 'test-media-id' !== ( $data['media_id'] ?? '' ) ) { $failures[] = 'media_create: lost successful response'; }
} catch ( Throwable $e ) { $failures[] = 'media_create: valid success rejected'; }

++$tests;
$count_before = $GLOBALS['snap_test_requests'];
try {
    snap_call( $method, 'media_create', '/v1/private_url/should_not_be_allowed' );
    $failures[] = 'unsafe path was accepted';
} catch ( InvalidArgumentException $e ) {
    if ( $GLOBALS['snap_test_requests'] !== $count_before ) {
        $failures[] = 'unsafe request reached network stub';
    }
}
if ( $failures ) {
    fwrite( STDERR, implode( PHP_EOL, $failures ) . PHP_EOL );
    exit( 1 );
}
echo 'Snapchat request diagnostics: ' . $tests . ' tests PASS' . PHP_EOL;
