/* Engagement Core G1 design-only prototype. Synthetic records; NO provider calls. */
(()=>{
"use strict";
const screens=[
 ["inbox","Inbox","✉","ENGAGEMENT","Unified Inbox"],
 ["conversation","Conversation","◉","ENGAGEMENT","Conversation Workspace"],
 ["profile","Customer 360°","◎","RELATIONSHIPS","Customer 360°"],
 ["pipeline","Sales Pipeline","▥","SALES","Sales Pipeline"],
 ["deal","Deal Detail","◇","SALES","Deal Detail"],
 ["tasks","Tasks & Follow-ups","☑","WORK","Tasks & Follow-ups"],
 ["channels","Channel Connections","⌁","INTEGRATIONS","Channel Connections"],
 ["assistant","AI Assistant","✧","ASSISTANCE","AI Assistant"],
 ["automations","Automation Builder","⤳","WORKFLOWS","Automation Builder"],
 ["campaigns","Campaigns","▤","OUTREACH","Campaigns & Templates"],
 ["calendar","Calendar & Bookings","▦","SCHEDULE","Calendar & Bookings"],
 ["reports","Reports","▧","ANALYTICS","Reports & Analytics"],
 ["team","Team & Permissions","♙","ACCESS","Team & Permissions"],
 ["integrations","Integration Management","⌘","SYSTEMS","Integration Management"],
 ["system","System & Data","⚙","ADMIN","System & Data Management"]
];
const names=Object.fromEntries(screens.map(s=>[s[0],s]));
const primary=[["home","Home","⌂"],["inbox","Inbox","✉"],["profile","Contacts","◎"],["pipeline","Deals","▥"],["more","More","☰"]];
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
const btn=(text,where,kind="")=>'<button type="button" class="btn '+kind+'" data-go="'+where+'">'+text+"</button>";
const action=(text,key,kind="")=>'<button type="button" class="btn '+kind+'" data-action="'+key+'">'+text+"</button>";
const panel=(title,body,sub="",cta="")=>'<section class="panel"><div class="panel-header"><div><h3>'+title+'</h3>'+(sub?'<p>'+sub+'</p>':"")+'</div>'+cta+'</div>'+body+'</section>';
const head=(name,desc,cta="",eyebrow="SCREEN WIREFRAME")=>'<div class="screen-head"><div><div class="kicker">'+eyebrow+'</div><h2>'+name+'</h2><p>'+desc+'</p></div>'+cta+'</div>';
const person=(name,description,time,where,tag="")=>'<button class="row-card" type="button" data-go="'+where+'"><span class="avatar">'+esc(name[0])+'</span><span class="row-details"><strong>'+esc(name)+'</strong><p>'+esc(description)+'</p></span>'+(tag?'<span class="badge">'+esc(tag)+'</span>':'<span class="tiny muted">'+esc(time)+'</span>')+'</button>';
const pill=(text,tone="")=>'<span class="badge '+tone+'">'+esc(text)+'</span>';
const emptyNote='<div class="note"><strong>Design simulation only.</strong> Actions here illustrate navigation or validation states; this preview cannot send messages, save CRM records, connect providers or run automations.</div>';
const fakeRow=(title,detail,where)=>'<button class="row-card" data-go="'+where+'"><span class="row-details"><strong>'+title+'</strong><p>'+detail+'</p></span><span>›</span></button>';
function home(){
 return '<div class="stack"><section class="hero"><div><div class="kicker" style="color:#d2e0ff">ENGAGEMENT CORE / PRODUCT WIREFRAMES</div><h2>15 CRM screens, one coherent experience.</h2><p>Review mobile interactions and states before functional CRM implementation.</p></div>'+btn("Review Inbox →","inbox","")+'</section>'+
 '<div class="stats"><div class="stat"><small>Screen modules</small><strong>15</strong><small>All navigable</small></div><div class="stat"><small>Device views</small><strong>9</strong><small>Width targets</small></div><div class="stat"><small>Live integrations</small><strong>0</strong><small>Wireframe only</small></div></div>'+
 '<div class="two-column">'+panel("Primary customer journey",fakeRow("Unified Inbox → Conversation","Queue, channel, assignment and reply.","inbox")+fakeRow("Customer 360°","Profile, external booking provenance and timeline.","profile"),"All data shown is synthetic")+
 panel("Sales and operations",fakeRow("Pipeline → Deal Detail","Opportunity stage and owner flows.","pipeline")+fakeRow("Task creation","Associated follow-up and due date.","tasks"),"Mobile interaction flows")+'</div>'+
 panel("All proposed modules",'<div class="grid-cards" style="padding:17px">'+screens.map((s,i)=>'<button type="button" class="tile" data-go="'+s[0]+'" style="text-align:left"><span class="tiny muted">S'+String(i+1).padStart(2,"0")+'</span><h3>'+s[2]+' '+s[1]+'</h3><p>Open wireframe →</p></button>').join("")+'</div>')+'</div>';
}
function inbox(){
return head("Unified Inbox","One queue for authorized customer channels.",btn("+ New conversation","conversation","primary"))+
'<div class="two-column"><div class="panel"><div class="search-line"><input type="search" aria-label="Search conversations" placeholder="Search conversation or name" id="inbox-search"><button class="chip active" data-action="filter-all">All</button><button class="chip" data-action="filter-mine">Mine</button></div><div class="chips" style="padding:12px 15px">'+["All channels","Unread","Unassigned"].map(t=>'<button class="chip" data-action="inbox-filter">'+t+"</button>").join("")+'</div>'+
 person("Guest enquiry","WhatsApp · Looking for a wellness session","18:40","conversation","Unread")+person("Group booking","Website chat · Is Friday available?","17:20","conversation")+person("Retreat follow-up","Email · Please confirm group price","Yesterday","conversation","Mine")+person("Partner introduction","Telegram · Business enquiry","Yesterday","conversation")+'</div>'+
 panel("Conversation preview",'<div class="panel-body"><span class="badge">Selected: Guest enquiry</span><h3>Can I book a wellness session tomorrow?</h3><p class="muted">The preview is deliberately read-only. Open the complete conversation to review the composer, notes, ownership and channel status.</p>'+btn("Open conversation →","conversation","primary")+'</div>')+'</div>';
}
function conversation(){
return '<div class="screen-breadcrumb"><button data-go="inbox">← Inbox</button><span>›</span> Sample Guest</div>'+
'<div class="three-column">'+panel("Queue",person("Guest enquiry","WhatsApp · unread","","conversation","New")+person("Follow-up","Email","","conversation"))+
'<section class="panel"><div class="panel-header"><div><h3>Sample Guest</h3><p>WhatsApp · Assigned: Team Member · Inbox open</p></div><button class="link-btn" data-go="profile">Profile →</button></div>'+
'<div class="message-thread" aria-label="Synthetic message timeline"><div class="bubble"><b>Customer</b><br>Hi, can I book a wellness session tomorrow?</div><div class="bubble out"><b>Agent draft</b><br>I can check the available options for you.</div><div class="bubble note">Internal note · Ask about preferred time before responding.</div><div class="note">Message transmission unavailable in wireframe mode. Consent and connector readiness are prerequisites.</div></div>'+
'<div class="composer"><div class="chips"><button class="chip active" data-action="reply-mode">Reply</button><button class="chip" data-action="note-mode">Internal note</button></div><label class="kicker" for="composer-text">COMPOSER DRAFT</label><textarea id="composer-text" placeholder="Compose draft; nothing will be sent"></textarea><div class="composer-actions"><span class="tiny muted">⌁ Attachment • ✧ AI suggestion</span>'+action("Send (disabled)","send-disabled","primary")+'</div></div></section>'+
panel("Customer context",'<div class="details"><div class="avatar">S</div><strong>Sample Guest</strong>'+pill("Lead")+'<div><span class="list-title">Phone / consent</span><p class="small muted">Masked · Channel opt-in unverified</p></div>'+btn("Open Customer 360°","profile")+'<div class="note">Booking references are sourced from StayCore/Booking Core only when authorized.</div></div>')+'</div>';
}
function profile(){
return '<div class="screen-breadcrumb"><button data-go="inbox">← Inbox</button><span>›</span> Customer profile</div>'+head("Sample Guest","Synthetic profile · CRM-owned record",btn("Create task","tasks","primary"))+
'<section class="panel padded" style="margin-bottom:15px"><div style="display:flex;align-items:center;gap:13px"><span class="avatar" style="width:52px;height:52px">S</span><div><h3 style="margin:0 0 5px">Sample Guest</h3>'+pill("Qualified","amber")+' '+pill("Identity review required","grey")+'</div></div><div class="chips" style="margin-top:17px">'+btn("Message","conversation")+btn("Add task","tasks")+'</div></section>'+
'<div class="chips" style="margin-bottom:15px">'+["Overview","Timeline","Conversations","Deals","Bookings"].map(s=>'<button class="chip" data-action="profile-tab">'+s+"</button>").join("")+'</div>'+
'<div class="two-column">'+panel("Contact & permissions",'<dl class="details"><div><dt>Phone</dt><dd>+XX •••• ••• 321</dd></div><div><dt>Email</dt><dd>sample@example.invalid</dd></div><div><dt>Consent</dt><dd>'+pill("Needs confirmation","amber")+'</dd></div><div><dt>Owner</dt><dd>Team Member</dd></div></dl>')+
panel("Linked records",'<div class="panel-body"><h4>Engagement Core</h4><p class="muted">2 synthetic messages · no outgoing delivery</p><h4>StayCore / Booking Core</h4><p class="muted">Unconnected · authoritative records stay in their systems</p>'+btn("View opportunities","pipeline")+'</div>')+'</div><div style="height:15px"></div>'+
panel("Recent timeline",'<div class="panel-body"><ol class="timeline"><li><b>Lead assigned</b><small>Example only · Today</small></li><li><b>Initial enquiry</b><small>Example only · Yesterday</small></li></ol></div>');
}
function pipeline(){
 const card=(title,detail,due)=>'<div class="tile"><h3>'+title+'</h3><p>'+detail+'</p><div class="chips">'+pill(due,"amber")+btn("Open deal","deal","sm")+'</div></div>';
 return head("Opportunities","A touch-friendly pipeline with accessible stage changes.",btn("+ Opportunity","deal","primary"))+
 '<div class="search-line panel" style="margin-bottom:16px"><input aria-label="Search opportunities" placeholder="Search deals or guests"><select aria-label="Filter pipeline"><option>All owners</option><option>Assigned to me</option></select></div>'+
 '<div class="kanban"><section class="stage"><h3>NEW · Sample total ₹12,000</h3>'+card("Wellness package","Sample Guest · ₹4,000","Today")+card("Group recovery session","Group enquiry · ₹8,000","Tomorrow")+'</section><section class="stage"><h3>QUALIFIED · Sample total ₹6,500</h3>'+card("Retreat enquiry","Retreat follow-up · ₹6,500","Friday")+'</section><section class="stage"><h3>PROPOSAL · Sample total ₹9,000</h3>'+card("Corporate recovery","Partner introduction · ₹9,000","Monday")+'</section></div><div class="note" style="margin-top:14px">On phones, stages stack vertically; tap “Open deal” and use explicit stage control. Dragging is never required.</div>';
}
function deal(){
return '<div class="screen-breadcrumb"><button data-go="pipeline">← Pipeline</button><span>›</span> Opportunity</div>'+head("Wellness package enquiry","Sample deal · Value ₹4,000",btn("Add follow-up","tasks","primary"))+
'<div class="two-column">'+panel("Opportunity details",'<div class="panel-body"><div class="form-grid">'+
'<div class="field-block"><label for="deal-stage">Stage</label><select id="deal-stage" class="field"><option>New</option><option>Qualified</option><option>Proposal</option><option>Won</option><option>Lost</option></select></div>'+
'<div class="field-block"><label for="deal-owner">Assigned owner</label><select id="deal-owner" class="field"><option>Team Member</option><option>Unassigned</option></select></div>'+
'<div class="field-block"><label>Amount</label><input class="field" value="₹4,000" aria-label="Opportunity value"></div>'+
'<div class="field-block"><label>Due date</label><input class="field" type="date" aria-label="Opportunity due date"></div></div><div class="chips" style="margin-top:17px">'+action("Preview change (no save)","design-save") + btn("Open customer","profile")+'</div></div>')+
panel("Activity & next actions",'<div class="panel-body"><ol class="timeline"><li><b>New lead</b><small>Lifecycle event, synthetic</small></li><li><b>Staff follow-up needed</b><small>Tomorrow</small></li></ol>'+btn("Create task","tasks","primary")+'</div>')+'</div>';
}
function tasks(){
return head("Tasks & Follow-ups","Assignments, due dates and a linked source.",action("+ New task","new-task","primary"))+
'<div class="chips" style="margin-bottom:15px">'+["My tasks","Overdue","All","Completed"].map(t=>'<button class="chip" data-action="task-filter">'+t+"</button>").join("")+'</div>'+
panel("Task queue",person("Confirm preferred session","Linked: Sample Guest · Due today","","profile","P1")+person("Prepare group quote","Linked: Group booking · Due tomorrow","","deal","P2")+person("Review campaign consent","Linked: Engagement campaign","","campaigns","Draft"))+
'<div style="height:14px"></div>'+panel("Task editor specimen",'<div class="panel-body"><div class="form-grid">'+
'<div class="field-block"><label for="task-name">Task title</label><input id="task-name" class="field" placeholder="Contact guest about booking"></div>'+
'<div class="field-block"><label for="task-due">Due date</label><input id="task-due" type="date" class="field"></div>'+
'<div class="field-block"><label for="task-owner">Assigned to</label><select id="task-owner" class="field"><option>Team Member</option></select></div>'+
'<div class="field-block"><label for="task-link">Related record</label><select id="task-link" class="field"><option>Sample Guest</option><option>Wellness package deal</option></select></div></div><div style="margin-top:15px">'+action("Preview task (no save)","design-save")+'</div></div>');
}
function channels(){
return head("Channel Connections","Only provider-authorized accounts may send or sync.")+
'<div class="grid-cards">'+[
 ["WhatsApp","Not connected","Official scoped messaging adapter, consent and webhook verification.", "channel-review"],
 ["Email","Not connected","Verified sender domain, mailbox OAuth scope and delivery receipts.","channel-review"],
 ["Instagram","Not connected","Business account scopes and permission review.","channel-review"],
 ["Telegram","Not connected","Approved bot/group permissions; separate from Ashwakaal.","channel-review"],
 ["Website chat","Design only","WordPress self-hosted conversation adapter.","channel-review"]
 ].map(x=>'<article class="tile"><div class="chips" style="justify-content:space-between">'+pill(x[1],"grey")+'<span>⌁</span></div><h3>'+x[0]+'</h3><p>'+x[2]+'</p>'+action("Review connection prerequisites",x[3])+'</article>').join("")+'</div>';
}
function assistant(){
 return head("AI Assistant","Optional and permission-scoped; core CRM works without AI.")+
 '<div class="two-column">'+panel("Context and approval",'<div class="panel-body"><h3>What should I follow up on?</h3><div class="bubble" style="max-width:100%;margin:16px 0">Design sample: suggest two overdue tasks and cite authorized CRM records. No provider has been called.</div><label class="field-block"><span class="small muted">Prompt</span><textarea class="field" style="width:100%;min-height:100px" placeholder="Ask about your permitted CRM records"></textarea></label><div style="margin-top:14px">'+action("AI unavailable in wireframe","ai-unavailable")+'</div></div>')+
 panel("Suggested action request",'<div class="panel-body">'+pill("Approval required","amber")+'<h3>Propose one follow-up task</h3><p class="muted">Shows evidence sources, what would change and an independent accept/reject control.</p>'+action("Preview approval flow","approval-flow")+'<p class="tiny muted">No background model access, implicit database changes or spending.</p></div>')+'</div>';
}
function automations(){
return head("Automation Builder","Draft, validate and dry-run workflow logic.")+
 '<div class="panel padded"><div class="chips"><span class="badge">DRAFT</span>'+action("Validate model","design-save")+action("Dry-run only","design-save")+'</div><div class="grid-cards" style="margin:22px 0"><article class="tile"><div class="kicker">TRIGGER</div><h3>New CRM lead</h3><p>Run only for consented records.</p></article><article class="tile"><div class="kicker">CONDITION</div><h3>Lead stage = New</h3><p>Ignore duplicates and missing owner.</p></article><article class="tile"><div class="kicker">ACTION</div><h3>Create follow-up task</h3><p>Local database action; no messaging.</p></article><article class="tile"><div class="kicker">EXECUTION</div><h3>Audit + rollback</h3><p>Versioned definition and execution receipt.</p></article></div>'+emptyNote+'</div>';
}
function campaigns(){
return head("Campaigns & Templates","Consent-first campaigns; no live sends in design preview.",action("+ New campaign","design-save","primary"))+
'<div class="grid-cards">'+[
 ['Wellness follow-up','Draft','WhatsApp + Email · eligible recipients 0'],
 ['Past guests review request','Draft','Email · eligible recipients 0'],
 ['Community session announcement','Draft','Telegram · eligibility unverified']
].map(x=>'<article class="tile"><span class="badge grey">'+x[1]+'</span><h3>'+x[0]+'</h3><p>'+x[2]+'</p>'+action("Preview campaign", "campaign-preview")+'</article>').join("")+'</div><div class="note" style="margin-top:15px">Audience consent, quiet hours, sender account and provider quotas must be checked before activation. The G1 preview has zero eligible contacts.</div>';
}
function calendar(){
return head("Calendar & Bookings","Tasks and authorized booking references. External systems stay authoritative.")+
 '<div class="panel padded"><div class="chips" style="justify-content:space-between"><h3 style="margin:8px 0">October 2026</h3>'+btn("View tasks","tasks")+'</div><div class="calendar-grid">'+["M","T","W","T","F","S","S"].map(x=>'<b class="tiny muted" style="text-align:center">'+x+"</b>").join("")+Array.from({length:28},(_,i)=>'<div class="calendar-day '+(i===19?"today":"")+'"><strong>'+(i+1)+'</strong>'+(i===19?'<span class="badge">Task</span>':"")+'</div>').join("")+'</div><div class="note" style="margin-top:16px">Design dates are illustrative. StayCore/Booking Core write actions are disabled unless independently authorized.</div></div>';
}
function reports(){
return head("Reports & Analytics","Metrics must come from real source data after implementation.")+
'<div class="stats" style="margin-bottom:14px"><div class="stat"><small>Conversions</small><strong>—</strong><small>Not connected</small></div><div class="stat"><small>Response time</small><strong>—</strong><small>Not connected</small></div><div class="stat"><small>Attributed value</small><strong>—</strong><small>Not connected</small></div></div>'+
'<div class="two-column">'+panel("Source-attributed funnel",'<div class="panel-body"><div class="chart-placeholder" aria-label="Illustrative bar chart — no real metrics">'+[34,53,45,69,82,61,72,92].map(n=>'<div class="bar" style="height:'+n+'%"></div>').join("")+'</div><p class="tiny muted">Illustrative chart only. No business claims or fabricated actuals.</p></div>')+
 panel("Data provenance",'<div class="panel-body"><p class="muted">Each production statistic must cite its SQL aggregation, date range and matching activity or opportunity records.</p><div class="chips">'+action("Filter report","design-save")+action("Export disabled","export-disabled")+'</div></div>')+'</div>';
}
function team(){
return head("Team & Permissions","Least-privilege roles, assignments, auditable changes.",action("Invite staff (disabled)","permission-disabled"))+
panel("Scoped users",person("CRM Administrator","Manage only authorized site","", "team","Admin")+person("Sales Agent","View assigned contacts and deals","", "team","Agent")+person("Reviewer","Staging-only CRM QA","", "team","Read-only"))+
'<div style="height:14px"></div>'+panel("Capability matrix",'<div class="table-wrap"><table class="data-table"><thead><tr><th>Role</th><th>Contacts</th><th>Assigned deals</th><th>Messages</th><th>Integrations</th></tr></thead><tbody><tr><td>Administrator</td><td>Manage</td><td>Manage</td><td>Approved only</td><td>Review</td></tr><tr><td>Sales Agent</td><td>Assigned</td><td>Assigned</td><td>Approved only</td><td>Denied</td></tr><tr><td>Reviewer</td><td>Read</td><td>None</td><td>Denied</td><td>Denied</td></tr></tbody></table></div>');
}
function integrations(){
 return head("Integration Management","Constrained adapters; clear provenance and sync health.")+
 '<div class="grid-cards">'+[
 ["Engagement Core","Connection pending","Messaging transport; scoped per owner/channel."],
 ["StayCore","Not connected","Stay and guest record references, read-only default."],
 ["Booking Core","Not connected","Appointments/availability references, no silent edits."],
 ["Webhook registry","Not connected","Signed events, retries, dedupe and audit."]
 ].map(x=>'<article class="tile"><span class="badge grey">'+x[1]+'</span><h3>'+x[0]+'</h3><p>'+x[2]+'</p>'+action("View adapter specification","integration-review")+'</article>').join("")+'</div>';
}
function system(){
return head("System & Data","Privacy, backup, recovery and controlled migrations.")+
'<div class="grid-cards">'+[
 ["Privacy & consent","Export, erase and retention requests require scoped authorization."],
 ["Backups & restore","Restore into isolated staging, verify receipts, then request production approval."],
 ["Audit & security","Signed approvals, role denials, data access logs and replay protection."],
 ["Version & updates","Schema migrations, rollback snapshots and dependency disclosure."],
 ["Tenant isolation","Never share accounts, customer data or tokens across sites/workstreams."],
 ["Release gate","No unattended production deployment or external message delivery."]
 ].map(x=>'<article class="tile"><span class="kicker">CONTROL</span><h3>'+x[0]+'</h3><p>'+x[1]+'</p>'+action("View design note","system-review")+'</article>').join("")+'</div>';
}
const views={home,inbox,conversation,profile,pipeline,deal,tasks,channels,assistant,automations,campaigns,calendar,reports,team,integrations,system};
const sampleState={
 empty:["No records yet","This screen has no linked records. Provide a clear creation or connection path and avoid an empty dashboard."],
 loading:["Loading customer data","Show a skeleton while WordPress REST requests are in progress. Keep prior navigation and unsaved drafts."],
 error:["The request could not be completed","State which operation failed, preserve form drafts and offer a safe retry or support path."],
 denied:["Access is restricted","The user's WordPress role does not have the scoped permission for this record or action."]
};
let current="home",mode="normal",trail=[];
function navigate(where,recordHistory=true){
 if(where==="more"){toggleMenu();return;}
 if(!views[where])where="home";
 if(recordHistory&&where!==current)trail.push(current);
 current=where;mode="normal";$("state-select").value="normal";
 window.location.hash=where;render();$("main").focus({preventScroll:true});
 window.scrollTo({top:0,behavior:"auto"});
}
function stateView(which){
 const v=sampleState[which];if(!v)return "";
 const icon={empty:"○",loading:"⋯",error:"!",denied:"⊘"}[which];
 return '<div class="state-panel"><span class="state-symbol">'+icon+'</span><h3>'+v[0]+'</h3><p>'+v[1]+'</p>'+(
  which==="loading"?'<div class="skeleton"></div><div class="skeleton"></div>':
  which==="denied"?btn("Return home","home"):
  which==="error"?action("Retry preview","retry-preview"):
  btn("Return to modules","home")
 )+'</div>';
}
function isActive(group,where){
 if(group==="home")return where==="home";
 if(group==="inbox")return ["inbox","conversation"].includes(where);
 if(group==="profile")return where==="profile";
 if(group==="pipeline")return ["pipeline","deal"].includes(where);
 return !["home","inbox","conversation","profile","pipeline","deal"].includes(where);
}
function renderNav(){
 $("side-nav").innerHTML='<a href="#home" data-go="home" class="'+(current==="home"?"active":"")+'"><span class="nav-symbol">⌂</span>Overview</a>'+
 screens.map(s=>'<a href="#'+s[0]+'" data-go="'+s[0]+'" class="'+(current===s[0]?"active":"")+'" '+(current===s[0]?'aria-current="page"':'')+'><span class="nav-symbol">'+s[2]+'</span>'+s[1]+'</a>').join("");
 $("bottom-nav").innerHTML=primary.map(p=>'<a href="#'+p[0]+'" data-go="'+p[0]+'" class="'+(isActive(p[0],current)?"active":"")+'" '+(isActive(p[0],current)?'aria-current="page"':'')+'><span>'+p[2]+'</span><span>'+p[1]+'</span></a>').join("");
}
function render(){
 const def=names[current];
 $("page-heading").textContent=def?def[4]:"Overview";
 $("section-heading").textContent=def?def[3]:"WORKSPACE";
 $("screen-counter").textContent=current==="home"?"OVERVIEW":"S"+String(screens.findIndex(s=>s[0]===current)+1).padStart(2,"0")+" / 15";
 $("screen").innerHTML=mode==="normal"?views[current]():head(def?def[4]:"Overview","Previewing "+mode+" state")+stateView(mode);
 renderNav();closeMenu();
}
function toast(text){
 const el=$("toast");el.hidden=false;el.textContent=text;
 clearTimeout(toast.timer);
 toast.timer=setTimeout(()=>{el.hidden=true},3300);
}
function closeMenu(){
 $("sidebar").classList.remove("open");$("drawer-shade").hidden=true;$("menu-toggle").setAttribute("aria-expanded","false");
}
function toggleMenu(){
 let open=$("sidebar").classList.toggle("open");$("drawer-shade").hidden=!open;$("menu-toggle").setAttribute("aria-expanded",String(open));
}
document.addEventListener("click",e=>{
 const route=e.target.closest("[data-go]");
 if(route){e.preventDefault();navigate(route.dataset.go);return;}
 const control=e.target.closest("[data-action]");
 if(control){
  const key=control.dataset.action;
  if(key==="retry-preview"){mode="normal";$("state-select").value="normal";render();return;}
  if(key==="filter-all"||key==="filter-mine"||key==="inbox-filter"||key==="task-filter"||key==="profile-tab"||key==="reply-mode"||key==="note-mode"){
   const area=control.parentElement;if(area){area.querySelectorAll(".chip").forEach(n=>n.classList.remove("active"));control.classList.add("active");}
   toast("Design state only. Real filtering will use scoped WordPress data.");return;
  }
  const messages={"send-disabled":"No provider transmission. Real send requires consent, authenticated channel and delivery receipts.","design-save":"Wireframe action only; no database save occurred.","new-task":"Task editor is shown below. No CRM record was created.","ai-unavailable":"No AI request was made. This requires an explicitly connected provider.","approval-flow":"Action approval must show before/after details and produce an auditable receipt.","campaign-preview":"Preview only. No audience was contacted.","channel-review":"Provider onboarding requires scoped credentials, webhook verification and consent.","integration-review":"An integration adapter must be verified independently; none is connected.","permission-disabled":"No staff invitations can be sent from a wireframe.","system-review":"System and data controls require separately authorized production implementation.","export-disabled":"No live customer data is available to export."};
  toast(messages[key]||"Design-only interaction; not a production CRM operation.");
 }
});
$("menu-toggle").addEventListener("click",toggleMenu);
$("drawer-shade").addEventListener("click",closeMenu);
$("back-button").addEventListener("click",()=>navigate(trail.pop()||"home",false));
$("state-select").addEventListener("change",e=>{mode=e.target.value;render()});
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeMenu()});
window.addEventListener("hashchange",()=>{const dest=location.hash.slice(1);if(views[dest]&&dest!==current)navigate(dest,false)});
navigate(views[location.hash.slice(1)]?location.hash.slice(1):"home",false);
})();
