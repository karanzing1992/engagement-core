<?php
defined('ABSPATH') || exit;
/**
 * Standalone, allowlisted WP Control abilities for staging.
 * No dependency on Cowboy MCP. No mutation of booking, guests or payments.
 */
final class WPControl_Native {
    public static function run(string $action,array $input=[]) {
        if (!current_user_can('manage_options')) return new WP_Error('wpcontrol_forbidden','Administrator required',['status'=>403]);
        switch ($action) {
            case 'site_overview':
                global $wp_version;
                return ['site'=>home_url('/'),'wordpress'=>$wp_version,'php'=>PHP_VERSION,'environment'=>wp_get_environment_type(),
                    'rest_pretty_url'=>rest_url('wp/v2/'),'rest_query_url'=>home_url('/?rest_route=/wp/v2/'),
                    'staycore_active'=>class_exists('StayCore_REST'),'staycore_version'=>defined('STAYCORE_PMS_VERSION')?STAYCORE_PMS_VERSION:null];
            case 'list_plugins':
                if (!function_exists('get_plugins')) require_once ABSPATH.'wp-admin/includes/plugin.php';
                $active=(array)get_option('active_plugins',[]);
                $plugins=[];
                foreach(get_plugins() as $file=>$meta){$plugins[]=['file'=>$file,'name'=>$meta['Name'],'version'=>$meta['Version'],'active'=>in_array($file,$active,true)];}
                return $plugins;
            case 'staycore_diagnostics':
                if(!class_exists('StayCore_DB') || !class_exists('StayCore_REST'))return new WP_Error('staycore_missing','StayCore is not active',['status'=>404]);
                global $wpdb;
                $tables=StayCore_DB::tables();
                $counts=[];
                foreach(['units','reservations','guests','payments','reservation_units'] as $key){
                    if(!isset($tables[$key]))continue;
                    $table=$tables[$key];
                    if(!preg_match('/^[a-zA-Z0-9_]+$/',$table))continue;
                    $exists=$wpdb->get_var($wpdb->prepare('SHOW TABLES LIKE %s',$table));
                    $counts[$key]=$exists ? (int)$wpdb->get_var("SELECT COUNT(*) FROM `{$table}`") : null;
                }
                $routes=array_keys(rest_get_server()->get_routes());
                return ['version'=>STAYCORE_PMS_VERSION,'tables'=>$counts,
                    'routes'=>array_values(array_filter($routes,static fn($r)=>str_starts_with($r,'/staycore/v1/'))),
                    'rest_url'=>rest_url('staycore/v1/health'),'query_rest_url'=>home_url('/?rest_route=/staycore/v1/health'),
                    'mutations_enabled'=>false];
            case 'staycore_inventory_check':
                if(!class_exists('StayCore_DB'))return new WP_Error('staycore_missing','StayCore is not active',['status'=>404]);
                global $wpdb;
                $t=StayCore_DB::tables();
                $units=$wpdb->get_results("SELECT id,name,type,room_group,capacity,status,housekeeping_status,base_rate FROM {$t['units']} ORDER BY id LIMIT 250",ARRAY_A);
                return ['units'=>$units,'count'=>count($units),'truncated'=>count($units)>=250];
            case 'staycore_availability_check':
                if(!class_exists('StayCore_DB'))return new WP_Error('staycore_missing','StayCore is not active',['status'=>404]);
                $from=sanitize_text_field($input['from']??'');$to=sanitize_text_field($input['to']??'');
                if(!preg_match('/^\\d{4}-\\d{2}-\\d{2}$/',$from)||!preg_match('/^\\d{4}-\\d{2}-\\d{2}$/',$to)||$from>=$to)return new WP_Error('invalid_date','Valid exclusive check-out date range required',['status'=>400]);
                if((strtotime($to)-strtotime($from))>31*DAY_IN_SECONDS)return new WP_Error('range_too_large','Maximum 31 nights',['status'=>400]);
                global $wpdb;$t=StayCore_DB::tables();
                $sql="SELECT u.id,u.name,u.type,u.room_group,u.status,u.housekeeping_status, COUNT(DISTINCT r.id) conflicts FROM {$t['units']} u LEFT JOIN {$t['reservation_units']} ru ON ru.unit_id=u.id LEFT JOIN {$t['reservations']} r ON r.id=ru.reservation_id AND r.status NOT IN ('cancelled','checked_out') AND r.check_in < %s AND r.check_out > %s GROUP BY u.id,u.name,u.type,u.room_group,u.status,u.housekeeping_status ORDER BY u.id LIMIT 250";
                $rows=$wpdb->get_results($wpdb->prepare($sql,$to.' 00:00:00',$from.' 00:00:00'),ARRAY_A);
                foreach($rows as &$u){$u['available']=($u['status']==='available'&&$u['housekeeping_status']==='clean'&&(int)$u['conflicts']===0);}unset($u);
                return ['from'=>$from,'to'=>$to,'units'=>$rows,'note'=>'Read-only overlap assessment; booking engine remains authoritative.'];
        }
        return new WP_Error('unknown_native_action','Unsupported native action',['status'=>400]);
    }
}
