// Local synthetic UI regressions. Chromium cannot prove AppKit focus delivery.
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
      window.decisionComputations=0;
      const original=MonitorCore.decisions;
      MonitorCore.decisions=(...args)=>{window.decisionComputations++;return original(...args);};
      window.receive({ui:{mode:'Compact',reduced:true,acknowledgesMode:true},connections:1,
        threads:{fixture:{name:'Synthetic agent',status:'active',model:'gpt-6-luna',effort:'high',updated:1}},
        history:Array.from({length:37000},(_,i)=>({event:'decision_created',decision_id:'d'+i,thread:'t'+i,time:i}))});
    });
    assert.equal(await page.evaluate(()=>window.decisionComputations),0,'Compact must not project full journal');
    assert.equal(await page.locator('.task-row').count(),0,'Hidden activity rebuilt');
    const avatar=await page.locator('#agents .avatar').boundingBox();
    await page.evaluate(p=>window.monitorPointer(p),{x:avatar.x+22,y:avatar.y+22});
    assert.equal(await page.locator('#peek').isVisible(),true,'Inactive native projection did not open agent peek');
    assert.ok((await page.locator('#peek').innerText()).includes('Synthetic agent'));
    assert.equal(await page.evaluate(()=>document.activeElement.tagName),'BODY','Hover stole keyboard focus');
    const peek=await page.locator('#peek').boundingBox();
    await page.evaluate(p=>window.monitorPointer(p),{x:peek.x+20,y:peek.y+20});
    await page.waitForTimeout(260);
    assert.equal(await page.locator('#peek').isVisible(),true,'Peek closes while pointer inside it');
    await page.evaluate(()=>window.monitorPointer(null));
    await page.locator('#peek').waitFor({state:'hidden',timeout:2000});
    assert.equal(await page.locator('#peek').isVisible(),false,'Pointer exit did not close peek');
    await page.evaluate(p=>window.monitorPointer(p),{x:avatar.x+22,y:avatar.y+22});
    await page.evaluate(()=>window.monitorPointer(null,false));await page.waitForTimeout(260);
    assert.equal(await page.locator('#peek').isVisible(),true,'Key-window handoff closed active hover');
    // Native hosts keep reporting pointer positions. Repeated outside samples
    // must not postpone the leave deadline forever (agent and account quota).
    await page.clock.install();
    for(const selector of ['#agents .avatar','#quota']) {
      const rect=await page.locator(selector).boundingBox();
      await page.evaluate(p=>window.monitorPointer(p),{x:rect.x+rect.width/2,y:rect.y+rect.height/2});
      assert.equal(await page.locator('#peek').isVisible(),true);
      for(let i=0;i<12;i++) {await page.evaluate(()=>window.monitorPointer(null));await page.clock.runFor(33);}
      assert.equal(await page.locator('#peek').isVisible(),false,selector+' remains expanded during repeated native pointer exits');
      await page.evaluate(p=>window.monitorPointer(p),{x:rect.x+rect.width/2,y:rect.y+rect.height/2});
      await page.evaluate(()=>window.monitorPointer(null));await page.clock.runFor(100);
      const content=await page.locator('#peek').boundingBox();
      await page.evaluate(p=>window.monitorPointer(p),{x:content.x+20,y:content.y+20});await page.clock.runFor(300);
      assert.equal(await page.locator('#peek').isVisible(),true,'Returning to details must cancel closure');
      assert.equal(await page.locator('#compact [title]').count(),0,'Native tooltips duplicate compact details');
      await page.keyboard.press('Escape');
      await page.evaluate(()=>window.monitorPointer(null));await page.clock.runFor(300);
      assert.equal(await page.locator('#peek').isVisible(),false);
    }
    const timings=await page.evaluate(()=>{
      const start=performance.now();setMode('Expanded');const expanded=performance.now()-start;
      setMode('Compact');
      return {expanded,requests:window.nativeMessages.filter(m=>m.action==='mode').slice(-2)};
    });
    const [old,newest]=timings.requests;
    await page.evaluate(request=>window.receiveUI({mode:'Expanded'},request),old.request);
    assert.equal(await page.locator('#compact').isVisible(),true,'Stale ack reversed latest mode');
    await page.evaluate(()=>window.receive({ui:{mode:'Expanded'},connections:1}));
    assert.equal(await page.locator('#compact').isVisible(),true,'Polling snapshot reversed pending mode');
    await page.evaluate(request=>window.receiveUI({mode:'Compact'},request),newest.request);
    await page.evaluate(request=>window.receiveUI({mode:'Expanded'},request),old.request);
    assert.equal(await page.locator('#compact').isVisible(),true,'Late ack reversed acknowledged mode');
    await page.evaluate(request=>window.receive({ui:{mode:'Expanded',modeRequest:request,acknowledgesMode:true}}),old.request);
    assert.equal(await page.locator('#compact').isVisible(),true,'Late polling snapshot reversed acknowledged mode');
    const before=await page.evaluate(()=>window.decisionComputations);
    await page.evaluate(()=>window.receive({threads:{fixture:{name:'Updated synthetic agent',status:'active',updated:2}}}));
    assert.equal(await page.evaluate(()=>window.decisionComputations),before,'Hidden update projected full journal');
    await page.locator('#expand').click();
    assert.equal(await page.locator('#expanded').isVisible(),true,'One DOM click must expand immediately');
    assert.ok((await page.locator('#activity').innerText()).includes('Updated synthetic agent'),'Expanded view stale');
    // One deadline closes Expanded; re-entry cancels it, regardless of repeated
    // native outside samples. The shared path also receives DOM leave events.
    await page.evaluate(()=>window.monitorPointer(null));await page.clock.runFor(100);
    const nav=await page.locator('nav').boundingBox();
    await page.evaluate(p=>window.monitorPointer(p),{x:nav.x+20,y:nav.y+20});await page.clock.runFor(400);
    assert.equal(await page.locator('#expanded').isVisible(),true,'Re-entry failed to cancel auto-collapse');
    for(let i=0;i<12;i++){await page.evaluate(()=>window.monitorPointer(null));await page.clock.runFor(40);}
    assert.equal(await page.locator('#compact').isVisible(),true,'Repeated outside samples postponed auto-collapse');
    assert.equal(await page.evaluate(()=>window.nativeMessages.filter(m=>m.action==='mode').at(-1).value),'Compact');
    await page.locator('#expand').click();
    await page.evaluate(()=>window.receive({config:{enabled:true,routing_engine:'jev'}}));
    await page.locator('[data-tab="settings"]').click();
    await page.locator('[data-settings-section=routing]').click();
    await page.evaluate(()=>{const input=document.querySelector('#settings input[type=password]');input.closest('.key-editor').hidden=false;input.value='synthetic-unsaved-fixture';});
    await page.mouse.move(1,850);await page.clock.runFor(400);
    assert.equal(await page.locator('#compact').isVisible(),true,'DOM exit failed to compact the island');
    await page.locator('#expand').click();
    assert.equal(await page.locator('#settings input[type=password]').first().inputValue(),'synthetic-unsaved-fixture','Auto-collapse discarded unsaved input');
    await page.evaluate(()=>{heightDrag={y:0,height:600};window.monitorPointer(null);});await page.clock.runFor(400);
    assert.equal(await page.locator('#expanded').isVisible(),true,'Auto-collapse interrupted height drag');
    await page.evaluate(()=>finishHeightDrag());await page.clock.runFor(400);
    assert.equal(await page.locator('#compact').isVisible(),true,'Outside release failed to resume auto-collapse');
    // Legacy Windows host has no UI-only ack; polling/menu mode remains authoritative.
    await page.evaluate(()=>{pendingModeRequest=0;window.receiveUI({acknowledgesMode:false,mode:'Expanded'},null);setMode('Compact');window.receive({ui:{mode:'Expanded'}});});
    assert.equal(await page.locator('#expanded').isVisible(),true,'Legacy host mode sync broken');
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({pass:true,synthetic_records:37000,expand_projection_ms:Math.round(timings.expanded),native_focus_delivery:'not_proven_by_browser'}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
