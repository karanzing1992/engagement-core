/**
 * META CORE Lane A — isolated, injected-provider MCP candidate runtime.
 *
 * Does not create an HTTP listener, Graph fetch, webhook receiver, session,
 * database, credential resolver, outbound sender or OAuth grant.
 *
 * The only provider boundary is the WACRM owner: template read broker, owned
 * Dojo SDK / consent-aware durable outbox, trusted Graph host and inbox reader.
 * This is a source contract; those providers require Lane B certification.
 */
import { WHATSAPP_LANE_A_CATALOG } from './lane-a-capability-catalog.mjs';
import { createWhatsAppLaneAMcpHarness } from './lane-a-mcp-harness.mjs';
import { buildWacrmGraphV26Plan } from './lane-a-graph-v26-plans.mjs';
import { types as nodeTypes } from 'node:util';

const all=new Map(WHATSAPP_LANE_A_CATALOG.map(x=>[x.name,x]));
const opaque=/^(?:wamid\.[A-Za-z0-9._:-]{4,256}|[0-9]{6,64}|meta-core-[A-Za-z0-9_-]{8,96})$/;
const deniedKey=/^(?:access[_-]?token|refresh[_-]?token|token|app[_-]?secret|secret|api[_-]?key|credential|authorization|bearer|private[_-]?key|password|phone|recipientPhone|phoneNumberId|wabaId)$/i;
const copyKeys=new Set([
  'data','id','name','status','category','language','after','count','total',
  'type','quality_rating','messaging_limit_tier','throughput','display_phone_number',
  'verified_name','code_verification_status','description','about','address',
  'vertical','is_cart_enabled','is_catalog_visible','success','accepted',
  'flowId','resourceId','messageId','mediaId','mimeType','sha256','fileSize','bytes',
  'start','end','sent','delivered','read','failed','statusTimestamp','timestamp',
  'requestCount','errorCount','errorRate','durationMs','active','health_status',
  'validation_errors','json_version','data_api_version','categories',
  'granularity','data_points','metrics','result'
]);
const analyticsCopyKeys=new Set(['analytics','template_analytics','template_id','clicked','cost','currency','value']);
// Public Graph business-profile fields are NOT general-purpose output keys.
const businessProfileCopyKeys=new Set(['email','websites','profile_picture_url']);
// Explicit Graph read fields are scoped to their own top-level output or
// data[] records; never widened in the shared global response allowlist.
const hostReadCopyKeys=new Map([
  ['whatsapp_get_business_account',new Set(['timezone_id','message_template_namespace'])],
  ['whatsapp_list_qr_codes',new Set(['code','prefilled_message','deep_link','qr_image_url'])],
  ['whatsapp_get_flow',new Set(['preview','data_channel_uri','whatsapp_business_account'])],
  ['whatsapp_get_flow_assets',new Set(['asset_type','download_url'])],
  ['whatsapp_get_subscription_status',new Set(['subscribed_fields','override_callback_uri'])]
]);
const flowPreviewFields=new Set(['preview_url','expires_at']);
const flowBusinessFields=new Set(['business_type','timezone_id','message_template_namespace']);
const tenantPattern=/^wacrm_[a-f0-9]{40}$/;
const idPattern=/^[0-9]{6,64}$/;
// Valid WACRM Graph resource IDs, synthetic receipt IDs and Meta QR codes.
// Arbitrary objects, booleans, empty strings and truncated IDs are never
// acceptable mutation receipts, even alongside accepted:true.
const resourceIdPattern=/^(?:[0-9]{6,64}|meta-core-[A-Za-z0-9_-]{8,96}|[A-Z0-9]{8,128})$/;
const actorIdPattern=/^[A-Za-z0-9_.:-]{1,128}$/;
const requestIdPattern=/^[A-Za-z0-9_-]{12,128}$/;

