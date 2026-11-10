/** META CORE Lane A: synthetic-only MCP inventory. This exports NO live runtime. */
const s=(maxLength=256,minLength=1)=>({type:'string',minLength,maxLength});
const i=(maximum=100)=>({type:'integer',minimum:1,maximum});
const e=(...values)=>({type:'string',enum:values});
const a=(items,maxItems=10)=>({type:'array',items,minItems:1,maxItems});
const o=(properties,required=Object.keys(properties))=>({type:'object',properties,required,additionalProperties:false});
const id={type:'string',pattern:'^[0-9]{6,64}$',maxLength:64};
const to={type:'string',pattern:'^\\+[1-9][0-9]{6,14}$',maxLength:16};
const wamid={type:'string',pattern:'^wamid\\.[A-Za-z0-9._:-]{4,256}$',maxLength:262};
const url={type:'string',pattern:'^https://[^/?#@\\s]+(?:/[^#\\s]*)?$',maxLength:2048};
const lang={type:'string',pattern:'^[a-z]{2,3}_[A-Z]{2}$',maxLength:6};
const cursor={type:'string',pattern:'^[A-Za-z0-9_-]{1,256}$',maxLength:256};
const component=o({type:e('HEADER','BODY','FOOTER','BUTTONS'),text:s(1024),format:e('TEXT','IMAGE','VIDEO','DOCUMENT')},['type']);
const fields={
  to,body:s(4096),previewUrl:{type:'boolean'},replyTo:wamid,link:url,id,caption:s(1024),
  filename:s(255),latitude:{type:'number',minimum:-90,maximum:90},longitude:{type:'number',minimum:-180,maximum:180},
  name:s(512),address:s(1024),contacts:a(o({name:s(256),phone:to}),10),
  buttons:a(o({id:s(200),title:s(20)}),3),button:s(20),
  sections:a(o({title:s(128),rows:a(o({id:s(200),title:s(24)}),10)}),10),
  header:s(128),footer:s(60),language:lang,components:a(component,15),
  category:e('MARKETING','UTILITY','AUTHENTICATION'),limit:i(),after:cursor,before:cursor,
  templateId:id,otp:s(15),otpButtonIndex:s(2),bodyParameters:a(s(512),10),
  cards:a(o({mediaId:id}),10),messageId:wamid,emoji:s(12,0),typing:{type:'boolean'},
  status:e('APPROVED','PENDING','REJECTED','PAUSED','DISABLED'),mediaId:id,sourceUrl:url,mimeType:s(120),
  flowId:id,flowToken:s(256),flowCta:s(30),
  categories:a(e('SIGN_UP','SIGN_IN','APPOINTMENT_BOOKING','LEAD_GENERATION','CONTACT_US','CUSTOMER_SUPPORT','SURVEY','OTHER'),8),
  flowJson:s(16384),endpointUri:url,catalogId:id,productRetailerId:s(100),
  productRetailerIds:a(s(100),30),qrId:id,prefilledMessage:s(256),
  startDate:s(20),endDate:s(20),description:s(1024),website:url,email:s(256),
  about:s(139),vertical:s(100),commerceEnabled:{type:'boolean'}
};
const DATA = "whatsapp_get_business_account|account|read|management|host||\nwhatsapp_list_phone_numbers|account|read|management|host|limit,after|\nwhatsapp_get_phone_number|account|read|management|host||\nwhatsapp_get_quality_metrics|account|read|management|host||\nwhatsapp_get_business_profile|account|read|messaging|host||\nwhatsapp_update_business_profile|account|write|messaging|host|about,description,website,email,address,vertical|\nwhatsapp_get_commerce_settings|commerce|read|management|host||\nwhatsapp_update_commerce_settings|commerce|write|management|host|commerceEnabled|commerceEnabled\nwhatsapp_get_subscription_status|account|read|management|host||\nwhatsapp_send_text|messages|send_window|messaging|dojo|to,body,previewUrl,replyTo|to,body\nwhatsapp_send_image|messages|send_window|messaging|dojo|to,link,id,caption,replyTo|to\nwhatsapp_send_video|messages|send_window|messaging|dojo|to,link,id,caption,replyTo|to\nwhatsapp_send_audio|messages|send_window|messaging|dojo|to,link,id,replyTo|to\nwhatsapp_send_voice|messages|send_window|messaging|dojo|to,link,id,replyTo|to\nwhatsapp_send_document|messages|send_window|messaging|dojo|to,link,id,caption,filename,replyTo|to\nwhatsapp_send_location|messages|send_window|messaging|dojo|to,latitude,longitude,name,address|to,latitude,longitude\nwhatsapp_send_contacts|messages|send_window|messaging|dojo|to,contacts|to,contacts\nwhatsapp_send_interactive_buttons|messages|send_window|messaging|dojo|to,body,buttons,header,footer|to,body,buttons\nwhatsapp_send_interactive_list|messages|send_window|messaging|dojo|to,body,button,sections,header,footer|to,body,button,sections\nwhatsapp_send_template|messages|send_template|messaging|dojo|to,name,language,components,replyTo|to,name,language\nwhatsapp_send_auth_template|messages|send_template|messaging|dojo|to,name,language,otp,otpButtonIndex|to,name,language,otp\nwhatsapp_send_carousel_template|messages|send_template|messaging|dojo|to,name,language,bodyParameters,cards|to,name,language,cards\nwhatsapp_send_reaction|messages|send_window|messaging|dojo|to,messageId,emoji|to,messageId,emoji\nwhatsapp_send_sticker|messages|send_window|messaging|host|to,id,link|to\nwhatsapp_send_product|commerce|send_window|messaging|host|to,catalogId,productRetailerId|to,catalogId,productRetailerId\nwhatsapp_send_multi_product|commerce|send_window|messaging|host|to,catalogId,productRetailerIds|to,catalogId,productRetailerIds\nwhatsapp_send_catalog|commerce|send_window|messaging|host|to,body|to,body\nwhatsapp_send_flow|flows|send_window|messaging|host|to,flowId,flowCta,flowToken,body|to,flowId,flowCta\nwhatsapp_mark_as_read|messages|ack|messaging|dojo|messageId,typing|messageId\nwhatsapp_list_templates|templates|read|management|broker|limit,after|\nwhatsapp_get_template|templates|read|management|broker|templateId|templateId\nwhatsapp_create_template|templates|write|management|host|name,language,category,components|name,language,category,components\nwhatsapp_update_template|templates|write|management|host|templateId,components|templateId,components\nwhatsapp_delete_template|templates|irreversible|management|host|templateId|templateId\nwhatsapp_get_template_analytics|analytics|read|management|host|startDate,endDate|\nwhatsapp_get_business_analytics|analytics|read|management|host|startDate,endDate|\nwhatsapp_upload_media_from_url|media|write|messaging|dojo|sourceUrl,mimeType,filename|sourceUrl,mimeType\nwhatsapp_get_media_info|media|read|messaging|dojo|mediaId|mediaId\nwhatsapp_delete_media|media|irreversible|messaging|host|mediaId|mediaId\nwhatsapp_list_flows|flows|read|management|host|limit,after|\nwhatsapp_get_flow|flows|read|management|host|flowId|flowId\nwhatsapp_get_flow_assets|flows|read|management|host|flowId|flowId\nwhatsapp_get_flow_metrics|flows|read|management|host|flowId|flowId\nwhatsapp_create_flow|flows|write|management|host|name,categories,endpointUri|name,categories\nwhatsapp_update_flow_metadata|flows|write|management|host|flowId,name,categories,endpointUri|flowId\nwhatsapp_upload_flow_json|flows|write|management|host|flowId,flowJson|flowId,flowJson\nwhatsapp_publish_flow|flows|irreversible|management|host|flowId|flowId\nwhatsapp_deprecate_flow|flows|irreversible|management|host|flowId|flowId\nwhatsapp_delete_flow|flows|irreversible|management|host|flowId|flowId\nwhatsapp_list_qr_codes|commerce|read|management|host||\nwhatsapp_create_qr_code|commerce|write|management|host|prefilledMessage|prefilledMessage\nwhatsapp_delete_qr_code|commerce|irreversible|management|host|qrId|qrId\nwhatsapp_get_message_status|events|read|wacrm|wacrm|messageId|messageId\nwhatsapp_list_inbound_events|events|read|wacrm|wacrm|limit,after|\nwhatsapp_get_delivery_status|events|read|wacrm|wacrm|messageId|messageId";
export const WHATSAPP_LANE_A_CATALOG=Object.freeze(DATA.trim().split('\n').map(line=>{
  const [name,group,kind,providerPermission,adapter,keys='',required='']=line.split('|');
  const props=keys?keys.split(','):[];
  const req=required?required.split(','):[];
  if (!/^whatsapp_[a-z0-9_]+$/.test(name)||props.some(x=>!Object.hasOwn(fields,x))||
      req.some(x=>!props.includes(x))) throw new Error('Invalid META CORE catalog row');
  return Object.freeze({
    name,group,kind,providerPermission,adapter,integrationState:'synthetic_contract_only',
    description:'META CORE '+group+' operation '+name+'. Not enabled for live Graph API.',
    inputSchema:Object.freeze({type:'object',properties:Object.fromEntries(props.map(x=>[x,fields[x]])),required:req,additionalProperties:false}),
    annotations:Object.freeze({
      readOnlyHint:kind==='read',destructiveHint:kind==='irreversible',
      idempotentHint:kind==='ack',openWorldHint:false
    })
  });
}));
if(new Set(WHATSAPP_LANE_A_CATALOG.map(x=>x.name)).size!==WHATSAPP_LANE_A_CATALOG.length)
  throw new Error('Duplicate META CORE MCP tool');
export const WHATSAPP_LANE_A_EXCLUDED=Object.freeze([
 'phone_register','phone_deregister','phone_migrate','phone_coexistence_reconfigure',
 'waba_subscribe_app','waba_unsubscribe_app','credit_line_share','account_transfer',
 'business_user_assignment','regional_payments','business_calling','group_management'
]);
