/**
 * META CORE Lane A: WACRM-bound Graph v26.0 request blueprints.
 *
 * The returned object is NOT an HTTP client. It has no bearer, fetch(),
 * resolver, Graph domain, webhook or outbound queue. An independently
 * authorized WACRM Central runtime owns Graph transport and the credentials.
 * This module is only a deterministic, testable API contract.
 *
 * All tool arguments MUST be prevalidated by the Lane A MCP ingress gate.
 * The route and ownership proof MUST be obtained from trusted WACRM authority,
 * never from MCP arguments or model-provided user claims.
 */
import { WHATSAPP_LANE_A_CATALOG } from './lane-a-capability-catalog.mjs';

const tools=new Map(WHATSAPP_LANE_A_CATALOG.map(x=>[x.name,x]));
const numeric=/^[0-9]{6,64}$/;
const qrCode=/^[A-Za-z0-9_-]{6,128}$/;
const version='v26.0';
const jsonSafe=value=>JSON.parse(JSON.stringify(value));
function refuse(code){const e=new Error('META CORE Graph plan refused');e.code=code;throw e;}
function routeIds(route){
  if(!route||typeof route!=='object'||route.status!=='active'||
      typeof route.tenantId!=='string'||!/^wacrm_[a-f0-9]{40}$/.test(route.tenantId)||
      !Number.isSafeInteger(route.activationId)||route.activationId<1||
      !numeric.test(route.wabaId)||!numeric.test(route.phoneNumberId))
    refuse('route_unavailable');
  return {waba:route.wabaId,phone:route.phoneNumberId};
}
function pathPart(id){if(typeof id!=='string'||!numeric.test(id))refuse('invalid_resource');return id;}
function owned(ownership,key,id){
  if(typeof id!=='string'||!numeric.test(id)||!ownership||ownership[key]!==id||
      ownership.wabaIdVerified!==true)refuse('ownership_unverified');
  return id;
}
const make=(def,method,resourcePath,query={},body=null,encoding='json')=>{
  if(!/^\/v26\.0\/[A-Za-z0-9/_-]+$/.test(resourcePath))
    refuse('invalid_graph_resource');
  if(!['GET','POST','DELETE'].includes(method))refuse('invalid_method');
  if(def.kind==='read'&&method!=='GET')refuse('method_not_allowed');
  const result={toolName:def.name,graphApiVersion:version,method,
    resourcePath,query:jsonSafe(query),body:body===null?null:jsonSafe(body),
    bodyEncoding:encoding,providerPermission:def.providerPermission,
    operationKind:def.kind,
    credentialMode:'wacrm_central_only'};
  if(JSON.stringify(result).length>32768)refuse('plan_too_large');
  return Object.freeze(result);
};
function msg(to,interactive,type='interactive'){
  return {messaging_product:'whatsapp',recipient_type:'individual',to,
    type,[type]:interactive};
}
function expand(a,key){return Object.hasOwn(a,key)?a[key]:undefined;}
function clean(values){return Object.fromEntries(Object.entries(values).filter(([,v])=>v!==undefined));}

/** The supported Graph host-operation names must be reflected in the MCP catalog. */
export const LANE_A_GRAPH_HOST_TOOLS=Object.freeze(
  WHATSAPP_LANE_A_CATALOG.filter(d=>d.adapter==='host').map(d=>d.name));