function error(code){
  const structuredContent={error:{code,message:'META CORE resource unavailable'}};
  return {isError:true,structuredContent,
    content:[{type:'text',text:JSON.stringify(structuredContent)}]};
}
function plain(value){
  try{return value!==null&&typeof value==='object'&&!nodeTypes.isProxy(value)&&
    !Array.isArray(value)&&
    Object.getPrototypeOf(value)===Object.prototype;}catch(_){return false;}
}

/**
 * Snapshot MCP arguments synchronously before any async host callback.
 * The caller retains ownership of its object; downstream policy/route callbacks
 * must never observe later mutations or invoke getters from untrusted inputs.
 *
 * Require JSON-tree-shaped inputs (no cycles or repeated object references),
 * preventing alias-based expansion. The trusted catalog schema ONLY permits
 * "phone" only at contacts[].phones[].phone (pinned Dojo 0.5.0).
 * Structural position is tracked as typed path segments and keys are limited
 * to ASCII alphanumeric/underscores, so crafted keys cannot impersonate it.
 * A cumulative UTF-8 value budget prevents multi-node preflight exhaustion.
 */
function inputSnapshot(value,toolName,depth=0,seen=new WeakSet(),budget={nodes:0,bytes:0},path=[]){
  if(++budget.nodes>1024||depth>12)throw new Error('input_size');
  if(value===null||typeof value==='boolean')return value;
  if(typeof value==='number'&&Number.isFinite(value))return value;
  if(typeof value==='string'){
    const bytes=Buffer.byteLength(value,'utf8');
    if(bytes>32768||(budget.bytes+=bytes)>65536||value.includes('\u0000'))
      throw new Error('input_size');
    return value;
  }
  if(typeof value!=='object'||nodeTypes.isProxy(value)||seen.has(value))
    throw new Error('input_shape');
  seen.add(value);
  if(Array.isArray(value)){
    const descriptors=Object.getOwnPropertyDescriptors(value);
    const keys=Reflect.ownKeys(descriptors);
    if(value.length>100||keys.length!==value.length+1||
      keys.some(k=>k!=='length'&&(typeof k!=='string'||!/^(?:0|[1-9][0-9]*)$/.test(k)||
        Number(k)>=value.length||!Object.hasOwn(descriptors[k],'value'))))
      throw new Error('input_array');
    return Object.freeze(Array.from({length:value.length},(_,i)=>{
      if(!Object.hasOwn(descriptors,String(i)))throw new Error('input_sparse');
      return inputSnapshot(descriptors[i].value,
        toolName,depth+1,seen,budget,[...path,null]);
    }));
  }
  if(!plain(value))throw new Error('input_object');
  const descriptors=Object.getOwnPropertyDescriptors(value);
  const keys=Reflect.ownKeys(descriptors);
  if(keys.length>64)throw new Error('input_object_size');
  const copy={};
  for(const key of keys){
    if(typeof key!=='string'||!/^[A-Za-z0-9_]{1,128}$/.test(key)||
      ['__proto__','constructor','prototype'].includes(key)||
      // Use typed structural segments (null=array element), never untrusted
      // key strings joined with "." or "[]"; no synthetic path collision.
      (deniedKey.test(key)&&!(key==='phone'&&
        toolName==='whatsapp_send_contacts'&&path.length===4&&
        path[0]==='contacts'&&path[1]===null&&
        path[2]==='phones'&&path[3]===null))||
      !Object.hasOwn(descriptors[key],'value'))
      throw new Error('input_key');
    Object.defineProperty(copy,key,{
      enumerable:true,configurable:false,writable:false,
      value:inputSnapshot(descriptors[key].value,
        toolName,depth+1,seen,budget,[...path,key])
    });
  }
  return Object.freeze(copy);
}

