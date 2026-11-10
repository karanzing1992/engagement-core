import test from 'node:test';
import assert from 'node:assert/strict';
import { createWhatsAppToolset } from '@dojocoding/whatsapp-mcp';

const phone='+919999999999';
const mid='wamid.synthetic12345';
const media='123456789012';
const base={to:phone};
const fixtures={
 whatsapp_send_text:{...base,body:'Synthetic delivery test'},
 whatsapp_send_image:{...base,id:media,caption:'Synthetic image'},
 whatsapp_send_video:{...base,id:media},
 whatsapp_send_audio:{...base,id:media},
 whatsapp_send_voice:{...base,id:media},
 whatsapp_send_document:{...base,id:media,filename:'synthetic.pdf'},
 whatsapp_send_location:{...base,latitude:15.689,longitude:73.703},
 whatsapp_send_contacts:{...base,contacts:[{name:{formatted_name:'Synthetic Contact'}}]},
 whatsapp_send_interactive_buttons:{...base,body:'Choose',buttons:[{id:'a',title:'A'}]},
 whatsapp_send_interactive_list:{...base,body:'Choose',button:'Options',
   sections:[{title:'List',rows:[{id:'a',title:'Option A'}]}]},
 whatsapp_send_template:{...base,name:'synthetic_template',language:'en_US'},
 whatsapp_send_auth_template:{...base,name:'synthetic_auth',language:'en_US',otp:'123456'},
 whatsapp_send_carousel_template:{...base,name:'synthetic_carousel',language:'en_US',
   cards:[{header:{type:'image',mediaId:media}}]},
 whatsapp_send_reaction:{...base,messageId:mid,emoji:'👍'},
 whatsapp_mark_as_read:{messageId:mid,typing:true},
 whatsapp_list_templates:{limit:10},
 whatsapp_get_template:{templateId:media},
 whatsapp_get_media_info:{mediaId:media},
 whatsapp_upload_media_from_url:{sourceUrl:'https://public.example.invalid/picture.jpg',mimeType:'image/jpeg'},
};
const template={id:media,name:'synthetic_template',language:'en_US',status:'APPROVED',
 category:'UTILITY',components:[]};
const calls=[];
const send=method=>async input=>{
  calls.push({method,input});
  return {messages:[{id:'wamid.synthetic_outbound_12345'}]};
};
const client={
 sendText:send('text'),sendImage:send('image'),sendVideo:send('video'),sendAudio:send('audio'),
 sendVoice:send('voice'),sendDocument:send('document'),sendLocation:send('location'),
 sendContacts:send('contacts'),sendInteractive:send('interactive'),sendTemplate:send('template'),
 sendAuthTemplate:send('auth_template'),sendCarouselTemplate:send('carousel'),
 sendReaction:send('reaction'),
 markAsRead:async input=>{calls.push({method:'ack',input});return {success:true};},
 listTemplates:async input=>{
   calls.push({method:'list_templates',input});return {data:[template],paging:{}};
 },
 getTemplate:async id=>{
   calls.push({method:'get_template',id});return template;
 },
 downloadMedia:async id=>{
   calls.push({method:'get_media',id});
   return {id,mimeType:'image/jpeg',sha256:'abcdef',fileSize:4,url:'mock://never-expose'};
 },
 uploadMedia:async input=>{
   calls.push({method:'upload',input});
   return {id:media};
 }
};
test('all 19 installed upstream Dojo MCP handlers dispatch to fake transport without Meta credentials',async()=>{
  const ts=createWhatsAppToolset({client,wabaPhoneNumberId:'223456789012'});
  assert.deepEqual(new Set(ts.tools.map(x=>x.name)),new Set(Object.keys(fixtures)));
  const originalFetch=globalThis.fetch;
  const fetches=[];
  globalThis.fetch=async (url,options)=>{
    fetches.push({url:String(url),options});
    assert.equal(String(url),'https://public.example.invalid/picture.jpg');
    assert.equal(options?.redirect,'error');
    return new Response(new Uint8Array([255,216,255,217]),{
      status:200,headers:{'content-type':'image/jpeg'}
    });
  };
  try{
    for(const [name,args]of Object.entries(fixtures)){
      const out=await ts.dispatch(name,args);
      assert.notEqual(out.isError,true,name+': '+JSON.stringify(out).slice(0,300));
      assert.ok(out.structuredContent,name+' missing MCP structured result');
    }
  }finally{globalThis.fetch=originalFetch}
  assert.equal(calls.length,19);
  assert.equal(fetches.length,1);
  assert.ok(calls.some(x=>x.method==='upload'));
  assert.ok(calls.some(x=>x.method==='get_media'));
  assert.ok(calls.some(x=>x.method==='ack'));
});
test('upstream send rejection and malformed schema do not accidentally call provider',async()=>{
  let invoked=0;
  const ts=createWhatsAppToolset({
    client:{sendText:async()=>{invoked++;return {messages:[{id:mid}]}}},
    wabaPhoneNumberId:'223456789012',
  });
  const invalids=[
    {name:'whatsapp_send_text',args:{...base,body:''}},
    {name:'whatsapp_send_interactive_buttons',args:{...base,body:'x',buttons:[]}},
    {name:'whatsapp_send_location',args:{...base,latitude:100,longitude:0}},
    {name:'whatsapp_send_carousel_template',args:{...base,name:'a',language:'en_US',cards:[]}},
  ];
  for(const {name,args}of invalids){
    const out=await ts.dispatch(name,args);
    assert.equal(out.isError,true,name);
  }
  assert.equal(invoked,0);
});
test('upstream URL guard rejects private, local, and userinfo media locations before fake fetch',async()=>{
  const ts=createWhatsAppToolset({
    client:{uploadMedia:async()=>{throw Error('never upload');}},
    wabaPhoneNumberId:'223456789012',
  });
  const forbiddenUrls=[
    'http://example.org/img.jpg','https://127.0.0.1/img.jpg',
    'https://169.254.169.254/latest/meta-data','https://localhost/file',
    'https://user:pass@example.org/img.jpg'
  ];
  for(const sourceUrl of forbiddenUrls){
    const r=await ts.dispatch('whatsapp_upload_media_from_url',{
      sourceUrl,mimeType:'image/jpeg'
    });
    assert.equal(r.isError,true,sourceUrl);
  }
});
