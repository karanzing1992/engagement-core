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
const tenantPattern=/^wacrm_[a-f0-9]{40}$/;
const idPattern=/^[0-9]{6,64}$/;
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
function safeRead(value,depth=0,allowAnalytics=false,seen=new WeakSet(),budget={nodes:0},allowProfile=false,path=[],allowFlowMetric=false){
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
        allowProfile,[...path,null],allowFlowMetric);
    }
    return out;
  }
  if(!plain(value))throw new Error('shape');
  const descriptors=Object.getOwnPropertyDescriptors(value);
  const keys=Reflect.ownKeys(descriptors);
  if(keys.length>48)throw new Error('keys');
  const out={};
  for(const key of keys){
    if(typeof key!=='string'||deniedKey.test(key)||
      !Object.hasOwn(descriptors[key],'value'))throw new Error('sensitive');
    // Special-purpose fields must stay confined to the matching tool and
    // the actual Graph business-profile object, never to unrelated payloads.
    const profileObject=allowProfile&&(path.length===0||
      (path.length===2&&path[0]==='data'&&path[1]===null)||
      (path.length===1&&path[0]==='data'));
    const permittedProfile=profileObject&&businessProfileCopyKeys.has(key);
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
       permittedProfile||permittedFlowMetric){
      const v=safeRead(descriptors[key].value,depth+1,allowAnalytics,seen,budget,
        allowProfile,[...path,key],allowFlowMetric);
      if(permittedProfile&&key==='websites'&&
        (!Array.isArray(v)||v.length>10||v.some(u=>
          typeof u!=='string'||u.length>2048||!/^https:\/\/[^\s]+$/.test(u))))
        throw new Error('profile_websites');
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
  if(descriptors.ok?.value===false||descriptors.isError?.value===true)
    throw new Error('provider');
  const value=Object.hasOwn(descriptors,'structuredContent')
    ?descriptors.structuredContent.value:Object.hasOwn(descriptors,'data')
      ?descriptors.data.value:result;
  if(!plain(value))throw new Error('provider');
  const analyticsKey=def.name==='whatsapp_get_business_analytics'?'analytics':
    def.name==='whatsapp_get_template_analytics'?'template_analytics':null;
  const data=safeRead(value,0,analyticsKey!==null,new WeakSet(),{nodes:0},
    def.name==='whatsapp_get_business_profile',[],
    def.name==='whatsapp_get_flow_metrics');
  if(analyticsKey&&!Object.hasOwn(data,analyticsKey))throw new Error('missing_analytics');
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
  // Do not convert an explicit provider refusal into a successful MCP
  // mutation, even if another affirmative receipt field is present.
  if(def.kind!=='read'){
    for(const flag of ['accepted','success']){
      if(Object.hasOwn(data,flag)&&data[flag]!==true)
        throw new Error('negative_receipt');
    }
  }
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
function validateRoute(route,tenantId){
  return plain(route)&&route.tenantId===tenantId&&route.status==='active'&&
    Number.isSafeInteger(route.activationId)&&route.activationId>0&&
    typeof route.wabaId==='string'&&idPattern.test(route.wabaId)&&
    typeof route.phoneNumberId==='string'&&idPattern.test(route.phoneNumberId);
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
      try {route=await resolveRoute(tenantId,verifiedPrincipal);}
      catch(_){return error('route_unavailable');}
      if(!validateRoute(route,tenantId))return error('route_unavailable');
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