/**
 * Sanitize provider results without calling methods, indexed getters, or
 * iterators owned by the provider. In particular, Array#map can be replaced
 * on an untrusted response and is NEVER called here.
 *
 * Every output value is recreated from own *data* descriptors. Bounded
 * depth/node counts support Meta's nested analytics clicked/cost arrays but
 * prevent recursive payload exhaustion and alias-based cycles. Reused object
 * identities (DAG payloads) are intentionally denied, not silently duplicated;
 * WACRM providers must return JSON-tree-shaped objects without shared refs.
 */
function safeRead(value,depth=0,allowAnalytics=false,seen=new WeakSet(),budget={nodes:0},allowProfile=false,path=[],allowFlowMetric=false,toolName=''){
  if(++budget.nodes>1024||depth>(allowAnalytics?12:7))throw new Error('depth');
  if(value===null||typeof value==='boolean')return value;
  if(typeof value==='number'&&Number.isFinite(value))return value;
  if(typeof value==='string'){
    if(Buffer.byteLength(value,'utf8')>1024||/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(value))
      throw new Error('content');
    return value;
  }
  if(typeof value!=='object'||nodeTypes.isProxy(value)||seen.has(value))
    throw new Error('shape');
  seen.add(value);
  if(Array.isArray(value)){
    if(Object.getPrototypeOf(value)!==Array.prototype)throw new Error('array_prototype');
    const descriptors=Object.getOwnPropertyDescriptors(value);
    const size=descriptors.length?.value;
    if(!Number.isSafeInteger(size)||size>100||size<0)throw new Error('size');
    const keys=Reflect.ownKeys(descriptors);
    if(keys.length!==size+1||keys.some(key=>
      typeof key!=='string'||(key!=='length'&&
      (!/^(?:0|[1-9][0-9]*)$/.test(key)||Number(key)>=size||
        !Object.hasOwn(descriptors[key],'value')||descriptors[key].enumerable!==true))))
      throw new Error('array_keys');
    const out=[];
    for(let i=0;i<size;i++){
      const descriptor=descriptors[String(i)];
      if(!descriptor||!Object.hasOwn(descriptor,'value'))throw new Error('array_accessor');
      out[i]=safeRead(descriptor.value,depth+1,allowAnalytics,seen,budget,
        allowProfile,[...path,null],allowFlowMetric,toolName);
    }
    return out;
  }
  if(!plain(value))throw new Error('shape');
  const descriptors=Object.getOwnPropertyDescriptors(value);
  const keys=Reflect.ownKeys(descriptors);
  if(keys.length>48)throw new Error('keys');
  const out={};
  for(const key of keys){
    // Never silently strip error indicators from nested Graph/MCP payloads.
    // A partial batch failure should not become a success-shaped response.
    if(key==='error'||key==='errors')throw new Error('provider_error');
    if(typeof key!=='string'||deniedKey.test(key)||
      !Object.hasOwn(descriptors[key],'value'))throw new Error('sensitive');
    // Special-purpose fields must stay confined to the matching tool and
    // the actual Graph business-profile object, never to unrelated payloads.
    const profileObject=allowProfile&&(path.length===0||
      (path.length===2&&path[0]==='data'&&path[1]===null)||
      (path.length===1&&path[0]==='data'));
    const permittedProfile=profileObject&&businessProfileCopyKeys.has(key);
    const atHostReadRecord=path.length===0||
      (path.length===2&&path[0]==='data'&&path[1]===null);
    const permittedHostField=atHostReadRecord&&
      hostReadCopyKeys.get(toolName)?.has(key);
    // The Flow preview is itself an object. Retain only the two documented
    // nested fields inside this specific operation, never raw URL fields
    // elsewhere or unrestricted auth-token-bearing response keys.
    const flowRecordPath=path.length===1||
      (path.length===3&&path[0]==='data'&&path[1]===null);
    const permittedFlowPreview=toolName==='whatsapp_get_flow'&&
      flowRecordPath&&path[path.length-1]==='preview'&&flowPreviewFields.has(key);
    const permittedFlowBusiness=toolName==='whatsapp_get_flow'&&
      flowRecordPath&&path[path.length-1]==='whatsapp_business_account'&&
      flowBusinessFields.has(key);
    // Graph Flow metrics: only the root metric and its nested measurement
    // key/value pairs, never an unrestricted response-wide allowlist.
    const flowMeasurement=allowFlowMetric&&path.length===5&&
      path[0]==='metric'&&path[1]==='data_points'&&path[2]===null&&
      path[3]==='data'&&path[4]===null&&(key==='key'||key==='value');
    const permittedFlowMetric=allowFlowMetric&&path.length===0&&key==='metric'||
      flowMeasurement;
    if(flowMeasurement&&key==='key'&&descriptors[key].value!=='value')
      throw new Error('metric_key');
    if(flowMeasurement&&key==='value'&&
      (!Number.isSafeInteger(descriptors[key].value)||descriptors[key].value<0))
      throw new Error('metric_value');
    if(permittedProfile){
      const v=descriptors[key].value;
      if(key==='email'&&(typeof v!=='string'||v.length>256||
          !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)))throw new Error('profile_email');
      if(key==='profile_picture_url'&&(typeof v!=='string'||
          v.length>2048||!/^https:\/\/[^\s]+$/.test(v)))throw new Error('profile_url');
      if(key==='websites'&&(!Array.isArray(v)||nodeTypes.isProxy(v)))
        throw new Error('profile_websites');
    }
    if(copyKeys.has(key)||(allowAnalytics&&analyticsCopyKeys.has(key))||
       permittedProfile||permittedFlowMetric||permittedHostField||
       permittedFlowPreview||permittedFlowBusiness){
      const v=safeRead(descriptors[key].value,depth+1,allowAnalytics,seen,budget,
        allowProfile,[...path,key],allowFlowMetric,toolName);
      if(permittedProfile&&key==='websites'&&
        (!Array.isArray(v)||v.length>10||v.some(u=>
          typeof u!=='string'||u.length>2048||!/^https:\/\/[^\s]+$/.test(u))))
        throw new Error('profile_websites');
      if(permittedFlowPreview&&key==='preview_url'){
        if(typeof v!=='string'||v.length>1024)throw new Error('flow_preview_url');
        let parsed;
        try{parsed=new URL(v);}catch(_){throw new Error('flow_preview_url');}
        if(parsed.protocol!=='https:'||!parsed.hostname||parsed.username||
           parsed.password||parsed.hash)throw new Error('flow_preview_url');
      }
      if(permittedFlowPreview&&key==='expires_at'&&
         (typeof v!=='string'||v.length<10||v.length>64))
        throw new Error('flow_preview_expiry');
      out[key]=v;
    }
  }
  return out;
}
function sanitize(result,def){
  if(!plain(result))throw new Error('provider');
  // Never invoke untrusted getters while selecting or sizing provider output.
  const descriptors=Object.getOwnPropertyDescriptors(result);
  for(const key of ['ok','isError','structuredContent','data']){
    if(Object.hasOwn(descriptors,key)&&!Object.hasOwn(descriptors[key],'value'))
      throw new Error('provider_accessor');
  }
  // Envelope-level mutation receipts are just as authoritative as nested
  // data receipts. Never discard an explicit rejection while unwrapping.
  for(const key of ['accepted','success']){
    if(Object.hasOwn(descriptors,key)&&
       (!Object.hasOwn(descriptors[key],'value')||descriptors[key].value!==true))
      throw new Error('negative_envelope_receipt');
  }
  // Optional wrapper status fields must be actual booleans. Do not
  // accidentally convert malformed "false", null or error wrappers to OK.
  if((Object.hasOwn(descriptors,'ok')&&descriptors.ok.value!==true)||
     (Object.hasOwn(descriptors,'isError')&&descriptors.isError.value!==false)||
     Object.hasOwn(descriptors,'error'))
    throw new Error('provider');
  const value=Object.hasOwn(descriptors,'structuredContent')
    ?descriptors.structuredContent.value:Object.hasOwn(descriptors,'data')
      ?descriptors.data.value:result;
  if(!plain(value))throw new Error('provider');
  // Error objects must not be silently stripped by the generic allowlist.
  if(Object.hasOwn(Object.getOwnPropertyDescriptors(value),'error'))
    throw new Error('provider_error');
  const analyticsKey=def.name==='whatsapp_get_business_analytics'?'analytics':
    def.name==='whatsapp_get_template_analytics'?'template_analytics':null;
  const data=safeRead(value,0,analyticsKey!==null,new WeakSet(),{nodes:0},
    def.name==='whatsapp_get_business_profile',[],
    def.name==='whatsapp_get_flow_metrics',def.name);
  if(analyticsKey&&!Object.hasOwn(data,analyticsKey))throw new Error('missing_analytics');
  if(def.name==='whatsapp_get_business_profile'&&Array.isArray(data.data)&&
      (data.data.length===0||data.data.some(item=>!plain(item)||!Object.keys(item).length)))
    throw new Error('empty_profile');
  // A syntactically nonempty QR response with blank records is a contract
  // failure, not a successful listing.
  if(def.name==='whatsapp_list_qr_codes'&&Array.isArray(data.data)&&
      data.data.some(item=>!plain(item)||!Object.keys(item).length))
    throw new Error('empty_qr_record');
  if(def.name==='whatsapp_get_flow_metrics'){
    const metric=data.metric;
    if(!plain(metric)||metric.name!=='ENDPOINT_REQUEST_COUNT'||
       metric.granularity!=='LIFETIME'||!Array.isArray(metric.data_points))
      throw new Error('missing_flow_metric');
    // An explicit empty data_points array means no observations. A missing
    // metric or malformed datapoint must not become a successful ID-only read.
    for(const point of metric.data_points){
      if(!plain(point)||!Array.isArray(point.data)||point.data.length===0)
        throw new Error('flow_metric_shape');
      for(const measurement of point.data){
        if(!plain(measurement)||measurement.key!=='value'||
           !Number.isSafeInteger(measurement.value)||measurement.value<0)
          throw new Error('flow_metric_measure');
      }
    }
  }
  if(Buffer.byteLength(JSON.stringify(data),'utf8')>65536)
    throw new Error('provider');
  if(def.kind==='read'&&!Object.keys(data).length)throw new Error('empty_read');
  const mediaUpload=def.name==='whatsapp_upload_media_from_url';
  if(mediaUpload&&(typeof data.mediaId!=='string'||
      !/^(?:[0-9]{6,64}|media\.mock-[1-9][0-9]*)$/.test(data.mediaId)))
    throw new Error('bad_media_id');
  // A negative or malformed operation indicator is a provider failure even
  // on a read response; mutation paths additionally require a receipt.
  for(const flag of ['accepted','success']){
    if(Object.hasOwn(data,flag)&&data[flag]!==true)
      throw new Error('negative_receipt');
  }
  if(def.kind!=='read'&&Object.hasOwn(data,'resourceId')&&
     (typeof data.resourceId!=='string'||!resourceIdPattern.test(data.resourceId)))
    throw new Error('bad_resource_id');
  if(def.kind!=='read'&&!Object.hasOwn(data,'accepted')&&
      !Object.hasOwn(data,'success')&&!Object.hasOwn(data,'messageId')&&
      !Object.hasOwn(data,'resourceId')&&!(mediaUpload&&Object.hasOwn(data,'mediaId')))
    throw new Error('missing_receipt');
  if(data.messageId!==undefined&&
      (typeof data.messageId!=='string'||!opaque.test(data.messageId)))
    throw new Error('bad_id');
  return data;
}
function validateActor(p,tenantId){
  return plain(p)&&p.tenantId===tenantId&&
    typeof p.actorId==='string'&&actorIdPattern.test(p.actorId)&&
    typeof tenantId==='string'&&tenantPattern.test(tenantId);
}
// Copy the authoritative route before calling an asynchronous ownership
// resolver; a mutable host row must not change WABA/phone after validation.
function snapshotRoute(raw,tenantId){
  if(!plain(raw))throw new Error('route_unavailable');
  const ds=Object.getOwnPropertyDescriptors(raw),copy={};
  for(const key of ['tenantId','status','activationId','wabaId','phoneNumberId']){
    if(!ds[key]||!Object.hasOwn(ds[key],'value'))
      throw new Error('route_unavailable');
    copy[key]=ds[key].value;
  }
  if(copy.tenantId!==tenantId||copy.status!=='active'||
     !Number.isSafeInteger(copy.activationId)||copy.activationId<1||
     typeof copy.wabaId!=='string'||!idPattern.test(copy.wabaId)||
     typeof copy.phoneNumberId!=='string'||!idPattern.test(copy.phoneNumberId))
    throw new Error('route_unavailable');
  return Object.freeze(copy);
}
function invokeMethod(provider,method,args){
  if(!provider||typeof provider[method]!=='function')return Promise.reject(new Error('unbound'));
  return provider[method](args);
}

