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

const all=new Map(WHATSAPP_LANE_A_CATALOG.map(x=>[x.name,x]));
const opaque=/^(?:wamid\.[A-Za-z0-9._:-]{4,256}|[0-9]{6,64}|meta-core-[A-Za-z0-9_-]{8,96})$/;
const deniedKey=/^(?:access[_-]?token|refresh[_-]?token|token|app[_-]?secret|secret|api[_-]?key|credential|authorization|bearer|private[_-]?key|password|phone|recipientPhone|phoneNumberId|wabaId)$/i;
const copyKeys=new Set([
  'data','id','name','status','category','language','after','count','total',
  'type','quality_rating','messaging_limit_tier','throughput','display_phone_number',
  'verified_name','code_verification_status','description','about','address',
  'vertical','is_cart_enabled','is_catalog_visible','success','accepted',
  'flowId','resourceId','messageId','mimeType','sha256','fileSize','bytes',
  'start','end','sent','delivered','read','failed','statusTimestamp','timestamp',
  'requestCount','errorCount','errorRate','durationMs','active','health_status',
  'validation_errors','json_version','data_api_version','categories',
  'granularity','data_points','metrics','result'
]);
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
  try{return value!==null&&typeof value==='object'&&!Array.isArray(value)&&
    Object.getPrototypeOf(value)===Object.prototype;}catch(_){return false;}
}

/**
 * Snapshot MCP arguments synchronously before any async host callback.
 * The caller retains ownership of its object; downstream policy/route callbacks
 * must never observe later mutations or invoke getters from untrusted inputs.
 */
function inputSnapshot(value,depth=0,seen=new WeakSet(),budget={nodes:0}){
  if(++budget.nodes>1024||depth>12)throw new Error('input_size');
  if(value===null||typeof value==='boolean')return value;
  if(typeof value==='number'&&Number.isFinite(value))return value;
  if(typeof value==='string'&&Buffer.byteLength(value,'utf8')<=32768&&
      !value.includes('\u0000'))return value;
  if(typeof value!=='object'||seen.has(value))throw new Error('input_shape');
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
      return inputSnapshot(descriptors[i].value,depth+1,seen,budget);
    }));
  }
  if(!plain(value))throw new Error('input_object');
  const descriptors=Object.getOwnPropertyDescriptors(value);
  const keys=Reflect.ownKeys(descriptors);
  if(keys.length>64)throw new Error('input_object_size');
  const copy={};
  for(const key of keys){
    if(typeof key!=='string'||key.length>128||
      ['__proto__','constructor','prototype'].includes(key)||
      // Contacts legitimately contain phone; ingress Zod validates its shape.
      // Do not confuse contact fields with bearer/tenant/Graph credentials.
      (deniedKey.test(key)&&key!=='phone')||!Object.hasOwn(descriptors[key],'value'))
      throw new Error('input_key');
    Object.defineProperty(copy,key,{
      enumerable:true,configurable:false,writable:false,
      value:inputSnapshot(descriptors[key].value,depth+1,seen,budget)
    });
  }
  return Object.freeze(copy);
}

function safeRead(value,depth=0){
  if(depth>7)throw new Error('depth');
  if(value===null||typeof value==='boolean')return value;
  if(typeof value==='number'&&Number.isFinite(value))return value;
  if(typeof value==='string'){
    if(Buffer.byteLength(value,'utf8')>1024||/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(value))
      throw new Error('content');
    return value;
  }
  if(Array.isArray(value)){
    if(value.length>100)throw new Error('size');
    return value.map(x=>safeRead(x,depth+1));
  }
  if(!plain(value))throw new Error('shape');
  const descriptors=Object.getOwnPropertyDescriptors(value);
  const keys=Reflect.ownKeys(descriptors);
  if(keys.length>48)throw new Error('keys');
  const out={};
  for(const key of keys){
    if(typeof key!=='string'||deniedKey.test(key)||
       !Object.hasOwn(descriptors[key],'value'))throw new Error('sensitive');
    // Drop non-allowlisted public Graph fields, never echo credentials,
    // signed CDN URLs, customer message text or raw webhook payloads.
    if(copyKeys.has(key))out[key]=safeRead(descriptors[key].value,depth+1);
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
  const data=safeRead(value);
  if(Buffer.byteLength(JSON.stringify(data),'utf8')>65536)
    throw new Error('provider');
  if(def.kind==='read'&&!Object.keys(data).length)throw new Error('empty_read');
  if(def.kind!=='read'&&!Object.hasOwn(data,'accepted')&&
      !Object.hasOwn(data,'success')&&!Object.hasOwn(data,'messageId')&&
      !Object.hasOwn(data,'resourceId'))throw new Error('missing_receipt');
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
    async callTool({name,arguments:args}={}, context={}){
      const def=all.get(name);
      if(!def)return error('unknown_tool');
      if(!granted.has(name)||def.kind!=='read'&&!enableWriteCandidates)return error('not_enabled');
      if(!exposed().some(t=>t.name===name))return error('provider_unavailable');
      // Snapshot *before* readPolicy, any await, or route/ownership resolution.
      // The entire decision and provider call must use the same immutable input.
      try { args=inputSnapshot(args??{}); }
      catch(_) { return error('invalid_input'); }
      const {verifiedPrincipal,tenantId,requestId}=context;
      if(!validateActor(verifiedPrincipal,tenantId))return error('forbidden');
      // A signed, issuer/client/audience/role-proven principal is mandatory.
      // No route, policy or provider action until identity verification passes.
      try {
        if(await verifyIdentity(verifiedPrincipal,tenantId,name)!==true)
          return error('forbidden');
      }catch(_){return error('forbidden');}
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
