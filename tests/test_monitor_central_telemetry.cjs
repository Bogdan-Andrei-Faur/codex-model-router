// Separate consent, live sync state and in-app deletion confirmation in the shared web view.
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
  const channel=process.env.ROUTER_TEST_BROWSER==='chromium'?undefined:process.env.ROUTER_TEST_BROWSER||(process.platform==='win32'?'msedge':'chrome');
  const browser=await chromium.launch({...channel?{channel}:{},headless:true});
  try{
    const page=await browser.newPage({viewport:{width:900,height:900}}),errors=[];
    page.on('pageerror',e=>errors.push(String(e)));
    await page.addInitScript(()=>{window.nativeMessages=[];window.webkit={messageHandlers:{monitor:{postMessage:m=>window.nativeMessages.push(m)}}};});
    await page.route('**/codex.png',r=>r.fulfill({path:path.resolve(__dirname,'../assets/brand/router-256.png')}));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
    await page.evaluate(()=>{window.receive({ui:{mode:'Expanded',reduced:true},centralTelemetry:{enabled:false,status:'disabled'}});showTab('settings');selectSettingsSection('data');});
    const settings=page.locator('#settings');
    const last=()=>page.evaluate(()=>window.nativeMessages.at(-1));
    await settings.getByRole('switch',{name:'Compartir métricas',exact:true}).click();
    assert.deepEqual(await last(),{action:'config',key:'central_enabled',value:true});
    assert.equal(await settings.getByRole('switch',{name:/^Compartir (mensajes|diagnóstico completo)$/}).count(),0);
    await page.evaluate(()=>window.receive({centralTelemetry:{enabled:true,prompts:false,raw_otlp:false,status:'retrying',pending:12,rejected:3,canDelete:true}}));
    assert.ok((await settings.innerText()).includes('12 pendientes'));
    for(const [status,label] of [['installation_capacity','Límite de esta instalación'],['total_capacity','Almacenamiento del servicio lleno'],['database_capacity','Base de datos llena'],['server_busy','Servicio ocupado']]){
      await page.evaluate(status=>window.receive({centralTelemetry:{enabled:true,status,pending:233,rejected:10,canDelete:true}}),status);
      assert.ok((await settings.innerText()).includes(label));
      assert.ok((await settings.innerText()).includes('233 pendientes'));
    }
    assert.equal(await settings.getByRole('switch',{name:'Compartir mensajes',exact:true}).getAttribute('aria-checked'),'false');
    assert.equal(await settings.getByRole('switch',{name:'Compartir diagnóstico completo',exact:true}).getAttribute('aria-checked'),'false');
    assert.ok((await settings.innerText()).includes('sin filtrar ni anonimizar'));
    assert.ok((await settings.innerText()).includes('sin borrado automático'));
    assert.ok((await settings.innerText()).includes('No se envía el historial anterior'));
    await settings.getByRole('switch',{name:'Compartir mensajes',exact:true}).click();
    assert.deepEqual(await last(),{action:'config',key:'central_prompts',value:true});
    await settings.getByRole('switch',{name:'Compartir diagnóstico completo',exact:true}).click();
    assert.deepEqual(await last(),{action:'config',key:'central_raw_otlp',value:true});
    await settings.getByRole('button',{name:/^Eliminar mis datos enviados/}).click();
    assert.notEqual((await last()).key,'central_delete');
    await settings.getByRole('button',{name:/^Cancelar eliminación/}).click();
    assert.equal(await settings.getByRole('button',{name:/^Confirmar eliminación/}).count(),0);
    await settings.getByRole('button',{name:/^Eliminar mis datos enviados/}).click();
    await settings.getByRole('button',{name:/^Confirmar eliminación/}).click();
    assert.deepEqual(await last(),{action:'config',key:'central_delete',value:true});
    await page.evaluate(()=>window.receive({centralTelemetry:{enabled:false,status:'retrying',delete_pending:true,pending:0}}));
    assert.ok((await settings.innerText()).includes('Eliminación pendiente de conexión'));
    await page.evaluate(()=>window.receive({readOnly:true,centralTelemetry:{enabled:true,prompts:false,raw_otlp:false,status:'synced'}}));
    assert.equal(await settings.getByRole('switch',{name:'Compartir métricas',exact:true}).isDisabled(),true);
    assert.equal(await settings.getByRole('switch',{name:'Compartir mensajes',exact:true}).isDisabled(),true);
    assert.deepEqual(errors,[]);
    console.log('PASS: default opt-out, separate permissions, sync-only refresh, in-app delete confirmation and read-only Settings');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
