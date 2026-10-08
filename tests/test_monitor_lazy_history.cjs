// Activity must remain independent of journal replay, including on first open.
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
  const channel=process.env.ROUTER_TEST_BROWSER==='chromium'?undefined:process.env.ROUTER_TEST_BROWSER||(process.platform==='win32'?'msedge':'chrome');
  const browser=await chromium.launch({...channel?{channel}:{},headless:true});
  try {
    const page=await browser.newPage({viewport:{width:432,height:900}});
    const errors=[];page.on('pageerror',e=>errors.push(String(e)));
    await page.addInitScript(()=>{
      window.nativeMessages=[];
      window.webkit={messageHandlers:{monitor:{postMessage:m=>window.nativeMessages.push(m)}}};
    });
    await page.route('**/codex.png',r=>r.fulfill({path:path.resolve(__dirname,'../assets/codex-official.png')}));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
    await page.evaluate(()=>{
      window.projections=0;
      const original=MonitorCore.decisions;
      MonitorCore.decisions=(...args)=>{window.projections++;return original(...args);};
      window.receive({ui:{mode:'Compact',lazyHistory:true},historyLoaded:false,connections:1,
        threads:{live:{name:'Live fixture',status:'active',decision_id:'chosen',updated:1}}});
    });
    const timing=await page.evaluate(()=>{
      const started=performance.now();setMode('Expanded');
      return {activity_ms:performance.now()-started,transition:getComputedStyle(document.querySelector('#surface')).transitionDuration};
    });
    assert.equal(await page.evaluate(()=>window.projections),0,'Activity replayed history on first open');
    assert.ok((await page.locator('#activity').innerText()).includes('Live fixture'));
    assert.equal(timing.transition,'0.36s, 0.36s');
    assert.equal(await page.evaluate(()=>window.nativeMessages.some(m=>m.action==='history' && m.value)),false,'Activity requested journal');
    await page.locator('[data-tab="settings"]').click();
    assert.equal(await page.evaluate(()=>window.projections),0,'Settings replayed history');
    await page.locator('[data-tab="home"]').click();
    await page.locator('.detail-toggle').click();
    await page.locator('[data-tab="history"]').click();
    assert.ok((await page.locator('#history').innerText()).includes('Cargando historial'));
    assert.equal(await page.evaluate(()=>selectedDecision),null,'Navigation must not select an unrelated historical decision');
    assert.equal(await page.evaluate(()=>window.nativeMessages.filter(m=>m.action==='history').at(-1).value),true);
    const records=Array.from({length:37000},(_,i)=>({event:'decision_created',decision_id:i===0?'chosen':'d'+i,
      thread:i===0?'live':'t'+i,time:i+1,title:'Synthetic history '+i,model:'gpt-6-luna',effort:'high'}));
    await page.evaluate(history=>window.receive({history}),records);
    assert.equal(await page.locator('.history-row').count(),40,'Historical data was truncated or not paginated');
    await page.locator('.history-row').first().click();
    assert.ok((await page.locator('.history-detail').innerText()).includes('Synthetic history 36999'),'Selected history detail missing');
    const count=await page.evaluate(()=>window.projections);
    await page.locator('[data-tab="home"]').click();
    await page.evaluate(()=>window.receive({threads:{live:{name:'Fresh live fixture',status:'active',updated:2}}}));
    const cachedTiming=await page.evaluate(()=>{const start=performance.now();setMode('Compact');setMode('Expanded');return performance.now()-start;});
    assert.equal(await page.evaluate(()=>window.projections),count,'Activity replayed already-loaded journal');
    assert.ok((await page.locator('#activity').innerText()).includes('Fresh live fixture'));
    assert.equal(await page.evaluate(()=>window.nativeMessages.filter(m=>m.action==='history').at(-1).value),false);
    await page.locator('[data-tab="history"]').click();
    await page.evaluate(()=>window.receive({threads:{live:{name:'Updated live title',status:'active',decision_id:'chosen',updated:3}}}));
    assert.equal(await page.evaluate(()=>window.projections),count,'Live task updates replayed the unchanged historical journal');
    await page.locator('[data-tab="statistics"]').click();
    assert.ok(!(await page.locator('#statistics').innerText()).includes('Cargando historial'),'Loaded statistics unavailable');
    // Reduced-motion preference remains authoritative.
    await page.evaluate(()=>window.receive({ui:{reduced:true}}));
    assert.equal(await page.locator('#surface').evaluate(n=>getComputedStyle(n).transitionDuration),'0s');
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({pass:true,history_records:records.length,activity_first_open_ms:Math.round(timing.activity_ms),cached_roundtrip_ms:Math.round(cachedTiming),activity_history_projections:0,transition_ms:360,physical_latency_verified:false}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
