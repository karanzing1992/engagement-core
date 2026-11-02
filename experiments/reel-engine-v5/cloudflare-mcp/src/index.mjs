import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { createMcpHandler } from "agents/mcp";
import { z } from "zod";

function constantTimeEqual(a,b) { if (typeof a!=="string" || typeof b!=="string" || a.length!==b.length) return false; let d=0; for(let i=0;i<a.length;i++) d|=a.charCodeAt(i)^b.charCodeAt(i); return d===0; }
function createServer(env) {
  const server = new McpServer({name:"moksha-reel-engine-v5",version:"0.1.0"});
  const gh = async (path, options={}) => {
    const response = await fetch("https://api.github.com/repos/"+env.GITHUB_REPO+path, {
      ...options,
      headers:{"Authorization":"Bearer "+env.GITHUB_TOKEN,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"moksha-v5-mcp",...(options.headers||{})}
    });
    const body = await response.text();
    if (!response.ok) throw new Error("GitHub API HTTP "+response.status);
    return body ? JSON.parse(body) : {};
  };
  const response = value => ({content:[{type:"text",text:JSON.stringify(value)}]});
  server.tool("v5_submit_render","Dispatch GitHub-hosted private V5 render from an existing source artifact; does not publish.",{source_artifact_run:z.string().regex(/^\\d+$/),source_artifact_name:z.string().regex(/^[a-zA-Z0-9_-]{1,100}$/),job_id:z.string().regex(/^[a-zA-Z0-9_-]{1,80}$/)},async (args)=>{
    await gh("/actions/workflows/"+encodeURIComponent(env.GITHUB_WORKFLOW)+"/dispatches",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ref:"main",inputs:args})});
    return response({dispatched:true,job_id:args.job_id,workflow:env.GITHUB_WORKFLOW,verification:"Check v5_list_runs; dispatch is not a completed render"});
  });
  server.tool("v5_list_runs","List the latest GitHub-hosted V5 render runs and their states.",{},async()=>response((await gh("/actions/workflows/"+encodeURIComponent(env.GITHUB_WORKFLOW)+"/runs?per_page=10")).workflow_runs.map(r=>({id:r.id,status:r.status,conclusion:r.conclusion,html_url:r.html_url,created_at:r.created_at}))));
  server.tool("v5_get_results","Read render run state and private artifact metadata; artifact download requires GitHub authorization.",{run_id:z.string().regex(/^\\d+$/)},async({run_id})=>{
    const [run,arts]=await Promise.all([gh("/actions/runs/"+run_id),gh("/actions/runs/"+run_id+"/artifacts")]);
    return response({run:{id:run.id,status:run.status,conclusion:run.conclusion,url:run.html_url},artifacts:arts.artifacts.map(a=>({id:a.id,name:a.name,size_in_bytes:a.size_in_bytes,expired:a.expired}))});
  });
  return server;
}
export default {
  async fetch(request, env, ctx) {
    const token=request.headers.get("Authorization")?.replace(/^Bearer /i,"");
    if(!env.MCP_ACCESS_TOKEN || !env.GITHUB_TOKEN || !token || !constantTimeEqual(token,env.MCP_ACCESS_TOKEN)) return new Response("Unauthorized",{status:401,headers:{"WWW-Authenticate":"Bearer"}});
    if(new URL(request.url).pathname!=="/mcp") return new Response("Not Found",{status:404});
    return createMcpHandler(()=>createServer(env))(request,env,ctx);
  }
};
