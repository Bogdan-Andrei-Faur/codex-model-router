// Shared settings on the real web surface: progress-only updates and truthful install gates.
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
  const channel=process.env.ROUTER_TEST_BROWSER==='chromium'?undefined:process.env.ROUTER_TEST_BROWSER||(process.platform==='win32'?'msedge':'chrome');
  const browser=await chromium.launch({...channel?{channel}:{},headless:true});
  try{
    const page=await browser.newPage({viewport:{width:432,height:900}}),errors=[];
    page.on('pageerror',e=>errors.push(String(e)));
    await page.addInitScript(()=>{window.nativeMessages=[];window.webkit={messageHandlers:{monitor:{postMessage:m=>window.nativeMessages.push(m)}}};});
    await page.route('**/codex.png',r=>r.fulfill({path:path.resolve(__dirname,'../assets/brand/router-256.png')}));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
    await page.evaluate(()=>{window.receive({productVersion:'0.8.1',ui:{mode:'Expanded',reduced:true},updates:{status:'idle',installedVersion:'0.8.1'}});showTab('settings');});
    const settings=page.locator('#settings');
    assert.ok((await settings.innerText()).includes('Versión instalada · v0.8.1'));
    await settings.getByRole('button',{name:'Comprobar ahora',exact:true}).click();
    assert.deepEqual(await page.evaluate(()=>window.nativeMessages.filter(m=>m.action==='update').at(-1)),{action:'update',value:'check'});
    await page.evaluate(()=>window.receive({updates:{status:'available',installedVersion:'0.8.1',latestVersion:'0.9.0',canDownload:true}}));
    await settings.getByRole('button',{name:'Descargar versión 0.9.0',exact:true}).click();
    assert.equal(await page.evaluate(()=>window.nativeMessages.at(-1).value),'download');
    await page.evaluate(()=>window.receive({updates:{status:'downloading',installedVersion:'0.8.1',latestVersion:'0.9.0',progress:42}}));
    assert.equal(await settings.getByRole('progressbar').getAttribute('value'),'42');
    assert.equal(await settings.getByRole('button',{name:'Comprobar ahora',exact:true}).isDisabled(),true);
    await settings.getByRole('button',{name:'Cancelar',exact:true}).click();
    assert.equal(await page.evaluate(()=>window.nativeMessages.at(-1).value),'cancel');
    await page.evaluate(()=>window.receive({updates:{status:'downloaded',installedVersion:'0.8.1',latestVersion:'0.9.0',progress:100,canInstall:false}}));
    assert.ok((await settings.innerText()).includes('La instalación desde la aplicación aún no está disponible'));
    assert.equal(await settings.getByRole('button',{name:/^Instalar/}).count(),0);
    await page.evaluate(()=>window.receive({updates:{status:'error',installedVersion:'0.8.1',error:'release_unavailable'}}));
    assert.ok((await settings.innerText()).includes('No hay una entrega pública accesible'));
    assert.ok(!(await settings.innerText()).includes('No hay una versión estable más reciente'));
    await page.evaluate(()=>window.receive({preview:true,updates:{status:'idle',installedVersion:'0.8.1'}}));
    assert.equal(await settings.getByRole('button',{name:'Comprobar ahora',exact:true}).isDisabled(),true);
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({pass:true,shared_update_controls:true,progress_only_refresh:true,native_installation:'pending'}));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
