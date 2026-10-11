/* Resumable browser-to-WordPress private video ingest. No public storage. */
(() => {
  "use strict";
  const ui = window.MRSIngest;
  const choose = document.querySelector("#mrs-files");
  const start = document.querySelector("#mrs-start");
  const status = document.querySelector("#mrs-upload-feedback");
  if (!ui || !choose || !start || !status) return;
  const storeKey = "mrsPrivateUploadSession:v1";
  const pause = n => new Promise(resolve => setTimeout(resolve, n));
  function announce(text) { status.textContent = text; }
  async function request(url, {method="GET", body, isBinary=false, sha}={}) {
    const headers = {"X-WP-Nonce": ui.nonce};
    if (isBinary) {
      headers["Content-Type"] = "application/octet-stream";
      headers["X-Chunk-SHA256"] = sha;
    } else if (method !== "GET") headers["Content-Type"]="application/json";
    let last;
    for (let trial=0;trial<4;trial++) {
      try {
        const response = await fetch(url, {
          method, headers, credentials:"same-origin",
          body: isBinary ? body : (body === undefined ? undefined : JSON.stringify(body))
        });
        const data=await response.json();
        if (!response.ok || !data.ok) throw new Error(data.message || data.code || "HTTP "+response.status);
        return data;
      } catch (error) {
        last=error;
        if (trial<3) await pause(500*Math.pow(2,trial));
      }
    }
    throw last;
  }
  async function sha256(buffer) {
    const bytes=new Uint8Array(await crypto.subtle.digest("SHA-256",buffer));
    return Array.from(bytes,x=>x.toString(16).padStart(2,"0")).join("");
  }
  function fingerprint(files) {
    return files.map(f=>f.name+"|"+f.size+"|"+f.lastModified).join(";");
  }
  async function run() {
    const files=Array.from(choose.files||[]);
    if (!files.length || files.length>8) throw new Error("Select 1–8 MP4 or MOV clips.");
    for(const f of files) {
      if(!/\.(mp4|mov|m4v)$/i.test(f.name)||f.size<1024||f.size>ui.maxFile)
        throw new Error(f.name+": only MP4/MOV up to 800 MiB");
    }
    const key=fingerprint(files);
    let prev;
    try { prev=JSON.parse(localStorage.getItem(storeKey)||"null"); } catch { prev=null; }
    let session=prev&&prev.fingerprint===key?prev.id:null;
    if(session) { try { await request(ui.api+session+"/status"); } catch { session=null; } }
    if(!session) {
      const r=await request(ui.api+"start",{method:"POST",body:{files:files.map(f=>({name:f.name,size:f.size}))}});
      session=r.id;
      localStorage.setItem(storeKey,JSON.stringify({id:session,fingerprint:key}));
    }
    const initial=await request(ui.api+session+"/status");
    if(initial.state==="preview_ready_private") { announce("Private final already rendered. Open Reel Uploads for review."); return; }
    const completed=initial.files||[];
    for(let i=0;i<files.length;i++) {
      if(completed[i] && completed[i].complete)continue;
      const file=files[i], count=Math.ceil(file.size/ui.chunk);
      for(let part=0;part<count;part++) {
        const begin=part*ui.chunk;
        const payload=await file.slice(begin,Math.min(file.size,begin+ui.chunk)).arrayBuffer();
        await request(ui.api+session+"/chunk/"+i+"/"+part,{
          method:"POST",body:payload,isBinary:true,sha:await sha256(payload)
        });
        announce("Uploading "+file.name+": "+Math.round((part+1)/count*100)+"%; clip "+(i+1)+" of "+files.length+". Safe to resume if connection drops.");
      }
      const r=await request(ui.api+session+"/finish/"+i,{method:"POST",body:{}});
      announce(file.name+" verified ("+r.sha256.slice(0,12)+"…), "+r.state+".");
    }
    localStorage.removeItem(storeKey);
    announce("All original clips uploaded privately. Session "+session+". Cloud worker will produce a 30-second review-only MP4. Nothing will be posted.");
  }
  start.addEventListener("click",async()=>{
    start.disabled=true;choose.disabled=true;
    announce("Preparing private upload…");
    try { await run(); }
    catch(e) { announce("Upload interrupted: "+e.message+". Re-select the same files and retry to resume."); }
    finally { start.disabled=false;choose.disabled=false; }
  });
})();
