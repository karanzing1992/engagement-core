/**
 * META CORE Lane A — offline MCP tools/list + tools/call contract harness.
 * DELIBERATELY NO Graph transport, no credentials, no remote MCP listener.
 * An integration-ready contract/negative-test harness, NOT a live sender.
 */
import { createHash } from 'node:crypto';
import { WHATSAPP_LANE_A_CATALOG } from './lane-a-capability-catalog.mjs';

const catalog=new Map(WHATSAPP_LANE_A_CATALOG.map(def=>[def.name,def]));
const tenantPattern=/^wacrm_[a-f0-9]{40}$/;
const blockedKeys=/^(?:access[_-]?token|auth(?:orization)?|bearer|api[_-]?key|secret|password|credential|private[_-]?key|wabaId|phoneNumberId|tenantId|clientId)$/i;

function plain(value) {
  return value!==null && typeof value==='object' && !Array.isArray(value) &&
    Object.getPrototypeOf(value)===Object.prototype;
}
function cloneChecked(value,schema,depth=0) {
  if(depth>8) throw new Error('invalid_input');
  if(schema.type==='object') {
    if(!plain(value)) throw new Error('invalid_input');
    const descriptors=Object.getOwnPropertyDescriptors(value);
    const keys=Reflect.ownKeys(descriptors);
    if(keys.length>64||keys.some(k=>typeof k!=='string'||blockedKeys.test(k)||
        !Object.hasOwn(schema.properties,k)||!Object.hasOwn(descriptors[k],'value'))) {
      throw new Error('invalid_input');
    }
    for(const k of schema.required||[])if(!Object.hasOwn(descriptors,k))throw new Error('invalid_input');
    if(schema.minProperties!==undefined&&keys.length<schema.minProperties)throw new Error('invalid_input');
    if(schema.maxProperties!==undefined&&keys.length>schema.maxProperties)throw new Error('invalid_input');
    const safe={};
    for(const k of keys)safe[k]=cloneChecked(descriptors[k].value,schema.properties[k],depth+1);
    return safe;
  }
  if(schema.type==='array') {
    if(!Array.isArray(value)||value.length<(schema.minItems??0)||value.length>(schema.maxItems??100)||
        Object.keys(value).length!==value.length)throw new Error('invalid_input');
    return value.map(item=>cloneChecked(item,schema.items,depth+1));
  }
  if(schema.type==='boolean') {
    if(typeof value!=='boolean')throw new Error('invalid_input');
    return value;
  }
  if(schema.type==='integer'||schema.type==='number') {
    if(typeof value!=='number'||!Number.isFinite(value)||
       (schema.type==='integer'&&!Number.isInteger(value))||
       (schema.minimum!==undefined&&value<schema.minimum)||
       (schema.maximum!==undefined&&value>schema.maximum))throw new Error('invalid_input');
    return value;
  }
  if(schema.type==='string') {
    if(typeof value!=='string'||Buffer.byteLength(value,'utf8')>(schema.maxLength??4096)||
       value.length<(schema.minLength??0)||value.includes('\u0000')||
       (schema.pattern&&!new RegExp(schema.pattern,'u').test(value))||
       (schema.enum&&!schema.enum.includes(value)))throw new Error('invalid_input');
    return value;
  }
  throw new Error('invalid_input');
}
function publicHttps(input) {
  try {
    const u=new URL(input);
    if(u.protocol!=='https:'||u.username||u.password||u.hash)return false;
    const h=u.hostname.toLowerCase().replace(/^\[|\]$/g,'');
    if(h==='localhost'||h.endsWith('.localhost')||h.endsWith('.local')||
        h.includes(':')||h==='0.0.0.0'||h==='255.255.255.255')return false;
    if(/^\d+(?:\.\d+){3}$/.test(h)){
      const n=h.split('.').map(Number);
      if(n.some(x=>x>255)||n[0]===0||n[0]===10||n[0]===127||n[0]>=224||
          n[0]===169&&n[1]===254||
          n[0]===172&&n[1]>=16&&n[1]<=31||
          n[0]===192&&n[1]===168||
          n[0]===100&&n[1]>=64&&n[1]<=127)return false;
    }
    return true;
  }catch(_){return false;}
}
function checkedArguments(def,args) {
  const safe=cloneChecked(args??{},def.inputSchema);
  for(const key of ['link','sourceUrl','website','endpointUri']){
    if(Object.hasOwn(safe,key)&&!publicHttps(safe[key]))throw new Error('invalid_input');
  }
  // Dojo media calls expect exactly one uploaded ID OR an HTTPS link.
  if(/^whatsapp_send_(?:image|video|audio|voice|document|sticker)$/.test(def.name)){
    if(Number(Object.hasOwn(safe,'link'))+Number(Object.hasOwn(safe,'id'))!==1)
      throw new Error('invalid_input');
  }
  // No arbitrary Graph / Media / Flow pass-through in this contract.
  if(def.name==='whatsapp_upload_flow_json'){
    try {
      const flow=JSON.parse(safe.flowJson);
      if(!plain(flow)||!Array.isArray(flow.screens)||flow.screens.length>30)
        throw new Error('invalid_input');
    }catch(_){throw new Error('invalid_input');}
  }
  return Object.freeze(safe);
}
function err(code) {
  const result={error:{code,message:'META CORE operation unavailable'}};
  return {isError:true,content:[{type:'text',text:JSON.stringify(result)}],structuredContent:result};
}
function policyPass(kind,p) {
  if(kind==='read')return true;
  if(kind==='ack')return p.operatorApproved===true;
  if(kind==='write')return p.operatorApproved===true;
  if(kind==='irreversible')return p.operatorApproved===true&&p.irreversibleApproved===true;
  if(kind==='send_window')return p.optInVerified===true&&p.customerWindowOpen===true&&p.billableSendApproved===true;
  if(kind==='send_template')return p.optInVerified===true&&p.templateApproved===true&&p.billableSendApproved===true;
  return false;
}

