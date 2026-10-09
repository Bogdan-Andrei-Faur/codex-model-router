// Production artwork sampled through its full cycles; synthetic characters only.
const {chromium}=require('playwright'),{pathToFileURL}=require('node:url');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({headless:true});try{
 const page=await browser.newPage({viewport:{width:800,height:900}});
 await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
 const result=await page.evaluate(()=>{
  window.monitorPointer=()=>{};
  window.receive({connections:1,ui:{mode:'Expanded',reduced:false}});
  const kinds=['preparing','working','thinking','planning','writing','executing','editing','searching','tool','collaborating','inspecting','generating','reviewing','compacting','approval','question','retrying','error','interrupted','done','idle','unknown','offline','waiting'];
  const failures=[];let sampled=0;
  for(const color of ['#81d7bd','#ff9e88','#c8b2f3'])for(const kind of kinds){
   state.connections=kind==='offline'?0:1;
   const row={status:kind==='waiting'?'waiting':kind==='idle'?'idle':'active',turn_id:'fixture',activity:{version:1,source:'native',turn_id:'fixture',kind,observed_at:Date.now()/1000}};
   const pet=avatar('rigid',row,()=>{},null,{color,head:'none',outfit:'none',glasses:'none'});
   pet.style.cssText+=';position:absolute;top:200px;left:200px;width:142px;height:150px;--pose-phase:0s';
   document.body.append(pet);pet.querySelector('.character-body').style.removeProperty('animation-delay');
   const animations=pet.getAnimations({subtree:true});animations.forEach(a=>a.pause());
   for(const time of [0,100,400,800,1200,2000,3000,3900]){
    animations.forEach(a=>a.currentTime=time);
    const frame=pet.querySelector('.character').getBoundingClientRect();
    for(const node of pet.querySelectorAll('.character *')){
     const style=getComputedStyle(node),m=new DOMMatrixReadOnly(style.transform);
     if(Math.abs(Math.hypot(m.a,m.b)-1)>0.001||Math.abs(Math.hypot(m.c,m.d)-1)>0.001||Math.abs(m.a*m.c+m.b*m.d)>0.001||!['none','1','1 1'].includes(style.scale))failures.push(kind+': deformed '+node.getAttribute('class'));
     if(!['path','rect','ellipse','circle'].includes(node.localName)||node.closest('defs')||style.visibility==='hidden'||style.display==='none')continue;
     const r=node.getBoundingClientRect();if(!r.width&&!r.height)continue;
     if(r.left<frame.left-2||r.top<frame.top-2||r.right>frame.right+2||r.bottom>frame.bottom+2)failures.push(kind+': outside scene '+node.getAttribute('class'));
    }
    sampled++;
   }
   const face=pet.querySelector('.character-face');
   if(face.getAttribute('width')!=='78'||face.getAttribute('height')!=='65')failures.push(kind+': changed body shape');
   pet.remove();
  }
  return {sampled,failures:[...new Set(failures)]};
 });
 assert.deepEqual(result.failures,[]);console.log('PASS: rigid components and contained scenes across '+result.sampled+' pose/color/time samples');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
