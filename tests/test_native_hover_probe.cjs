// Exercise the same probe used by GTK, including a delayed native delivery and
// negative controls. Browser evidence does not substitute for native GTK runs.
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  for(const scenario of ['delayed','broken-close','missing-outside']) {
   const page=await browser.newPage({viewport:{width:432,height:900}});
   try {
    await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
    await page.clock.install();
    await page.clock.pauseAt(new Date(Date.now()+1000));
    await page.evaluate(()=>window.receive({connections:1,ui:{mode:'Compact',reduced:true},
      threads:{fixture:{name:'Synthetic agent',status:'active',model:'gpt-6.1-sol'}}}));
    await page.evaluate(fs.readFileSync(path.resolve(__dirname,'fixtures/native_hover_probe.js'),'utf8'));
    await page.evaluate(scenario=>{
     if(scenario==='broken-close')window.closePeek=()=>{};
     window.probeResult=null;
     window.runNativeHoverProbe().then(result=>window.probeResult=result);
     if(scenario!=='missing-outside') {
      // A stale inside sample arrives after opening; the native outside update
      // follows805ms later, reproducing the observed GTK/WebKit ordering.
      const r=document.querySelector('#agents .avatar').getBoundingClientRect();
      setTimeout(()=>window.monitorPointer({x:r.x+r.width/2,y:r.y+r.height/2}),3);
      setTimeout(()=>{
       window.monitorPointer(null);
       window.nativeFixtureTimer=setInterval(()=>window.monitorPointer(null),250);
      },805);
     }
    },scenario);
    for(let elapsed=0;elapsed<10000 && !await page.evaluate(()=>window.probeResult);elapsed+=100)await page.clock.runFor(100);
    const result=await page.evaluate(()=>window.probeResult);
    assert.ok(result?.done,scenario+' must finish within bounded deadlines');
    if(scenario==='delayed') {
     assert.equal(result.checks.length,8,'All original native hover assertions remain');
     assert.ok(result.checks.every(Boolean),JSON.stringify(result));
     assert.ok(result.stages[0].firstOutsideMs>=800,'No fixed500ms startup assumption');
     assert.ok(result.stages.every(s=>s.outsideDelivered && s.elapsedMs-s.firstOutsideMs<=1000));
    } else if(scenario==='broken-close') {
     assert.equal(result.checks.length,8,'All original native hover assertions remain');
     assert.equal(result.checks[2],false,'Broken native exit must fail agent closure');
     assert.equal(result.checks[4],false,'Broken native exit must fail quota closure');
     assert.equal(result.stages[1].reason,'automatic close not observed');
    } else {
     assert.deepEqual(result.checks,[false]);
     assert.equal(result.stages[0].reason,'outside sample not delivered');
    }
   } finally {await page.close();}
  }
  console.log('PASS: native hover probe waits for delivery; broken close and missing outside still fail');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
