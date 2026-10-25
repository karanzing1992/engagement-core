/* Engagement Core CRM. Tabler 1.7 visual foundation; all records from WordPress REST. */
(() => {
'use strict';
const cfg = window.ECCRM_CONFIG || {};
const $ = id => document.getElementById(id);
const state = { view:'overview', offset:0, search:'', lifecycle:'', pageSize:19, hasNext:false, editing:null, loading:false };
const apiBase = String(cfg.api || '').replace(/\/?$/, '/');
const node = (tag,klass,text) => { const n=document.createElement(tag); if(klass)n.className=klass; if(text!==undefined&&text!==null)n.textContent=String(text); return n; };
const setText = (id,value) => { const n=$(id); if(n)n.textContent=String(value); };
const fmtDate = str => { if(!str)return ''; const dt = new Date(str.replace(' ','T')+'Z'); return Number.isNaN(dt.getTime()) ? '' : new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}).format(dt); };
const stageBadge = stage => { const name=['lead','qualified','customer','inactive'].includes(stage)?stage:'lead';return node('span','eccrm-stage '+name,name); };
const clear = n => { while(n.firstChild)n.removeChild(n.firstChild); };
const empty = msg => node('p','eccrm-empty',msg);
const toast = (message,error=false) => { const el=$('eccrm-notice');el.textContent=message;el.classList.toggle('error',error);el.hidden=false; };
async function api(path='',options={}) {
 const endpoint=apiBase.includes('?') ? apiBase+path.replace('?', '&') : apiBase+path;
 const response=await fetch(endpoint,{...options,credentials:'same-origin',headers:{'X-WP-Nonce':cfg.nonce,'Accept':'application/json',...(options.body?{'Content-Type':'application/json'}:{}),...(options.headers||{})}});
 let body;try{body=await response.json();}catch{body={};}
 if(!response.ok){throw new Error(body.message||'CRM request failed ('+response.status+').');}
 return body;
}
function person(record,compact=false) {
 const button=node('button',compact?'eccrm-person':'eccrm-contactrow');button.type='button';
 button.setAttribute('aria-label','Open contact '+record.display_name);
 const initial=node('span','eccrm-initial',(record.display_name||'?').trim().charAt(0).toUpperCase());
 const main=node('span',compact?'eccrm-person-text':'eccrm-contactdetails');
 main.append(node('strong','',record.display_name || 'Unnamed contact'),node('small','',record.email || record.phone || 'No contact details'));
 if(compact){button.append(initial,main,stageBadge(record.lifecycle));}
 else{const inner=node('span','eccrm-contactmain');inner.append(initial,main);button.append(inner,node('span','eccrm-contactmeta',record.phone||record.source||''),stageBadge(record.lifecycle));}
 button.addEventListener('click',()=>editContact(record.id));
 return button;
}
function activityItem(record) {
 const row=node('div','eccrm-event');
 row.append(node('span','eccrm-event-marker','↗'));
 const group=node('span','eccrm-event-text');
 const labels={'contact.created':'Contact created','contact.updated':'Contact updated'};
 group.append(node('strong','',labels[record.event_type] || String(record.event_type||'CRM activity').replace(/[._]/g,' ')),node('small','','Contact #'+record.entity_id));
 row.append(group,node('time','eccrm-event-time',fmtDate(record.created_at)));
 return row;
}
function displayItems(id,items,factory,message) {
 const root=$(id);clear(root);
 if(!Array.isArray(items)||!items.length){root.append(empty(message));return;}
 items.forEach(item=>root.append(factory(item)));
}
async function loadOverview(){
 try{
 const [counts,contacts,events]=await Promise.all([api('overview'),api('contacts?limit=5'),api('activity?limit=5')]);
 setText('eccrm-stat-total',counts.total??0);
 setText('eccrm-stat-qualified',counts.qualified??0);
 setText('eccrm-stat-customers',counts.customer??0);
 displayItems('eccrm-recent-contacts',contacts.items,record=>person(record,true),'No contacts yet. Add your first profile.');
 displayItems('eccrm-recent-activity',events.items,activityItem,'No activity yet.');
 }catch(err){toast(err.message,true);['eccrm-recent-contacts','eccrm-recent-activity'].forEach(id=>displayItems(id,[],()=>{},'Unable to load CRM records.')); }
}
async function loadContacts(){
 const list=$('eccrm-contacts-list');clear(list);list.append(node('p','eccrm-loading','Loading contacts…'));
 const search=new URLSearchParams({limit:String(state.pageSize+1),offset:String(state.offset)});
 if(state.search)search.set('search',state.search);
 if(state.lifecycle)search.set('lifecycle',state.lifecycle);
 try{
  const result=await api('contacts?'+search.toString());
  const all=Array.isArray(result.items)?result.items:[];
  state.hasNext=all.length>state.pageSize;
  const items=all.slice(0,state.pageSize);
  displayItems('eccrm-contacts-list',items,record=>person(record,false),'No matching contacts. Try another search or create a contact.');
  const start=state.offset+1;const end=state.offset+items.length;
  setText('eccrm-page-indicator',items.length?start+'–'+end+' contacts':'No results');
  $('eccrm-prev').disabled=state.offset===0;
  $('eccrm-next').disabled=!state.hasNext;
 }catch(err){clear(list);list.append(empty('Unable to load contacts.'));toast(err.message,true);}
}
async function loadActivity(){
 try{const result=await api('activity?limit=40');displayItems('eccrm-full-activity',result.items,activityItem,'No CRM changes recorded yet.');}
 catch(err){toast(err.message,true);displayItems('eccrm-full-activity',[],()=>{},'Activity unavailable.');}
}
function closeMenu(){const sidebar=$('eccrm-sidebar');sidebar.classList.remove('is-open');$('eccrm-backdrop').hidden=true;$('eccrm-open-menu').setAttribute('aria-expanded','false');}
async function changeView(view){
 if(!['overview','contacts','activity'].includes(view))return;
 state.view=view;
 document.querySelectorAll('#eccrm-workspace .eccrm-view').forEach(el=>{el.hidden=el.id!=='eccrm-view-'+view;});
 document.querySelectorAll('#eccrm-workspace [data-view]').forEach(btn=>{btn.classList.toggle('is-active',btn.dataset.view===view);if(btn.dataset.view===view)btn.setAttribute('aria-current','page');else btn.removeAttribute('aria-current');});
 setText('eccrm-page-title',view==='overview'?'Overview':view==='contacts'?'Contacts':'Activity');
 $('eccrm-notice').hidden=true;closeMenu();
 if(view==='overview')await loadOverview();
 if(view==='contacts')await loadContacts();
 if(view==='activity')await loadActivity();
}

