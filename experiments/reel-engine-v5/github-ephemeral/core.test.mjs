import test from "node:test";
import assert from "node:assert/strict";
import {validateJob,jobTag,chunkAssetName,parseMetadata,checkSourceAssets,validateChunkRequest,expired,outputAssets} from "./core.mjs";
const valid = () => ({
  job_id:"moksha-guest-review-001",project_id:"moksha_wellness",
  prompt:"Create a cinematic, feel-good Moksha Wellness guest review Reel.",
  source_sha256:"a".repeat(64),source_bytes:9000,chunk_count:1,
  rights:{source_rights_confirmed:true,people_consent_confirmed:true,external_ai_processing_approved:false}
});
test("valid job has scoped tag and rights decision",()=> {
  const d=validateJob(valid());assert.equal(jobTag(d.job_id),"mad-v5-tmp-moksha-guest-review-001");
  assert.equal(d.state,"awaiting_upload");
  assert.equal(d.rights.external_ai_processing_approved,false);
});
test("unknown projects, missing permissions and malformed hashes fail closed",()=> {
  for(const delta of [{project_id:"evil_site"},{source_sha256:"bad"},{chunk_count:0},
    {source_bytes:100000000,chunk_count:1},{rights:{source_rights_confirmed:true}},
    {job_id:"../bad"},{prompt:"x"}]){
    assert.throws(()=>validateJob({...valid(),...delta}));
  }
});
test("rejects wrong source asset inventory",()=> {
  const d=validateJob(valid());
  assert.equal(checkSourceAssets(d,[{name:"source-000.part",size:9000}]),true);
  for(const a of [[],[{name:"source-000.part",size:5000}],[{name:"source-001.part",size:9000}],
    [{name:"source-000.part",size:9000},{name:"source-000.part",size:9000}]]){
    assert.throws(()=>checkSourceAssets(d,a));
  }
});
test("only explicitly declared binary chunks are allowed",()=> {
  const d=validateJob(valid());
  assert.equal(validateChunkRequest(d,0,{headers:new Headers({"Content-Length":"9000","Content-Type":"application/octet-stream"})}),chunkAssetName(0));
  assert.throws(()=>validateChunkRequest(d,1,{headers:new Headers({"Content-Length":"9000","Content-Type":"application/octet-stream"})}));
  assert.throws(()=>validateChunkRequest(d,0,{headers:new Headers({"Content-Length":"9000","Content-Type":"video/mp4"})}));
  assert.throws(()=>validateChunkRequest({...d,state:"dispatched"},0,{headers:new Headers({"Content-Length":"9000","Content-Type":"application/octet-stream"})}));
});
test("draft release metadata is bound to exact V5 tag",()=> {
  const d=validateJob(valid());const rel={draft:true,tag_name:jobTag(d.job_id),body:JSON.stringify(d)};
  assert.equal(parseMetadata(rel).job_id,d.job_id);
  assert.throws(()=>parseMetadata({...rel,draft:false}));
  assert.throws(()=>parseMetadata({...rel,tag_name:"mad-v5-tmp-otherjob9"}));
});
test("TTL and result asset identity",()=> {
  const created_at="2026-11-03T00:00:00Z";
  assert.equal(expired({created_at},Date.parse("2026-11-04T01:00:00Z")),true);
  assert.equal(expired({created_at},Date.parse("2026-11-03T01:00:00Z")),false);
  assert.equal(outputAssets([{name:"v5-output.mp4",id:7},{name:"v5-receipt.json",id:8}]).ready,true);
  assert.equal(outputAssets([]).ready,false);
});
