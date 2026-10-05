// Shared WebKit-surface layout checks in Chromium; native platform shells remain separate.
const { chromium } = require('playwright');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const channel = process.env.ROUTER_TEST_BROWSER === 'chromium' ? undefined :
    process.env.ROUTER_TEST_BROWSER || (process.platform === 'win32' ? 'msedge' : 'chrome');
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
    for (const [mismatch,unknown,restartRequired,label] of [[false,false,false,'v0.3.1'],[false,true,false,'v0.3.1 · puente sin verificar'],[true,true,false,'v0.3.1 · router anterior'],[false,false,true,'v0.3.1 · reinicio pendiente']]) {
      await page.evaluate(([bridgeBuildMismatch,bridgeBuildUnknown,restartRequired])=>window.receive({productVersion:'0.3.1',bridgeVersions:['0.3.1'],bridgeBuildMismatch,bridgeBuildUnknown,restartRequired}),[mismatch,unknown,restartRequired]);
      assert.equal(await page.locator('#product-version').innerText(),label);
    }
    await page.evaluate(()=>window.receive({bridgeBuildMismatch:false,bridgeBuildUnknown:false,restartRequired:false}));
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
    assert.equal(await page.locator('.task-row').count(),1,'Inactive task must not fill Agentes');
    assert.equal(await page.locator('.featured-title').count(),0,'Featured task removed by approved design');
    await page.locator('.task-row').filter({hasText:'Agente anterior'}).click();
    assert.ok((await page.locator('.agent-detail').innerText()).includes('Agente anterior'));
    activityFixture.newer.updated=30;
    activityFixture.older.phase_pipeline[0].label='Validación terminada';
    activityFixture.older.phase_pipeline[0].state='completed';
    await page.evaluate(threads=>window.receive({threads}),activityFixture);
    assert.ok((await page.locator('#activity .pipeline').innerText()).includes('Validación terminada'),'Selected detail stopped refreshing');
    await page.clock.fastForward(65000);
    assert.ok((await page.locator('.agent-detail').innerText()).includes('Agente anterior'),'Selected detail expired unexpectedly');
    await page.locator('.task-row').focus();await page.keyboard.press('Enter');
    assert.equal(await page.locator('.agent-detail').count(),0,'Keyboard cannot close detail');
    await page.locator('.task-row').click();
    await page.evaluate(threads=>window.receive({threads}),{newer:activityFixture.newer});
    assert.equal(await page.locator('.task-row').count(),0);
    assert.equal(await page.locator('.agent-detail').count(),0,'Missing task left stale detail');
    console.log('PASS: active-only agents, no featured task, persistent selected detail, live pipeline and keyboard');
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
    await page.locator('#history-search').fill('');
    await page.evaluate(()=>window.receive({history:[
      {event:'decision_created',decision_id:'error-demo',thread:'demo',time:1,title:'Diagnóstico sintético'},
      {event:'native_turn_error',decision_id:'error-demo',time:2,error_type:'responseStreamDisconnected',will_retry:true},
      {event:'decision_completed',decision_id:'error-demo',time:3,status:'failed',error_type:'httpConnectionFailed',error_http_status:503}
    ]}));
    await page.locator('.history-row').click();
    const diagnosticText=await page.locator('.history-detail').innerText();
    assert.ok(diagnosticText.includes('httpConnectionFailed · HTTP 503'));
    assert.ok(diagnosticText.includes('REINTENTOS NATIVOS'));
    assert.equal(await page.locator('.history-detail').evaluate(el=>el.scrollWidth<=el.clientWidth),true,'Diagnostics overflow detail');
    console.log('PASS: native error codes and separate retry count in history details');
    await page.evaluate(()=>window.receive({config:{enabled:true,inference_telemetry:true},telemetry:{enabled:true,requests:20,invalid_requests:3,invalid_size:2,invalid_wire_size:1,invalid_decoded_size:1,invalid_length:1,size_wire_512k:10,size_wire_1m:8,size_wire_16m:1,size_decoded_512k:10,size_decoded_4m:8,size_decoded_over16m:1}}));
    await page.locator('[data-tab="statistics"]').click();
    await page.locator('.consumption-diagnostics>summary').click();
    const telemetryText=await page.locator('#statistics').innerText();
    assert.ok(telemetryText.includes('recibido 1 · descomprimido 1'));
    assert.ok(telemetryText.includes('La captura está incompleta'));
    assert.ok(telemetryText.includes('Longitud o formato HTTP no admitido: 1'));
    assert.ok(telemetryText.includes('Tamaño recibido · ≤512 KiB: 10'));
    assert.ok(telemetryText.includes('Tamaño descomprimido · ≤512 KiB: 10'));
    assert.equal(await page.locator('#statistics').evaluate(el=>el.scrollWidth<=el.clientWidth),true,'Telemetry size diagnostics overflow');
    console.log('PASS: telemetry size bins and distinct receiver rejections');
    for (const enabled of [false,true]) {
      await page.evaluate(value=>window.receive({config:{enabled:true,phase_routing:value,prompt_logging:value}}),enabled);
      await page.locator('[data-tab="settings"]').click();
      const settingsText=await page.locator('#settings').innerText();
      assert.ok(settingsText.includes(enabled?'Cambios por fases habilitados':'cambios por fases están desactivados'));
      assert.ok(settingsText.includes(enabled?'Desactivar cambios automáticos por fases':'Activar cambios automáticos por fases'));
      assert.ok(settingsText.includes(enabled?'Desactivar captura de prompts':'Activar captura de prompts'));
      assert.equal(settingsText.includes('archivo local privado state/prompts.jsonl'),enabled);
    }
    console.log('PASS: settings reflect optional phase routing and private prompt capture');
    for (const deviceScaleFactor of [1,1.25,1.5,2]) {
      for (const viewport of [{width:390,height:640},{width:432,height:900}]) {
        const context=await browser.newContext({viewport,deviceScaleFactor});
        const dpiPage=await context.newPage();
        await dpiPage.addInitScript(()=>{
          window.nativeMessages=[];
          window.webkit={messageHandlers:{monitor:{postMessage:message=>window.nativeMessages.push(message)}}};
        });
        await dpiPage.route('**/codex.png',route=>route.fulfill({path:path.resolve(__dirname,'../assets/codex-official.png')}));
        await dpiPage.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
        await dpiPage.evaluate(height=>window.receive({ui:{mode:'Expanded',reduced:true,panelHeight:height}}),viewport.height);
        const metrics=await dpiPage.evaluate(()=>({
          ratio:window.devicePixelRatio,
          documentFits:document.documentElement.scrollWidth<=document.documentElement.clientWidth,
          bodyFits:document.body.scrollWidth<=document.body.clientWidth,
          surface:(()=>{const r=document.querySelector('#surface').getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};})()
        }));
        assert.equal(metrics.ratio,deviceScaleFactor,`Unexpected device scale factor: ${deviceScaleFactor}`);
        assert.ok(metrics.documentFits && metrics.bodyFits,`Horizontal overflow at ${viewport.width}x${viewport.height} @${deviceScaleFactor}x`);
        assert.ok(metrics.surface.left>=0 && metrics.surface.right<=viewport.width,
          `Surface escaped width at ${viewport.width}x${viewport.height} @${deviceScaleFactor}x`);
        assert.ok(metrics.surface.top>=0 && metrics.surface.bottom<=viewport.height,
          `Surface escaped height at ${viewport.width}x${viewport.height} @${deviceScaleFactor}x`);
        await context.close();
      }
    }
    console.log('PASS: 390/432 px layouts at 1x, 1.25x, 1.5x and 2x device scale');
    if(process.env.ROUTER_LAYOUT_SCREENSHOT)await page.screenshot({path:process.env.ROUTER_LAYOUT_SCREENSHOT});
    assert.deepEqual(errors,[]);
    console.log('PASS: responsive height, fixed chrome, bottom anchor, drag persistence message and keyboard reset');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
