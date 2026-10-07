import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.117.2/+esm";

const PROJECT_URL="https://saczglesalubroyaucqe.supabase.co";
const PUBLIC_KEY="sb_publishable_QWn0aEO4-fHulmZaUacbIQ_1ejYsDXY";
const supabase=createClient(PROJECT_URL,PUBLIC_KEY,{auth:{detectSessionInUrl:true,persistSession:true,flowType:"pkce"}});

const qs=new URLSearchParams(location.search);
let authorizationId=qs.get("authorization_id")||localStorage.getItem("wpcontrol_authorization_id");
if(authorizationId) localStorage.setItem("wpcontrol_authorization_id",authorizationId);

const login=document.querySelector("#login");
const consent=document.querySelector("#consent");
const status=document.querySelector("#status");
const email=document.querySelector("#email");
const send=document.querySelector("#send");
const approve=document.querySelector("#approve");
const deny=document.querySelector("#deny");
const say=(t)=>status.textContent=t||"";

async function boot(){
  if(!authorizationId){
    say("Missing authorization request. Start the connection from ChatGPT.");
    return;
  }

  const {data:{session}}=await supabase.auth.getSession();
  if(!session){
    login.classList.remove("hidden");
    consent.classList.add("hidden");
    say("Sign in to continue.");
    return;
  }

  const r=await supabase.auth.oauth.getAuthorizationDetails(authorizationId);
  if(r.error){
    say(r.error.message||"Could not load the authorization request.");
    return;
  }

  if(r.data?.redirect_url&&!r.data?.authorization_id){
    location.replace(r.data.redirect_url);
    return;
  }

  document.querySelector("#clientName").textContent=r.data?.client?.name||r.data?.client_name||"ChatGPT";
  document.querySelector("#scopeText").textContent=r.data?.scope||"email";
  consent.classList.remove("hidden");
  login.classList.add("hidden");
  say("Review the request, then approve or deny.");
}

send.addEventListener("click",async()=>{
  const v=email.value.trim();
  if(!v){say("Enter your email address.");return;}
  send.disabled=true;
  const callback=location.origin+"/?authorization_id="+encodeURIComponent(authorizationId);
  const r=await supabase.auth.signInWithOtp({email:v,options:{emailRedirectTo:callback,shouldCreateUser:false}});
  send.disabled=false;
  say(r.error?r.error.message:"Check your email for the sign-in link, then open it in this browser.");
});

approve.addEventListener("click",async()=>{
  approve.disabled=true;
  const r=await supabase.auth.oauth.approveAuthorization(authorizationId);
  if(r.error){approve.disabled=false;say(r.error.message);return;}
  localStorage.removeItem("wpcontrol_authorization_id");
  location.href=r.data.redirect_url;
});

deny.addEventListener("click",async()=>{
  deny.disabled=true;
  const r=await supabase.auth.oauth.denyAuthorization(authorizationId);
  if(r.error){deny.disabled=false;say(r.error.message);return;}
  localStorage.removeItem("wpcontrol_authorization_id");
  location.href=r.data.redirect_url;
});

supabase.auth.onAuthStateChange(()=>boot());
boot();
