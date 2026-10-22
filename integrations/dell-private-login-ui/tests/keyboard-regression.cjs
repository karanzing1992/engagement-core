const fs=require('fs'),assert=require('assert/strict'),{webcrypto}=require('crypto');
const {chromium}=require(process.env.HOME+'/moksha-browser/node_modules/playwright');
(async()=>{
const dir=process.env.HOME+'/dell-ai-operator/keyboard-fix-20261023';
let html=fs.readFileSync(dir+'/index.html','utf8');
const keys=await webcrypto.subtle.generateKey({name:'ECDH',namedCurve:'P-256'},true,['deriveKey']);
const pub=await webcrypto.subtle.exportKey('jwk',keys.publicKey);
html=html.replace(/import \{createClient\} from '[^']+';/,'const createClient=()=>({auth:{onAuthStateChange(){},getSession:async()=>({data:{session:null}})}});');
html=html.replace('init();\n</script>',`init();window.__qa={show(){token='synthetic-test-session';workerKey=${JSON.stringify(pub)};document.querySelector('#remote').style.display='block';document.body.classList.add('remote-active');},drain:()=>inputQueue};\n</script>`);
const b=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true});
try{
const p=await b.newPage({viewport:{width:1280,height:900}}),actions=[],errors=[];let denied=false;
p.on('pageerror',e=>errors.push(e.message));
await p.route('**/*',async r=>{
 const req=r.request();
 if(req.url().endsWith('/input')){
  const body=req.postData();assert(!body.includes('SYNTHETIC_KEY_12345'));
  if(denied){await r.fulfill({status:401,contentType:'application/json',body:'{"error":"test denied"}'});return;}
  const c=JSON.parse(body),peer=await webcrypto.subtle.importKey('jwk',c.jwk,{name:'ECDH',namedCurve:'P-256'},false,[]);
  const key=await webcrypto.subtle.deriveKey({name:'ECDH',public:peer},keys.privateKey,{name:'AES-GCM',length:256},false,['decrypt']);
  const plain=await webcrypto.subtle.decrypt({name:'AES-GCM',iv:Buffer.from(c.iv,'base64url')},key,Buffer.from(c.ciphertext,'base64url'));
  actions.push(JSON.parse(Buffer.from(plain).toString()));
  await r.fulfill({status:200,contentType:'application/json',body:'{"accepted":true}'});return;
 }
 assert.equal(req.url(),'https://dell-private-login-ui.vercel.app/');
 await r.fulfill({contentType:'text/html',body:html});
});
await p.goto('https://dell-private-login-ui.vercel.app/');await p.waitForFunction(()=>window.__qa);await p.evaluate(()=>__qa.show());
assert.equal(await p.locator('#privateText').getAttribute('type'),'password');
await p.locator('#privateText').fill('SYNTHETIC_KEY_12345');await p.locator('#sendPrivate').click();
await p.waitForFunction(()=>document.querySelector('#inputStatus').textContent.includes('accepted'));
assert.deepEqual(actions.shift(),{kind:'type',text:'SYNTHETIC_KEY_12345'});assert.equal(await p.locator('#privateText').inputValue(),'');
await p.locator('#remoteEnter').click();await p.evaluate(()=>__qa.drain());assert.deepEqual(actions.shift(),{kind:'key',key:'Return'});
await p.locator('#sendPrivate').click();assert.equal(actions.length,0);
await p.locator('#privateText').fill('do-not-retain');await p.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));});assert.equal(await p.locator('#privateText').inputValue(),'');
await p.evaluate(()=>Object.defineProperty(document,'hidden',{configurable:true,value:false}));
denied=true;await p.locator('#privateText').fill('SYNTHETIC_KEY_12345');await p.locator('#sendPrivate').click();await p.waitForFunction(()=>document.querySelector('#inputStatus').textContent.includes('Private input failed'));
assert.equal(await p.locator('#privateText').inputValue(),'');assert.equal(actions.length,0);denied=false;
await p.locator('#keyboardButton').click();assert.equal(await p.evaluate(()=>document.activeElement.id),'remoteInput');await p.keyboard.type('BENIGN');await p.keyboard.press('Enter');await p.evaluate(()=>__qa.drain());
assert.deepEqual(actions.splice(0),[{kind:'type',text:'BENIGN'},{kind:'key',key:'Return'}]);
await p.setViewportSize({width:390,height:844});assert(await p.locator('#privateText').isVisible());
assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);
console.log(JSON.stringify({status:'PASS',checks:['masked-native-field','encrypted-browser-to-test-recipient','clear-after-send','explicit-enter','empty-rejected','clear-on-hidden','401-fail-closed','activate-keyboard-and-typing','mobile-no-overflow','no-page-errors'],live_owner_auth_tested:false,real_credentials_used:false}));
}finally{await b.close();}
})().catch(e=>{console.log(JSON.stringify({status:'FAIL',error:e.message}));process.exit(1)});
