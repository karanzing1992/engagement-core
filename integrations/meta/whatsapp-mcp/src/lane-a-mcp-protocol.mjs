/**
 * META CORE Lane A: MCP SDK protocol bridge (no network listener).
 * Authentication context MUST come from an independently verified host/
 * Lane B resource gateway, never from tools/call request arguments.
 *
 * This constructs a Server instance only. It does NOT connect any transport
 * or publish an endpoint; a trusted caller may bind an in-memory transport
 * for the synthetic protocol-level certification.
 */
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import {
  ListToolsRequestSchema, CallToolRequestSchema
} from '@modelcontextprotocol/sdk/types.js';

const generic=code=>{
  const structuredContent={error:{code,message:'META CORE operation unavailable'}};
  return {isError:true,structuredContent,
    content:[{type:'text',text:JSON.stringify(structuredContent)}]};
};

export function createLaneAProtocolServer({runtime,resolveTrustedContext}={}){
  if(!runtime||typeof runtime.listTools!=='function'||
     typeof runtime.callTool!=='function'||typeof resolveTrustedContext!=='function')
    throw new TypeError('Host runtime and verified per-request identity resolver required');
  const server=new Server({name:'meta-core-lane-a',version:'1.0.0-rc1'},
    {capabilities:{tools:{listChanged:false}}});
  server.setRequestHandler(ListToolsRequestSchema,async()=>({
    tools:runtime.listTools()
  }));
  server.setRequestHandler(CallToolRequestSchema,async(request,extra)=>{
    let context;
    try{context=await resolveTrustedContext({request,extra});}
    catch(_){return generic('forbidden');}
    if(!context||typeof context!=='object')return generic('forbidden');
    // A tool cannot self-assert its principal, tenant, grants or approvals.
    return runtime.callTool({
      name:request.params.name,
      arguments:request.params.arguments??{}
    },context);
  });
  return server;
}
