/**
 * Exact pinned Dojo SDK/MCP contract discovery and safe input validation.
 * No network client is instantiated; this reads the installed 19-tool
 * metadata using an inert client and never calls SDK .dispatch().
 *
 * Broker template reads remain the narrower WACRM Central schema.
 */
import { z } from 'zod';
import { types as nodeTypes } from 'node:util';
import { createWhatsAppToolset } from '@dojocoding/whatsapp-mcp';
const toolset=createWhatsAppToolset({
  client:Object.freeze({}),wabaPhoneNumberId:'223456789012'
});
const dojo=new Map(toolset.tools.map(t=>[t.name,t]));
const readNames=new Set(['whatsapp_list_templates','whatsapp_get_template']);
const safeSpecs=new Map();
const sensitive=/^(?:access[_-]?token|refresh[_-]?token|token|app[_-]?secret|secret|api[_-]?key|credential|authorization|bearer|private[_-]?key|password|wabaId|phoneNumberId|tenantId|clientId)$/i;

function structure(value){
  const stack=[{value,depth:0}],seen=new WeakSet();
  let nodes=0;
  try{
    while(stack.length){
      const {value:v,depth}=stack.pop();
      if(++nodes>1024||depth>12)return false;
      if(v===null||typeof v==='boolean')continue;
      if(typeof v==='string'){
        if(Buffer.byteLength(v,'utf8')>16384||v.includes('\u0000'))return false;
        continue;
      }
      if(typeof v==='number'&&Number.isFinite(v))continue;
      if(typeof v!=='object'||nodeTypes.isProxy(v)||seen.has(v))return false;
      seen.add(v);
      if(Array.isArray(v)){
        const descriptors=Object.getOwnPropertyDescriptors(v),size=descriptors.length?.value;
        if(!Number.isSafeInteger(size)||size>50||
           Reflect.ownKeys(descriptors).length!==size+1)return false;
        for(let i=0;i<size;i++){
          const entry=descriptors[String(i)];
          if(!entry||!Object.hasOwn(entry,'value'))return false;
          stack.push({value:entry.value,depth:depth+1});
        }
        continue;
      }
      if(Object.getPrototypeOf(v)!==Object.prototype)return false;
      const descriptors=Object.getOwnPropertyDescriptors(v);
      const keys=Reflect.ownKeys(descriptors);
      if(keys.length>64)return false;
      for(const key of keys){
        if(typeof key!=='string'||key.length>128||sensitive.test(key)||
          !Object.hasOwn(descriptors[key],'value'))return false;
        stack.push({value:descriptors[key].value,depth:depth+1});
      }
    }
    return true;
  }catch(_){return false;}
}
function publicUrl(input){
  let u;
  try{u=new URL(input);}catch(_){return false;}
  if(u.protocol!=='https:'||u.username||u.password||u.hash)return false;
  const h=u.hostname.toLowerCase();
  // Defense in depth only: host transport still must validate DNS and egress.
  const dynamicDns=['nip.io','sslip.io','localtest.me','lvh.me'];
  if(h==='localhost'||h.endsWith('.localhost')||h.endsWith('.local')||
     dynamicDns.some(d=>h===d||h.endsWith('.'+d)))return false;
  if(h.includes(':'))return false; // deny all IPv6 literals, including mapped localhost
  if(/^\d+(?:\.\d+){3}$/.test(h)){
    const x=h.split('.').map(Number);
    const a=x[0],b=x[1];
    if(x.some(v=>v>255)||a===0||a===10||a===127||a>=224||
      (a===169&&b===254)||(a===172&&b>=16&&b<=31)||
      (a===192&&b===168)||(a===100&&b>=64&&b<=127))return false;
  }
  return true;
}
function urlsSafe(root){
  const stack=[root];
  while(stack.length){
    const v=stack.pop();
    if(!v||typeof v!=='object')continue;
    if(Array.isArray(v)){stack.push(...v);continue;}
    for(const [k,item] of Object.entries(v)){
      if((k==='sourceUrl'||k==='link'||k==='endpointUri')&&
         typeof item==='string'&&!publicUrl(item))return false;
      if(item&&typeof item==='object')stack.push(item);
    }
  }
  return true;
}
/** The official WACRM broker owns its two template tools, never Dojo direct. */
export const PINNED_DOJO_OWNED_NAMES=Object.freeze(
  [...dojo.keys()].filter(n=>!readNames.has(n)));
export function getPinnedDojoInputJsonSchema(name){
  if(!PINNED_DOJO_OWNED_NAMES.includes(name))return null;
  if(!safeSpecs.has(name)){
    const d=dojo.get(name);
    const inputSchema=z.strictObject(d.inputSchema);
    safeSpecs.set(name,{
      parser:inputSchema,
      json:z.toJSONSchema(inputSchema,{target:'draft-7'})
    });
  }
  return safeSpecs.get(name).json;
}
/** Returns a cloned strict Zod result, or null. Never reveals validation errors. */
export function validatePinnedDojoArgs(name,args){
  if(!PINNED_DOJO_OWNED_NAMES.includes(name)||!structure(args))return null;
  const jsonSize=Buffer.byteLength(JSON.stringify(args),'utf8');
  if(jsonSize>32768)return null;
  const parser=getPinnedDojoInputJsonSchema(name)&&safeSpecs.get(name).parser;
  const parsed=parser.safeParse(args);
  if(!parsed.success||!urlsSafe(parsed.data))return null;
  // The upstream SDK accepts any non-empty recipient; enforce the narrower
  // verified E.164 cohort until separately certified BSUID support is added.
  if(Object.hasOwn(parsed.data,'to')&&
      !/^\+[1-9][0-9]{6,14}$/.test(parsed.data.to))return null;
  if(/^whatsapp_send_(?:image|video|audio|voice|document)$/.test(name)){
    if(Number(Object.hasOwn(parsed.data,'id'))+Number(Object.hasOwn(parsed.data,'link'))!==1)
      return null;
  }
  // Even the upstream upload handler has only literal-IP guards. The owner
  // must still enforce DNS, redirect and egress safety before network I/O.
  return parsed.data;
}