/**
 * Integration contract:
 * verifyIdentity       Host-proven signed issuer/audience/client/role; NEVER model claims.
 * authorizeTenant      Explicit tool-level grant for verified actor and tenant.
 * readPolicy           Host-owned opt-in, window, approved templates, owner decisions.
 * resolveRoute         WACRM Central tenant+activation+WABA+phone active route.
 * resolveOwnership     WACRM Central verifies by-ID resources belong to route WABA.
 * providers.broker     Existing tokenless signed two-tool template read adapter.
 * providers.dojo       WACRM-owned Dojo SDK + durable consent-aware outbound outbox.
 * providers.host       WACRM-owned host Graph plan executor; no tokens leave Central.
 * providers.wacrm      WACRM-owned tenant inbox/status reader.
 *
 * Default grants = []; no network provider or customer message storage here.
 */
export function createLaneAProviderMcp({
  verifyIdentity,authorizeTenant,readPolicy,resolveRoute,resolveOwnership,
  providers={},grants=[],enableWriteCandidates=false
}={}){
  for(const f of [verifyIdentity,authorizeTenant,readPolicy,resolveRoute,resolveOwnership])
    if(typeof f!=='function')throw new TypeError('Trusted Lane B host authority required');
  if(!Array.isArray(grants)||grants.some(name=>!all.has(name)))
    throw new TypeError('Invalid tool grant set');
  const granted=new Set(grants);
  const ingress=createWhatsAppLaneAMcpHarness({
    authorizeTenant,capabilityGrants:grants,allowSyntheticWrites:enableWriteCandidates
  });
  const exposed=()=>ingress.listTools().filter(t=>{
    const d=all.get(t.name);
    return d&&providers[d.adapter]&&typeof providers[d.adapter][
      d.adapter==='host'?'executePlan':d.adapter==='wacrm'?'read':'invoke'
    ]==='function';
  });
  return Object.freeze({
    listTools:exposed,
    async callTool(request={}, context={}){
      // Reject Proxy-backed MCP envelopes and contexts before property access,
      // object reflection or any host call. Proxies can run arbitrary traps.
      if(!plain(request))return error('invalid_input');
      if(!plain(context))return error('forbidden');
      const requestFields=Object.getOwnPropertyDescriptors(request);
      const contextFields=Object.getOwnPropertyDescriptors(context);
      if(!Object.hasOwn(requestFields,'name')||
          !Object.hasOwn(requestFields.name,'value')||
          (requestFields.arguments&&!Object.hasOwn(requestFields.arguments,'value')))
        return error('invalid_input');
      for(const key of ['verifiedPrincipal','tenantId','requestId']){
        if(contextFields[key]&&!Object.hasOwn(contextFields[key],'value'))
          return error('forbidden');
      }
      const name=requestFields.name.value;
      let args=requestFields.arguments?.value;
      const verifiedPrincipal=contextFields.verifiedPrincipal?.value;
      const tenantId=contextFields.tenantId?.value;
      const requestId=contextFields.requestId?.value;
      const def=all.get(name);
      if(!def)return error('unknown_tool');
      if(!granted.has(name)||def.kind!=='read'&&!enableWriteCandidates)return error('not_enabled');
      if(!exposed().some(t=>t.name===name))return error('provider_unavailable');
      if(!validateActor(verifiedPrincipal,tenantId))return error('forbidden');
      // A signed, issuer/client/audience/role-proven principal is mandatory.
      // No route, policy or provider action until identity verification passes.
      try {
        if(await verifyIdentity(verifiedPrincipal,tenantId,name)!==true)
          return error('forbidden');
      }catch(_){return error('forbidden');}
      // No untrusted input inspection occurs before identity proof. The immutable
      // snapshot precedes policy authorization, routing and provider execution.
      try { args=inputSnapshot(args??{},name); }
      catch(_) { return error('invalid_input'); }
      let policy;
      try {policy=await readPolicy(verifiedPrincipal,tenantId,name,args);}
      catch(_){return error('policy_denied');}
      if(!plain(policy))return error('policy_denied');
      const check=await ingress.callTool(
        {name,arguments:args},{verifiedPrincipal,tenantId,trustedPolicy:policy});
      if(check.isError)return check;
      // All *side-effecting* calls require an owner-issued durable request ID,
      // not a model-supplied idempotency key. WACRM owns dedupe and retries.
      if(def.kind!=='read'&&
          (typeof requestId!=='string'||!requestIdPattern.test(requestId)))
        return error('request_id_required');
      let route;
      try {route=snapshotRoute(await resolveRoute(tenantId,verifiedPrincipal),tenantId);}
      catch(_){return error('route_unavailable');}
      let proof={};
      if(def.adapter==='host'&&
        ['templateId','flowId','mediaId','qrId'].some(k=>Object.hasOwn(args??{},k))){
        try {proof=await resolveOwnership(route,name,args,verifiedPrincipal);}
        catch(_){return error('ownership_unverified');}
        if(!plain(proof)||proof.wabaIdVerified!==true)return error('ownership_unverified');
      }
      const envelope={
        toolName:name,tenantId,activationId:route.activationId,
        graphApiVersion:'v26.0',requestId:requestId??null,
        principal:{actorId:verifiedPrincipal.actorId},
        args // from ingress validation: original args are additionally checked below
      };
      let response;
      try {
        // Strict immutable argument snapshot was captured before authorization.
        // Never revisit caller-owned mutable inputs after async policy checks.
        envelope.args=args;
        if(def.adapter==='host'){
          const plan=buildWacrmGraphV26Plan({
            name,args:envelope.args,route,ownership:proof
          });
          response=await invokeMethod(providers.host,'executePlan',{...envelope,plan});
        }else if(def.adapter==='wacrm'){
          response=await invokeMethod(providers.wacrm,'read',envelope);
        }else if(def.adapter==='broker'){
          response=await invokeMethod(providers.broker,'invoke',{
            principal:verifiedPrincipal,tenantId,toolName:name,args:envelope.args
          });
        }else if(def.adapter==='dojo'){
          // Must be a WACRM-owned Dojo SDK/outbox adapter, NEVER a direct
          // unrestricted Cloud API instance on the MCP/browser host.
          response=await invokeMethod(providers.dojo,'invoke',envelope);
        }else return error('provider_unavailable');
        const safe=sanitize(response,def);
        const structuredContent={ok:true,toolName:name,graphApiVersion:'v26.0',data:safe};
        return {isError:false,structuredContent,
          content:[{type:'text',text:JSON.stringify(structuredContent)}]};
      }catch(_){return error('upstream_unavailable');}
    }
  });
}
