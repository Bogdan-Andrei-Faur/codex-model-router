// Inline editor: drafts survive polling, identity is per-agent, failures preserve input.
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:800,height:1100}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.addInitScript(()=>{window.messages=[];window.webkit={messageHandlers:{monitor:{postMessage:m=>window.messages.push(m)}}};});
  await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
  await page.evaluate(()=>window.receive({connections:1,ui:{mode:'Expanded',reduced:true},threads:{a:{name:'Agent A',status:'active',model:'gpt-6.1-sol'},b:{name:'Agent B',status:'idle'}}}));
  await page.getByRole('button',{name:'Agentes',exact:true}).click();
  await page.getByRole('button',{name:'Personalizar',exact:true}).click();
  assert.equal(await page.locator('input[type=color],.appearance-mini,.appearance-sample').count(),0);
  const colors=page.getByRole('group',{name:'Color del cuerpo',exact:true});
  assert.equal(await colors.getByRole('button').count(),9);
  await colors.getByRole('button',{name:'Cielo',exact:true}).click();
  assert.equal(await page.locator('.agent-portrait').evaluate(n=>n.style.getPropertyValue('--character')),'#96cfff');
  assert.equal(await colors.getByRole('button',{name:'Cielo',exact:true}).getAttribute('aria-pressed'),'true');
  assert.ok((await page.getByRole('textbox',{name:'Nombre del personaje',exact:true}).boundingBox()).width<=220);
  await page.getByRole('textbox',{name:'Nombre del personaje',exact:true}).fill('Brisa');
  const categories=page.getByRole('group',{name:'Categorías del personaje',exact:true});
  await categories.getByRole('button',{name:'Cabeza',exact:true}).click();
  await page.getByRole('group',{name:'Cabeza',exact:true}).getByRole('button',{name:'Antena',exact:true}).click();
  await categories.getByRole('button',{name:'Gafas',exact:true}).click();
  await page.getByRole('group',{name:'Gafas',exact:true}).getByRole('button',{name:'Redondas',exact:true}).click();
  await categories.getByRole('button',{name:'Ropa',exact:true}).click();
  await page.getByRole('group',{name:'Ropa',exact:true}).getByRole('button',{name:'Sudadera',exact:true}).click();
  await categories.getByRole('button',{name:'Cuerpo',exact:true}).click();
  await page.evaluate(()=>window.receive({connections:1,threads:{a:{name:'Renamed A',status:'active',model:'gpt-6-astra'},b:{name:'Agent B',status:'idle'}}}));
  assert.equal(await page.getByRole('textbox',{name:'Nombre del personaje',exact:true}).inputValue(),'Brisa');
  await page.evaluate(()=>window.monitorPointer(null));
  await page.waitForTimeout(450);
  assert.equal(await page.locator('body').evaluate(n=>n.classList.contains('expanded')),true);
  await page.getByRole('button',{name:'Guardar',exact:true}).click();
  let request=await page.evaluate(()=>window.messages.filter(m=>m.action==='appearance').at(-1));
  assert.equal(request.thread,'a');assert.equal(request.value.name,'Brisa');assert.equal(request.value.glasses,'round');assert.equal(request.value.color,'#96cfff');assert.equal(request.value.outfit,'hoodie');
  await page.evaluate(m=>window.monitorAppearanceResult({...m,ok:false}),request);
  assert.equal(await page.getByRole('textbox',{name:'Nombre del personaje',exact:true}).inputValue(),'Brisa');
  await page.getByRole('button',{name:'Guardar',exact:true}).click();
  const retry=await page.evaluate(()=>window.messages.filter(m=>m.action==='appearance').at(-1));
  await page.evaluate(m=>window.monitorAppearanceResult({...m,ok:true}),request);
  assert.equal(await page.locator('.appearance-editor').count(),1,'Late acknowledgement must not close a new save');
  await page.evaluate(m=>window.monitorAppearanceResult({...m,ok:true}),retry);
  assert.equal(await page.locator('.appearance-editor').count(),0);
  assert.equal(await page.locator('.agent-identity-copy .companion-alias').textContent(),'Brisa');
  await page.locator('.agent-pick[data-agent="b"]').click();
  assert.notEqual(await page.locator('.agent-identity-copy .companion-alias').textContent(),'Brisa');
  await page.locator('.agent-pick[data-agent="a"]').click();
  await page.getByRole('button',{name:'Personalizar',exact:true}).click();
  await page.getByRole('textbox',{name:'Nombre del personaje',exact:true}).fill('Unsaved');
  await page.getByRole('button',{name:'Cancelar',exact:true}).click();
  assert.equal(await page.locator('.agent-identity-copy .companion-alias').textContent(),'Brisa');
  await page.getByRole('button',{name:'Personalizar',exact:true}).click();
  await page.getByRole('button',{name:'Restaurar original',exact:true}).click();
  await page.getByRole('button',{name:'Guardar',exact:true}).click();
  request=await page.evaluate(()=>window.messages.filter(m=>m.action==='appearance').at(-1));assert.equal(request.value,null);
  await page.evaluate(m=>window.monitorAppearanceResult({...m,ok:true}),request);
  await page.getByRole('button',{name:'Personalizar',exact:true}).click();
  for(const category of ['Ropa','Gafas','Cabeza','Cuello','Detalles']){
   await categories.getByRole('button',{name:category,exact:true}).click();
   const group=page.getByRole('group',{name:category,exact:true});
   for(const choice of await group.getByRole('button').all()){
    const value=await choice.getAttribute('data-appearance-choice');await choice.click();
    assert.equal(await group.locator('[aria-pressed=true]').getAttribute('data-appearance-choice'),value);
   }
  }
  for(const width of [800,600,390,320]){
   await page.setViewportSize({width,height:1100});await page.waitForTimeout(450);
   assert.equal(await page.locator('.appearance-editor').evaluate(n=>n.scrollWidth>n.clientWidth),false,'Editor overflow at '+width);
  }
  if(process.env.ROUTER_EDITOR_SCREENSHOT){await page.setViewportSize({width:800,height:900});await page.waitForTimeout(450);await categories.getByRole('button',{name:'Ropa',exact:true}).click();await page.screenshot({path:process.env.ROUTER_EDITOR_SCREENSHOT});}
  assert.deepEqual(errors,[]);
  console.log('PASS: appearance drafts/polling, failure/retry/stale ack, independent agents, cancel/reset and responsive editor');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
