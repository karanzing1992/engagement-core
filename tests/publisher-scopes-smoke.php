<?php
/**
 * Regression for scope names with periods, e.g. snapchat.publish.
 * PHP CLI smoke test without a WordPress installation.
 */
define( 'ABSPATH', __DIR__ );
$GLOBALS['test_options'] = array();
function get_option( $name, $default = false ) {
    return $GLOBALS['test_options'][ $name ] ?? $default;
}
require_once dirname( __DIR__ ) . '/src/class-grec-publisher-rest.php';

$defaults = GREC_Publisher_REST::machine_scopes();
if ( ! in_array( 'snapchat.publish', $defaults, true ) ) {
    fwrite( STDERR, 'FAIL: new Snapchat permission is absent from defaults.' . PHP_EOL );
    exit( 1 );
}
$GLOBALS['test_options']['grec_publish_key_scopes'] = array(
    'snapchat.publish', 'telegram.publish', ' vk.status ', 'snapchat.publish', 'unsafe scope'
);
$scopes = GREC_Publisher_REST::machine_scopes();
$expected = array( 'snapchat.publish', 'telegram.publish', 'vk.status' );
if ( $scopes !== $expected ) {
    fwrite( STDERR, 'FAIL: machine permission scopes lost punctuation or included invalid values.' . PHP_EOL );
    exit( 1 );
}
echo "Dot-separated publisher permission scope smoke tests PASS\n";
