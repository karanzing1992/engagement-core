import test from 'node:test';
import assert from 'node:assert/strict';
import { createLaneAProviderMcp } from '../src/lane-a-provider-runtime.mjs';

const tenant='wacrm_'+'a'.repeat(40);
const principal={tenantId:tenant,actorId:'synthetic-reviewer'};
const route={tenantId:tenant,status:'active',activationId:44,
  wabaId:'123456789012',phoneNumberId:'223456789012'};
const policy={operatorApproved:true,irreversibleApproved:true,optInVerified:true,
  customerWindowOpen:true,templateApproved:true,billableSendApproved:true};

function hostProviders(providers,names){
  return createLaneAProviderMcp({
    verifyIdentity:async()=>true,
    authorizeTenant:async()=>true,
    readPolicy:async()=>policy,
    resolveRoute:async()=>route,
    resolveOwnership:async()=>({wabaIdVerified:true}),
    grants:names,enableWriteCandidates:true,providers,
  });
}
const invoke=(mcp,name,args={})=>mcp.callTool(
  {name,arguments:args},
  {tenantId:tenant,verifiedPrincipal:principal,requestId:'host-issued-review-id-123456'}
);

test('Dojo media upload returns reusable synthetic media ID, MIME and byte count',async()=>{
  const mcp=hostProviders({
    dojo:{invoke:async()=>({
      structuredContent:{mediaId:'media.mock-1',mimeType:'image/jpeg',bytes:4}
    })}
  },['whatsapp_upload_media_from_url']);
  const result=await invoke(mcp,'whatsapp_upload_media_from_url',{
    sourceUrl:'https://example.org/synthetic.jpg',mimeType:'image/jpeg'
  });
  assert.equal(result.isError,false,JSON.stringify(result.structuredContent));
  assert.equal(result.structuredContent.data.mediaId,'media.mock-1');
  assert.equal(result.structuredContent.data.mimeType,'image/jpeg');
  assert.equal(result.structuredContent.data.bytes,4);
});
test('Graph WABA business analytics retain bucket metrics without leaking raw phone list',async()=>{
  const upstream={analytics:{
    phone_numbers:['+919999999999'],country_codes:['IN'],granularity:'DAY',
    data_points:[{start:1793491200,end:1793577600,sent:12,delivered:10}]
  },id:'123456789012'};
  const mcp=hostProviders({host:{executePlan:async()=>({ok:true,data:upstream})}},
    ['whatsapp_get_business_analytics']);
  const result=await invoke(mcp,'whatsapp_get_business_analytics',{
    startDate:'2026-11-01',endDate:'2026-11-02'
  });
  assert.equal(result.isError,false,JSON.stringify(result.structuredContent));
  assert.deepEqual(result.structuredContent.data.analytics.data_points,[{
    start:1793491200,end:1793577600,sent:12,delivered:10
  }]);
  assert.equal(result.structuredContent.data.analytics.phone_numbers,undefined);
  assert.ok(!JSON.stringify(result).includes('+919999999999'));
});
test('Graph template analytics retain aggregate template buckets and click metrics',async()=>{
  const upstream={template_analytics:{data:[{
    template_id:'123456789012',
    data_points:[{start:1793491200,end:1793577600,
      sent:18,delivered:17,read:9,clicked:4}]
  }]}};
  const mcp=hostProviders({host:{executePlan:async()=>({ok:true,data:upstream})}},
    ['whatsapp_get_template_analytics']);
  const result=await invoke(mcp,'whatsapp_get_template_analytics',{
    startDate:'2026-11-01',endDate:'2026-11-02'
  });
  assert.equal(result.isError,false,JSON.stringify(result.structuredContent));
  assert.equal(result.structuredContent.data.template_analytics.data[0].data_points[0].clicked,4);
  assert.equal(result.structuredContent.data.template_analytics.data[0].template_id,'123456789012');
});
test('unexpected nested credentials in analytics fail closed',async()=>{
  const upstream={analytics:{data_points:[{start:1,sent:2,access_token:'fake-secret'}]}};
  const mcp=hostProviders({host:{executePlan:async()=>({ok:true,data:upstream})}},
    ['whatsapp_get_business_analytics']);
  const result=await invoke(mcp,'whatsapp_get_business_analytics',{
    startDate:'2026-11-01',endDate:'2026-11-02'
  });
  assert.equal(result.isError,true);
  assert.ok(!JSON.stringify(result).includes('fake-secret'));
});
test('analytics data does not escape on unrelated business profile operations',async()=>{
  const upstream={analytics:{data_points:[{sent:42}]},id:'123456789012'};
  const mcp=hostProviders({host:{executePlan:async()=>({ok:true,data:upstream})}},
    ['whatsapp_get_business_profile']);
  const result=await invoke(mcp,'whatsapp_get_business_profile');
  assert.equal(result.isError,false);
  assert.equal(result.structuredContent.data.analytics,undefined);
});
