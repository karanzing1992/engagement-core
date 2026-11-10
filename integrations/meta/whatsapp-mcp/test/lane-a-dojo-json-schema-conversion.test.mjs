import test from 'node:test';
import assert from 'node:assert/strict';
import {z} from 'zod';
import {createWhatsAppToolset} from '@dojocoding/whatsapp-mcp';
test('Pinned Dojo 0.5.0 tool input schemas convert to truthful MCP JSON Schema',()=>{
 const tools=createWhatsAppToolset({client:{},wabaPhoneNumberId:'223456789012'}).tools;
 assert.equal(tools.length,19);
 for(const tool of tools){
   const json=z.toJSONSchema(z.object(tool.inputSchema),{target:'draft-7'});
   assert.equal(json.type,'object',tool.name);
   assert.ok(json.properties?.to||['whatsapp_mark_as_read','whatsapp_list_templates',
    'whatsapp_get_template','whatsapp_get_media_info','whatsapp_upload_media_from_url'].includes(tool.name),tool.name);
   assert.equal(json.additionalProperties,false,tool.name);
 }
});
