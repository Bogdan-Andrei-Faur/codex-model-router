// Synthetic event projections only: no real Desktop transcript is loaded.
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:800,height:1050}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.addInitScript(()=>{window.messages=[];window.webkit={messageHandlers:{monitor:{postMessage:m=>window.messages.push(m)}}};});
  await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
  const update=async(kind,attention=[],blocking=false,status='active',connections=1)=>page.evaluate(data=>window.receive(data),{
   connections,ui:{mode:'Expanded',reduced:false},appearances:{a:{name:'Brisa',color:'#96cfff',head:'beanie',outfit:'hoodie',glasses:'round'}},
   threads:{a:{name:'Synthetic agent',turn_id:'t',model:'gpt-6.1-sol',status,activity:{version:1,source:'native',scope:'turn',turn_id:'t',kind,attention,blocking,observed_at:Date.now()/1000-5}}}
  });
  await update('thinking');
  const portrait=page.locator('.hero-character');
  assert.equal(await portrait.getAttribute('data-state'),'thinking');
  assert.match(await portrait.getAttribute('aria-label'),/Pensando/);
  assert.equal(await portrait.locator('.character-body').evaluate(n=>getComputedStyle(n).animationName),'companion-think');
  const look=await portrait.getAttribute('data-appearance');
  for(const kind of ['writing','executing','editing','searching','tool','collaborating','inspecting','generating','reviewing','compacting','retrying','preparing']){
   await update(kind);assert.equal(await portrait.getAttribute('data-state'),kind);
   assert.equal(await portrait.getAttribute('data-appearance'),look);
   assert.notEqual(await portrait.locator(kind==='collaborating'?'.hand-right':'.character-body').evaluate(n=>getComputedStyle(n).animationName),'none');
  }
  await update('thinking',['input']);
  assert.equal(await portrait.getAttribute('data-state'),'thinking');
  assert.equal(await portrait.locator('.character-attention').isVisible(),true);
  assert.equal(await portrait.locator('.character-attention').getAttribute('data-kind'),'input');
  await update('approval',['approval'],true);
  assert.equal(await portrait.getAttribute('data-state'),'approval');
  assert.match(await portrait.getAttribute('aria-label'),/Esperando aprobación/);
  await page.getByRole('button',{name:'Agentes',exact:true}).click();
  assert.match(await page.locator('.routing-attention').innerText(),/Aprobación pendiente/);
  await update('question',['input'],true);
  assert.match(await page.locator('.routing-attention').innerText(),/Respuesta pendiente/);
  await page.getByRole('button',{name:'Inicio',exact:true}).click();
  await update('error',[],false,'failed');
  assert.equal(await portrait.getAttribute('data-state'),'error');
  assert.ok(parseFloat(await portrait.locator('.character-body').evaluate(n=>getComputedStyle(n).animationDelay))<=-.6,'old failure must not replay flinch every poll');
  await update('done',[],false,'completed');
  assert.match(await portrait.getAttribute('aria-label'),/Turno terminado/);
  await update('thinking',['input'],false,'active',0);
  assert.equal(await portrait.getAttribute('data-state'),'offline');
  assert.equal(await portrait.locator('.character-attention').isVisible(),false);
  await update('thinking');
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await portrait.locator('.character-body').evaluate(n=>getComputedStyle(n).animationName),'none');
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.evaluate(()=>window.receive({ui:{reduced:true}}));
  assert.equal(await portrait.locator('.character-body').evaluate(n=>getComputedStyle(n).animationName),'none');
  await page.evaluate(()=>window.receive({ui:{reduced:false,mode:'Compact'}}));
  assert.equal(await page.locator('#agents .avatar').first().getAttribute('data-state'),'thinking');
  await page.evaluate(()=>document.body.classList.add('motion-hidden'));
  assert.equal(await page.locator('#agents .character-body').first().evaluate(n=>getComputedStyle(n).animationPlayState),'paused');
  assert.deepEqual(errors,[]);
  const actions=await page.evaluate(()=>window.messages.filter(m=>!['ready','bounds','mode','height','history'].includes(m.action)));
  assert.deepEqual(actions,[],'viewing native attention must not answer or approve');
  console.log('PASS: native activity poses, attention, stable wardrobe, scoped labels, one-shot motion and reduced/hidden motion');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
