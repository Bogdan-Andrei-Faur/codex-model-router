// Exercise the real shared UI with the Windows message channel (no WebKit shim).
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
      window.chrome=window.chrome||{};
      window.chrome.webview={postMessage:m=>{
        window.nativeMessages.push(m);
        if(m.action==='mode')queueMicrotask(()=>window.receiveUI({mode:m.value,modeRequest:m.request}));
      }};
    });
    await page.route('**/codex.png',r=>r.fulfill({path:path.resolve(__dirname,'../assets/codex-official.png')}));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
    assert.ok(await page.evaluate(()=>window.nativeMessages.some(m=>m.action==='ready')));
    await page.evaluate(()=>window.receive({platform:'windows',secretStorage:'Windows DPAPI',historyLoaded:false,
      ui:{mode:'Compact',acknowledgesMode:true,lazyHistory:true},connections:1,
      threads:{live:{name:'Windows fixture',status:'active',model:'gpt-6.1-sol',effort:'high'},idle:{status:'idle'}},
      config:{enabled:true,jev:{connection:'typesafe'}}}));
    await page.locator('#expand').click();
    assert.equal(await page.evaluate(()=>state.ui.mode),'Expanded');
    assert.equal(await page.locator('.task-row').count(),1);
    assert.ok((await page.locator('#activity').innerText()).includes('Sol 6.1'));
    await page.locator('[data-tab="history"]').click();
    assert.equal(await page.evaluate(()=>window.nativeMessages.filter(m=>m.action==='history').at(-1).value),true);
    await page.evaluate(()=>window.receive({history:[]}));
    await page.locator('[data-tab="settings"]').click();
    assert.ok((await page.locator('#settings').innerText()).includes('Windows DPAPI'));
    const connect=page.locator('[data-connection-action="install"]');
    await connect.click();
    assert.equal(await connect.getAttribute('aria-busy'),'true');
    assert.ok(await connect.isDisabled());
    assert.ok((await connect.innerText()).includes('Conectando…'));
    assert.equal(await page.locator('[data-connection-action="doctor"]').isDisabled(),true);
    assert.equal(await connect.locator('.action-spinner').isVisible(),true);
    await page.evaluate(()=>window.receive({ui:{connectionProgress:true}}));
    await page.evaluate(()=>window.monitorFeedback('Una operación sigue en curso.'));
    assert.equal(await connect.isDisabled(),true);
    await page.evaluate(()=>window.monitorConnectionState({pending:false}));
    await page.evaluate(()=>window.monitorFeedback('Conexión instalada. Reinicia Desktop al terminar tus tareas.'));
    assert.equal(await connect.isDisabled(),false);
    assert.equal(await connect.getAttribute('aria-busy'),'false');
    assert.ok((await connect.innerText()).includes('Conectar al inicio habitual'));
    assert.equal(await connect.locator('.action-spinner').isVisible(),false);
    assert.ok(await connect.locator('.action-affordance').isVisible());
    await page.evaluate(()=>window.receive({connections:0,desktopRestartPending:true,restartRequired:true}));
    assert.ok((await page.locator('#connection').innerText()).includes('Conexión preparada'));
    assert.ok((await page.locator('#product-version').innerText()).includes('reinicio pendiente'));
    await page.locator('#pause').click();
    assert.ok(await page.evaluate(()=>window.nativeMessages.some(m=>m.action==='config'&&m.key==='enabled'&&m.value===false)));
    await page.locator('#collapse').click();
    assert.equal(await page.evaluate(()=>state.ui.mode),'Compact');
    assert.ok(await page.evaluate(()=>window.nativeMessages.some(m=>m.action==='bounds'&&m.height>0)));
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({pass:true,windows_message_channel:true,native_windows_execution:false}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
