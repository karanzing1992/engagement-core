<?php
/**
 * Pure, zero-network safety checks for the direct GSC adapter.
 * No WordPress bootstrap, OAuth credentials or calls to Google.
 */
define( 'ABSPATH', __DIR__ );
function trailingslashit( $v ) { return rtrim( $v, '/' ) . '/'; }
function home_url( $v = '/' ) { return 'https://mokshagoa.com' . $v; }
function wp_parse_url( $url ) { return parse_url( $url ); }
function get_option( $name, $default = false ) { return $default; }
function wp_next_scheduled( $hook ) { return false; }
class GREC_Secrets {
    public static function open( string $value ): array { return array(); }
}
require dirname( __DIR__ ) . '/src/class-grec-search-console.php';
function check_gsc( bool $condition, string $label ): void {
    if ( ! $condition ) { fwrite( STDERR, 'FAIL: ' . $label . PHP_EOL ); exit( 1 ); }
}
check_gsc( GREC_Search_Console::property() === 'https://mokshagoa.com/', 'Canonical property' );
check_gsc( GREC_Search_Console::allowed_local_url( 'https://mokshagoa.com/mud-bath-goa/' ), 'Permits the local canonical landing page' );
foreach ( array(
    'https://mokshagoa.com.evil.tld/path/',
    'https://attacker.tld/mud-bath-goa/',
    'http://mokshagoa.com/mud-bath-goa/',
    'https://mokshagoa.com:8080/mud-bath-goa/',
    'https://user:pass@mokshagoa.com/mud-bath-goa/',
    'https://mokshagoa.com@attacker.tld/mud-bath-goa/',
) as $bad ) { check_gsc( ! GREC_Search_Console::allowed_local_url( $bad ), 'Blocks foreign/unsafe URL ' . $bad ); }
$status = GREC_Search_Console::status();
check_gsc( $status['connected'] === false, 'Disconnected by default' );
check_gsc( $status['oauth_client_configured'] === false, 'OAuth app must be explicitly configured' );
check_gsc( ! isset( $status['refresh_token'] ), 'Secrets never exposed in status' );
$report = GREC_Search_Console::report_ability( array( 'dimension' => 'query' ) );
check_gsc( $report['ok'] === false, 'Unconnected report fails closed' );
$invalid = GREC_Search_Console::report_ability( array( 'dimension' => 'externals' ) );
check_gsc( $invalid['ok'] === false, 'Unsupported report dimensions fail closed' );
echo "GSC safety smoke PASS: strict property, credentials withheld, disconnected fail-closed, no HTTP calls.\n";
