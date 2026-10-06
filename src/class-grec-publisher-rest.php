<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_Publisher_REST {
 public static function init(): void { add_action('rest_api_init',array(__CLASS__,'routes')); }
 public static function routes(): void {
  register_rest_route('engagement-core/v1','/telegram/config',array('methods'=>'POST','callback'=>array(__CLASS__,'config'),'permission_callback'=>array(__CLASS__,'admin')));
  register_rest_route('engagement-core/v1','/telegram/test',array('methods'=>'POST','callback'=>array(__CLASS__,'test'),'permission_callback'=>array(__CLASS__,'admin')));
  register_rest_route('engagement-core/v1','/telegram/status',array('methods'=>'GET','callback'=>array(__CLASS__,'status'),'permission_callback'=>array(__CLASS__,'admin')));
 }
 public static function admin(): bool { return current_user_can('manage_options'); }
 public static function config(WP_REST_Request $r): WP_REST_Response {
  $token=trim((string)$r->get_param('token')); $chat=sanitize_text_field((string)$r->get_param('chat_id'));
  if($token!==''){ GREC_Telegram::save_token($token); }
  if($chat!==''){ update_option('grec_telegram_chat_id',$chat,false); }
  return new WP_REST_Response(array('connected'=>GREC_Telegram::is_connected(),'chat_id'=>get_option('grec_telegram_chat_id','')),200);
 }
 public static function test(): WP_REST_Response {
  try { $d=GREC_Telegram::send('Publishing connection test ✓'); return new WP_REST_Response(array('ok'=>true,'message_id'=>$d['result']['message_id']??null),200); }
  catch(Throwable $e){ return new WP_REST_Response(array('ok'=>false,'error'=>$e->getMessage()),502); }
 }
 public static function status(): WP_REST_Response {
  return new WP_REST_Response(array('connected'=>GREC_Telegram::is_connected(),'chat_id'=>get_option('grec_telegram_chat_id',''),'last_publish'=>get_option('grec_telegram_last_publish',array())),200);
 }
}
