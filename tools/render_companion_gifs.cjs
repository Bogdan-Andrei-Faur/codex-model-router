// Production companion artwork/styles, deterministic synthetic events, no owner data.
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const {execFile}=require('node:child_process');
const {promisify}=require('node:util');
const assert=require('node:assert/strict');
const run=promisify(execFile);
const ROOT=path.resolve(__dirname,'..');
const OUT=path.join(ROOT,'docs/design/companion-animations');
const FPS=20,FRAME_MS=1000/FPS;
const CASES=[
 ['preparing','Preparando turno','Bucle'],['working','Trabajando','Bucle'],
 ['thinking','Pensando','Bucle'],['planning','Planificando','Bucle'],
 ['writing','Escribiendo','Bucle'],['executing','Ejecutando comandos','Bucle'],
 ['editing','Editando archivos','Bucle'],['searching','Buscando en la web','Bucle'],
 ['tool','Usando una herramienta','Bucle'],['collaborating','Colaborando','Bucle'],
 ['inspecting','Observando una imagen','Bucle'],['generating','Generando una imagen','Bucle'],
 ['reviewing','Revisando','Bucle'],['compacting','Compactando contexto','Bucle'],
 ['approval','Esperando aprobación','Bucle'],['question','Esperando tu respuesta','Bucle'],
 ['retrying','Reintentando','Bucle'],['error','Error','Gesto único'],
 ['interrupted','Turno interrumpido','Gesto único'],['done','Turno terminado','Gesto único'],
 ['enter','Entrada del personaje','Transición'],['leave','Salida del personaje','Transición'],
 ['idle','En reposo','Bucle'],['unknown','Actividad sin confirmar','Bucle'],
 ['offline','Sin conexión','Bucle'],['waiting','Espera genérica · compatibilidad','Bucle'],
].map(([key,label,category],index)=>({key,label,category,number:index+1,file:`${String(index+1).padStart(2,'0')}-${key}.gif`}));
const selected=process.argv.slice(2);
if(selected.some(key=>!CASES.some(item=>item.key===key)))throw Error('Use activity keys from the gallery, or no arguments for all previews.');
const gcd=(a,b)=>b?gcd(b,a%b):a;
const lcm=(a,b)=>a/gcd(a,b)*b;
const escape=text=>text.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const CSS=`
body>main{visibility:hidden}body{margin:0;background:#101112}
#capture{width:480px;height:296px;box-sizing:border-box;padding:22px 24px;background:#0b0d0e;color:#f5f7fa;font-family:'Router Nunito',sans-serif;overflow:hidden;position:absolute;left:0;top:0;visibility:visible}
#capture h1{font-size:19px;line-height:25px;margin:0;font-weight:800;letter-spacing:-.02em}
#capture .subtitle{font-size:11px;color:#97a7b6;margin-top:4px}
#capture .samples{display:grid;grid-template-columns:264px 168px;margin-top:12px;height:178px;align-items:center}
#capture .sample{display:grid;place-items:center;grid-template-rows:24px 154px}
#capture .sample-label{font-size:11px;color:#a3b0bd;align-self:start}
#capture .stage{width:100%;height:154px;display:grid;place-items:center}
#capture .avatar{margin:0;padding:0;min-width:0;min-height:0;flex:0 0 auto;background:none;border:0;filter:none}
#capture .large{width:142px;height:150px}
#capture .small{width:38px;height:40px}
#capture .character-context{display:none}
#capture .footer{margin:12px 0 0;font-size:10px;color:#6f8192}
`;
async function capture(browser,item){
 const page=await browser.newPage({viewport:{width:800,height:700},deviceScaleFactor:1,reducedMotion:'no-preference'});
 const temporary=await fs.mkdtemp(path.join(os.tmpdir(),'router-animation-'));
 const errors=[];
 page.on('pageerror',error=>errors.push(String(error)));
 try{
  await page.goto(pathToFileURL(path.join(ROOT,'monitor-ui/index.html')).href);
  const details=await page.evaluate(({item,css})=>{
   // A single synthetic, stable mint identity. Production receive/avatar builds
   // both images; only the surrounding review card is fixture-specific.
   const nativeKind=['enter','leave'].includes(item.key)?'working':item.key;
   const row={name:'Synthetic animation',model:'gpt-6.1-sol',status:item.key==='waiting'?'waiting':item.key==='idle'?'idle':'active',turn_id:'synthetic'};
   if(!['unknown','offline','waiting','idle'].includes(item.key))row.activity={version:1,source:'native',scope:'turn',turn_id:'synthetic',kind:nativeKind,attention:nativeKind==='approval'?['approval']:nativeKind==='question'?['input']:[],blocking:['approval','question'].includes(nativeKind),observed_at:Date.now()/1000};
   if(item.key==='unknown')row.activity={version:1,source:'native',turn_id:'synthetic',kind:'unknown'};
   window.receive({connections:item.key==='offline'?0:1,ui:{mode:'Expanded',reduced:false},threads:{a:row}});
   const original=document.querySelector('.hero-character');
   if(original.dataset.state!==nativeKind)throw Error('Unexpected production pose: '+original.dataset.state+' vs '+nativeKind);
   const style=document.createElement('style');style.textContent=css;document.head.append(style);
   const root=document.createElement('section');root.id='capture';
   const title=document.createElement('h1');title.textContent=String(item.number).padStart(2,'0')+' · '+item.label;
   const subtitle=document.createElement('div');subtitle.className='subtitle';subtitle.textContent=item.key+' · '+item.category;
   const samples=document.createElement('div');samples.className='samples';
   for(const [size,label] of [['large','Inicio / Agentes · 142 px'],['small','Cápsula · 38 px']]){
    const sample=document.createElement('div');sample.className='sample';
    const caption=document.createElement('span');caption.className='sample-label';caption.textContent=label;
    const stage=document.createElement('div');stage.className='stage';
    const pet=original.cloneNode(true);pet.classList.remove('enter','leave');pet.classList.toggle('hero-character',size==='large');pet.classList.add(size);
    // Rebase the production monotonic phase to t=0 for reproducible captures.
    pet.style.setProperty('--pose-phase','0s');pet.querySelector('.character-body').style.removeProperty('animation-delay');
    if(['enter','leave'].includes(item.key))pet.classList.add(item.key);
    // Clones must not resolve gradients/clips against a different SVG copy.
    const ids=new Map([...pet.querySelectorAll('[id]')].map(n=>[n.id,n.id+'-'+size]));
    for(const node of pet.querySelectorAll('*'))for(const attribute of [...node.attributes]){
     let value=attribute.value;
     if(attribute.name==='id')value=ids.get(value)||value;
     else for(const [oldId,newId] of ids)value=value.replaceAll('url(#'+oldId+')','url(#'+newId+')');
     node.setAttribute(attribute.name,value);
    }
    stage.append(pet);sample.append(caption,stage);samples.append(sample);
   }
   const footer=document.createElement('p');footer.className='footer';footer.textContent=item.category==='Gesto único'||item.category==='Transición'?'El GIF repite el gesto para revisarlo. En la app se ejecuta una vez.':'Renderizado real del monitor · datos sintéticos';
   root.append(title,subtitle,samples,footer);document.body.append(root);
   const animations=root.getAnimations({subtree:true});
   for(const animation of animations){animation.pause();animation.currentTime=0;}
   window.reviewAnimations=animations;
   return {animations:animations.map(animation=>({name:animation.animationName,duration:animation.effect.getTiming().duration,iterations:animation.effect.getTiming().iterations===Infinity?'infinite':animation.effect.getTiming().iterations,delay:animation.effect.getTiming().delay})),width:root.offsetWidth,height:root.offsetHeight};
  },{item,css:CSS});
  await page.evaluate(()=>document.fonts.ready);
  await page.mouse.move(799,699);
  let durationMs;
  if(item.category==='Bucle'){
   const periods=[...new Set(details.animations.filter(a=>a.iterations==='infinite').map(a=>Math.round(a.duration/10)))];
   assert.ok(periods.length,'Loop has no production animation');
   durationMs=periods.reduce(lcm)*10;
   while(durationMs<3000)durationMs*=2;
   assert.ok(durationMs<=60000,'Unexpectedly long combined animation cycle');
  }else durationMs=2400;
  const frameCount=Math.ceil(durationMs/FRAME_MS);
  for(let frame=0;frame<frameCount;frame++){
   const time=frame*FRAME_MS;
   await page.evaluate(time=>{for(const animation of window.reviewAnimations)animation.currentTime=time;},time);
   await page.screenshot({path:path.join(temporary,String(frame).padStart(5,'0')+'.png'),clip:{x:0,y:0,width:480,height:296},animations:'allow'});
  }
  assert.deepEqual(errors,[]);
  const {stdout}=await run(process.env.ROUTER_GIF_PYTHON||'python3',[path.join(ROOT,'tools/encode_companion_gif.py'),'--frames',temporary,'--output',path.join(OUT,item.file),'--frame-ms',String(FRAME_MS)],{maxBuffer:1024*1024});
  const encoded=JSON.parse(stdout);
  assert.ok(encoded.frames>1);
  const result={...item,...encoded,animations:details.animations};
  console.log(`${String(item.number).padStart(2,'0')} ${item.key}: ${encoded.frames} frames, ${encoded.durationMs/1000}s, ${Math.round(encoded.bytes/1024)} KiB`);
  return result;
 }finally{await page.close();await fs.rm(temporary,{recursive:true,force:true});}
}
async function indexes(results){
 const manifest={schema:1,fps:FPS,synthetic:true,renderer:'Chromium / production monitor-ui',sourceSha256:{},previews:results};
 for(const file of ['monitor.css','monitor.js','characters.js','scenes.js','icons.js','core.js'])manifest.sourceSha256[file]=crypto.createHash('sha256').update(await fs.readFile(path.join(ROOT,'monitor-ui',file))).digest('hex');
 for(const item of results)item.sourceSha256??={...manifest.sourceSha256};
 await fs.writeFile(path.join(OUT,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
 const introductions=['# Animaciones de los personajes','',`${results.length} GIFs del renderizado real del monitor con datos sintéticos. Cada uno compara el personaje grande (142 px) y la cápsula (38 px).`,'','[Abrir la galería visual](index.html) · [Contrato de actividad](../../COMPANION-ACTIVITY.md)','','Usa el número o la clave para pedir cambios, por ejemplo: **03 Pensando** o **thinking**. Los gestos únicos y las transiciones se repiten en el GIF para revisarlos; en la app se ejecutan una vez. Reposo, espera y desconexión incluyen sus movimientos suaves. El cuerpo y los objetos conservan su forma.','','Los bucles cubren un ciclo completo de todos los movimientos combinados, incluido el parpadeo. El código de producción determina la duración; no se acelera el movimiento.','','## Índice',''];
 const table=['| Nº | Animación | Clave | Tipo |','| --- | --- | --- | --- |',...results.map(item=>`| ${String(item.number).padStart(2,'0')} | [${item.label}](#${item.key}) | \`${item.key}\` | ${item.category} |`)];
 const cards=results.map(item=>`<a id="${item.key}"></a>\n\n## ${String(item.number).padStart(2,'0')} · ${item.label}\n\n![${item.label}](${item.file})\n\n\`${item.key}\` · ${item.category} · ${item.durationMs/1000} s\n`);
 const reproduction=['','## Regenerar después de corregir una animación','','Requiere las dependencias Node del proyecto, Chromium de Playwright y Python con Pillow. No accede a datos personales ni a Desktop.','','```sh','node tools/render_companion_gifs.cjs           # todos','node tools/render_companion_gifs.cjs thinking # solo Pensando', '# Si Pillow está en un entorno virtual:', 'ROUTER_GIF_PYTHON=/ruta/al/venv/bin/python node tools/render_companion_gifs.cjs','```','','Los GIFs y el índice se guardan en esta carpeta. `manifest.json` registra las animaciones, tiempos y hashes del código renderizado.'];
 await fs.writeFile(path.join(OUT,'README.md'),[...introductions,...table,'',...cards,...reproduction].join('\n')+'\n');
 const cardsHtml=results.map(item=>`<article id="${item.key}" data-search="${escape((String(item.number).padStart(2,'0')+' '+item.key+' '+item.label+' '+item.category).toLowerCase())}"><h2>${String(item.number).padStart(2,'0')} · ${escape(item.label)}</h2><a href="${item.file}" title="Abrir GIF"><img src="${item.file}" width="480" height="296" alt="${escape(item.label)}" loading="lazy"></a><p><code>${item.key}</code><span>${escape(item.category)} · ${item.durationMs/1000} s</span><a href="#${item.key}">Enlace</a></p></article>`).join('\n');
 const html=`<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>Animaciones · Codex Model Router</title><style>*{box-sizing:border-box}body{margin:0;background:#090b0d;color:#e8edf2;font:15px system-ui,sans-serif}header{max-width:1510px;margin:auto;padding:36px 24px 24px}h1{font-size:28px;margin:0 0 10px}header p{color:#a0b1c0;line-height:1.6;max-width:1000px}a{color:#96cfff}input{font:inherit;border:1px solid #35424c;background:#141a1f;color:#e8edf2;padding:12px 14px;border-radius:12px;width:min(100%,480px);margin:12px 0 0}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,370px),1fr));gap:18px;max-width:1510px;margin:auto;padding:0 24px 40px}article{background:#12171b;border:1px solid #ffffff0b;border-radius:18px;overflow:hidden;scroll-margin-top:20px}article[hidden]{display:none}h2{font-size:15px;margin:18px 20px 8px}img{width:100%;height:auto;display:block}article p{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:12px 20px 18px;font-size:12px;color:#9cafbd}article p a{margin-left:auto}code{color:#96cfff}footer{max-width:1510px;margin:auto;padding:0 24px 30px;color:#90a2b2;font-size:13px}</style></head><body><header><h1>Animaciones de los personajes</h1><p>${results.length} GIFs · personaje grande y cápsula de 38 px. Pide cambios usando el número o la clave.<br>Los gestos únicos se repiten aquí para revisarlos. Reposo, espera y desconexión también tienen movimiento suave.</p><p><a href="README.md">Índice Markdown</a> · <a href="manifest.json">Datos del renderizado</a></p><label for="filter">Buscar animación</label><br><input id="filter" type="search" placeholder="Número, nombre o clave…" autocomplete="off"></header><main>${cardsHtml}</main><footer>Renderizado real de monitor-ui con datos sintéticos. Los GIFs permanecen en el repositorio y se pueden abrir sin conexión.</footer><script>document.querySelector('#filter').addEventListener('input',event=>{const query=event.target.value.toLocaleLowerCase('es').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');for(const card of document.querySelectorAll('article'))card.hidden=!card.dataset.search.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').includes(query)});</script></body></html>`;
 await fs.writeFile(path.join(OUT,'index.html'),html);
}
(async()=>{
 await run(process.env.ROUTER_GIF_PYTHON||'python3',['-c','from PIL import Image']);
 await fs.mkdir(OUT,{recursive:true});
 let previous=[];
 if(selected.length){try{const saved=JSON.parse(await fs.readFile(path.join(OUT,'manifest.json'),'utf8'));previous=saved.previews.map(item=>({...item,sourceSha256:item.sourceSha256||saved.sourceSha256}));}catch{throw Error('Generate all previews once before selectively updating them.');}}
 const browser=await chromium.launch({headless:true});
 try{
  const pending=CASES.filter(item=>!selected.length||selected.includes(item.key));
  const results=[];
  await Promise.all(Array.from({length:3},async()=>{while(pending.length){const item=pending.shift();results.push(await capture(browser,item));}}));
  const merged=CASES.map(item=>results.find(r=>r.key===item.key)||previous.find(r=>r.key===item.key));
  assert.ok(merged.every(Boolean));
  await indexes(merged);
  await run(process.env.ROUTER_GIF_PYTHON||'python3',[path.join(ROOT,'tools/render_companion_board.py')]);
  console.log(`Saved ${merged.length} GIFs and gallery: ${path.relative(ROOT,OUT)}/index.html`);
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