function openEditor(record=null){
 const dialog=$('eccrm-editor'),form=$('eccrm-contact-form');
 form.reset();state.editing=record?Number(record.id):null;
 setText('eccrm-editor-title',record?'Edit contact':'New contact');
 $('eccrm-form-error').hidden=true;
 $('eccrm-field-name').value=record?record.display_name||'':'';
 $('eccrm-field-email').value=record?record.email||'':'';
 $('eccrm-field-phone').value=record?record.phone||'':'';
 $('eccrm-field-lifecycle').value=record?record.lifecycle||'lead':'lead';
 if(!dialog.open)dialog.showModal();
 window.setTimeout(()=>$('eccrm-field-name').focus(),35);
}
async function editContact(id){
 try{const record=await api('contacts/'+encodeURIComponent(id));openEditor(record);}
 catch(err){toast(err.message,true);}
}
async function saveContact(event){
 event.preventDefault();
 if(state.loading)return;
 const form=$('eccrm-contact-form');
 if(!form.reportValidity())return;
 const data={
  display_name:$('eccrm-field-name').value.trim(),
  email:$('eccrm-field-email').value.trim(),
  phone:$('eccrm-field-phone').value.trim(),
  lifecycle:$('eccrm-field-lifecycle').value
 };
 const submit=$('eccrm-save-contact');
 state.loading=true;submit.disabled=true;submit.textContent='Saving…';$('eccrm-form-error').hidden=true;
 try{
  const editing=Boolean(state.editing);
  await api(editing?'contacts/'+state.editing:'contacts',{method:editing?'PATCH':'POST',body:JSON.stringify(data)});
  if(state.view==='overview')await loadOverview();
  if(state.view==='contacts')await loadContacts();
  if(state.view==='activity')await loadActivity();
  $('eccrm-editor').close();
  toast(editing?'Contact updated successfully.':'Contact created successfully.');
 }catch(err){$('eccrm-form-error').hidden=false;setText('eccrm-form-error',err.message);}
 finally{state.loading=false;submit.disabled=false;submit.textContent='Save contact';}
}
function init(){
 if(!$('eccrm-workspace')||!apiBase){return;}
 document.querySelectorAll('#eccrm-workspace [data-view]').forEach(button=>button.addEventListener('click',()=>changeView(button.dataset.view)));
 document.querySelectorAll('#eccrm-workspace [data-create]').forEach(button=>button.addEventListener('click',()=>openEditor()));
 $('eccrm-refresh').addEventListener('click',()=>changeView(state.view));
 $('eccrm-open-menu').addEventListener('click',()=>{
  const open=$('eccrm-sidebar').classList.toggle('is-open');
  $('eccrm-backdrop').hidden=!open;
  $('eccrm-open-menu').setAttribute('aria-expanded',String(open));
 });
 $('eccrm-backdrop').addEventListener('click',closeMenu);
 $('eccrm-close-dialog').addEventListener('click',()=>$('eccrm-editor').close());
 $('eccrm-cancel-dialog').addEventListener('click',()=>$('eccrm-editor').close());
 $('eccrm-contact-form').addEventListener('submit',saveContact);
 let timer;
 $('eccrm-search').addEventListener('input',event=>{
  window.clearTimeout(timer);
  timer=window.setTimeout(()=>{state.search=event.target.value.trim();state.offset=0;loadContacts();},220);
 });
 $('eccrm-stage').addEventListener('change',event=>{state.lifecycle=event.target.value;state.offset=0;loadContacts();});
 $('eccrm-prev').addEventListener('click',()=>{state.offset=Math.max(0,state.offset-state.pageSize);loadContacts();});
 $('eccrm-next').addEventListener('click',()=>{if(state.hasNext){state.offset+=state.pageSize;loadContacts();}});
 window.addEventListener('keydown',event=>{if(event.key==='Escape')closeMenu();});
 changeView('overview');
}
if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init,{once:true});}else{init();}
})();

