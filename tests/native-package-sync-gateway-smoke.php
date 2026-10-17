<?php
/**
 * No-network source contract for the existing WP Control > Engagement Core
 * > Deployer for Git capability. Does NOT attempt sync/backup/WordPress login.
 */
declare(strict_types=1);
$root = dirname(__DIR__);
$wp = file_get_contents($root . '/src/class-grec-wp-control.php');
$edge = file_get_contents($root . '/product/gateway/supabase/functions/wpcontrol-mcp/lib/server.ts');
if ($wp === false || $edge === false) {
    fwrite(STDERR, "Cannot read bridge sources\n");
    exit(1);
}
$checks = [
    'existing registered package-list ability' => strpos($wp, "'wp-control/package-list'") !== false,
    'existing registered package-sync ability' => strpos($wp, "'wp-control/package-sync'") !== false,
    'WordPress gateway package-list action' => strpos($wp, "case 'package_list': return self::package_list();") !== false,
    'WordPress gateway package-sync action' => strpos($wp, "case 'package_sync':") !== false,
    'explicit true confirmation on gateway sync' => strpos($wp, "true !== ( \$input['confirm'] ?? false )") !== false,
    'reject wrong active theme' => strpos($wp, "\$package !== get_stylesheet()") !== false,
    'require branch and repository source lock' => strpos($wp, "'wp_control_sync_source_mismatch'") !== false,
    'reuse existing DFG authorization' => strpos($wp, 'return self::package_sync( $input );') !== false,
    'existing DFG allowlist' => strpos($wp, "'wp_control_package_not_configured'") !== false,
    'read-only typed package discovery tool' => strpos($edge, "'list_git_packages'") !== false,
    'destructive sync tool' => strpos($edge, "'sync_git_package'") !== false,
    'typed source confirmation' => strpos($edge, 'confirm: z.literal(true)') !== false,
    'exact target branch input' => strpos($edge, 'expected_branch: z.string()') !== false,
    'exact repository URL input' => strpos($edge, 'expected_repo_url: z.string().url()') !== false,
];
foreach ($checks as $name => $pass) {
    echo ($pass ? 'PASS ' : 'FAIL ') . $name . "\n";
    if (!$pass) exit(1);
}
echo 'PACKAGE_SYNC_BRIDGE_PREFLIGHT=PASS' . "\n";
