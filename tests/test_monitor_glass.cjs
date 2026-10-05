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
    assert.equal(await page.locator('#expand [data-lucide="panel-left-open"]').count(),1);
    assert.equal(await page.locator('#collapse [data-lucide="panel-left-close"]').count(),1);
    assert.equal(await page.locator('#hide [data-lucide="x"]').count(),1);
    assert.equal(await page.locator('#pause [data-lucide="pause"]').count(),1);
    const rounding=await page.locator('.agent-model .badge').first().evaluate(n=>getComputedStyle(n).borderTopLeftRadius);
    assert.equal(rounding,'999px','Colored labels must remain pill-shaped');
    const positions=await page.locator('header,nav,#pages').evaluateAll(nodes=>nodes.map(n=>n.getBoundingClientRect().top));
    assert.ok(positions[0]<positions[1]&&positions[1]<positions[2],'Navigation must be above content');
    const zeroTags=page.locator('.task-row').filter({hasText:'Fixture zero'}).locator('.agent-model .badge');
    assert.deepEqual(await zeroTags.allTextContents(),['Sol 6.1','Alto']);
    assert.notEqual(await zeroTags.first().evaluate(n=>getComputedStyle(n).backgroundColor),await zeroTags.last().evaluate(n=>getComputedStyle(n).backgroundColor),'Model and effort must keep distinct colored labels');
    assert.notEqual(await zeroTags.first().evaluate(n=>getComputedStyle(n).color),await page.locator('.task-row').filter({hasText:'Fixture unknown'}).locator('.agent-model .badge').first().evaluate(n=>getComputedStyle(n).color),'Model identity lost semantic color');
    assert.ok(!(await page.locator('.task-row').allTextContents()).join(' ').includes('Fixture idle'));
    assert.equal(await page.locator('.task-row').filter({hasText:'Fixture zero'}).locator('.agent-usage strong').innerText(),'0');
    assert.equal(await page.locator('.task-row').filter({hasText:'Fixture unknown'}).locator('.agent-usage strong').innerText(),'—');
    assert.equal(await page.locator('.task-row .compacting-ring').count(),1);
    assert.equal(await page.locator('#expanded .quota-ring').count(),0);
    assert.deepEqual(await page.locator('#activity .quota-value').allTextContents(),['3 % disponible','68 % disponible']);
    assert.match(await page.locator('.attention-notice summary').innerText(),/1 agente/);
    await page.locator('.task-row').filter({hasText:'Fixture zero'}).click();
    assert.match(await page.locator('.agent-detail').innerText(),/No es el total del turno/);
    assert.ok((await page.locator('.agent-detail').innerText()).includes('Manual'));
    await page.locator('[data-tab="statistics"]').click();
    assert.match(await page.locator('.consumption-summary').innerText(),/POR MODELO ELEGIDO/);
    assert.match(await page.locator('.consumption-summary').innerText(),/no confirma el modelo de cada inferencia/);
    assert.equal(await page.locator('.consumption-diagnostics').getAttribute('open'),null);
    await page.locator('.consumption-diagnostics summary').click();
    await page.evaluate(()=>window.receive({telemetry:{requests:1}}));
    assert.equal(await page.locator('.consumption-diagnostics').getAttribute('open'),'','Live refresh closed diagnostics');
    assert.ok((await page.locator('.consumption-diagnostics').innerText()).includes('INFERENCIA OBSERVADA') || (await page.locator('.consumption-diagnostics').innerText()).includes('Inferencias confirmadas'));
    await page.locator('[data-tab="settings"]').click();
    assert.equal(await page.locator('#view-title').innerText(),'Ajustes');
    await page.locator('.icon-catalog summary').click();
    assert.equal(await page.locator('.icon-catalog-grid > *').count(),16);
    assert.deepEqual(await page.locator('.icon-catalog .glyph').evaluateAll(nodes=>nodes.map(n=>n.dataset.lucide).sort()),await page.evaluate(()=>Object.values(RouterIcons.categories).sort()));
    assert.equal(await page.locator('.icon-catalog .glyph').evaluateAll(nodes=>nodes.every(n=>n.getAttribute('aria-hidden')==='true'&&n.getAttribute('focusable')==='false')),true);
    // The DOM uses the exact primitive attributes from the pinned library.
    assert.equal(await page.locator('.icon-catalog .glyph').evaluateAll(nodes=>nodes.every(n=>JSON.stringify([...n.children].map(c=>[c.localName,Object.fromEntries([...c.attributes].map(a=>[a.name,a.value]))]))===JSON.stringify(RouterIcons.nodes[n.dataset.lucide]))),true);
    const glass=await page.locator('#surface').evaluate(n=>getComputedStyle(n).backgroundColor);
    await page.evaluate(()=>window.receiveUI({reduceTransparency:true},null));
    const solid=await page.locator('#surface').evaluate(n=>getComputedStyle(n).backgroundColor);
    assert.notEqual(glass,solid);
    await page.locator('#collapse').click();
    assert.equal(await page.locator('#quota').innerText(),'68%');
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
