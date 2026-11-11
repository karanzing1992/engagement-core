import test from 'node:test';
import assert from 'node:assert/strict';
import { createWacrmCentralConnectionResolver, WacrmConnectionUnavailable } from '../src/wacrm-route-boundary.mjs';
import { createMetaCoreDojoReadAdapter } from '../src/dojo-v26.mjs';

const route = Object.freeze({
  tenantId: 'brand_a', activationId: 42, wabaId: '123456789013',
  phoneNumberId: '123456789012', status: 'active'
});
const credential = Object.freeze({
  tenantId: route.tenantId, activationId: route.activationId,
  wabaId: route.wabaId, phoneNumberId: route.phoneNumberId,
  graphApiVersion: 'v26.0', accessToken: 'synthetic-not-a-real-token-00000000',
  appSecret: 'synthetic-not-a-real-secret'
});
function make(opts = {}) {
  const calls = [];
  const resolve = createWacrmCentralConnectionResolver({
    readRoute: async id => { calls.push('route'); return id === 'brand_a' ? route : null; },
    resolveCredential: async () => { calls.push('credential'); return credential; },
    ...opts,
  });
  return { resolve, calls };
}

test('WACRM route binding supplies exactly matching v26 credentials', async () => {
  const {resolve,calls} = make();
  const out=await resolve('brand_a');
  assert.equal(out.graphApiVersion,'v26.0');
  assert.equal(out.businessAccountId,route.wabaId);
  assert.equal(out.phoneNumberId,route.phoneNumberId);
  assert.deepEqual(calls,['route','credential']);
  assert.ok(Object.isFrozen(out));
});
test('unknown tenant cannot resolve credentials', async () => {
  const {resolve,calls} = make();
  await assert.rejects(resolve('brand_b'),WacrmConnectionUnavailable);
  assert.deepEqual(calls,['route']);
});
test('malformed tenant fails before Central query', async () => {
  const {resolve,calls} = make();
  await assert.rejects(resolve('../brand_a'),WacrmConnectionUnavailable);
  assert.deepEqual(calls,[]);
});
test('inactive route blocks credential resolution', async () => {
  const {resolve,calls} = make({readRoute: async () => { calls.push('route'); return {...route,status:'revoked'}; }});
  await assert.rejects(resolve('brand_a'),WacrmConnectionUnavailable);
  assert.deepEqual(calls,['route']);
});
test('wrong WABA/phone, version or tenant binding blocks credentials', async () => {
  for (const c of [{wabaId:'123456789099'},{phoneNumberId:'123456789099'},{graphApiVersion:'v24.0'},{tenantId:'brand_b'},{activationId:43}]) {
    const {resolve} = make({resolveCredential: async () => ({...credential,...c})});
    await assert.rejects(resolve('brand_a'),WacrmConnectionUnavailable);
  }
});
test('missing secure token authority is rejected at construction', () => {
  assert.throws(() => createWacrmCentralConnectionResolver({readRoute: async () => route}),TypeError);
});
test('WACRM-resolved credentials reach existing META CORE read adapter only after user grant', async () => {
  const {resolve} = make();
  const calls=[];
  const adapter = createMetaCoreDojoReadAdapter({
    authorizeTenant: (principal,tenantId) => principal==='staff_a' && tenantId==='brand_a',
    resolveConnection: resolve,
    toolsetFactory: async c => ({dispatch: async (name) => { calls.push({name,waba:c.wabaId}); return {isError:false,structuredContent:{data:[]}}; }}),
  });
  assert.equal((await adapter.invoke({principal:'staff_b',tenantId:'brand_a',toolName:'whatsapp_list_templates'})).error.code,'forbidden');
  assert.equal(calls.length,0);
  assert.equal((await adapter.invoke({principal:'staff_a',tenantId:'brand_a',toolName:'whatsapp_list_templates'})).ok,true);
  assert.equal(calls[0].waba,route.wabaId);
});

test('P2 WACRM route snapshot stays consistent across credential provider awaits',async()=>{
  const mutable={...route};
  let received;
  const {resolve}=make({
    readRoute:async()=>mutable,
    resolveCredential:async expected=>{
      received=expected;
      mutable.tenantId='brand_b';
      mutable.wabaId='999999999999';
      mutable.phoneNumberId='888888888888';
      return credential;
    }
  });
  const got=await resolve('brand_a');
  assert.equal(got.businessAccountId,route.wabaId);
  assert.equal(got.phoneNumberId,route.phoneNumberId);
  assert.equal(received.wabaId,route.wabaId);
  assert.equal(received.tenantId,'brand_a');
});
test('P2 WACRM route accessors cannot run prior to credential resolution',async()=>{
  let reads=0,credentials=0;
  const raw={...route};
  Object.defineProperty(raw,'phoneNumberId',{enumerable:true,
    get(){reads++;throw Error('forbidden inherited getter');}
  });
  const {resolve}=make({
    readRoute:async()=>raw,
    resolveCredential:async()=>{credentials++;return credential;}
  });
  await assert.rejects(resolve('brand_a'),WacrmConnectionUnavailable);
  assert.equal(reads,0);
  assert.equal(credentials,0);
});
