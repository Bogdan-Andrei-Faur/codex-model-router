// Grouped settings preserve drafts and action scope; consumption retains evidence limits.
const {chromium}=require('playwright'),{pathToFileURL}=require('node:url');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:800,height:950}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.addInitScript(()=>{window.messages=[];window.webkit={messageHandlers:{monitor:{postMessage:m=>window.messages.push(m)}}};});
  await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
  await page.evaluate(()=>{
   window.monitorPointer=()=>{};
   window.receive({productVersion:'0.9.6',connections:1,ui:{mode:'Expanded',reduced:true},config:{enabled:true,routing_engine:'jev',phase_routing:true,inference_telemetry:true,prompt_logging:true},telemetry:{enabled:true,requests:15,telemetry_confirmed:4},accountUsage:{valid_until:Date.now()/1000+3600,windows:[{duration_minutes:10080,remaining_percent:67}]},history:[
    {event:'decision_created',decision_id:'a',thread:'a',model:'gpt-6.1-sol',effort:'high',inputTokens:1200,outputTokens:300,time:1},
    {event:'decision_created',decision_id:'b',thread:'b',model:'gpt-6-luna',inputTokens:100,time:2}
   ]});showTab('statistics');
  });
  assert.equal(await page.locator('.consumption-total').textContent(),new Intl.NumberFormat('es-ES').format(1500));
  assert.equal(await page.locator('.consumption-coverage').textContent(),'1 / 2');
  assert.equal(await page.locator('.consumption-diagnostics').evaluate(n=>n.open),false);
  assert.equal(await page.getByText('Solicitudes procesadas',{exact:true}).isVisible(),false);
  await page.locator('.consumption-scope summary').click();
  assert.match(await page.locator('.consumption-scope').innerText(),/no confirma el modelo de cada inferencia/);
  await page.locator('.consumption-scope summary').click();
  if(process.env.ROUTER_PREFERENCES_SCREENSHOTS)await page.locator('#surface').screenshot({path:path.join(process.env.ROUTER_PREFERENCES_SCREENSHOTS,'consumption.png')});
  await page.locator('.consumption-diagnostics>summary').click();
  await page.locator('[data-consumption-section=telemetry]').click();
  await page.evaluate(()=>window.receive({telemetry:{enabled:true,requests:20,invalid_requests:2}}));
  assert.equal(await page.locator('[data-consumption-group=telemetry]').isVisible(),true);
  assert.equal(await page.locator('[data-consumption-group=routing]').isVisible(),false);
  assert.equal(await page.locator('.consumption-diagnostics .meter').count(),0);
  await page.evaluate(()=>showTab('settings'));
  assert.equal(await page.locator('[data-settings-group=application]').isVisible(),true);
  assert.equal(await page.locator('[data-settings-group=data]').isVisible(),false);
  if(process.env.ROUTER_PREFERENCES_SCREENSHOTS)await page.locator('#surface').screenshot({path:path.join(process.env.ROUTER_PREFERENCES_SCREENSHOTS,'settings.png')});
  await page.locator('[data-settings-section=routing]').click();
  await page.getByRole('button',{name:/^Añadir clave de TypeSafe/}).click();
  await page.getByLabel('Clave API de TypeSafe').fill('synthetic-unsaved');
  await page.locator('[data-settings-section=data]').click();
  await page.evaluate(()=>window.receive({updates:{status:'idle',installedVersion:'0.9.6'}}));
  assert.equal(await page.locator('[data-settings-group=data]').isVisible(),true);
  await page.locator('[data-settings-section=routing]').click();
  assert.equal(await page.getByLabel('Clave API de TypeSafe').inputValue(),'synthetic-unsaved');
  assert.equal(await page.evaluate(()=>window.messages.some(m=>m.action==='secret')),false);
  await page.locator('[data-settings-section=data]').click();
  await page.getByRole('button',{name:/^Desactivar captura de prompts/}).click();
  assert.deepEqual(await page.evaluate(()=>window.messages.at(-1)),{action:'config',key:'prompt_logging',value:false});
  for(const width of [800,620,390,320]){
   await page.setViewportSize({width,height:950});
   for(const key of ['application','routing','data','connection']){
    await page.locator('[data-settings-section='+key+']').click();await page.waitForTimeout(400);
    assert.equal(await page.locator('#settings').evaluate(n=>n.scrollWidth>n.clientWidth),false,'Settings overflow at '+width+'/'+key);
   }
   await page.evaluate(()=>showTab('statistics'));await page.waitForTimeout(400);
   assert.equal(await page.locator('#statistics').evaluate(n=>n.scrollWidth>n.clientWidth),false,'Consumption overflow at '+width);
   await page.evaluate(()=>showTab('settings'));
  }
  await page.evaluate(()=>window.receive({readOnly:true}));
  await page.locator('[data-settings-section=data]').click();
  assert.equal(await page.getByRole('button',{name:/^Desactivar captura de prompts/}).isDisabled(),true);
  assert.deepEqual(errors,[]);
  console.log('PASS: grouped consumption/settings, evidence limits, refresh state, credential draft isolation, action payloads and 320–800px layout');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
