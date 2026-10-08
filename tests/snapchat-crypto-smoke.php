<?php
// Standalone smoke test of the streaming AES-256-CBC uploader; no WordPress database required.
// Run: php tests/snapchat-crypto-smoke.php
define( 'ABSPATH', __DIR__ );
require_once dirname( __DIR__ ) . '/src/class-grec-snap-public-api.php';
$method = new ReflectionMethod( 'GREC_Snap_Public_API', 'encrypt_media' );
$method->setAccessible( true );
foreach ( array( 1, 15, 16, 17, 1024 * 1024 + 37, 2 * 1024 * 1024 + 16 ) as $size ) {
    $in = tempnam( sys_get_temp_dir(), 'snapin' );
    $out = tempnam( sys_get_temp_dir(), 'snapout' );
    $plain = random_bytes( $size );
    file_put_contents( $in, $plain );
    $key = random_bytes( 32 );
    $iv = random_bytes( 16 );
    try {
        $method->invoke( null, $in, $out, $key, $iv );
        $decoded = openssl_decrypt( file_get_contents( $out ), 'aes-256-cbc', $key, OPENSSL_RAW_DATA, $iv );
        if ( $decoded !== $plain ) {
            fwrite( STDERR, 'FAIL at size ' . $size . PHP_EOL );
            exit( 1 );
        }
    } finally {
        @unlink( $in );
        @unlink( $out );
    }
}
echo "Snapchat AES-256-CBC media encryption smoke tests PASS\n";