/** Capability grants and trustedPolicy come from the host, never MCP arguments. */
export function createWhatsAppLaneAMcpHarness({authorizeTenant,capabilityGrants=[],allowSyntheticWrites=false}={}) {
  if(typeof authorizeTenant!=='function'||!Array.isArray(capabilityGrants)||
     capabilityGrants.some(name=>!catalog.has(name)))
    throw new TypeError('Trusted tenant authorizer and explicit capability grants required');
  const grants=new Set(capabilityGrants);
  return Object.freeze({
    listTools(){
      return WHATSAPP_LANE_A_CATALOG.filter(d=>grants.has(d.name)&&
        (d.kind==='read'||allowSyntheticWrites)).map(d=>({
        name:d.name,description:d.description,inputSchema:d.inputSchema,
        annotations:d.annotations
      }));
    },
    listCapabilityInventory(){
      return WHATSAPP_LANE_A_CATALOG.map(d=>({
        name:d.name,group:d.group,kind:d.kind,providerPermission:d.providerPermission,
        adapter:d.adapter,integrationState:d.integrationState
      }));
    },
    async callTool({name,arguments:rawArgs}={},context={}){
      const def=catalog.get(name);
      if(!def)return err('unknown_tool');
      if(!grants.has(name)||def.kind!=='read'&&!allowSyntheticWrites)return err('not_enabled');
      let args;
      try {args=checkedArguments(def,rawArgs);}catch(_){return err('invalid_input');}
      const {verifiedPrincipal,tenantId,trustedPolicy={}}=context;
      if(!plain(verifiedPrincipal)||typeof tenantId!=='string'||
          !tenantPattern.test(tenantId)||verifiedPrincipal.tenantId!==tenantId)
        return err('forbidden');
      // No credential, WABA, phone ID or inbound data is ever resolved here.
      try {
        if(await authorizeTenant(verifiedPrincipal,tenantId,name)!==true)return err('forbidden');
      }catch(_){return err('forbidden');}
      if(!plain(trustedPolicy)||!policyPass(def.kind,trustedPolicy))return err('policy_denied');
      // No network callback is accepted: deterministic offline receipt ONLY.
      const digest=createHash('sha256').update(name).update('\n').update(tenantId)
        .update('\n').update(JSON.stringify(args)).digest('hex').slice(0,24);
      const receipt={
        simulation:true,operation:name,adapter: def.adapter,
        syntheticReceipt:'meta-core-synthetic-'+digest,
        integrationState:'pending_provider_binding'
      };
      return {isError:false,content:[{type:'text',text:JSON.stringify(receipt)}],structuredContent:receipt};
    }
  });
}
