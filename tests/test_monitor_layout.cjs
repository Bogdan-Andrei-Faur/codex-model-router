// Local WebKit-surface layout checks in Chromium; native macOS still needs a Mac.
const { chromium } = require('playwright');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const channel = process.env.ROUTER_TEST_BROWSER === 'chromium' ? undefined :
    process.env.ROUTER_TEST_BROWSER || (process.platform === 'darwin' ? 'chrome' : 'msedge');
  const browser = await chromium.launch({...channel ? {channel} : {},headless:true});
  try {
    const page = await browser.newPage();
    const errors=[];page.on('pageerror',error=>errors.push(String(error)));
    await page.addInitScript(()=>{
      window.nativeMessages=[];
      window.webkit={messageHandlers:{monitor:{postMessage:message=>window.nativeMessages.push(message)}}};
    });
    await page.route('**/codex.png',route=>route.fulfill({path:path.resolve(__dirname,'../assets/codex-official.png')}));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
    for (const [mismatch,unknown,label] of [[false,false,'v0.3.1'],[false,true,'v0.3.1 · puente sin verificar'],[true,true,'v0.3.1 · reinicio del router pendiente']]) {
      await page.evaluate(([bridgeBuildMismatch,bridgeBuildUnknown])=>window.receive({productVersion:'0.3.1',bridgeVersions:['0.3.1'],bridgeBuildMismatch,bridgeBuildUnknown}),[mismatch,unknown]);
      assert.equal(await page.locator('#product-version').innerText(),label);
    }
    await page.evaluate(()=>window.receive({bridgeBuildMismatch:false,bridgeBuildUnknown:false}));
    for (const height of [1020,1380,674,460]) {
      await page.setViewportSize({width:432,height});
      const preferred=Math.min(height,Math.max(560,(height+20)*.9));
      await page.evaluate(value=>window.receive({ui:{mode:'Expanded',topmost:true,reduced:true,panelHeight:value}}),preferred);
      const rect=await page.locator('#surface').boundingBox();
      assert.ok(Math.abs(rect.y+rect.height-(height-8))<1,'Bottom anchor moved');
      assert.ok(rect.y>=8 && rect.height<=height-16,'Panel exceeds available area');
      assert.ok(Math.abs(rect.height-(preferred-16))<1,'Adaptive height differs');
      const header=await page.locator('header').boundingBox(),footer=await page.locator('footer').boundingBox();
      assert.ok(header.y>=rect.y && footer.y+footer.height<=rect.y+rect.height,'Chrome escaped panel');
    }
    await page.setViewportSize({width:432,height:1020});
    await page.evaluate(()=>window.receive({ui:{mode:'Expanded',reduced:true,panelHeight:936}}));
    const before=await page.locator('#surface').boundingBox();
    const grip=await page.locator('#height-grip').boundingBox();
    await page.mouse.move(grip.x+grip.width/2,grip.y+7);
    await page.mouse.down();await page.mouse.move(grip.x+grip.width/2,grip.y+157,{steps:6});await page.mouse.up();
    const after=await page.locator('#surface').boundingBox();
    assert.ok(Math.abs(after.height-(before.height-150))<2,'Grip did not resize panel');
    assert.ok(Math.abs(after.y+after.height-before.y-before.height)<1,'Resize moved bottom');
    const message=await page.evaluate(()=>window.nativeMessages.filter(m=>m.action==='resizeEnd').at(-1));
    assert.ok(message && Math.abs(message.height-after.height-16)<1,'Native preference not submitted');
    await page.locator('#height-grip').focus();await page.keyboard.press('Home');
    assert.ok(await page.evaluate(()=>window.nativeMessages.some(m=>m.action==='resizeReset')),'Automatic height reset unavailable');
    await page.clock.install();
    const activityFixture={older:{name:'Agente anterior',status:'active',updated:10,phase_pipeline:[{label:'Validación inicial',state:'active',evidence:'observed'}]},
      newer:{name:'Agente reciente',status:'completed',updated:20}};
    await page.evaluate(threads=>window.receive({threads,connections:1}),activityFixture);
    assert.equal(await page.locator('.featured-title').innerText(),'Agente reciente','Default must use latest update, not active priority');
    await page.locator('.task-row').filter({hasText:'Agente anterior'}).click();
    assert.equal(await page.locator('.featured-title').innerText(),'Agente anterior');
    assert.equal(await page.locator('[data-tab="activity"]').getAttribute('class'),'selected');
    activityFixture.newer.updated=30;
    activityFixture.older.phase_pipeline[0].label='Validación terminada';
    activityFixture.older.phase_pipeline[0].state='completed';
    await page.evaluate(threads=>window.receive({threads}),activityFixture);
    assert.equal(await page.locator('.featured-title').innerText(),'Agente anterior','Snapshot stole selected task');
    assert.ok((await page.locator('#activity .pipeline').innerText()).includes('Validación terminada'),'Held pipeline stopped refreshing');
    await page.clock.fastForward(45000);
    await page.locator('.featured-row .avatar').click();
    await page.clock.fastForward(20000);
    assert.equal(await page.locator('.featured-title').innerText(),'Agente anterior','Repeated click did not renew hold');
    await page.clock.fastForward(40001);
    assert.equal(await page.locator('.featured-title').innerText(),'Agente reciente','Hold did not expire without incoming snapshots');
    await page.locator('.task-row').filter({hasText:'Agente anterior'}).focus();await page.keyboard.press('Enter');
    await page.locator('.featured-release').click();
    assert.equal(await page.locator('.featured-title').innerText(),'Agente reciente','Explicit release failed');
    await page.locator('.task-row').filter({hasText:'Agente anterior'}).click();
    await page.evaluate(threads=>window.receive({threads}),{newer:activityFixture.newer});
    assert.equal(await page.locator('.featured-title').innerText(),'Agente reciente','Missing task left stale featured data');
    assert.equal(await page.locator('.featured-release').count(),0);
    console.log('PASS: latest task, manual one-minute hold, live pipeline, renewal, expiry, keyboard, release and missing task');
    for(const count of [1000,10000]){
      const elapsed=await page.evaluate(count=>{
        const records=Array.from({length:count},(_,i)=>({event:'decision_created',decision_id:'d'+i,thread:'t'+i,time:i+1,
          title:'Synthetic task '+String(i).padStart(5,'0'),model:'gpt-5.6-terra',effort:'medium',product_version:'0.3.0',build_id:'synthetic',routing_policy_version:3}));
        const start=performance.now();window.receive({history:records,threads:{},connections:1,productVersion:'0.3.0',bridgeVersions:['0.2.7']});
        return Math.round(performance.now()-start);
      },count);
      assert.ok(elapsed<3000,`Projection blocked too long: ${count} records / ${elapsed} ms`);
      console.log(`Projection: ${count} decisions / ${elapsed} ms`);
    }
    await page.locator('[data-tab="history"]').click();
    assert.equal(await page.locator('.history-row').count(),40,'History page must have bounded row count');
    await page.locator('#history-search').fill('Synthetic task 00001');
    assert.equal(await page.locator('.history-row').count(),1,'Cannot find decision beyond the old 80-record limit');
    await page.locator('.history-row').click();
    assert.ok((await page.locator('.history-detail').innerText()).includes('Synthetic task 00001'));
    await page.locator('#history-search').fill('Synthetic task');
    await page.evaluate(()=>window.receive({connections:2}));
    assert.equal(await page.locator('#history-search').inputValue(),'Synthetic task');
    assert.equal(await page.locator('.history-row').count(),40);
    assert.ok((await page.locator('#product-version').innerText()).includes('puente 0.2.7'));
    if(process.env.ROUTER_LAYOUT_SCREENSHOT)await page.screenshot({path:process.env.ROUTER_LAYOUT_SCREENSHOT});
    assert.deepEqual(errors,[]);
    console.log('PASS: responsive height, fixed chrome, bottom anchor, drag persistence message and keyboard reset');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
