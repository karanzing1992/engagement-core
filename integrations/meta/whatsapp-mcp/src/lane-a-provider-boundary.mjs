/** META CORE Lane A. Synthetic provider boundary, no network or Meta credentials. */
import { createHash } from 'node:crypto';
import { WHATSAPP_LANE_A_CATALOG } from './lane-a-capability-catalog.mjs';
const tools=new Map(WHATSAPP_LANE_A_CATALOG.map(x=>[x.name,x]));
const tenant=/^wacrm_[a-f0-9]{40}$/;
const number=/^[0-9]{6,64}$/;
const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&Object.getPrototypeOf(x)===Object.prototype;
const deny=code=>({ok:false,error:{code,message:'META CORE synthetic integration unavailable'}});
const safeReceipt=result=>{
  if(!plain(result)||result.ok!==true||!plain(result.receipt))return null;
  const d=Object.getOwnPropertyDescriptors(result.receipt);
  const keys=Reflect.ownKeys(d);
  if(keys.length>5||keys.some(k=>typeof k!=='string'||!['operation','state','reference','readOnly','retryAfter'].includes(k)||
     !Object.hasOwn(d[k],'value')))return null;
  const r={};
  for(const key of keys){
    const value=d[key].value;
    if(key==='operation'&&(!tools.has(value)))return null;
    if(key==='state'&&!['simulated','queued','accepted','verified_read'].includes(value))return null;
    if(key==='reference'&&(typeof value!=='string'||!/^[A-Za-z0-9_-]{1,64}$/.test(value)))return null;
    if(key==='readOnly'&&typeof value!=='boolean')return null;
    if(key==='retryAfter'&&(!Number.isInteger(value)||value<0||value>86400))return null;
    r[key]=value;
  }
  return {ok:true,receipt:Object.freeze(r)};
};
/** All injected functions are owned by the approved host, never the MCP caller. */
export function createLaneAProviderHarness({authorize,resolveRoute,adapterFactory}={}){
  if(typeof authorize!=='function'||typeof resolveRoute!=='function'||typeof adapterFactory!=='function')
    throw new TypeError('Host authorization, route and adapters required');
  return Object.freeze({
    listCapabilities:()=>WHATSAPP_LANE_A_CATALOG.map(d=>({
      name:d.name,group:d.group,kind:d.kind,adapter:d.adapter,
      providerPermission:d.providerPermission,integrationState:'synthetic_contract_only'
    })),
    async dispatch({principal,tenantId,toolName,args,approval,environment,grant}={}){
      const def=tools.get(toolName);
      if(!def)return deny('unsupported_tool');
      if(typeof tenantId!=='string'||!tenant.test(tenantId)||
         !plain(principal)||principal.tenantId!==tenantId)return deny('forbidden');
      if(environment!=='synthetic'||grant!=='synthetic_verified')return deny('not_enabled');
      if(!plain(args)||!plain(approval))return deny('invalid_input');
      let serialized;
      try {serialized=JSON.stringify(args)}catch(_){return deny('invalid_input')}
      if(!serialized||serialized.length>16384||Object.keys(args).length>32)return deny('invalid_input');
      let allowed;
      try {allowed=await authorize(principal,tenantId,toolName,def.kind)}
      catch(_){return deny('forbidden')}
      if(allowed!==true)return deny('forbidden');
      if(def.kind!=='read'&&approval.operator!==true)return deny('approval_required');
      if(def.kind==='irreversible'&&approval.irreversible!==true)return deny('approval_required');
      if(def.kind.startsWith('send')&&
          (approval.optIn!==true||approval.cost!==true||
           def.kind==='send_window'&&approval.windowOpen!==true||
           def.kind==='send_template'&&approval.templateApproved!==true))
        return deny('policy_denied');
      let route;
      try{route=await resolveRoute(tenantId)}catch(_){return deny('route_unavailable')}
      if(!plain(route)||route.tenantId!==tenantId||route.status!=='active'||
        !Number.isSafeInteger(route.activationId)||route.activationId<1||
        !number.test(route.wabaId)||!number.test(route.phoneNumberId))
        return deny('route_unavailable');
      const operation=Object.freeze({
        name:toolName,kind:def.kind,adapter:def.adapter,group:def.group,
        providerPermission:def.providerPermission,tenantId,
        activationId:route.activationId,wabaId:route.wabaId,
        phoneNumberId:route.phoneNumberId,
        argumentsDigest:createHash('sha256').update(serialized).digest('hex'),
      });
      let implementation;
      try{implementation=await adapterFactory(def.adapter,operation)}
      catch(_){return deny('adapter_unavailable')}
      if(!implementation||implementation.synthetic!==true||
         typeof implementation.execute!=='function')return deny('adapter_unavailable');
      try {return safeReceipt(await implementation.execute(operation))??deny('provider_unavailable')}
      catch(_){return deny('provider_unavailable')}
    }
  });
}