export function buildWacrmGraphV26Plan({name,args={},route,ownership}={}){
  const def=tools.get(name);
  if(!def||def.adapter!=='host')refuse('not_a_graph_host_tool');
  const {waba,phone}=routeIds(route);
  if(!args||typeof args!=='object'||Array.isArray(args))refuse('invalid_input');
  const w='/v26.0/'+waba,p='/v26.0/'+phone;
  const limited=clean({limit:expand(args,'limit'),after:expand(args,'after')});
  const r=(method,path,query={},body=null,encoding='json')=>
    make(def,method,path,query,body,encoding);
  switch(name){
  case 'whatsapp_get_business_account':
    return r('GET',w,{fields:'id,name,timezone_id,message_template_namespace'});
  case 'whatsapp_list_phone_numbers':
    return r('GET',w+'/phone_numbers',limited);
  case 'whatsapp_get_phone_number':
    return r('GET',p,{fields:'id,display_phone_number,verified_name,quality_rating,code_verification_status'});
  case 'whatsapp_get_quality_metrics':
    return r('GET',p,{fields:'id,quality_rating,messaging_limit_tier,throughput'});
  case 'whatsapp_get_business_profile':
    return r('GET',p+'/whatsapp_business_profile',
      {fields:'about,address,description,email,profile_picture_url,websites,vertical'});
  case 'whatsapp_update_business_profile':
    return r('POST',p+'/whatsapp_business_profile',{},
      clean({messaging_product:'whatsapp',about:args.about,description:args.description,
        email:args.email,address:args.address,vertical:args.vertical,
        websites:args.website?[args.website]:undefined}));
  case 'whatsapp_get_commerce_settings':
    return r('GET',p+'/whatsapp_commerce_settings');
  case 'whatsapp_update_commerce_settings':
    return r('POST',p+'/whatsapp_commerce_settings',
      {is_cart_enabled:String(args.commerceEnabled),is_catalog_visible:String(args.commerceEnabled)});
  case 'whatsapp_get_subscription_status':
    return r('GET',w+'/subscribed_apps');
  case 'whatsapp_create_template':
    return r('POST',w+'/message_templates',{},
      {name:args.name,language:args.language,category:args.category,components:args.components});
  case 'whatsapp_update_template':{
    const id=owned(ownership,'templateId',args.templateId);
    return r('POST','/v26.0/'+id,{}, {components:args.components});
  }
  case 'whatsapp_delete_template':{
    const id=owned(ownership,'templateId',args.templateId);
    if(typeof ownership.templateName!=='string'||!/^[-a-z0-9_]{1,512}$/.test(ownership.templateName))
      refuse('ownership_unverified');
    return r('DELETE',w+'/message_templates',
      {hsm_id:id,name:ownership.templateName});
  }
  case 'whatsapp_get_template_analytics':{
    // Template analytics requires Meta's per-WABA reporting field contract.
    const start=toUnix(args.startDate),end=toUnix(args.endDate);
    return r('GET',w,{fields:'template_analytics.start('+start+').end('+end+').granularity(DAILY)'});
  }
  case 'whatsapp_get_business_analytics':{
    const start=toUnix(args.startDate),end=toUnix(args.endDate);
    return r('GET',w,{fields:'analytics.start('+start+').end('+end+').granularity(DAY)'});
  }
  case 'whatsapp_delete_media':{
    const id=owned(ownership,'mediaId',args.mediaId);
    return r('DELETE','/v26.0/'+id);
  }
  case 'whatsapp_list_flows':
    return r('GET',w+'/flows',limited);
  case 'whatsapp_get_flow':{
    const id=owned(ownership,'flowId',args.flowId);
    return r('GET','/v26.0/'+id,
      {fields:'id,name,categories,preview,status,validation_errors,json_version,data_api_version,data_channel_uri,health_status,whatsapp_business_account'});
  }
  case 'whatsapp_get_flow_assets':{
    const id=owned(ownership,'flowId',args.flowId);
    return r('GET','/v26.0/'+id+'/assets');
  }
  case 'whatsapp_get_flow_metrics':{
    const id=owned(ownership,'flowId',args.flowId);
    return r('GET','/v26.0/'+id,
      {fields:'metric.name(ENDPOINT_REQUEST_COUNT).granularity(LIFETIME)'});
  }
  case 'whatsapp_create_flow':
    return r('POST',w+'/flows',{},clean({
      name:args.name,categories:JSON.stringify(args.categories),
      endpoint_uri:args.endpointUri
    }),'form');
  case 'whatsapp_update_flow_metadata':{
    const id=owned(ownership,'flowId',args.flowId);
    return r('POST','/v26.0/'+id,{},clean({
      name:args.name,
      categories:args.categories?JSON.stringify(args.categories):undefined,
      endpoint_uri:args.endpointUri
    }),'form');
  }
  case 'whatsapp_upload_flow_json':{
    const id=owned(ownership,'flowId',args.flowId);
    let parsed;
    try{parsed=JSON.parse(args.flowJson);
      if(!parsed||typeof parsed!=='object'||!Array.isArray(parsed.screens))
        refuse('invalid_flow_json');
    }catch(_){refuse('invalid_flow_json');}
    return r('POST','/v26.0/'+id+'/assets',{},
      {name:'flow.json',asset_type:'FLOW_JSON',flow_json:JSON.stringify(parsed)},'multipart');
  }
  case 'whatsapp_publish_flow':
  case 'whatsapp_deprecate_flow':{
    const id=owned(ownership,'flowId',args.flowId);
    return r('POST','/v26.0/'+id+
      (name==='whatsapp_publish_flow'?'/publish':'/deprecate'));
  }
  case 'whatsapp_delete_flow':{
    const id=owned(ownership,'flowId',args.flowId);
    return r('DELETE','/v26.0/'+id);
  }
  case 'whatsapp_list_qr_codes':
    return r('GET',p+'/message_qrdls');
  case 'whatsapp_create_qr_code':
    return r('POST',p+'/message_qrdls',{},
      {prefilled_message:args.prefilledMessage,generate_qr_image:'SVG'});
  case 'whatsapp_delete_qr_code':{
    // Meta QR IDs are alphanumeric (e.g. AWHPX5O6XYVUM1), not Graph IDs.
    const code=ownership&&ownership.qrCode;
    if(typeof code!=='string'||!qrCode.test(code)||ownership.wabaIdVerified!==true||
      ownership.qrId!==args.qrId)refuse('ownership_unverified');
    return r('DELETE',p+'/message_qrdls/'+code);
  }
  case 'whatsapp_send_sticker':
    return r('POST',p+'/messages',{},msg(args.to,
      args.id?{id:args.id}:{link:args.link},'sticker'));
  case 'whatsapp_send_product':
    return r('POST',p+'/messages',{},msg(args.to,
      {type:'product',action:{catalog_id:args.catalogId,
        product_retailer_id:args.productRetailerId}}));
  case 'whatsapp_send_multi_product':
    return r('POST',p+'/messages',{},msg(args.to,{
      type:'product_list',action:{catalog_id:args.catalogId,
        sections:[{title:'Products',product_items:args.productRetailerIds.map(
          product_retailer_id=>({product_retailer_id}))}]} }));
  case 'whatsapp_send_catalog':
    return r('POST',p+'/messages',{},msg(args.to,
      {type:'catalog_message',body:{text:args.body},action:{name:'catalog_message'}}));
  case 'whatsapp_send_flow':
    return r('POST',p+'/messages',{},msg(args.to,{
      type:'flow',body:{text:args.body||'Open flow'},
      action:{name:'flow',parameters:{flow_message_version:'3',
        flow_id:args.flowId,flow_cta:args.flowCta,
        ...(args.flowToken?{flow_token:args.flowToken}:{})}}
    }));
  default:
    refuse('unsupported_host_operation');
  }
}
function toUnix(raw){
  if(typeof raw!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(raw))
    refuse('invalid_reporting_range');
  const epoch=Date.parse(raw+'T00:00:00Z');
  if(!Number.isFinite(epoch)||new Date(epoch).toISOString().slice(0,10)!==raw)
    refuse('invalid_reporting_range');
  return Math.trunc(epoch/1000);
}
