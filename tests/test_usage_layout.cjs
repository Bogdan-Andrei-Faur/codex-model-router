// Real shared surface, synthetic telemetry: character identity, metrics and lifecycle.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
  const channel=process.env.ROUTER_TEST_BROWSER==='chromium'?undefined:process.env.ROUTER_TEST_BROWSER||'chrome';
  const browser=await chromium.launch({...channel?{channel}:{},headless:true});
  try{
    for(const width of [320,390,432,600])for(const deviceScaleFactor of [1,1.25,1.5,2]){
      const page=await browser.newPage({viewport:{width,height:850},deviceScaleFactor}),errors=[];
      page.on('pageerror',e=>errors.push(String(e)));await page.clock.install({time:new Date('2026-10-08T08:00:00Z')});
      await page.route('**/codex.png',r=>r.fulfill({path:path.resolve(__dirname,'../assets/codex-official.png')}));
      await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
      // Expiry is driven by explicit advances, never by host load during assertions.
      await page.clock.pauseAt(new Date('2026-10-08T10:00:00Z'));
      await page.evaluate(()=>window.receive({connections:1,ui:{mode:'Compact',reduced:true},
        threads:Object.fromEntries(Array.from({length:7},(_,i)=>['a'+i,{name:'Agente '+i,status:'active',model:'gpt-6.1-sol',effort:'high',context_window:{used_percent:37,used_tokens:37000,capacity_tokens:100000}}])),
        accountUsage:{valid_until:Date.now()/1000+10,windows:[{duration_minutes:300,remaining_percent:3},{duration_minutes:10080,remaining_percent:76}]}}));
      await page.clock.fastForward(500);
      assert.equal(await page.locator('#quota .quota-number').innerText(),'76%');
      assert.match(await page.locator('#quota').getAttribute('aria-label'),/semanal restante: 76 %/);
      assert.equal(await page.locator('.usage-ring,#count').count(),0,'Old rings and count must not return');
      const boxes=await page.locator('#agents,#quota,.divider').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,scroll:n.scrollWidth,width:n.clientWidth,center:r.y+r.height/2};}));
      assert.ok(boxes[0].scroll<=boxes[0].width,'Characters overflow crew');
      assert.ok(boxes[0].right<=boxes[1].left&&boxes[1].right<=boxes[2].left,'Controls overlap');
      assert.ok(boxes.every(b=>Math.abs(b.center-boxes[0].center)<.1),'Compact components must align');
      const visible=await page.locator('#agents .avatar').count();
      assert.ok(visible>=3,'Compact mode should show a crew, even on a narrow display');
      assert.equal(await page.locator('#agents .overflow').innerText(),'+'+(7-visible));
      const avatar=page.locator('#agents .avatar').first();
      assert.match(await avatar.getAttribute('aria-label'),/Contexto usado: 37 %/);
      assert.equal(await avatar.locator('.character-context span').evaluate(n=>n.style.width),'37%');
      const identity=await avatar.getAttribute('data-companion');
      await page.locator('#quota').click();assert.match(await page.locator('#peek').innerText(),/semanal/);
      assert.equal(await page.locator('#peek .quota-card-number').innerText(),'76%');
      assert.equal(await page.locator('#peek .quota-meter[aria-valuenow="3"]').count(),1,'Short quota must retain its own value');
      assert.equal(await page.locator('#peek .quota-meter[aria-valuenow="76"]').count(),1);
      assert.ok(await page.locator('#peek').evaluate(n=>n.scrollHeight<=n.clientHeight),'Quota details should fit without scrolling when viewport height is sufficient');
      await page.clock.fastForward(12000);assert.equal(await page.locator('#quota .quota-number').innerText(),'—','Quota expiry must not require a new snapshot');
      await page.evaluate(()=>{
        const r=document.querySelector('#quota').getBoundingClientRect();
        window.quotaPointerFixture={x:r.x+r.width/2,y:r.y+r.height/2};
        window.monitorPointer(window.quotaPointerFixture);
      });
      await page.keyboard.press('Escape');assert.equal(await page.locator('#peek').isVisible(),false,JSON.stringify(await page.evaluate(()=>({width:innerWidth,dpi:devicePixelRatio,focus:document.activeElement.id,mode:state.ui.mode,peekDismissed,quotaOpen,peekId,peekTimer,body:document.body.className}))));
      // Layout updates can replay enter events without any physical movement.
      await page.evaluate(()=>{
        document.querySelector('#compact').dispatchEvent(new MouseEvent('mouseenter'));
        document.querySelector('#quota').dispatchEvent(new MouseEvent('mouseenter'));
      });
      assert.equal(await page.locator('#peek').isVisible(),false,'Stationary enter events must not undo Escape dismissal');
      await page.evaluate(()=>{window.monitorPointer(null);window.monitorPointer(window.quotaPointerFixture);});
      assert.equal(await page.locator('#peek').isVisible(),false,'Native hit-target replay at the same coordinates must preserve dismissal');
      await page.evaluate(()=>window.monitorPointer({...window.quotaPointerFixture,x:window.quotaPointerFixture.x-1}));
      assert.equal(await page.locator('#peek').isVisible(),true,'A new pointer movement must restore quota hover');
      await page.keyboard.press('Escape');
      for(const percent of [0,100,null]){
        await page.evaluate(percent=>window.receive({threads:{a0:{name:'Tarea segura',status:'active',model:'gpt-6-astra',effort:'ultra',agent_category:'audit',context_window:percent===null?{}:{used_percent:percent,used_tokens:percent*1000,capacity_tokens:100000}}}}),percent);
        await page.clock.fastForward(500);
        assert.equal(await avatar.getAttribute('data-companion'),identity,'Model/effort/category changes must preserve character');
        assert.equal(await avatar.locator('.character-context span').evaluate(n=>n.style.width),(percent??0)+'%');
        assert.equal(await avatar.locator('.character-context').evaluate(n=>n.classList.contains('unavailable')),percent===null);
      }
      await page.evaluate(()=>window.receive({threads:{a0:{name:'Tarea segura',status:'active',model:'gpt-6.1-sol',context_window:{used_percent:37,used_tokens:37000,capacity_tokens:100000}}},accountUsage:{valid_until:Date.now()/1000+60,windows:[{duration_minutes:10080,remaining_percent:76}]}}));
      await avatar.click();assert.match(await page.locator('#peek').innerText(),/37 %/);
      assert.doesNotMatch(await page.locator('#peek').innerText(),/Trabajando|Contexto usado:/);
      assert.match(await page.locator('#peek .context-meter').getAttribute('aria-label'),/37000 \/ 100000/);
      const peekMeter=await page.locator('#peek .context-meter').evaluate(n=>({height:getComputedStyle(n).height,color:getComputedStyle(n.firstElementChild).backgroundColor}));
      const top=await page.locator('#surface').boundingBox();assert.equal(top.y,0);
      await page.keyboard.press('Escape');await page.locator('#expand').click();
      assert.equal(await page.locator('#activity .context-meter[aria-valuenow="37"]').count(),1);
      assert.deepEqual(await page.locator('#activity .context-meter').evaluate(n=>({height:getComputedStyle(n).height,color:getComputedStyle(n.firstElementChild).backgroundColor})),peekMeter,'Context meter must match between peek and overview');
      assert.match(await page.locator('.overview-quota').innerText(),/76 % libre/);
      await page.locator('.overview-quota').click();
      assert.match(await page.locator('.account-quota').innerText(),/76 % disponible/);
      await page.clock.fastForward(62000);assert.match(await page.locator('.overview-quota').innerText(),/Sin datos/);assert.match(await page.locator('.account-quota').innerText(),/Sin datos actuales/);
      await page.keyboard.press('Escape');
      await page.evaluate(()=>window.receive({threads:{a0:{name:'Tarea segura',status:'completed',context_window:{used_percent:90,used_tokens:90000,capacity_tokens:100000},context_compaction:{state:'compacting'}}},ui:{reduced:false}}));
      assert.equal(await avatar.getAttribute('data-state'),'compacting');assert.match(await avatar.getAttribute('aria-label'),/Compactando contexto/);
      assert.equal(await avatar.locator('.character-context').evaluate(n=>getComputedStyle(n).visibility),'hidden');
      const motion=await avatar.locator('.character-body').evaluate(n=>{
        const animation=n.getAnimations()[0];animation.currentTime=0;const first=getComputedStyle(n).transform;animation.currentTime=800;
        window.testCharacter=n;return {name:getComputedStyle(n).animationName,moves:first!==getComputedStyle(n).transform};
      });assert.equal(motion.name,'companion-pack');assert.ok(motion.moves);
      await page.evaluate(()=>window.receive({}));assert.ok(await avatar.locator('.character-body').evaluate(n=>n===window.testCharacter),'Heartbeat replaced the animation DOM');
      await page.evaluate(()=>window.receive({ui:{reduced:true}}));assert.equal(await avatar.locator('.character-body').evaluate(n=>getComputedStyle(n).animationName),'none');
      await page.locator('#expand').click();assert.equal(await page.locator('.companion-headline').innerText(),'Poniendo orden.');
      assert.equal(await page.locator('#activity .context-meter').getAttribute('aria-valuenow'),null,'Compaction must not show stale percent');
      await page.evaluate(()=>window.receive({threads:{a0:{name:'Tarea segura',status:'active',context_compaction:{state:'awaiting_usage'}}}}));
      assert.match(await page.locator('.hero-character').getAttribute('aria-label'),/esperando nueva medición/);assert.equal(await page.locator('.companion-hero [data-state="compacting"]').count(),0);
      await page.evaluate(()=>window.receive({threads:{a0:{name:'Tarea segura',status:'waiting'}}}));assert.equal(await page.locator('.companion-headline').innerText(),'Te necesita.');
      await page.evaluate(()=>window.receive({threads:{a0:{name:'Tarea segura',status:'completed'}}}));assert.equal(await page.locator('.companion-headline').innerText(),'Turno terminado.');
      await page.evaluate(()=>window.receive({connections:0}));assert.equal(await page.locator('.companion-headline').innerText(),'Sin noticias.');assert.equal(await page.locator('#quota .quota-number').innerText(),'—');
      assert.deepEqual(errors,[]);await page.close();
    }
    console.log('PASS: notch characters, stable identities, quota expiry, unknown/zero/full context, compaction motion and reduced motion at 320–600px × 1–2 DPI');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
