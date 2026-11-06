// Additive V6 event wake. Reuses existing, scoped V5 GitHub dispatch secret.
// This module never touches V5 job routes or V5 media.
const ID=/^v6job-[a-f0-9]{32}$/;
const TARGET="https://api.github.com/repos/karanzing1992/engagement-core/actions/workflows/mad-v6-kv-filmcraft.yml/dispatches";
const response=(data,status)=>new Response(JSON.stringify(data),{status,headers:{"content-type":"application/json","cache-control":"no-store"}});
export async function dispatchV6(req,env){
 if(!env.DB||!env.MAD_GITHUB_ACTIONS_DISPATCH_TOKEN)return response({error:{message:"V6 dispatch service unavailable"}},503);
 const body=await req.json().catch(()=>null),job=body?.job_id;
 if(!ID.test(job||""))return response({error:{message:"Invalid V6 job identity"}},400);
 const now=Math.floor(Date.now()/1000);
 const item=await env.DB.prepare("SELECT state,expires_at,source_chunks FROM mad_v6_kv_jobs WHERE job_id=?").bind(job).first();
 if(!item||item.state!=="dispatching"||item.expires_at<=now)return response({error:{message:"Private V6 job not eligible for dispatch"}},409);
 try{
   const result=await fetch(TARGET,{method:"POST",redirect:"manual",
     headers:{"Authorization":"Bearer "+env.MAD_GITHUB_ACTIONS_DISPATCH_TOKEN,
       "Accept":"application/vnd.github+json",
       "Content-Type":"application/json",
       "X-GitHub-Api-Version":"2022-11-28",
       "User-Agent":"MAD-V6-Owner-Only-Event-Wake"},
     body:JSON.stringify({ref:"main",inputs:{job_id:job}}),
     signal:AbortSignal.timeout(9000)});
   if(result.status!==204)return response({error:{message:"Existing GitHub dispatch declined V6 job"},status:result.status},503);
   await env.DB.prepare("UPDATE mad_v6_kv_jobs SET state='sent',updated_at=?,error_code=NULL WHERE job_id=? AND state='dispatching'").bind(now,job).run();
   return response({job_id:job,state:"dispatched"},202);
 }catch{return response({error:{message:"GitHub dispatch unavailable"}},503)}
}
