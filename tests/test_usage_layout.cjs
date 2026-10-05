// Gauge geometry, updates, overflow and accessibility on the shared Mac/Linux UI.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
  const channel=process.env.ROUTER_TEST_BROWSER==='chromium'?undefined:process.env.ROUTER_TEST_BROWSER || 'chrome';
  const browser=await chromium.launch({channel,headless:true});
  try {
    for(const width of [390,432])for(const deviceScaleFactor of [1,1.25,1.5,2]) {
      const page=await browser.newPage({viewport:{width,height:700},deviceScaleFactor});
      const errors=[];page.on('pageerror',e=>errors.push(String(e)));
      await page.clock.install();
      await page.route('**/codex.png',r=>r.fulfill({path:path.resolve(__dirname,'../assets/codex-official.png')}));
      await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
      await page.evaluate(()=>{
        const threads=Object.fromEntries(Array.from({length:7},(_,i)=>['a'+i,{name:'Agente '+i,model:'gpt-6.1-sol',effort:'high',status:'active',agent_category:'interface',updated:1,
          context_window:{used_percent:37,used_tokens:37000,capacity_tokens:100000}}]));
        window.receive({threads,connections:1,accountUsage:{remaining_percent:76,valid_until:Date.now()/1000+10,
          windows:[{limit_id:'codex',window:'primary',duration_minutes:10080,remaining_percent:76}]},ui:{mode:'Compact',reduced:true}});
      });
      await page.clock.fastForward(500);
      assert.equal(await page.locator('#quota').innerText(),'76%');
      assert.match(await page.locator('#quota').getAttribute('aria-label'),/Cuota semanal restante: 76 %/);
      assert.equal(await page.locator('#count').count(),0,'Task count must not occupy the compact capsule');
      const centers=await page.locator('#agents,#quota,#compact .logo').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return r.y+r.height/2;}));
      assert.ok(centers.every(y=>Math.abs(y-centers[0])<.1),'Compact agents, quota and logo are not vertically aligned');
      const number=await page.locator('#quota .quota-number').evaluate(n=>{
        const ring=n.parentElement.getBoundingClientRect(),label=n.getBoundingClientRect();
        return {ringCenter:ring.x+ring.width/2,labelCenter:label.x+label.width/2,y:n.getAttribute('y')};
      });
      assert.ok(Math.abs(number.ringCenter-number.labelCenter)<.1,'Number is not horizontally centered on the quota circle');
      assert.ok(Number(number.y)>22,'Visible digits need a baseline below the circle center');
      const avatar=page.locator('#agents .avatar').first();
      assert.match(await avatar.getAttribute('aria-label'),/Contexto usado: 37 %/);
      const geometry=await avatar.evaluate(el=>{
        const face=el.querySelector('.face').getBoundingClientRect(),ring=el.querySelector('.context-ring').getBoundingClientRect(),circle=el.querySelector('.context-ring .usage-progress');
        return {faceX:face.x+face.width/2,ringX:ring.x+ring.width/2,faceY:face.y+face.height/2,ringY:ring.y+ring.height/2,
          progress:1-Number(circle.getAttribute('stroke-dashoffset'))/Number(circle.getAttribute('stroke-dasharray'))};
      });
      assert.ok(Math.abs(geometry.faceX-geometry.ringX)<.1 && Math.abs(geometry.faceY-geometry.ringY)<.1);
      assert.ok(Math.abs(geometry.progress-.37)<.00001);
      const boxes=await page.locator('#agents,#quota,.divider').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,scroll:n.scrollWidth,width:n.clientWidth};}));
      assert.ok(boxes[0].scroll<=boxes[0].width,'Agents overflow the reserved crew width');
      assert.ok(boxes[0].right<=boxes[1].left && boxes[1].right<=boxes[2].left,'Quota overlaps controls');
      const visible=await page.locator('#agents .avatar').count();
      assert.equal(await page.locator('#agents .overflow').innerText(),'+'+(7-visible));
      for(const font of ['sans-serif','serif','monospace','Lato Black','C059']) {
        await page.evaluate(font=>{
          document.getElementById('quota').style.fontFamily=font;
          window.receive({});
        },font);
        const offset=await page.locator('#quota .quota-number').evaluate(n=>{const bounds=n.getBBox();return bounds.x+bounds.width/2-22;});
        assert.ok(Math.abs(offset)<.1,`Glyph overhang shifted quota center for ${font}: ${offset}`);
      }
      await page.evaluate(()=>{document.getElementById('quota').style.fontFamily='';window.receive({});});
      await page.locator('#quota').click();
      assert.match(await page.locator('#peek').innerText(),/CUOTA DE LA CUENTA.*\n.*semanal/s);
      await page.clock.fastForward(12000);
      assert.equal(await page.locator('#quota').innerText(),'—','Expired quota stayed current without incoming snapshot');
      for(const percent of [0,100,null]) {
        await page.evaluate(percent=>window.receive({threads:{a0:{name:'Agente 0',status:'active',model:'gpt-6.1-sol',context_window:percent===null?{}:{used_percent:percent,used_tokens:percent*1000,capacity_tokens:100000}}},
          accountUsage:percent===null?{}:{remaining_percent:percent,valid_until:Date.now()/1000+60,windows:[{duration_minutes:10080,remaining_percent:percent}]}}),percent);
        await page.clock.fastForward(500);
        assert.equal(await page.locator('#quota').innerText(),percent===null?'—':percent+'%');

        const circle=page.locator('#agents .context-ring .usage-progress');
        assert.equal(await circle.count(),percent===null?0:1);
        if(percent===100)assert.equal(Number(await circle.getAttribute('stroke-dashoffset')),0);
        if(percent===0)assert.equal(await circle.getAttribute('visibility'),'hidden');
      }
      await page.evaluate(()=>window.receive({threads:{a0:{name:'Diseñar el monitor',agent_category:'interface',status:'active',model:'gpt-6.1-sol',effort:'high',context_window:{used_percent:37,used_tokens:37000,capacity_tokens:100000}}},accountUsage:{remaining_percent:76,valid_until:Date.now()/1000+60,windows:[{duration_minutes:10080,remaining_percent:76}]}}));
      await avatar.click();
      assert.match(await page.locator('#peek').innerText(),/37 %.*37000 \/ 100000/);
      await page.keyboard.press('Escape');
      if(width===432 && deviceScaleFactor===2 && process.env.ROUTER_USAGE_SCREENSHOT)await page.locator('#surface').screenshot({path:process.env.ROUTER_USAGE_SCREENSHOT});
      await page.locator('#expand').click();
      assert.equal(await page.locator('.task-row .context-ring').count(),1);
      assert.equal(await page.locator('#expanded .quota-ring').count(),0,'Quota circle is capsule-only');
      assert.match(await page.locator('.account-quota').innerText(),/76 % disponible/);
      assert.ok(await page.locator('header').evaluate(n=>n.scrollWidth<=n.clientWidth),'Header overlaps controls');
      if(width===432 && deviceScaleFactor===2 && process.env.ROUTER_USAGE_PANEL_SCREENSHOT)await page.locator('#surface').screenshot({path:process.env.ROUTER_USAGE_PANEL_SCREENSHOT});
      await page.clock.fastForward(62000);
      assert.match(await page.locator('.account-quota').innerText(),/Sin datos actuales/,'Panel quota did not expire');
      await page.locator('#collapse').click();
      await page.evaluate(()=>window.receive({threads:{a0:{name:'Diseñar el monitor',status:'active',model:'gpt-6.1-sol',effort:'high',agent_category:'interface',
        context_window:{used_percent:90,used_tokens:90000,capacity_tokens:100000},context_compaction:{state:'compacting'}}},
        accountUsage:{remaining_percent:76,valid_until:Date.now()/1000+60,windows:[{duration_minutes:10080,remaining_percent:76}]},ui:{mode:'Compact',reduced:false}}));
      await page.clock.fastForward(500);
      const compacting=page.locator('#agents .compacting-ring');
      assert.equal(await compacting.count(),1);
      assert.equal(await avatar.locator('.usage-progress').count(),0,'Compaction must not display a stale percentage');
      assert.match(await avatar.getAttribute('aria-label'),/Compactando contexto/);
      assert.equal(await avatar.locator('.orbit').evaluate(n=>getComputedStyle(n).display),'none','Compaction needs its own motion instead of the activity orbit');
      const motion=await compacting.evaluate(n=>{
        const animation=n.getAnimations()[0];
        const name=getComputedStyle(n).animationName;
        animation.currentTime=0;const first=getComputedStyle(n).transform;
        animation.currentTime=800;const second=getComputedStyle(n).transform;
        window.compactionTestRing=n;
        return {name,moves:first!==second};
      });
      assert.equal(motion.name,'context-compacting');assert.ok(motion.moves);
      await page.evaluate(()=>window.receive({}));
      assert.ok(await compacting.evaluate(n=>n===window.compactionTestRing),'Heartbeat restarted the compaction animation');
      if(width===432 && deviceScaleFactor===2 && process.env.ROUTER_COMPACTION_SCREENSHOT)await page.locator('#surface').screenshot({path:process.env.ROUTER_COMPACTION_SCREENSHOT});
      await page.evaluate(()=>window.receive({ui:{mode:'Compact',reduced:true}}));
      assert.equal(await compacting.evaluate(n=>getComputedStyle(n).animationName),'none');
      assert.match(await avatar.getAttribute('aria-label'),/Compactando contexto/,'Reduced motion must still identify compaction');
      await page.locator('#expand').click();
      assert.equal(await page.locator('.task-row .compacting-ring').count(),1,'Panel lost the compaction state');
      await page.evaluate(()=>window.receive({threads:{a0:{name:'Diseñar el monitor',status:'active',model:'gpt-6.1-sol',context_compaction:{state:'awaiting_usage'}}}}));
      assert.equal(await page.locator('.compacting-ring').count(),0,'Compaction animation stayed after completion');
      assert.match(await page.locator('.task-row').getAttribute('aria-label'),/esperando nueva medición/);
      await page.evaluate(()=>window.receive({threads:{a0:{name:'Diseñar el monitor',status:'active',model:'gpt-6.1-sol',context_window:{used_percent:20,used_tokens:20000,capacity_tokens:100000}}}}));
      assert.match(await page.locator('.task-row').getAttribute('aria-label'),/Contexto usado: 20 %/);
      await page.evaluate(()=>window.receive({connections:0,accountUsage:{}}));
      assert.equal(await page.locator('#quota').innerText(),'—');

      assert.deepEqual(errors,[]);
      await page.close();
    }
    console.log('PASS: gauges, compaction lifecycle/motion/reduced motion, stale/disconnected quota, overflow, keyboard and aligned circles at 390/432 px × 1/1.25/1.5/2 DPI');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
