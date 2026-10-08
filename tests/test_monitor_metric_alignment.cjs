// Opening reflows metric labels; button centering must never offset the quota bar.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:800,height:900}});
  await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
  await page.evaluate(()=>document.fonts.ready);
  for(const context of [{context_window:{used_percent:76.8,capacity_tokens:258400,used_tokens:198451}},{},{context_compaction:{state:'compacting'}}]){
   await page.evaluate(context=>window.receive({connections:1,ui:{mode:'Expanded'},threads:{a:{name:'Metric fixture',status:'active',...context}},accountUsage:{valid_until:Date.now()/1000+3600,windows:[{duration_minutes:10080,remaining_percent:74}]}}),context);
   // Deterministically cover widths traversed by the compact-to-expanded animation.
   const samples=await page.evaluate(()=>{
    const surface=document.querySelector('#surface'),result=[];surface.style.transition='none';
    for(const width of [350,420,500,560,615,660,790]){
     surface.style.width=width+'px';
     const bars=[...document.querySelectorAll('.hero-metrics [role=progressbar]')].map(n=>n.getBoundingClientRect());
     result.push({width,difference:bars[1].bottom-bars[0].bottom});
    }
    surface.style.removeProperty('width');surface.getBoundingClientRect();surface.style.removeProperty('transition');return result;
   });
   assert.ok(samples.every(s=>Math.abs(s.difference)<1),JSON.stringify(samples));
  }
  // Also observe real animation frames, including re-entry after a collapsed island.
  await page.evaluate(()=>setMode('Compact'));await page.waitForTimeout(500);
  const frames=await page.evaluate(async()=>{
   setMode('Expanded');const samples=[];
   for(let i=0;i<35;i++){
    await new Promise(requestAnimationFrame);
    const bars=[...document.querySelectorAll('.hero-metrics [role=progressbar]')].map(n=>n.getBoundingClientRect());
    samples.push(bars[1].bottom-bars[0].bottom);
   }return samples;
  });
  assert.ok(frames.every(d=>Math.abs(d)<1),JSON.stringify(frames));
  await page.locator('.overview-quota').click();
  assert.equal(await page.locator('.quota-expanded').isVisible(),true,'Quota remains actionable');
  console.log('PASS: context/quota alignment throughout opening, unknown/compacting labels and quota action');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
