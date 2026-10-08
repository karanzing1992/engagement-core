<?php
// Standalone regression: remotely imported MP4 with missing WordPress video metadata.
define( 'ABSPATH', __DIR__ );
final class GREC_Snapchat {}
$GLOBALS['video_metadata'] = array( 'filesize' => 16828548 );
$GLOBALS['video_saved'] = null;
function get_post_type( $id ) { return 13080 === $id ? 'attachment' : 'post'; }
function get_attached_file( $id ) { return $GLOBALS['video_test_file']; }
function get_post_mime_type( $id ) { return 'video/mp4'; }
function wp_get_attachment_metadata( $id ) { return $GLOBALS['video_metadata']; }
function wp_read_video_metadata( $path ) { return $GLOBALS['video_parsed']; }
function wp_update_attachment_metadata( $id, $metadata ) { $GLOBALS['video_saved'] = $metadata; return true; }
function absint( $v ) { return abs( (int) $v ); }
require_once dirname( __DIR__ ) . '/src/class-grec-snap-public-api.php';
$tmp = tempnam( sys_get_temp_dir(), 'snap-mp4' );
$GLOBALS['video_test_file'] = $tmp;
file_put_contents( $tmp, str_repeat( 'm', 2000 ) );
$method = new ReflectionMethod( 'GREC_Snap_Public_API', 'media_attachment' );
$method->setAccessible( true );
try {
    $GLOBALS['video_parsed'] = array( 'length' => 30.0, 'width' => 1080, 'height' => 1920 );
    $valid = $method->invoke( null, 13080, 'story' );
    if ( 'VIDEO' !== $valid['type'] || (int) ( $GLOBALS['video_saved']['width'] ?? 0 ) !== 1080 ||
        (float) ( $GLOBALS['video_saved']['length'] ?? 0 ) !== 30.0 ) {
        throw new RuntimeException( 'Metadata import fallback failed.' );
    }
    $GLOBALS['video_metadata'] = array( 'filesize' => 2000 );
    $GLOBALS['video_parsed'] = array( 'length' => 120, 'width' => 1080, 'height' => 1920 );
    try {
        $method->invoke( null, 13080, 'story' );
        throw new RuntimeException( 'Rejected 120-second video was allowed.' );
    } catch ( InvalidArgumentException $e ) {
        if ( strpos( $e->getMessage(), '5–60' ) === false ) { throw $e; }
    }
    $GLOBALS['video_metadata'] = array( 'filesize' => 2000 );
    $GLOBALS['video_parsed'] = array( 'length' => 30, 'width' => 100, 'height' => 1920 );
    try {
        $method->invoke( null, 13080, 'story' );
        throw new RuntimeException( 'Rejected low-resolution video was allowed.' );
    } catch ( InvalidArgumentException $e ) {
        if ( strpos( $e->getMessage(), '540 x 960' ) === false ) { throw $e; }
    }
    echo "Snapchat imported MP4 metadata and validation smoke tests PASS\n";
} finally { @unlink( $tmp ); }
