// Synthetic wardrobe contact sheets from the production renderer, no owner data.
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path'),fs=require('node:fs/promises');
(async()=>{const browser=await chromium.launch({headless:true});try{
 const out=path.resolve(process.env.ROUTER_WARDROBE_OUTPUT||'output/playwright/wardrobe');await fs.mkdir(out,{recursive:true});
 const page=await browser.newPage({viewport:{width:2600,height:1100},deviceScaleFactor:1});
 await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
 const slots=await page.evaluate(()=>Object.keys(C.appearanceSlots));
 for(const slot of [...slots,'combined'])for(const time of [800,2000]){
  await page.evaluate(({slot,time})=>{
   window.receive({connections:1,ui:{mode:'Expanded',reduced:false}});
   document.querySelector('#wardrobe-audit')?.remove();
   if(!document.querySelector('#audit-style')){const style=document.createElement('style');style.id='audit-style';style.textContent='body>main{display:none}body{background:#080b0d;margin:0}#wardrobe-audit{background:#080b0d;color:#ddd;padding:12px;font:12px sans-serif;width:max-content}#wardrobe-audit .audit-row{display:flex;align-items:center}#wardrobe-audit .audit-label{width:85px}#wardrobe-audit .audit-cell{width:92px;height:115px;display:flex;flex-direction:column;align-items:center}#wardrobe-audit .avatar{width:88px;height:94px;flex:none}';document.head.append(style);}
   const root=document.createElement('section');root.id='wardrobe-audit';
   const title=document.createElement('h2');title.textContent=slot+' · '+time+' ms · production artwork';root.append(title);document.body.append(root);
   const kinds=['preparing','working','thinking','planning','writing','executing','editing','searching','tool','collaborating','inspecting','generating','reviewing','compacting','approval','question','retrying','error','interrupted','done','idle','unknown','offline','waiting','enter','leave'];
   const choices=slot==='combined'?Array.from({length:8},(_,i)=>[String(i), 'Look '+(i+1)]):C.appearanceSlots[slot];
   for(const [value,label] of choices){const rowEl=document.createElement('div');rowEl.className='audit-row';const labelEl=document.createElement('div');labelEl.className='audit-label';labelEl.textContent=label;rowEl.append(labelEl);root.append(rowEl);
    const look=slot==='combined'?Object.fromEntries(Object.entries(C.appearanceSlots).map(([key,values])=>[key,values[1+Number(value)%(values.length-1)][0]])):{[slot]:value};
    for(const kind of kinds){const cell=document.createElement('div');cell.className='audit-cell';const cap=document.createElement('span');cap.textContent=kind;const pose=['enter','leave'].includes(kind)?'idle':kind;
     const pet=avatar('audit',{status:pose==='waiting'?'waiting':pose==='idle'?'idle':'active',turn_id:'fixture',activity:{version:1,source:'native',turn_id:'fixture',kind:pose}},()=>{},null,look,kind!=='offline');
     pet.style.setProperty('--pose-phase','0s');pet.querySelector('.character-body').style.removeProperty('animation-delay');if(['enter','leave'].includes(kind))pet.classList.add(kind);
     cell.append(cap,pet);rowEl.append(cell);pet.getAnimations({subtree:true}).forEach(a=>{a.pause();a.currentTime=time;});
    }
   }
  },{slot,time});
  await page.locator('#wardrobe-audit').screenshot({path:path.join(out,`${slot}-${time}.png`)});
 }
 console.log('Rendered 12 wardrobe sheets: every choice and 8 combined looks × 26 states × 2 times');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
