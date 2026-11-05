#!/usr/bin/env node
/** Offline event-wake contract. Never sends real GitHub requests or reads secrets. */
import assert from 'node:assert/strict';
import {wakeMediaJob,readMediaWake,recoverPendingWakes} from './media_event_wake.mjs';
const uuid='b1234567-1111-4111-8111-123456789abc';
const id='madmedia-'+uuid;
const now=()=>Math.floor(Date.now()/1000);
class Database{
  constructor(){this.job={state:'queued',expires_at:now()+3600};this.wake=null;}
  prepare(sql){
    const self=this;
    return {bind(...args){
      return {
        async all(){
          if(sql.startsWith('SELECT j.job_id FROM mad_v1_media_jobs'))return {results:[{job_id:id}]};
          throw Error('Unexpected D1 list in test: '+sql.slice(0,70));
        },
        async first(){
          if(sql.startsWith('SELECT state,expires_at FROM mad_v1_media_jobs'))return self.job;
          if(sql.startsWith('SELECT state,attempts,last_error_code'))return self.wake ? {...self.wake} : null;
          throw Error('Unexpected D1 SELECT in test: '+sql.slice(0,70));
        },
        async run(){
          if(sql.startsWith('INSERT OR IGNORE INTO mad_v1_media_wakes')){
            if(!self.wake)self.wake={state:'pending',attempts:0,last_attempt_at:null,dispatched_at:null,
              last_http_status:null,last_error_code:null};
            return {meta:{changes:1}};
          }
          if(sql.startsWith("UPDATE mad_v1_media_wakes SET state='dispatching'")){
            const [at,,target,maxAttempts,olderFailed,olderInflight,olderDispatched]=args;
            assert.equal(target,id);
            const w=self.wake;
            const can=w.attempts<maxAttempts && (w.state==='pending' ||
              (w.state==='failed'&&w.last_attempt_at<olderFailed) ||
              (w.state==='dispatching'&&w.last_attempt_at<olderInflight) ||
              (w.state==='dispatched'&&w.dispatched_at<olderDispatched));
            if(!can)return {meta:{changes:0}};
            Object.assign(w,{state:'dispatching',attempts:w.attempts+1,
              last_attempt_at:at,last_error_code:null,last_http_status:null});
            return {meta:{changes:1}};
          }
          if(sql.startsWith("UPDATE mad_v1_media_wakes SET last_error_code='GITHUB_DISPATCH_CREDENTIAL_UNCONFIGURED'")){
            if(self.wake&&['pending','failed'].includes(self.wake.state))self.wake.last_error_code='GITHUB_DISPATCH_CREDENTIAL_UNCONFIGURED';
            return {meta:{changes:1}};
          }
          if(sql.startsWith("UPDATE mad_v1_media_wakes SET state='failed'")){
            const [code,http,,target,at]=args;assert.equal(target,id);
            assert.equal(self.wake.last_attempt_at,at);
            Object.assign(self.wake,{state:'failed',last_error_code:code,last_http_status:http});
            return {meta:{changes:1}};
          }
          if(sql.startsWith("UPDATE mad_v1_media_wakes SET state='dispatched'")){
            const [at,,target,lease]=args;assert.equal(target,id);
            assert.equal(self.wake.last_attempt_at,lease);
            Object.assign(self.wake,{state:'dispatched',dispatched_at:at,last_http_status:204,last_error_code:null});
            return {meta:{changes:1}};
          }
          throw Error('Unexpected D1 UPDATE in test: '+sql.slice(0,70));
        }
      };
    }};
  }
}
let requests=[];
const originalFetch=globalThis.fetch;
try{
  globalThis.fetch=async (url,opts)=>{
    assert.equal(url,'https://api.github.com/repos/karanzing1992/engagement-core/actions/workflows/mad-v5-cloudflare-bridge.yml/dispatches');
    assert.equal(opts.method,'POST');
    assert.equal(opts.headers.Authorization,'Bearer '+'X'.repeat(35));
    assert.equal(opts.redirect,'manual');
    const data=JSON.parse(opts.body);
    assert.deepEqual(data,{ref:'main',inputs:{media_job_id:id}});
    assert(!opts.body.includes('footage')&&!opts.body.includes('prompt'));
    requests.push({url,body:opts.body});
    return {status:204};
  };
  const db=new Database();
  const env={DB:db,MAD_GITHUB_ACTIONS_DISPATCH_TOKEN:'X'.repeat(35)};
  let result=await wakeMediaJob(env,id);
  assert.deepEqual({state:result.state,attempts:result.attempts},{state:'dispatched',attempts:1});
  assert.equal(requests.length,1,'exactly one workflow wake');
  result=await wakeMediaJob(env,id);
  assert.equal(result.state,'dispatched');
  assert.equal(requests.length,1,'idempotent repeated owner click');
  assert.deepEqual(result,await readMediaWake(db,id));
  console.log('WAKE_01_ON_SUBMIT_DISPATCH_204_AND_NO_DUPLICATE_PASS');

  const dbMissing=new Database();
  result=await wakeMediaJob({DB:dbMissing},id);
  assert.equal(result.state,'pending');
  assert.equal(result.last_error_code,'GITHUB_DISPATCH_CREDENTIAL_UNCONFIGURED');
  assert.equal((await readMediaWake(dbMissing,id)).attempts,0);
  result=await wakeMediaJob({DB:dbMissing},id);
  assert.equal(result.attempts,0,'missing secret must not exhaust retry budget');
  assert.equal((await recoverPendingWakes({DB:dbMissing})).status,'dispatch_key_not_configured');
  console.log('WAKE_02_MISSING_CREDENTIAL_NO_RETRY_BUDGET_EXHAUSTION_PASS');

  const dbDenied=new Database();let called=0;
  globalThis.fetch=async ()=>{called++;return {status:401}};
  result=await wakeMediaJob({DB:dbDenied,MAD_GITHUB_ACTIONS_DISPATCH_TOKEN:'X'.repeat(35)},id);
  assert.equal(result.state,'failed');
  assert.equal(result.last_error_code,'GITHUB_DISPATCH_AUTH_REJECTED');
  assert.equal(result.last_http_status,401);
  dbDenied.wake.last_attempt_at-=95;
  globalThis.fetch=async ()=>{called++;return {status:204}};
  result=await wakeMediaJob({DB:dbDenied,MAD_GITHUB_ACTIONS_DISPATCH_TOKEN:'X'.repeat(35)},id);
  assert.equal(result.state,'dispatched');assert.equal(result.attempts,2);
  assert.equal(called,2);
  console.log('WAKE_03_DENIAL_RETRY_AFTER_COOLDOWN_PASS');

  // Cloudflare fetch uses manual redirect; a 302 must not be followed or accepted.
  const dbRedirect=new Database();
  globalThis.fetch=async()=>({status:302});
  result=await wakeMediaJob({DB:dbRedirect,MAD_GITHUB_ACTIONS_DISPATCH_TOKEN:'X'.repeat(35)},id);
  assert.equal(result.state,'failed');
  assert.equal(result.last_http_status,302);
  assert.equal(result.last_error_code,'GITHUB_DISPATCH_UNEXPECTED_REDIRECT');
  const dbTypeError=new Database();
  globalThis.fetch=async()=>{throw new TypeError('Fetch failed')};
  result=await wakeMediaJob({DB:dbTypeError,MAD_GITHUB_ACTIONS_DISPATCH_TOKEN:'X'.repeat(35)},id);
  assert.equal(result.last_http_status,null);
  assert.equal(result.last_error_code,'GITHUB_DISPATCH_FETCH_TYPE_ERROR');
  console.log('WAKE_06_REDIRECT_AND_SAFE_FETCH_ERROR_CLASSIFICATION_PASS');

  const dbClaimed=new Database();dbClaimed.job.state='claimed';
  result=await wakeMediaJob({DB:dbClaimed,MAD_GITHUB_ACTIONS_DISPATCH_TOKEN:'X'.repeat(35)},id);
  assert.equal(result.state,'not_queued');assert.equal(dbClaimed.wake,null);
  const dbExpired=new Database();dbExpired.job.expires_at=now()-1;
  assert.equal((await wakeMediaJob({DB:dbExpired},id)).state,'not_queued');
  assert.equal((await wakeMediaJob({DB:new Database()},'madmedia-invalid')).state,'invalid');
  console.log('WAKE_04_NO_CLAIMED_EXPIRED_OR_INVALID_JOB_DISPATCH_PASS');

  const dbLost=new Database();let calls=0;
  globalThis.fetch=async()=>{calls++;return {status:204}};
  let w=await wakeMediaJob({DB:dbLost,MAD_GITHUB_ACTIONS_DISPATCH_TOKEN:'X'.repeat(35)},id);
  assert.equal(w.state,'dispatched');assert.equal(calls,1);
  let report=await recoverPendingWakes({DB:dbLost,MAD_GITHUB_ACTIONS_DISPATCH_TOKEN:'X'.repeat(35)});
  assert.equal(report.checked,1);assert.equal(calls,1,'recent dispatch must not be duplicated');
  dbLost.wake.dispatched_at-=490;
  report=await recoverPendingWakes({DB:dbLost,MAD_GITHUB_ACTIONS_DISPATCH_TOKEN:'X'.repeat(35)});
  assert.equal(report.checked,1);assert.equal(calls,2,'lost unclaimed dispatch must be retried');
  assert.equal(dbLost.wake.attempts,2);
  dbLost.job.state='review_ready';
  assert.equal((await wakeMediaJob({DB:dbLost,MAD_GITHUB_ACTIONS_DISPATCH_TOKEN:'X'.repeat(35)},id)).state,'already_finished');
  console.log('WAKE_05_STALE_DISPATCH_RECOVERY_NO_DUPLICATE_RENDER_PASS');
  console.log('MAD_V5_EVENT_DRIVEN_WAKE_CONTRACT_PASS');
}finally{globalThis.fetch=originalFetch;}
