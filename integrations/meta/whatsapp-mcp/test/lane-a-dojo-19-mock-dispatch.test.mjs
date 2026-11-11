import test from 'node:test';
import assert from 'node:assert/strict';
import { MockWhatsAppClient } from '@dojocoding/whatsapp-sdk';
import { createWhatsAppToolset } from '@dojocoding/whatsapp-mcp';

const to='+919999999999',id='123456789012';
const templates=[{id:'300000000010',name:'synthetic_utility',
 language:'en_US',category:'UTILITY',status:'APPROVED',
 components:[{type:'BODY',text:'Synthetic test only'}]}];
const fixtures={
 whatsapp_send_text:{to,body:'Test only'},
 whatsapp_send_image:{to,id},
 whatsapp_send_video:{to,id},
 whatsapp_send_audio:{to,id},
 whatsapp_send_voice:{to,id},
 whatsapp_send_document:{to,id,filename:'test.pdf'},
 whatsapp_send_location:{to,latitude:15.56,longitude:73.75},
 whatsapp_send_contacts:{to,contacts:[{name:{formatted_name:'Synthetic Guest'},phones:[{phone:to}]}]},
 whatsapp_send_interactive_buttons:{to,body:'Choose',buttons:[{id:'one',title:'One'}]},
 whatsapp_send_interactive_list:{to,body:'Choose',button:'Options',
  sections:[{title:'Section',rows:[{id:'row1',title:'Choice 1'}]}]},
 whatsapp_send_template:{to,name:'synthetic_utility',language:'en_US'},
 whatsapp_send_auth_template:{to,name:'synthetic_auth',language:'en_US',otp:'654321'},
 whatsapp_send_carousel_template:{to,name:'synthetic_carousel',language:'en_US',
  cards:[{header:{type:'image',mediaId:id}}]},
 whatsapp_send_reaction:{to,messageId:'wamid.TESTINBOUND123456',emoji:'✅'},
 whatsapp_mark_as_read:{messageId:'wamid.TESTINBOUND123456',typing:true},
 whatsapp_list_templates:{limit:10},
 whatsapp_get_template:{templateId:'300000000010'},
 whatsapp_upload_media_from_url:{sourceUrl:'https://example.org/mock.jpeg',
  mimeType:'image/jpeg',filename:'mock.jpeg'},
 whatsapp_get_media_info:{mediaId:'media.mock-1'}
};
test('All 19 real Dojo MCP handlers dispatch on network-free MockWhatsAppClient',async()=>{
 const mock=new MockWhatsAppClient({phoneNumberId:'223456789012',
  wabaId:id,templates});
 const mcp=createWhatsAppToolset({client:mock,wabaPhoneNumberId:'223456789012'});
 assert.deepEqual(new Set(mcp.tools.map(x=>x.name)),new Set(Object.keys(fixtures)));
 let http=0;
 const saved=globalThis.fetch;
 globalThis.fetch=async (url,opt={})=>{
   http++;
   assert.equal(String(url),'https://example.org/mock.jpeg');
   assert.equal(opt.redirect,'error');
   return new Response(new Uint8Array([255,216,255,217]),{
     status:200,headers:{'content-type':'image/jpeg','content-length':'4'}});
 };
 try{
  for(const [name,args] of Object.entries(fixtures)){
    const result=await mcp.dispatch(name,args);
    assert.notEqual(result.isError,true,name+': '+JSON.stringify(result));
    assert.ok(result.structuredContent,name+' missing structured result');
    if(name==='whatsapp_upload_media_from_url')
      assert.equal(result.structuredContent.mediaId,'media.mock-1');
    if(name==='whatsapp_get_template')
      assert.equal(result.structuredContent.id,'300000000010');
  }
  assert.equal(http,1,'mock HTTP URL only, no Meta request');
  assert.ok(mock.sentMessages.length>=12);
  assert.equal(mock.markReads.length,1);
 }finally{globalThis.fetch=saved;}
});
test('Dojo MockWhastAppClient rejects sends when the service window is closed',async()=>{
 const mock=new MockWhatsAppClient({phoneNumberId:'223456789012',wabaId:id,
   windowTracker:{isWindowOpen:async()=>false},templates});
 const mcp=createWhatsAppToolset({client:mock,wabaPhoneNumberId:'223456789012'});
 const r=await mcp.dispatch('whatsapp_send_text',fixtures.whatsapp_send_text);
 assert.equal(r.isError,true);
 assert.equal(mock.sentMessages.length,0);
});
