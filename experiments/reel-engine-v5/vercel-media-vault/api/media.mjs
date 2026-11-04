import { put, get } from '@vercel/blob';
const ok = (s) => /^(source|render)\/[a-zA-Z0-9][a-zA-Z0-9._/-]{0,180}\.mp4$/.test(s) && !s.split('/').includes('..');
const auth=(req)=> Boolean(process.env.VAULT_TOKEN)&&req.headers.authorization==='Bearer '+process.env.VAULT_TOKEN;
const reply=(res,status,obj)=>res.status(status).json(obj);
export default async function handler(req,res) {
 res.setHeader('Cache-Control','private, no-store');
 if(!process.env.BLOB_READ_WRITE_TOKEN||!process.env.VAULT_TOKEN)return reply(res,503,{error:'not_configured'});
 const key=typeof req.query.key==='string'?req.query.key:'';
 if(!ok(key))return reply(res,400,{error:'invalid_key'});
 if(!auth(req))return reply(res,401,{error:'unauthorized'});
 if(req.method==='PUT'){
  if(req.headers['content-type']?.split(';')[0]!=='video/mp4')return reply(res,415,{error:'mp4_only'});
  // Server-side upload suitable for small files; large files require client upload token flow.
  const chunks=[];let size=0;
  for await(const chunk of req){size+=chunk.length;if(size>4*1024*1024)return reply(res,413,{error:'use_client_upload_for_large_files'});chunks.push(chunk);}
  const blob=await put(key,Buffer.concat(chunks),{access:'private',addRandomSuffix:false,contentType:'video/mp4',token:process.env.BLOB_READ_WRITE_TOKEN});
  return reply(res,201,{pathname:blob.pathname,size});
 }
 if(req.method==='GET'){
  const blob=await get(key,{access:'private',token:process.env.BLOB_READ_WRITE_TOKEN});
  if(!blob)return reply(res,404,{error:'not_found'});
  res.statusCode=200;res.setHeader('Content-Type','video/mp4');res.setHeader('Accept-Ranges','bytes');res.setHeader('Content-Disposition','inline');
  if(blob.size)res.setHeader('Content-Length',String(blob.size));
  for await(const chunk of blob.stream)res.write(chunk);
  return res.end();
 }
 return reply(res,405,{error:'method_not_allowed'});
}