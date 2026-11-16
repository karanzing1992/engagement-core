
import {createClient} from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.117.2/+esm";
const qs=new URLSearchParams(location.search),aid=qs.get("authorization_id")||"";
const base=location.origin;
const names={wordpress:"WordPress Control",linux:"Generic SSH Linux",manbir:"Manbir SSH",mcp:"MCP Connection"};
const ui=(id)=>document.getElementById(id),msg=(s)=>ui("status").textContent=s;
const current=location.pathname.split("/").pop();
function category(str){str=String(str||"").toLowerCase();
if(/manbir|pine.?manbir/.test(str))return "manbir";
if(/generic.?linux|linux.?ssh|ssh.?linux/.test(str))return "linux";
if(/wp.?control|wordpress/.test(str))return "wordpress";
return "mcp"}
function brand(type){ui("title").textContent=names[type]||names.mcp;ui("tag").textContent=(type||"mcp").toUpperCase()}
brand(names[current]?current:"mcp");
const sb=createClient("https://saczglesalubroyaucqe.supabase.co","__SUPABASE_PUBLISHABLE_KEY__",{
auth:{storage:localStorage,storageKey:"mcp-oauth-"+aid,persistSession:true,detectSessionInUrl:true,autoRefreshToken:true,flowType:"pkce"}});
async function load(){
if(!/^[a-zA-Z0-9_-]{10,256}$/.test(aid)){msg("Start authorization from the ChatGPT plugin.");return}
let {data:{session},error:authError}=await sb.auth.getSession();
if(authError){msg(authError.message);return}
if(!session){ui("login").hidden=false;ui("approval").hidden=true;msg("Sign in to continue.");return}
ui("login").hidden=true;msg("Checking OAuth client…");
const {data,error}=await sb.auth.oauth.getAuthorizationDetails(aid);
if(error){msg(error.message);return}
if(data?.redirect_url){location.assign(data.redirect_url);return}
const client=data?.client||{},clientName=client.name||client.client_name||"ChatGPT";
const type=category(clientName+" "+(client.client_uri||""));
if(type!=="mcp"&&current!==type){location.replace(base+"/"+type+"?authorization_id="+encodeURIComponent(aid));return}
brand(type);ui("requester").textContent=clientName;ui("scopes").textContent=String(data?.scope||"email");
ui("approval").hidden=false;msg("Review and authorize only if you initiated this connection.");
}
ui("form").addEventListener("submit",async e=>{e.preventDefault();msg("Signing in…");
const {error}=await sb.auth.signInWithPassword({email:ui("email").value.trim(),password:ui("password").value});
if(error){msg(error.message);return}await load()});
ui("send").addEventListener("click",async()=>{if(!ui("email").value.trim()){msg("Enter your email.");return}
msg("Sending verification email…");

const {error}=await sb.auth.signInWithOtp({email:ui("email").value.trim(),options:{shouldCreateUser:false}});
msg(error?error.message:"Check your email for a sign-in link or verification code.");
if(!error){ui("otpbox").hidden=false;ui("otp").focus()}});
ui("verify").addEventListener("click",async()=>{const email=ui("email").value.trim(),token=ui("otp").value.trim();if(!email){msg("Enter your account email above.");ui("email").focus();return}if(!/^[0-9]{6,8}$/.test(token)){msg("Enter the 6- to 8-digit code from your email.");ui("otp").focus();return}msg("Verifying…");const {error}=await sb.auth.verifyOtp({
email,token,type:"email"});
if(error){msg(error.message);return}await load()});
for(const action of ["approve","deny"])ui(action).addEventListener("click",async()=>{
ui("approve").disabled=true;ui("deny").disabled=true;msg("Processing authorization…");
const {data,error}=await sb.auth.oauth[action==="approve"?"approveAuthorization":"denyAuthorization"](aid);
if(error){msg(error.message);ui("approve").disabled=false;ui("deny").disabled=false;return}
if(data?.redirect_url)location.assign(data.redirect_url);else msg("OAuth callback was not returned.");
});
load().catch(e=>msg(e.message||"Unexpected authorization error."));
