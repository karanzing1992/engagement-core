/* Generic independent browser checks. No publishing, no mutation of target site. */
const {chromium}=require('playwright');
const AxeBuilder=require('@axe-core/playwright').default;
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const opt=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
(async()=>{
const b=await chromium.launch({executablePath:opt.chrome||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']});
const result={version:'1.0',site:opt.url,source_hash:opt.source_hash,rows:[],screenshots:[],critical_violations:[],missing_links:[],pass:false};
const pages=opt.pages||['index.html'],widths=opt.widths||[320,390,768,1440];
fs.mkdirSync(opt.screenshots,{recursive:true});
for(const page of pages)for(const width of widths){
 const ctx=await b.newContext({viewport:{width,height:width===320?720:width===390?844:width===768?1024:900},reducedMotion:'reduce'});
 const p=await ctx.newPage();let errors=[];p.on('pageerror',e=>errors.push(e.message.slice(0,220)));
 let status=0,dom={},viols=[],nav={};try{
  const res=await p.goto(opt.url+'/'+page,{waitUntil:'load',timeout:25000});
  status=res.status();
  // Deterministically settle local and lazy images before flagging broken assets.
  await p.evaluate(async()=> {
   await Promise.all([...document.images].map(async img=>{
    img.loading='eager';
    if (!img.complete) await Promise.race([
      new Promise(resolve=>{img.addEventListener('load',resolve,{once:true});img.addEventListener('error',resolve,{once:true});}),
      new Promise(resolve=>setTimeout(resolve,5000))
    ]);
    if(img.complete && img.naturalWidth>0 && typeof img.decode==='function'){
      try{await img.decode()}catch(_){}
    }
   }));
  });
  await p.waitForTimeout(150);
  dom=await p.evaluate(()=>({
   title:document.title,h1:document.querySelector('h1')?.innerText.trim()||'',
   overflow:Math.max(0,document.documentElement.scrollWidth-innerWidth),
   brokenImages:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.src),
   internalLinks:[...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')).filter(Boolean).filter(x=>!/^([a-z]+:|#|\/\/)/i.test(x)),
   ctas:[...document.querySelectorAll('a[href],button')].filter(a=>/book|enquir|contact|order|join|register|start|reserve/i.test(a.textContent)).length,
   lang:document.documentElement.lang||'',main:!!document.querySelector('main'),placeholder:/is being redesigned|not ready for review yet/i.test(document.body.innerText)
  }));
  const axe=await new AxeBuilder({page:p}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
  viols=axe.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.length,
   targets:v.nodes.slice(0,4).map(n=>({selector:(n.target||[]).join(' ').slice(0,140),
      failure_summary:String(n.failureSummary||'').slice(0,260)}))}));
  if(width<=390){
    const togg=p.locator('[aria-controls][aria-expanded]').first();
    if(await togg.count()){
      const region='#'+await togg.getAttribute('aria-controls');
      nav.initial=await togg.getAttribute('aria-expanded');await togg.click();
      nav.open=await togg.getAttribute('aria-expanded');nav.visible=await p.locator(region).isVisible();
      await p.keyboard.press('Escape');
      nav.afterEscape=await togg.getAttribute('aria-expanded');
      nav.closed=!(await p.locator(region).isVisible());
    }
  }
  const name=page.replace(/[^a-z0-9]/gi,'_')+'-'+width+'.jpg';
  await p.screenshot({path:path.join(opt.screenshots,name),type:'jpeg',quality:65,animations:'disabled'});
  result.screenshots.push({page,width,name,sha256:sha(path.join(opt.screenshots,name))});
 }catch(e){errors.push(String(e).slice(0,250));}
 const menuPass=!Object.keys(nav).length||(nav.open==='true'&&nav.visible===true&&nav.afterEscape==='false'&&nav.closed===true);
 const pass=status===200&&dom.h1?.length>0&&dom.main===true&&dom.overflow===0&&
   !dom.placeholder&&dom.brokenImages?.length===0&&!errors.length&&!viols.length&&menuPass;
 const row={page,width,status,pass,dom,axe:viols,nav,errors};result.rows.push(row);
 await ctx.close();
}
await b.close();
const allLinks=new Set(result.rows.flatMap(r=>r.dom.internalLinks||[]));
for(const link of allLinks){
 const clean=link.split(/[?#]/)[0];if(!clean||clean.startsWith('/'))continue;
 if(!fs.existsSync(path.join(opt.root,clean)))result.missing_links.push(link);
}
result.failed=result.rows.filter(r=>!r.pass).length;
result.pass=result.failed===0&&result.missing_links.length===0&&result.rows.length===pages.length*widths.length;
fs.mkdirSync(path.dirname(opt.report),{recursive:true});
fs.writeFileSync(opt.report,JSON.stringify(result,null,2));
console.log(JSON.stringify({status:result.pass?'PASS':'BLOCKED',cases:result.rows.length,failed:result.failed,missing_links:result.missing_links,screenshots:result.screenshots.length,source_hash:result.source_hash}));
if(!result.pass)process.exitCode=4;
})().catch(e=>{console.error(String(e.stack).slice(0,1600));process.exit(5)});
