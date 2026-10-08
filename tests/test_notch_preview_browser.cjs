// Exercise the actual read-only loopback adapter, including polling and lazy history.
const {chromium}=require('playwright'),{spawn}=require('node:child_process');
const fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
  const root=await fs.mkdtemp(path.join(os.tmpdir(),'router-notch-browser-'));
  await fs.mkdir(path.join(root,'state'));
  const fixture={threads:{a0:{name:'Pulir la interfaz',status:'active',model:'gpt-6.1-sol',effort:'high',context_window:{used_percent:58,used_tokens:58000,capacity_tokens:100000}},
    a1:{name:'Validar los cambios',status:'active',model:'gpt-6-luna',effort:'low',context_compaction:{state:'compacting'}},
    a2:{name:'Revisar la arquitectura',status:'active',model:'gpt-6-astra',effort:'xhigh',context_window:{used_percent:81,used_tokens:81000,capacity_tokens:100000}}},
    account_usage:{valid_until:Date.now()/1000+3600,windows:[{duration_minutes:10080,remaining_percent:85}]}};
  await fs.writeFile(path.join(root,'preview.json'),JSON.stringify(fixture));
  await fs.writeFile(path.join(root,'state/history.jsonl'),JSON.stringify({event:'decision_created',decision_id:'d',thread:'a0',title:'Fixture segura',model:'gpt-6.1-sol',time:1})+'\n');
  const server=spawn(process.env.ROUTER_TEST_PYTHON||(process.platform==='win32'?'python':'python3'),[path.resolve(__dirname,'../tools/preview_monitor.py'),'--fixture-root',root],{stdio:['ignore','pipe','pipe']});
  const channel=process.env.ROUTER_TEST_BROWSER==='chromium'?undefined:process.env.ROUTER_TEST_BROWSER||'chrome';
  let browser;
  try{
    const url=await new Promise((resolve,reject)=>{
      let output='';const timeout=setTimeout(()=>reject(Error('Preview server did not start')),15000);
      server.stdout.on('data',chunk=>{output+=chunk;const match=output.match(/http:\/\/127\.0\.0\.1:[0-9]+\/[^\s]+\/index.html/);if(match){clearTimeout(timeout);resolve(match[0]);}});
      server.once('exit',()=>{clearTimeout(timeout);reject(Error('Preview server exited'));});
      server.once('error',()=>{clearTimeout(timeout);reject(Error('Preview Python executable unavailable'));});
    });
    browser=await chromium.launch({...channel?{channel}:{},headless:true});
    const page=await browser.newPage({viewport:{width:900,height:950}}),errors=[],methods=[];
    page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>methods.push(r.method()));
    await page.goto(url);await page.waitForFunction(()=>document.querySelector('.companion-headline')?.textContent==='En ello.');
    assert.match(await page.locator('#connection').innerText(),/simulados/);
    await page.waitForFunction(()=>[...document.fonts].some(face=>face.family==='Router Nunito'&&face.status==='loaded'));
    assert.match(await page.locator('.companion-headline').evaluate(n=>getComputedStyle(n).fontFamily),/Router Nunito/);
    assert.equal(await page.locator('footer,#pause').count(),0);
    assert.equal(await page.locator('.history-row').count(),0,'Initial activity eagerly rendered history');
    // The default island fits its contents instead of filling the desktop.
    await page.waitForFunction(()=>{const n=document.querySelector('#surface');return !n.getAnimations().some(a=>a.playState==='running') && Math.abs(n.getBoundingClientRect().height-parseFloat(n.style.getPropertyValue('--overview-height')))<.1;});
    const overview=await page.locator('#surface').boundingBox();
    assert.ok(overview.height<420 && overview.height>200,'Overview is still a full-height panel');
    assert.equal(await page.locator('#pages').evaluate(n=>n.scrollHeight<=n.clientHeight+1),true,'Default overview requires scrolling');
    const meters=await page.locator('.hero-metrics [role=progressbar]').evaluateAll(nodes=>nodes.map(n=>n.getBoundingClientRect().y));
    assert.ok(Math.abs(meters[0]-meters[1])<1,'Metric tracks are not aligned');
    const columns=await page.locator('.home-primary,.home-others').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {x:r.x,right:r.right,y:r.y};}));
    assert.ok(columns[0].right<=columns[1].x&&Math.abs(columns[0].y-columns[1].y)<1,'Home must place the principal left and remaining agents right');
    assert.equal(await page.locator('.task-row').count(),2,'Principal must not be duplicated in the crew');
    await page.locator('.task-row').first().focus();await page.keyboard.press('Enter');
    assert.equal(await page.locator('.companion-headline').innerText(),'Poniendo orden.');
    assert.equal(await page.locator('.hero-character').evaluate(n=>n===document.activeElement),true,'Selection lost keyboard focus');
    assert.equal(await page.locator('.agent-workspace-detail').count(),0,'Selecting a character must not open the inspector');
    await page.locator('.task-row').first().click();await page.locator('.detail-toggle').click();
    await page.waitForFunction(()=>{const n=document.querySelector('#surface');return !n.getAnimations().some(a=>a.playState==='running') && Math.abs(n.getBoundingClientRect().height-parseFloat(n.style.getPropertyValue('--overview-height')))<.1;});
    const agentColumns=await page.locator('.agents-sidebar,.agent-workspace-detail').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {x:r.x,right:r.right,y:r.y};}));
    assert.ok(agentColumns[0].right<agentColumns[1].x&&Math.abs(agentColumns[0].y-agentColumns[1].y)<1,'Agents must place identity/selector left and routing right');
    assert.ok((await page.locator('#surface').boundingBox()).height<600,'Agents should fit its horizontal contents');
    assert.equal(await page.locator('.agent-workspace-detail').count(),1);
    await page.locator('[data-tab="home"]').click();
    await page.waitForFunction(expected=>{const n=document.querySelector('#surface');return !n.getAnimations().some(a=>a.playState==='running') && Math.abs(n.getBoundingClientRect().height-expected)<1;},overview.height);
    const closed=await page.locator('#surface').boundingBox();
    assert.ok(Math.abs(closed.height-overview.height)<1,`Closing details did not shrink the island: ${overview.height} -> ${closed.height}`);
    await page.setViewportSize({width:340,height:340});
    await page.waitForFunction(()=>document.querySelector('#surface').getBoundingClientRect().height<=324.5);
    assert.equal(await page.locator('#pages').evaluate(n=>n.scrollHeight>n.clientHeight),true,'Short screen does not scroll the overview');
    assert.equal(await page.locator('nav').isVisible(),true);
    await page.setViewportSize({width:900,height:950});
    await page.waitForFunction(()=>{const n=document.querySelector('#surface');return !n.getAnimations().some(a=>a.playState==='running') && Math.abs(n.getBoundingClientRect().height-parseFloat(n.style.getPropertyValue('--overview-height')))<.1;});
    const output=process.env.ROUTER_NOTCH_SCREENSHOTS;
    if(output){await fs.mkdir(output,{recursive:true});await page.locator('#surface').screenshot({path:path.join(output,'notch-expanded.png')});}
    await page.keyboard.press('Escape');
    await page.waitForFunction(()=>document.body.classList.contains('compact'));
    assert.equal(await page.locator('#quota .quota-number').innerText(),'85%');
    assert.equal(await page.locator('#agents .avatar').count(),3,'Compact crew hides active companions');
    await page.mouse.move(10,900);await page.keyboard.press('Escape');
    await page.waitForFunction(()=>document.querySelector('#peek').hidden);
    if(output)await page.locator('#surface').screenshot({path:path.join(output,'notch-compact.png')});
    await page.locator('#agents .avatar').nth(1).hover();
    await page.waitForFunction(()=>document.querySelector('#peek').textContent.includes('Validar los cambios'));
    assert.match(await page.locator('#peek').innerText(),/Validar los cambios/);
    await page.locator('#quota').hover();
    await page.waitForFunction(()=>document.querySelector('#peek .quota-card-number')?.textContent==='85%');
    assert.equal(await page.locator('#peek .quota-card-number').innerText(),'85%');
    if(output)await page.locator('#surface').screenshot({path:path.join(output,'notch-quota.png')});
    await page.mouse.move(10,900);await page.waitForFunction(()=>document.querySelector('#peek').hidden);
    await page.waitForTimeout(2300);
    assert.equal(await page.locator('#expanded').isVisible(),false,'Poll overwrote locally selected compact mode');
    await page.locator('#expand').click();
    await page.locator('[data-tab="history"]').click();await page.waitForFunction(()=>document.querySelectorAll('.history-row').length===1);
    await page.locator('.history-row').click();assert.equal(await page.locator('.choice:not(:disabled)').count(),0,'Preview permits rating or task mode changes');
    await page.locator('[data-tab="settings"]').click();
    // History is wider: keep the pointer inside while Settings narrows the island,
    // otherwise its genuine pointer-exit timer closes it before Playwright moves.
    await page.mouse.move(450,110);
    assert.equal(await page.locator('#settings #pause').isEnabled(),false);
    await page.locator('[data-tab="home"]').click();
    fixture.threads.a0.context_compaction={state:'compacting'};await fs.writeFile(path.join(root,'preview.json'),JSON.stringify(fixture));
    await page.waitForFunction(()=>document.querySelector('.companion-headline')?.textContent==='Poniendo orden.');
    assert.equal(await page.locator('#activity .context-meter').getAttribute('aria-valuenow'),null);
    fixture.threads={a0:{name:'Esperando una decisión',status:'waiting'}};await fs.writeFile(path.join(root,'preview.json'),JSON.stringify(fixture));
    await page.waitForFunction(()=>document.querySelector('.companion-headline')?.textContent==='Te necesita.');
    await page.keyboard.press('Escape');
    await page.waitForFunction(()=>document.querySelectorAll('#agents .avatar[data-state=waiting]').length===1);
    assert.ok(methods.every(m=>m==='GET'),'Preview sent a mutation request');assert.deepEqual(errors,[]);
    console.log('PASS: content-sized overview, horizontal crew, aligned metrics, keyboard selection, inspector expansion, short viewport, actual preview adapter, polling, mode persistence, lazy history, read-only controls and compaction refresh');
  }finally{
    if(browser)await browser.close();server.kill('SIGINT');
    if(server.pid && server.exitCode===null)await new Promise(resolve=>server.once('exit',resolve));
    await fs.rm(root,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
