// Restricted synthetic test-only entry; invoked only after pinned owner GitHub OIDC verification.
const hash=async body=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",body)),x=>x.toString(16).padStart(2,"0")).join("");
const reply=(status,data)=>new Response(JSON.stringify(data),{status,headers:{"content-type":"application/json","cache-control":"no-store"}});
export async function seedSynthetic(req,env,id,now){
 const bytes=Number(req.headers.get("content-length"));
 const expected=req.headers.get("x-chunk-sha256")||"";
 if(!Number.isInteger(bytes)||bytes<1024||bytes>262144||!/^[a-f0-9]{64}$/.test(expected))
  return reply(413,{error:"Synthetic-only 256 KiB MP4 required"});
 if(await env.DB.prepare("SELECT job_id FROM mad_v6_kv_jobs WHERE job_id=?").bind(id).first())
  return reply(409,{error:"Synthetic job ID already used"});
 const source=await req.arrayBuffer();
 if(source.byteLength!==bytes||await hash(source)!==expected||
   String.fromCharCode(...new Uint8Array(source).slice(4,8))!=="ftyp")
  return reply(422,{error:"Synthetic source integrity or MP4 signature invalid"});
 await env.MEDIA_KV.put("private/mad-v6/source/"+id+"/0",source,{expirationTtl:3600});
 const d="SYNTHETIC QA: Original FilmCraft color matte with no people or customer recordings.";
 const brief="Make an original cinematic wellness QA reel using only the synthetic color matte.";
 const row=await env.DB.prepare("INSERT INTO mad_v6_kv_jobs(job_id,project_id,file_name,mime,bytes,source_sha256,source_chunks,source_description,brief,state,created_at,updated_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?,'sent',?,?,?)")
   .bind(id,"synthetic-owner-qa","filmcraft-qa.mp4","video/mp4",bytes,expected,1,d,brief,now,now,now+3600).run();
 if(!row.meta?.changes)return reply(409,{error:"Synthetic job admission declined"});
 await env.DB.prepare("INSERT INTO mad_v6_kv_parts(job_id,kind,idx,bytes,sha256) VALUES(?,'source',0,?,?)")
   .bind(id,bytes,expected).run();
 return reply(201,{job_id:id,state:"sent",synthetic_only:true,source_sha256:expected,source_bytes:bytes});
}
