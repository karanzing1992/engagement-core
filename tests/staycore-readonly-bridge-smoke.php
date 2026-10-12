<?php
// Run directly: php tests/staycore-readonly-bridge-smoke.php
// Self-contained, synthetic records only. No WordPress database or live site access.
declare(strict_types=1);
define('ABSPATH', '/mock/');
define('STAYCORE_PMS_VERSION', '0.8.6');
$GLOBALS['allow_staycore_admin'] = true;
function current_user_can($cap) { return $cap === 'manage_options' && $GLOBALS['allow_staycore_admin']; }
function sanitize_text_field($s) { return strip_tags((string) $s); }
function sanitize_key($s) { return strtolower(preg_replace('/[^a-z0-9_\-]/i', '', (string) $s)); }
function get_option($name, $default = '') { return $name === 'staycore_pms_db_version' ? '0.8.6' : $default; }
function wp_get_environment_type() { return 'staging'; }
function rest_url($path) { return 'https://staging.invalid/wp-json/' . $path; }
class WP_Error {
    public $code;
    public function __construct($code, $message, $data = []) { $this->code = $code; }
}
function is_wp_error($x) { return $x instanceof WP_Error; }
class StayCore_DB {
    public static function tables(): array {
        $out = [];
        foreach (['units', 'guests', 'reservations', 'reservation_units',
                  'reservation_guests', 'payments', 'tasks', 'activity'] as $t) {
            $out[$t] = 'wp_staycore_' . $t;
        }
        return $out;
    }
}
class MockWpdb {
    public function prepare($sql, ...$values) {
        foreach ($values as $v) $sql = preg_replace('/%s/', "'" . addslashes($v) . "'", $sql, 1);
        return $sql;
    }
    public function get_var($sql) {
        if (strpos($sql, 'SHOW TABLES LIKE') !== false) {
            preg_match("/LIKE '([^']+)'/", $sql, $match);
            return $match[1] ?? null;
        }
        return 3;
    }
    public function get_results($query, $type = null) {
        return [
            ['id' => 1, 'name' => 'Bed A', 'type' => 'bed', 'room_group' => 'Room 8',
             'capacity' => 1, 'base_rate' => 500, 'status' => 'available', 'housekeeping_status' => 'clean'],
            ['id' => 2, 'name' => 'Bed B', 'type' => 'bed', 'room_group' => 'Room 8',
             'capacity' => 1, 'base_rate' => 500, 'status' => 'available', 'housekeeping_status' => 'dirty'],
            ['id' => 3, 'name' => 'Private', 'type' => 'private', 'room_group' => 'Room 12',
             'capacity' => 4, 'base_rate' => 2400, 'status' => 'maintenance', 'housekeeping_status' => 'clean'],
        ];
    }
    public function get_col($query) { return [2]; }
}
define('ARRAY_A', 'ARRAY_A');
$GLOBALS['wpdb'] = new MockWpdb();
require dirname(__DIR__) . '/product/wordpress-control/src/class-wp-control-bridge.php';
$call = new ReflectionMethod('WPControl_Bridge', 'staycore_readonly');
function check($condition, $message) {
    if (!$condition) { fwrite(STDERR, "FAIL: " . $message . PHP_EOL); exit(1); }
}
$health = $call->invoke(null, 'staycore_diagnostics', []);
check(is_array($health) && $health['version'] === '0.8.6', 'health version');
check($health['table_counts']['reservations'] === 3, 'aggregate count');
$inv = $call->invoke(null, 'staycore_inventory_check', []);
check(count($inv['units']) === 3, 'inventory count');
check(!array_key_exists('guest', $inv) && !array_key_exists('phone', $inv['units'][0]), 'no guest info');
$valid = $call->invoke(null, 'staycore_availability_check', ['from'=>'2026-10-13', 'to'=>'2026-10-15']);
check($valid['available_unit_ids'] === [1] && $valid['occupied_unit_count'] === 1, 'date overlap');
foreach ([['from'=>'2026-10-15','to'=>'2026-10-13'],
          ['from'=>'2026-02-30','to'=>'2026-03-02'],
          ['from'=>'2026-10-13','to'=>'2026-11-30']] as $args) {
    $error = $call->invoke(null, 'staycore_availability_check', $args);
    check(is_wp_error($error) && $error->code === 'staycore_invalid_dates', 'invalid dates denied');
}
$GLOBALS['allow_staycore_admin'] = false;
$denied = $call->invoke(null, 'staycore_inventory_check', []);
check(is_wp_error($denied) && $denied->code === 'staycore_forbidden', 'non-admin denied');
echo "StayCore read-only bridge synthetic smoke PASS" . PHP_EOL;
