import "jsr:@supabase/functions-js/edge-runtime.d.ts";
const DEST="https://saczglesalubroyaucqe.supabase.co/functions/v1/mcp-connection-consent/mcp";
Deno.serve((req:Request)=>{
 const u=new URL(req.url);
 if(req.method==="GET"&&u.pathname.endsWith("/health"))
 return Response.json({ok:true,service:"wpcontrol-auth",version:"0.5.0",mode:"service-aware-consent"},{headers:{"cache-control":"no-store"}});
 if(req.method!=="GET"&&req.method!=="HEAD")return Response.json({error:"method_not_allowed"},{status:405});
 const target=new URL(DEST);
 for(const k of ["authorization_id","code","error","error_code","error_description","state","type"]){
  const val=u.searchParams.get(k);
  if(val)target.searchParams.set(k,val);
 }
 return new Response(null,{status:302,headers:{"location":target.href,"cache-control":"private, no-store","referrer-policy":"no-referrer","x-content-type-options":"nosniff"}});
});