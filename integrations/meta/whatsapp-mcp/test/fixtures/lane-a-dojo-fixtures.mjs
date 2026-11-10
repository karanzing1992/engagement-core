/** Deterministic test-only valid upstream Dojo 0.5.0 MCP arguments. */
const to='+919999999999',id='123456789012';
const fixtures={
 whatsapp_send_text:{to,body:'Synthetic test only'},
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
 whatsapp_upload_media_from_url:{sourceUrl:'https://example.org/mock.jpeg',
  mimeType:'image/jpeg',filename:'mock.jpeg'},
 whatsapp_get_media_info:{mediaId:'media.mock-1'}
};
export function dojoFixture(name){
 const v=fixtures[name];
 if(!v)throw new Error('Missing deterministic Dojo fixture: '+name);
 return JSON.parse(JSON.stringify(v));
}
export const dojoFixtureNames=Object.freeze(Object.keys(fixtures));
