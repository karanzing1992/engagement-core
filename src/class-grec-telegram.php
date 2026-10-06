<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class GREC_Telegram {
 public static function credentials(): array {
  return GREC_Secrets::open( (string) get_option( 'grec_telegram_credentials', '' ) );
 }
 public static function is_connected(): bool {
  $c=self::credentials(); return ! empty($c['token']) && ! empty(get_option('grec_telegram_chat_id',''));
 }
 public static function save_token( string $token ): void {
  update_option('grec_telegram_credentials', GREC_Secrets::seal(array('token'=>trim($token))), false);
 }
 public static function send( string $text, string $media_url='' ): array {
  $c=self::credentials(); $chat=(string)get_option('grec_telegram_chat_id','');
  if(empty($c['token'])||''===$chat){ throw new RuntimeException('Telegram is not configured.'); }
  $method=$media_url ? 'sendVideo' : 'sendMessage';
  $body=array('chat_id'=>$chat);
  if($media_url){ $body['video']=$media_url; $body['caption']=mb_substr($text,0,1024); $body['supports_streaming']='true'; }
  else { $body['text']=$text; }
  $r=wp_remote_post('https://api.telegram.org/bot'.rawurlencode($c['token']).'/'.$method,array('timeout'=>60,'body'=>$body));
  if(is_wp_error($r)){ throw new RuntimeException($r->get_error_message()); }
  $data=json_decode(wp_remote_retrieve_body($r),true);
  if(wp_remote_retrieve_response_code($r)>=300 || empty($data['ok'])){ throw new RuntimeException('Telegram rejected publish: '.wp_json_encode($data)); }
  update_option('grec_telegram_last_publish',array('at'=>time(),'message_id'=>$data['result']['message_id']??null),false);
  return $data;
 }
}
