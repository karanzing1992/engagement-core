import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {WHATSAPP_LANE_A_CATALOG,WHATSAPP_LANE_A_EXCLUDED} from '../src/lane-a-capability-catalog.mjs';
const manifest=JSON.parse(readFileSync(fileURLToPath(new URL('../manifest/lane-a-whatsapp-mcp-v1.json',import.meta.url)),'utf8'));
test('Lane A immutable integration manifest exactly matches 55 operations and zero release grants',()=>{
 assert.equal(manifest.schemaVersion,'1.0.0-rc1');
 assert.equal(manifest.graphApiVersion,'v26.0');
 assert.deepEqual(manifest.defaultGrants,[]);
 assert.equal(manifest.writeEnabled,false);
 assert.equal(manifest.liveProviderBound,false);
 assert.equal(manifest.productionEnabled,false);
 assert.equal(manifest.operations.length,55);
 assert.deepEqual(new Set(manifest.operations.map(x=>x.name)),
    new Set(WHATSAPP_LANE_A_CATALOG.map(x=>x.name)));
 assert.deepEqual(new Set(manifest.excluded),new Set(WHATSAPP_LANE_A_EXCLUDED));
 const counts={};
 for(const op of manifest.operations){
  const d=WHATSAPP_LANE_A_CATALOG.find(x=>x.name===op.name);
  assert.equal(op.group,d.group);
  assert.equal(op.kind,d.kind);
  assert.equal(op.adapter,d.adapter);
  assert.equal(op.state,'SOURCE_ONLY_NO_RUNTIME_GRANT');
  assert.ok(['whatsapp_business_management','whatsapp_business_messaging','internal_wacrm_tenant_grant'].includes(op.providerPermission));
  counts[op.adapter]=(counts[op.adapter]??0)+1;
 }
 assert.deepEqual(counts,{host:33,dojo:17,broker:2,wacrm:3});
});
test('manifest has no credential, customer or live endpoint values',()=>{
 const str=JSON.stringify(manifest);
 assert.ok(!/Bearer\s|access_token\s*[:=]|client_secret\s*[:=]|sk-[A-Za-z0-9]+/i.test(str));
 assert.equal(str.includes('PRODUCTION_ENABLED'),false);
 assert.ok(!Object.hasOwn(manifest,'secret'));
});
