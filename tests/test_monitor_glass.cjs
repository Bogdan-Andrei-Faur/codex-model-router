// Approved daily UI contract with synthetic data; no live journal or provider.
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
  const channel=process.env.ROUTER_TEST_BROWSER==='chromium'?undefined:process.env.ROUTER_TEST_BROWSER||'chrome';
  const browser=await chromium.launch({...channel?{channel}:{},headless:true});
  try{
    const page=await browser.newPage({viewport:{width:432,height:900}}),errors=[];
    page.on('pageerror',e=>errors.push(String(e)));
    await page.addInitScript(()=>{window.nativeMessages=[];window.webkit={messageHandlers:{monitor:{postMessage:m=>window.nativeMessages.push(m)}}};});
    await page.route('**/codex.png',r=>r.fulfill({path:path.resolve(__dirname,'../assets/codex-official.png')}));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
    await page.evaluate(()=>window.receive({connections:1,ui:{mode:'Expanded',nativeGlass:true},
      accountUsage:{remaining_percent:3,valid_until:Date.now()/1000+60,windows:[{duration_minutes:300,remaining_percent:3},{duration_minutes:10080,remaining_percent:68}]},
      threads:{zero:{name:'Fixture zero',status:'active',decision_id:'d',model:'gpt-6.1-sol',effort:'high',tokens:{inputTokens:0,outputTokens:0}},
        unknown:{name:'Fixture unknown',status:'active',model:'gpt-6-luna'},
        compacting:{name:'Fixture compacting',status:'completed',context_compaction:{state:'compacting'}},
        idle:{name:'Fixture idle',status:'idle'},waiting:{name:'Fixture waiting',status:'waiting'}},
      history:[{event:'decision_created',decision_id:'d',model:'gpt-6.1-sol',time:1},
        {event:'decision_usage',decision_id:'d',inputTokens:12,outputTokens:3,time:2},
        {event:'decision_usage_total',decision_id:'d',inputTokens:1200,outputTokens:300,time:2}]}));
    assert.equal(await page.locator('.task-row').count(),3);
    assert.equal(await page.locator('#expand [data-lucide="chevron-right"]').count(),1);
    assert.equal(await page.locator('#collapse,#hide,header').count(),0);
    assert.equal(await page.locator('footer,#pause,#product-version').count(),0,'Home must not expose the old footer controls');
    const rounding=await page.locator('.hero-model .badge').first().evaluate(n=>getComputedStyle(n).borderTopLeftRadius);
    assert.equal(rounding,'999px','Model tags use the shared rounded pill treatment');
    const positions=await page.evaluate(()=>Object.fromEntries(['nav','#pages'].map(selector=>{const r=document.querySelector(selector).getBoundingClientRect();return [selector,{top:r.top,bottom:r.bottom}];})));
    assert.ok(positions.nav.top<20&&positions.nav.bottom<=positions['#pages'].top,'Navigation must sit at the top above content');
    assert.deepEqual(await page.locator('nav button').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('aria-label'))),['Inicio','Agentes','Historial','Consumo','Ajustes']);
    assert.equal(await page.locator('nav .ui-glyph').count(),5);
    assert.equal(await page.locator('nav [aria-pressed="true"]').getAttribute('data-tab'),'home');
    await page.getByRole('button',{name:'Agentes',exact:true}).click();
    assert.equal(await page.locator('.agent-workspace-detail').count(),1,'Agents opens the selected agent inspector');
    assert.equal(await page.locator('nav [aria-pressed="true"]').getAttribute('data-tab'),'activity');
    assert.equal(await page.locator('.agent-portrait .character').count(),1);
    assert.equal(await page.locator('.agent-portrait .character-context').count(),0,'Portrait must not repeat context meters');
    assert.equal(await page.locator('.agent-pick').count(),5,'Agents includes idle conversations');
    await page.locator('.agent-pick').filter({hasText:'Fixture idle'}).click();
    assert.equal(await page.locator('.agent-identity-copy h3').innerText(),'Fixture idle');

    await page.getByRole('button',{name:'Inicio',exact:true}).focus();await page.keyboard.press('Enter');
    assert.equal(await page.locator('.agent-workspace-detail').count(),0,'Home restores the overview');
    assert.equal(await page.locator('nav [aria-pressed="true"]').count(),1,'Exactly one destination is active');
    const zeroTags=page.locator('.hero-model .badge');
    assert.deepEqual(await zeroTags.allTextContents(),['Sol 6.1','Alto']);
    assert.equal(await page.locator('.companion-headline').innerText(),'En ello.');
    assert.equal(await page.locator('.hero-model').innerText(),'Modelo seleccionado\nSol 6.1\nAlto');
    assert.ok(!(await page.locator('.task-row').allTextContents()).join(' ').includes('Fixture idle'));
    await page.evaluate(()=>window.receive({agentThreads:{idle:{name:'Catalog idle',status:'idle'},archived:{name:'Archived task',status:'idle',archived:true}}}));
    await page.getByRole('button',{name:'Agentes',exact:true}).click();
    assert.deepEqual(await page.locator('.agent-pick-copy>span').allTextContents(),['Catalog idle']);
    await page.evaluate(()=>window.receive({agentThreads:{restored:{name:'Restored task',status:'idle'}}}));
    assert.equal(await page.locator('.agent-identity-copy h3').innerText(),'Restored task','Removed/archived selection must fall back safely');
    await page.getByRole('button',{name:'Inicio',exact:true}).click();
    assert.equal(await page.locator('.hero-task').innerText(),'Fixture zero','Inactive selection must not affect Home');
    await page.evaluate(()=>window.receive({agentThreads:undefined}));

    assert.equal(await page.locator('.task-row .avatar[data-state="compacting"]').count(),1);
    assert.equal(await page.locator('#expanded .quota-ring').count(),0);
    await page.locator('.overview-quota').click();
    assert.deepEqual(await page.locator('#activity .quota-value').allTextContents(),['3 % disponible','68 % disponible']);
    assert.equal(await page.locator('.task-row[data-status=waiting]').count(),1);
    assert.equal(await page.locator('.agent-list-heading').innerText(),'Otros agentes');
    await page.locator('.detail-toggle').click();
    assert.equal(await page.locator('#activity .companion-hero,#activity .hero-metrics,#activity .pipeline').count(),0,'Agents must not repeat Home or History');
    await page.locator('.agent-pick').filter({hasText:'Fixture unknown'}).click();
    assert.equal(await page.locator('.agent-identity-copy h3').innerText(),'Fixture unknown');
    await page.getByRole('button',{name:'Manual',exact:true}).click();
    assert.deepEqual(await page.evaluate(()=>window.nativeMessages.filter(m=>m.action==='taskMode').at(-1)),{action:'taskMode',thread:'unknown',value:'manual'});
    assert.equal(await page.getByRole('button',{name:'Automático',exact:true}).getAttribute('aria-pressed'),'true','Wait for native acknowledgement');
    await page.evaluate(()=>window.receive({taskModes:{unknown:'manual'},threads:{unknown:{name:'Fixture unknown',status:'active',model:'gpt-6-luna',accepted_model:'gpt-6-luna',observed_model:'gpt-6.1-sol',evidence_confidence:'probable'}}}));
    assert.equal(await page.getByRole('button',{name:'Manual',exact:true}).getAttribute('aria-pressed'),'true');
    assert.equal(await page.getByRole('button',{name:'Manual',exact:true}).evaluate(n=>n===document.activeElement),true,'Live updates preserve control focus');
    await page.evaluate(()=>window.receive({threads:{unknown:{name:'Fixture unknown',status:'waiting',model:'gpt-6-luna',accepted_model:'gpt-6-luna',observed_model:'gpt-6.1-sol',evidence_confidence:'confirmed'}}}));
    assert.match(await page.locator('.routing-attention').innerText(),/espera tu respuesta/);
    await page.evaluate(()=>window.receive({threads:{unknown:{name:'Fixture unknown',status:'active',turn_id:'live',live_plan:{turn_id:'live',steps:[{label:'Investigar',state:'completed'},{label:'Implementar',state:'active'},{label:'Validar',state:'pending'}]}}}}));
    assert.equal(await page.locator('.live-pipeline-step.completed').count(),1);
    assert.equal(await page.locator('.live-pipeline-step[aria-current="step"]').innerText(),'2\nImplementar\nEn curso');
    await page.evaluate(()=>window.receive({threads:{unknown:{name:'Fixture unknown',status:'active',turn_id:'live',live_plan:{turn_id:'live',steps:[{label:'Investigar',state:'completed'},{label:'Implementar',state:'completed'},{label:'Validar',state:'active'}]}}}}));
    assert.equal(await page.locator('.live-pipeline-step.completed').count(),2,'Plan must refresh without reselecting task');
    assert.match(await page.locator('.live-pipeline-step[aria-current="step"]').innerText(),/Validar/);

    await page.evaluate(()=>window.receive({config:{enabled:false}}));
    assert.match(await page.locator('.routing-mode').innerText(),/pausado/);
    await page.evaluate(()=>window.receive({connections:0}));
    assert.match(await page.locator('.routing-attention').innerText(),/últimos datos/);
    await page.evaluate(()=>window.receive({connections:1,config:{enabled:true},readOnly:true}));
    assert.equal(await page.getByRole('button',{name:'Manual',exact:true}).isDisabled(),true);
    await page.evaluate(()=>window.receive({readOnly:false}));
    await page.locator('[data-tab="statistics"]').click();
    assert.match(await page.locator('.consumption-summary').innerText(),/Por modelo elegido/);
    await page.locator('.consumption-scope summary').click();
    assert.match(await page.locator('.consumption-summary').innerText(),/no confirma el modelo de cada inferencia/);
    assert.equal(await page.locator('.consumption-diagnostics').getAttribute('open'),null);
    await page.locator('.consumption-diagnostics summary').click();
    await page.evaluate(()=>window.receive({telemetry:{requests:1}}));
    assert.equal(await page.locator('.consumption-diagnostics').getAttribute('open'),'','Live refresh closed diagnostics');
    assert.ok((await page.locator('.consumption-diagnostics').innerText()).includes('INFERENCIA OBSERVADA') || (await page.locator('.consumption-diagnostics').innerText()).includes('Inferencias confirmadas'));
    await page.locator('[data-tab="settings"]').click();
    assert.equal(await page.locator('#view-title').innerText(),'Ajustes');
    assert.equal(await page.locator('#settings #pause strong').innerText(),'Pausar enrutamiento');
    assert.equal(await page.locator('#settings #pause [data-lucide="pause"]').count(),1);
    assert.equal(await page.locator('#settings #product-version').count(),1);
    await page.locator('.icon-catalog summary').click();
    assert.equal(await page.locator('.icon-catalog-grid > *').count(),16);
    assert.deepEqual(await page.locator('.icon-catalog .glyph').evaluateAll(nodes=>nodes.map(n=>n.dataset.lucide).sort()),await page.evaluate(()=>Object.values(RouterIcons.categories).sort()));
    assert.equal(await page.locator('.icon-catalog .glyph').evaluateAll(nodes=>nodes.every(n=>n.getAttribute('aria-hidden')==='true'&&n.getAttribute('focusable')==='false')),true);
    // The DOM uses the exact primitive attributes from the pinned library.
    assert.equal(await page.locator('.icon-catalog .glyph').evaluateAll(nodes=>nodes.every(n=>JSON.stringify([...n.children].map(c=>[c.localName,Object.fromEntries([...c.attributes].map(a=>[a.name,a.value]))]))===JSON.stringify(RouterIcons.nodes[n.dataset.lucide]))),true);
    const glass=await page.locator('#surface').evaluate(n=>getComputedStyle(n,':before').backgroundColor);
    await page.evaluate(()=>window.receiveUI({reduceTransparency:true},null));
    const solid=await page.locator('#surface').evaluate(n=>getComputedStyle(n,':before').backgroundColor);
    assert.equal(glass,solid,'The notch remains opaque when native transparency preferences change');
    assert.equal(solid,'rgb(8, 9, 10)');
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#quota .quota-number').innerText(),'68%');
    await page.evaluate(()=>{const r=document.querySelector('#quota').getBoundingClientRect();window.monitorPointer({x:r.x+r.width/2,y:r.y+r.height/2});});
    assert.match(await page.locator('#peek').innerText(),/semanal/);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#peek').isVisible(),false);
    await page.emulateMedia({colorScheme:'light'});
    await page.locator('#expand').click();
    assert.ok((await page.locator('#surface').evaluate(n=>getComputedStyle(n).color)).startsWith('rgb('));
    assert.deepEqual(errors,[]);
    console.log('PASS: active/compacting filter, attention, true zero/unknown, weekly versus short quota, controls, chosen-model disclosure, diagnostics, 16 icons, transparency and quota native hover');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
