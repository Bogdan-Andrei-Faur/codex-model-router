// History navigation, recorded-data semantics, rating dispatch and responsive layout.
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:800,height:760}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.addInitScript(()=>{window.messages=[];window.webkit={messageHandlers:{monitor:{postMessage:m=>window.messages.push(m)}}};});
  await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
  await page.evaluate(()=>document.fonts.ready);
  const records=Array.from({length:43},(_,i)=>({event:'decision_created',decision_id:'record'+i,thread:'task'+i,time:1800000000+i*100,
   title:['Rediseñar el panel de agentes','Investigar el arranque local','Validar la sincronización'][i%3],model:['gpt-6-astra','gpt-6.1-sol','gpt-6-luna'][i%3],effort:'high',status:i%2?'completed':'active',
   model_reason:'El cambio afecta a varios componentes de la interfaz y necesita una revisión conjunta.',effort_reason:'Hay que comprobar estados, navegación y accesibilidad.',routing_engine:'rules'}));
  records.push({event:'decision_usage',decision_id:'record42',time:1800004250,inputTokens:2180,outputTokens:540},
   {event:'decision_completed',decision_id:'record42',time:1800004265,status:'completed'});
  await page.evaluate(history=>{window.receive({connections:1,ui:{mode:'Expanded',reduced:true,panelHeight:680},history});showTab('history');},records);
  assert.equal(await page.locator('.history-row').count(),40);
  await page.getByRole('button',{name:'Siguiente',exact:true}).click();
  assert.equal(await page.locator('.history-row').count(),3);
  await page.getByRole('button',{name:'Anterior',exact:true}).click();
  await page.locator('.history-row').first().focus();await page.keyboard.press('Enter');
  assert.equal(await page.locator('.history-detail').getAttribute('data-decision'),'record42');
  assert.equal(await page.locator('.history-row').first().getAttribute('aria-pressed'),'true');
  assert.equal(await page.locator('.history-detail>.reason-card').count(),0,'Generic explanations should not appear');
  assert.equal(await page.locator('[data-section=control],.history-detail .pipeline').count(),0,'History must not alter live task controls or infer a pipeline');
  assert.equal(await page.locator('[data-section=diagnostics]').count(),0,'A routine record needs no empty diagnostic section');
  assert.match(await page.locator('.history-measurements').innerText(),/Tiempo del turno\s+1 min 5 s/);
  const columns=await page.locator('.history-sidebar,.history-detail').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {x:r.x,right:r.right,top:r.top};}));
  assert.ok(columns[0].right<columns[1].x&&Math.abs(columns[0].top-columns[1].top)<1);
  await page.locator('[data-section=quality]>summary').click();
  await page.locator('[data-section=quality]').getByRole('button',{name:'Adecuada',exact:true}).first().click();
  assert.deepEqual(await page.evaluate(()=>window.messages.filter(m=>m.action==='quality').at(-1)),{action:'quality',id:'record42',thread:'task42',aspect:'overall',value:'adequate'});
  await page.evaluate(()=>{window.retainedHistoryList=document.querySelector('.history-list');window.retainedHistoryDetail=document.querySelector('.history-detail');window.receive({connections:2,accountUsage:{valid_until:Date.now()/1000+60},threads:{unrelated:{name:'Live task',status:'active',context_window:{used_percent:30}}}});});
  // The first live overlay change may rebuild; context-only updates must not.
  await page.evaluate(()=>{window.retainedHistoryList=document.querySelector('.history-list');window.retainedHistoryDetail=document.querySelector('.history-detail');window.receive({threads:{unrelated:{name:'Live task',status:'active',context_window:{used_percent:31}}}});});
  assert.equal(await page.evaluate(()=>window.retainedHistoryList===document.querySelector('.history-list')&&window.retainedHistoryDetail===document.querySelector('.history-detail')),true,'Context-only updates rebuilt History');

  assert.equal(await page.locator('[data-section=quality]').getAttribute('open'),'');
  await page.locator('[data-section=quality]>summary').click();
  await page.locator('.history-detail').evaluate(n=>n.scrollTop=0);
  if(process.env.ROUTER_HISTORY_SCREENSHOT)await page.locator('#surface').screenshot({path:process.env.ROUTER_HISTORY_SCREENSHOT});
  await page.locator('#history-search').fill('no matching record');
  assert.equal(await page.locator('.history-row').count(),0);
  assert.equal(await page.locator('#history-search').evaluate(n=>n===document.activeElement),true);
  assert.match(await page.locator('.history-no-results').innerText(),/No hay registros/);
  await page.locator('#history-search').fill('Sol');
  assert.ok(await page.locator('.history-row').count()>0);
  await page.evaluate(()=>window.receive({connections:1}));
  assert.equal(await page.locator('#history-search').inputValue(),'Sol');
  for(const width of [650,390]){
   await page.setViewportSize({width,height:640});
   const fits=await page.locator('#history').evaluate(n=>n.scrollWidth<=n.clientWidth);
   assert.ok(fits,'History overflows at '+width);
   assert.equal(await page.locator('nav').isVisible(),true);
  }
  await page.evaluate(()=>window.receive({readOnly:true}));
  await page.locator('[data-section=quality]>summary').click();
  assert.equal(await page.locator('[data-section=quality]').getByRole('button',{name:'Adecuada',exact:true}).first().isDisabled(),true);
  await page.getByRole('button',{name:'Inicio',exact:true}).click();
  assert.equal((await page.locator('#activity').innerText()).includes('Los trabajos anteriores están en Historial.'),false);

  await page.setViewportSize({width:800,height:760});
  const base={id:'evidence',thread:'synthetic',time:1800000000,started:1800000000,title:'Validar la conexión',model:'gpt-6-astra',effort:'high',routing_engine:'jev'};
  const select=async extra=>page.evaluate(record=>{
   window.receive({threads:{},readOnly:false,history:[{event:'monitor_decision_snapshot',record}]});
   selectedDecision=record.id;showTab('history');
  },{...base,...extra});
  await select({status:'failed',finished:1800000065,outputTokens:0,native_total_usage:{inputTokens:10000,outputTokens:2000},native_retries:2,error_type:'httpConnectionFailed',error_http_status:503});
  const measurements=page.locator('.history-measurements');
  assert.equal(await measurements.locator('.history-measurement').count(),3,'Missing input must not be replaced by cumulative totals or zero');
  assert.match(await measurements.innerText(),/Tokens de salida\s+0\s+Última llamada/);
  assert.match(await measurements.innerText(),/Reintentos de conexión\s+2/);
  assert.match(await page.locator('.history-detail>.incident').innerText(),/httpConnectionFailed · HTTP 503/,'Incidents must be visible without opening diagnostics');
  await select({inputTokens:-1,outputTokens:'0',finished:1799999999});
  assert.equal(await measurements.count(),0,'Invalid or absent measurements must not appear');
  assert.equal(await page.locator('[data-section=diagnostics]').count(),0);

  const sameSettings={accepted_model:base.model,accepted_effort:base.effort,configured_model:base.model,configured_effort:base.effort};
  await select({...sameSettings,comparisons:{jev:{routing_engine:'jev',engine_active:true,engine_status:'ok'}},usage_estimates:{empty:{}}});
  assert.equal(await page.locator('[data-section=diagnostics]').count(),0,'Identical settings, successful applied engine and empty estimates add no diagnostic value');
  await select({...sameSettings,observed_model:base.model,observed_effort:base.effort,evidence_confidence:'confirmed'});
  assert.equal(await page.locator('[data-section=diagnostics] .history-group-body').innerHTML(),'','Diagnostics must remain lazy');
  await page.locator('[data-section=diagnostics]>summary').click();
  await page.locator('.history-evidence-setting').first().waitFor({state:'visible'});
  assert.equal(await page.locator('.history-evidence-setting').count(),1,'Duplicate accepted/published settings should be suppressed');
  assert.match(await page.locator('[data-section=diagnostics]').innerText(),/Inferencia confirmada/);
  await select({...sameSettings,observed_candidate_model:base.model,evidence_confidence:'probable'});
  assert.equal(await page.locator('[data-section=diagnostics]').getAttribute('open'),'','Open diagnostics should survive new evidence');
  assert.match(await page.locator('[data-section=diagnostics]').innerText(),/Observación sin confirmar/);
  assert.doesNotMatch(await page.locator('[data-section=diagnostics]').innerText(),/Inferencia confirmada/);
  await select({...sameSettings,accepted_model:'gpt-6.1-sol',configured_model:'gpt-6.1-sol',phase_events:[{phase_status:'unchanged'},{phase_name:'execution',phase_status:'applied',phase_model:'gpt-6.1-sol'}],usage_estimates:{valid:{credits:0.002,usd:0.001},empty:{}}});
  const diagnosticText=await page.locator('[data-section=diagnostics]').innerText();
  assert.match(diagnosticText,/Ajustes aceptados por Codex/);
  assert.doesNotMatch(diagnosticText,/Configuración publicada|Sin cambio|NaN/);
  assert.match(diagnosticText,/Cambio aceptado/);
  assert.match(diagnosticText,/0.0020 créditos Codex/);
  assert.match(diagnosticText,/no es el coste facturado/);
  assert.deepEqual(errors,[]);
  console.log('PASS: responsive History, pagination/search, rating dispatch, cached/lazy DOM, useful detail, incidents, valid last-call metrics and strict evidence labels');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
