#!/usr/bin/env node
/**
 * Isolated synthetic-only test of the real owner-upload Worker and its D1/KV
 * transport contract. Uses Miniflare and ephemeral credentials/stores.
 * DOES NOT call production, access guest footage, Groq, or social APIs.
 * Signed live GitHub OIDC and mobile owner-code UX remain independent gates.
 */
import assert from 'node:assert/strict';
import { createHash, randomBytes } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Miniflare } from 'miniflare';

const here=dirname(fileURLToPath(import.meta.url));
const parent=join(here,'..');
const hash=x=>createHash('sha256').update(x).digest('hex');
const ownerCode=randomBytes(36).toString('base64url');
const origin='https://reel.delulutech.in';
const base='http://localhost:8787';
const root=mkdtempSync(join(tmpdir(),'mad-v5-private-transport-'));
const mf=new Miniflare({
  modules:true,
  scriptPath:join(parent,'worker.mjs'),
  compatibilityDate:'2026-10-25',
  d1Databases:{DB:'private-transport-test-db'},
  kvNamespaces:{MEDIA_KV:'private-transport-test-kv'},
  bindings:{MAD_OWNER_CODE_SHA256:hash(ownerCode)},
  log: { level: 'ERROR' },
});
async function run(){
  const db=await mf.getD1Database('DB');
  for(const file of ['002_media.sql','003_chunks.sql','010_serialized_queue.sql']){
    await db.exec(readFileSync(join(parent,file),'utf8'));
  }
  const kv=await mf.getKVNamespace('MEDIA_KV');
  const headers=(auth=true,orig=origin)=>({
    Origin:orig,
    ...(auth?{Authorization:'Bearer nk-'+ownerCode}:{}),
  });
  const call=(method,path,{body,auth=true,orig=origin,extra={}}={})=>
    mf.dispatchFetch(base+path,{
      method,headers:{...headers(auth,orig),...extra},
      ...(body===undefined?{}:{body}),
    });
  const json=(method,path,data,opts={})=>
    call(method,path,{...opts,body:JSON.stringify(data),
      extra:{'Content-Type':'application/json',...(opts.extra||{})}});
  const equalStatus=(res,code,label)=>assert.equal(res.status,code,label);
  try{
    const health=await call('GET','/health',{auth:false});
    equalStatus(health,200,'health');
    const alive=await health.json();
    assert.equal(alive.private_review_upload_ready,true);
    console.log('GATE_01_HEALTH_AND_ISOLATION_PASS');

    equalStatus(await json('POST','/v1/media/uploads',{}, {auth:false}),401,'anonymous denied');
    equalStatus(await json('POST','/v1/media/uploads',{}, {orig:'https://foreign.invalid'}),403,'origin denied');
    equalStatus(await json('POST','/v1/media/uploads',{}, {extra:{Authorization:'Bearer nk-invalid'}}),401,'forged key denied');
    equalStatus(await call('OPTIONS','/v1/media/uploads',{auth:false}),204,'allowed preflight');
    equalStatus(await call('OPTIONS','/v1/media/uploads',{auth:false,orig:'https://foreign.invalid'}),403,'foreign preflight');
    console.log('GATE_02_AUTH_ORIGIN_AND_PREFLIGHT_PASS');

    const fixture=join(root,'synthetic-only.mp4');
    const ffmpeg=spawnSync('ffmpeg',['-hide_banner','-loglevel','error','-y',
      '-f','lavfi','-i','testsrc2=size=180x320:rate=15',
      '-f','lavfi','-i','sine=frequency=440:sample_rate=44100',
      '-t','4','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',
      '-c:a','aac','-shortest',fixture],{timeout:60000});
    assert.equal(ffmpeg.status,0,'synthetic source FFmpeg generation');
    const source=readFileSync(fixture);
    assert(source.byteLength>1024 && source.byteLength<4*1024*1024);
    const meta={name:'synthetic-only.mp4',size:source.byteLength,mime:'video/mp4',sha256:hash(source)};
    equalStatus(await json('POST','/v1/media/uploads',{...meta,mime:'video/unknown'}),400,'reject mime');
    equalStatus(await json('POST','/v1/media/uploads',{...meta,sha256:'invalid'}),400,'reject digest');
    const created=await json('POST','/v1/media/uploads',meta);
    equalStatus(created,201,'authorized synthetic upload');
    const {upload_id,chunks,chunk_bytes}=await created.json();
    assert(upload_id.startsWith('upload-') && chunks===1 && chunk_bytes===4*1024*1024);
    const chunkPath='/v1/media/uploads/'+upload_id+'/chunks/0';
    equalStatus(await call('PUT',chunkPath,{body:source,extra:{'X-Chunk-SHA256':'0'.repeat(64)}}),422,'bad source digest rejected');
    const stored=await call('PUT',chunkPath,{body:source,extra:{'X-Chunk-SHA256':hash(source)}});
    equalStatus(stored,200,'verified source accepted');
    assert.equal((await stored.json()).sha256,hash(source));
    equalStatus(await call('PUT',chunkPath,{body:source,extra:{'X-Chunk-SHA256':hash(source)}}),200,'idempotent retry');
    equalStatus(await call('PUT',chunkPath,{body:source,extra:{'X-Chunk-SHA256':'1'.repeat(64)}}),409,'conflicting retry');
    const readSource=await kv.get('private/mad-v1/source/'+upload_id+'/0','arrayBuffer');
    assert.equal(hash(Buffer.from(readSource)),hash(source),'KV source readback');
    const completed=await json('POST','/v1/media/uploads/'+upload_id+'/complete',{});
    equalStatus(completed,200,'finalize');
    assert.equal((await completed.json()).state,'complete');
    console.log('GATE_03_SHA_CHUNK_UPLOAD_KV_READBACK_PASS');

    const prompt='Synthetic color-pattern technical preview; never real guest footage or publication';
    equalStatus(await json('POST','/v1/media/jobs',{upload_id,prompt,rights_confirmed:true,people_consent:false,external_ai_approved:true}),400,'consent gate');
    equalStatus(await json('POST','/v1/media/jobs',{upload_id,prompt,rights_confirmed:true,people_consent:true,external_ai_approved:false}),400,'external AI gate');
    const accepted=await json('POST','/v1/media/jobs',{upload_id,prompt,rights_confirmed:true,people_consent:true,external_ai_approved:true});
    equalStatus(accepted,201,'synthetic job accepted');
    const {job_id}=await accepted.json();
    assert(job_id.startsWith('madmedia-'));
    const statusPath='/v1/media/jobs/'+job_id;
    const status=await call('GET',statusPath);
    equalStatus(status,200,'job status');
    assert.equal((await status.json()).state,'queued');
    equalStatus(await call('GET',statusPath+'/preview'),409,'premature preview denied');
    equalStatus(await call('GET',statusPath+'/receipt'),409,'premature receipt denied');
    equalStatus(await call('GET',statusPath,{auth:false}),401,'owner job privacy');
    console.log('GATE_04_CONSENT_QUEUE_AND_PREVIEW_DENIAL_PASS');

    // Inject a known synthetic ONLY output, simulating an already verified
    // signed-render completion. This certifies preview transport, NOT OIDC or
    // actual production media processing. No source is ever published.
    const receipt={status:'PRIVATE_REAL_MEDIA_TECHNICAL_DRAFT',
      video:{sha256:hash(source),bytes:source.byteLength,full_decode:true,
        width:180,height:320,codec:'h264',audio_codec:'aac'},
      creative_model_called:false,artistic_quality_certified:false,
      public_release_certified:false,music_rights_certified:false,published:false};
    await kv.put('private/mad-v1/output/'+job_id+'/0',source,{expirationTtl:172800});
    await db.prepare('UPDATE mad_v1_media_jobs SET state=?,result_bytes=?,result_sha256=?,result_chunks=?,result_receipt=? WHERE job_id=?')
      .bind('review_ready',source.byteLength,hash(source),1,JSON.stringify(receipt),job_id).run();
    const preview=await call('GET',statusPath+'/preview');
    equalStatus(preview,200,'owner preview readback');
    assert.equal(preview.headers.get('cache-control'),'private, no-store');
    assert.equal(preview.headers.get('content-type'),'video/mp4');
    const bytes=Buffer.from(await preview.arrayBuffer());
    assert.equal(hash(bytes),hash(source),'preview byte digest');
    const previewFile=join(root,'private-preview.mp4');
    writeFileSync(previewFile,bytes);
    const verified=spawnSync('ffmpeg',['-nostdin','-v','error','-i',previewFile,'-f','null','-'],{timeout:60000});
    assert.equal(verified.status,0,'full decode of preview');
    const received=await call('GET',statusPath+'/receipt');
    equalStatus(received,200,'private receipt');
    assert.equal((await received.json()).receipt.published,false);
    equalStatus(await call('GET',statusPath+'/preview',{auth:false}),401,'private preview denied anonymously');
    equalStatus(await call('GET',statusPath+'/preview',{orig:'https://foreign.invalid'}),403,'foreign preview denied');
    console.log('GATE_05_PRIVATE_PREVIEW_SHA_DECODE_NEGATIVE_AUTH_PASS');

    const past=Math.floor(Date.now()/1000)-10;
    await db.prepare('UPDATE mad_v1_media_jobs SET expires_at=? WHERE job_id=?').bind(past,job_id).run();
    equalStatus(await call('GET',statusPath+'/preview'),409,'expired preview denied');
    await db.prepare('UPDATE mad_v1_uploads SET expires_at=? WHERE id=?').bind(past,upload_id).run();
    equalStatus(await call('GET','/v1/media/uploads/'+upload_id),404,'expired source denied');
    const metrics=await db.prepare('SELECT COUNT(*) AS n FROM mad_v1_media_jobs').first();
    assert.equal(metrics.n,1,'synthetic only; exactly one local job');
    console.log('GATE_06_EXPIRY_AND_PRIVATE_ONLY_PASS');
    console.log('MAD_V5_PRIVATE_UPLOAD_KV_PREVIEW_EMULATED_ACCEPTANCE_PASS; SIGNED_PRODUCTION_RUN_PENDING');
  } finally { await mf.dispose(); rmSync(root,{recursive:true,force:true}); }
}
run().catch(async e=>{console.error('MAD_V5_PRIVATE_TRANSPORT_TEST_FAILED',e?.message||'unknown');process.exitCode=1;});
