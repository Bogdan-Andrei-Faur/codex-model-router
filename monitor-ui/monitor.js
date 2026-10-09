'use strict';
const C = MonitorCore, $ = id => document.getElementById(id);
let state = {threads:{},history:[],config:{enabled:true},ui:{mode:'Compact',topmost:true},connections:0};
let currentTab = 'home', order = [], selectedDecision = null, selectedThread = null, peekId = null, peekTimer, reasonOpen = false;
let dataSignature = '', history = [], avatars = new Map();
let selectedWorkspaceAgent = null;
let appearanceEditing=null,appearanceRequest=0;
const appearanceDrafts=new Map();
function companion(id){return C.companion(id,state.appearances?.[id]);}
let selectedAgent = null, compactOrder=[], agentDetailsOpen=false, quotaDetailsOpen=false;
let avatarSerial=0, islandFrame=0;
let peekDismissed=false;
let quotaOpen = false, nativeHover = null, lastHoverPoint = null, modeRequest = 0, pendingModeRequest = 0;
let islandCloseTimer=null, islandPointerOutside=false;
function cancelIslandClose() {clearTimeout(islandCloseTimer);islandCloseTimer=null;}
function scheduleIslandClose() {
  if(state.ui.mode!=='Expanded'||heightDrag||appearanceEditing||islandCloseTimer)return;
  islandCloseTimer=setTimeout(()=>{
    islandCloseTimer=null;
    if(state.ui.mode==='Expanded'&&islandPointerOutside&&!heightDrag&&!appearanceEditing)setMode('Compact');
  },320);
}
function islandPointer(inside) {
  islandPointerOutside=!inside;
  if(inside)cancelIslandClose();else scheduleIslandClose();
}
let historyDirty = true, historyRevision = 0, projectedHistoryRevision=-1, historyBase=[], historyOverlayKey='';
const historySearchText=new WeakMap();
let connectionPending = null,settingsSection='application',consumptionSection='routing';
function requestHistory() {
  if(state.ui.lazyHistory)native({action:'history',value:state.ui.mode==='Expanded' && ['history','statistics'].includes(currentTab)});
}
function ensureHistory() {
  if(historyDirty){
    const fields=['decision_id','name','status','model','effort','requested_model','requested_effort','model_reason','effort_reason','phase_id','phase_name','phase_status','phase_model','phase_effort','phase_transition','observed_model','observed_effort','configured_model','configured_effort','accepted_model','accepted_effort','pipeline_mode','phase_pipeline','inference_source','evidence_confidence','inference_model_mismatch','inference_effort_mismatch','tokens'];
    const overlayKey=JSON.stringify(Object.entries(state.threads).map(([id,row])=>[id,...fields.map(key=>row[key])]));
    const rebuild=projectedHistoryRevision!==historyRevision;
    if(rebuild){historyBase=C.decisions(state.history);projectedHistoryRevision=historyRevision;}
    if(rebuild||overlayKey!==historyOverlayKey){history=C.withLiveDecisions(historyBase,state.threads);historyOverlayKey=overlayKey;}
    historyDirty=false;
  }
}
function selectAgent(id) {
  if(currentTab==='activity')selectedWorkspaceAgent=id;else selectedAgent=id;reasonOpen=false;activity();
}
function topObstruction() {
  const clock=Number.isFinite(state.ui.clockHeight) && state.ui.clockHeight>0;
  const w=clock?state.ui.clockWidth:state.ui.cameraWidth,h=clock?state.ui.clockHeight:state.ui.cameraHeight;
  return {width:Number.isFinite(w)?Math.max(0,w):0,height:Number.isFinite(h)?Math.max(0,h):0};
}
function cameraLayout() {
  const {width,height}=topObstruction();
  document.body.classList.toggle('clock-slot',Number.isFinite(state.ui.clockHeight) && state.ui.clockHeight>0);
  const wings=width>0 && innerWidth>=width+300;
  document.body.classList.toggle('camera-wings',wings);
  document.body.classList.toggle('camera-nav',wings && innerWidth>=width+24+72+280);
  document.body.classList.toggle('camera-inset',height>0 && !wings);
  document.documentElement.style.setProperty('--camera-gap',(wings?width+24:0)+'px');
  document.documentElement.style.setProperty('--camera-top',(height>0?height+8:0)+'px');
}
function fitIsland() {
  document.body.classList.toggle('overview',['home','activity'].includes(currentTab));
  document.body.classList.toggle('history-view',currentTab==='history');
  document.body.classList.toggle('settings-view',currentTab==='settings');
  document.body.classList.toggle('preferences-view',['statistics','settings'].includes(currentTab));
  cancelAnimationFrame(islandFrame);
  islandFrame=requestAnimationFrame(()=>{
    if(state.ui.mode!=='Expanded' || !['home','activity','statistics','settings'].includes(currentTab))return;
    const outer=node=>{const css=getComputedStyle(node);return node.getBoundingClientRect().height+parseFloat(css.marginTop)+parseFloat(css.marginBottom);};
    const page=['statistics','settings'].includes(currentTab)?$(currentTab):$('activity');
    const height=page.scrollHeight+outer(document.querySelector('nav'))+outer($('notices'))+parseFloat(getComputedStyle($('surface')).paddingTop);
    $('surface').style.setProperty(['statistics','settings'].includes(currentTab)?'--preferences-height':'--overview-height',Math.ceil(height)+'px');
  });
}
const native = message => {
  if(state.readOnly && !['mode','bounds','ready','history','resizeStart','resizeEnd','resizeReset'].includes(message.action)){window.monitorFeedback('Vista previa de solo lectura.');return;}
  if(window.chrome?.webview)window.chrome.webview.postMessage(message);
  else window.webkit?.messageHandlers?.monitor?.postMessage(message);
};
const heightGrip = $('height-grip');
let heightDrag = null;
function panelHeight(value) {
  const height = Math.min(Math.max(1,innerHeight-16),Math.max(544,value));
  $('surface').style.setProperty('--panel-height',height+'px');
  return height;
}
heightGrip.addEventListener('pointerdown',event=>{
  if(event.button!==0)return;
  heightDrag={y:event.screenY,height:$('surface').getBoundingClientRect().height};
  cancelIslandClose();
  heightGrip.setPointerCapture(event.pointerId);document.body.classList.add('resizing');
  native({action:'resizeStart'});event.preventDefault();
});
heightGrip.addEventListener('pointermove',event=>{
  if(heightDrag)panelHeight(heightDrag.height+event.screenY-heightDrag.y);
});
function finishHeightDrag() {
  if(!heightDrag)return;
  const height=$('surface').getBoundingClientRect().height+16;
  heightDrag=null;document.body.classList.remove('resizing');
  native({action:'resizeEnd',height});
  if(islandPointerOutside)scheduleIslandClose();
}
heightGrip.addEventListener('pointerup',finishHeightDrag);
heightGrip.addEventListener('pointercancel',finishHeightDrag);
heightGrip.addEventListener('lostpointercapture',finishHeightDrag);
heightGrip.addEventListener('dblclick',()=>{native({action:'resizeReset'});});
heightGrip.addEventListener('keydown',event=>{
  if(event.key==='Home'){native({action:'resizeReset'});event.preventDefault();}
  if(event.key==='ArrowUp'||event.key==='ArrowDown'){
    const height=panelHeight($('surface').getBoundingClientRect().height+(event.key==='ArrowDown'?24:-24));
    native({action:'resizeEnd',height:height+16});event.preventDefault();
  }
});
const el = (tag, cls, text) => { const node = document.createElement(tag); if(cls) node.className=cls; if(text !== undefined) node.textContent=String(text); return node; };
function button(text, action, cls='') { const node=el('button',cls,text);node.addEventListener('click',action);return node; }
function productButton(text,action,cls='') {const node=button(text,action,cls);node.disabled=!!state.readOnly;return node;}
function palette(node, colors) {node.style.setProperty('--tint',colors[0]);node.style.setProperty('--face',colors[1]);return node;}
function badge(value, effort=false) { const label=effort ? C.efforts[value] || 'Sin confirmar' : C.model(value);const node=palette(el('span','badge',label), effort ? C.effortColors[value] || C.neutral : C.models[C.family(value)] || C.neutral);node.setAttribute('aria-label',(effort?'Razonamiento: ':'Modelo: ')+label);return node; }
function tags(row, normalized=false) {const box=el('div','tags');box.append(badge(normalized?row.model:C.setting(row,'model')),badge(normalized?row.effort:C.setting(row,'effort'),true));return box;}
function svg(tag, attributes={}) { const node=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value] of Object.entries(attributes))node.setAttribute(key,String(value));return node; }
function icon(name,cls='ui-glyph') {
  const nodes=RouterIcons.nodes[name];if(!nodes)throw new Error('Unknown Lucide icon: '+name);
  const node=svg('svg',{viewBox:'0 0 24 24',class:cls,'data-lucide':name,'aria-hidden':'true',focusable:'false',fill:'none',stroke:'currentColor','stroke-width':2,'stroke-linecap':'round','stroke-linejoin':'round'});
  for(const [tag,attrs] of nodes)node.append(svg(tag,attrs));return node;
}
function controlLabel(node,name,label) {node.replaceChildren(icon(name),el('span','',label));}
function refreshQuota() {
  const gauge=C.weeklyQuota(state.accountUsage,!!state.connections),node=$('quota');
  node.replaceChildren(el('strong','quota-number',gauge.percent===null?'—':gauge.percent+'%'));
  node.setAttribute('aria-label',gauge.details);
  node.classList.toggle('unavailable',gauge.percent===null);
  refreshQuotaBars();refreshOverviewQuota();if(quotaOpen)renderQuotaPeek();
}
function renderQuotaPeek() {
  const gauge=C.weeklyQuota(state.accountUsage,!!state.connections),content=el('div','peek-content quota-card');
  const heading=el('div','quota-card-heading');heading.append(el('span','','Tu cuota'),el('span','quota-card-chip','Codex'));
  const hero=el('div','quota-card-hero'),copy=el('div');
  copy.append(el('strong','quota-card-number',gauge.percent===null?'—':gauge.percent+'%'),el('span','quota-card-caption',gauge.percent===null?'Pendiente de actualizar':'disponible esta semana'));
  hero.append(copy,icon('gauge'));content.append(heading,hero);quotaSection(content);
  $('peek').replaceChildren(content);$('surface').style.setProperty('--peek-height',(84+content.offsetHeight)+'px');
}
function openQuota(force=false) {
  if(peekDismissed && !force)return;peekDismissed=false;
  closePeek();quotaOpen=true;$('peek').hidden=false;document.body.classList.add('peek');renderQuotaPeek();
}
function activityArt(kind) { return RouterScenes.draw(svg,icon,kind); }
function avatar(id,row,open,existing,appearanceOverride) {
  const node=existing || button('',open,'avatar'),identity=appearanceOverride===undefined?companion(id):C.companion(id,appearanceOverride),visual=C.companionState(row,!!state.connections),context=C.contextGauge(row);
  const previousKind=node.dataset.state;
  node.dataset.companion=identity.variant;node.dataset.state=visual.kind;
  node.style.setProperty('--character',identity.color);
  node.classList.toggle('working',visual.kind==='working');node.classList.toggle('compacting',visual.kind==='compacting');
  node.dataset.eyes=identity.eyes;node.style.setProperty('--accessory',identity.accessoryColor);
  const appearanceKey=JSON.stringify(identity);
  if(!existing || node.dataset.appearance!==appearanceKey){
    node.dataset.appearance=appearanceKey;node.replaceChildren();
    const art=svg('svg',{viewBox:'-12 -28 124 132',preserveAspectRatio:'xMidYMid meet',class:'character','aria-hidden':'true',focusable:'false'});
    const gradientId='companion-light-'+(++avatarSerial),defs=svg('defs'),gradient=svg('linearGradient',{id:gradientId,x1:0,y1:0,x2:0.7,y2:1});
    gradient.append(svg('stop',{offset:0,'stop-color':'#ffffff','stop-opacity':.28}),svg('stop',{offset:.5,'stop-color':'#ffffff','stop-opacity':0}),svg('stop',{offset:1,'stop-color':'#000000','stop-opacity':.09}));defs.append(gradient);
    const mood=svg('linearGradient',{id:gradientId+'-mood',x1:0,y1:0,x2:0,y2:1});
    mood.append(svg('stop',{offset:0,'stop-color':'var(--mood-color,#b0c7de)','stop-opacity':.7}),svg('stop',{offset:.85,'stop-color':'var(--mood-color,#b0c7de)','stop-opacity':0}));defs.append(mood);art.append(defs);
    const body=svg('g',{class:'character-body'});
    body.append(svg('path',{d:'M15 51 Q6 48 7 60 Q8 69 18 65',class:'limbs hand-left'}),
      svg('path',{d:'M85 51 Q94 48 93 60 Q92 69 82 65',class:'limbs hand-right'}),
      svg('rect',{x:30,y:79,width:13,height:13,rx:6,class:'limbs foot-left'}),svg('rect',{x:57,y:79,width:13,height:13,rx:6,class:'limbs foot-right'}),
      svg('rect',{x:11,y:20,width:78,height:65,rx:identity.roundness,class:'character-face'}),
      svg('rect',{x:11,y:20,width:78,height:65,rx:identity.roundness,class:'character-light',fill:'url(#'+gradientId+')'}),
      svg('rect',{x:11,y:20,width:78,height:65,rx:identity.roundness,class:'character-mood',fill:'url(#'+gradientId+'-mood)'}),
      svg('path',{d:'M30 29 Q39 24 46 28',class:'character-mark'}),
      svg('ellipse',{cx:37,cy:51,rx:4.5,ry:identity.eyes==='round'?4.5:6,class:'eye'}),svg('ellipse',{cx:63,cy:51,rx:4.5,ry:identity.eyes==='round'?4.5:6,class:'eye'}),
      svg('path',{d:'M32 52 Q37 48 42 52 M58 52 Q63 48 68 52',class:'happy-eyes'}),
      svg('path',{d:'M32 52Q37 55 42 52 M58 52Q63 55 68 52',class:'closed-eyes'}),
      svg('path',{d:'M43 64 Q50 69 57 64',class:'mouth'}));
    const clipId=gradientId+'-body',clip=svg('clipPath',{id:clipId});clip.append(svg('rect',{x:11,y:20,width:78,height:65,rx:identity.roundness}));defs.append(clip);
    body.append(RouterCharacters.draw(svg,identity,clipId));
    // Keep active hands in front of the face/clothes so their gestures remain
    // legible in the 38px capsule as well as the large portrait.
    body.append(...body.querySelectorAll('.hand-left,.hand-right'));
    art.append(body);const meter=el('span','character-context');meter.append(el('span'));
    node.append(art,meter,el('span','character-attention'));
    if(identity.variant==='mint')body.querySelector('.character-mark').setAttribute('d','M43 19 Q43 8 53 12');
    if(identity.variant==='lilac')body.querySelector('.character-mark').setAttribute('d','M30 30 Q50 16 70 30');
  }
  const body=node.querySelector('.character-body');
  if(previousKind!==visual.kind || !body.querySelector('.activity-prop')){
    node.style.setProperty('--pose-phase',`-${performance.now()/1000}s`);
    body.querySelector('.activity-prop')?.remove();
    const prop=activityArt(visual.kind);
    if(visual.kind==='searching')body.insertBefore(prop,body.firstChild);else body.append(prop);
    body.append(...body.querySelectorAll('.hand-left,.hand-right')); // Hands grip in front of props.

    const mouths={thinking:'M45 66Q50 64 55 66',writing:'M44 65Q50 67 56 65',planning:'M44 65Q50 67 56 65',question:'M47 66Q50 63 54 66',interrupted:'M43 65H56',error:'M43 67Q50 63 57 67',reviewing:'M44 66H56',waiting:'M44 66H56',offline:'M46 66Q50 68 54 66',unknown:'M45 66H55',done:'M42 63Q50 70 58 63'};
    body.querySelector('.mouth').setAttribute('d',mouths[visual.kind]||'M43 64Q50 69 57 64');
  }
  if(previousKind!==visual.kind){
    const oneShot=['done','error','interrupted'].includes(visual.kind),elapsed=Math.max(0,Date.now()/1000-(row.activity?.observed_at||row.completed_at||Date.now()/1000));
    node.querySelector('.character-body').style.animationDelay=oneShot?`-${Math.min(elapsed,2)}s`:`-${performance.now()/1000}s`;
  }
  const attention=node.querySelector('.character-attention'),attentionKind=visual.attention?.includes('approval')?'approval':visual.attention?.includes('input')?'input':null;
  attention.hidden=!attentionKind || ['approval','question'].includes(visual.kind);attention.dataset.kind=attentionKind||'';
  attention.replaceChildren(...(attentionKind?[icon(attentionKind==='approval'?'lock-keyhole':'circle-help')]:[]));
  attention.setAttribute('aria-hidden','true');
  const meter=node.querySelector('.character-context');meter.classList.toggle('unavailable',context.percent===null);
  meter.firstElementChild.style.width=(context.percent??0)+'%';
  node.setAttribute('aria-label',`${identity.name} · identidad visual de ${row.name || id || 'reposo'} · ${visual.label} · ${C.model(C.setting(row,'model'))} · ${C.efforts[C.setting(row,'effort')] || 'Sin confirmar'} · ${context.label}`);
  return node;
}
function contextMeter(parent,row,concise=false) {
  const context=C.contextGauge(row),box=el('div','context-metric'),line=el('div','metric-line');
  line.append(el('span','','Contexto usado'),el('strong','',context.compacting?'Compactando…':context.percent===null?'Sin medición':Number(context.percent.toFixed(1))+' %'));
  const track=el('div','context-meter'+(context.percent===null?' unavailable':'')+(context.compacting?' compacting':'')),fill=el('span');fill.style.width=(context.percent??0)+'%';track.append(fill);
  track.setAttribute('role','progressbar');track.setAttribute('aria-label',context.label);track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax','100');
  if(context.percent!==null)track.setAttribute('aria-valuenow',String(context.percent));
  box.append(line,track);if(!concise)box.append(el('p','small',context.label));parent.append(box);
}
function companionHero(parent,entries) {
  const selected=entries.find(([id])=>id===selectedAgent),live=entries.find(([,row])=>C.liveAgent(row)),attention=entries.find(([,row])=>['waiting','error','failed'].includes(row.status));
  const recent=entries.slice().sort((a,b)=>(b[1].updated||0)-(a[1].updated||0))[0];
  const [id,row]=selected||live||attention||recent||['rest',{status:'idle'}],identity=companion(id),visual=C.companionState(row,!!state.connections);
  const hero=el('section','companion-hero'),scene=el('div','hero-scene'),art=avatar(id,row,()=>{if(state.threads[id]){selectedAgent=id;selectedWorkspaceAgent=id;showTab(agentDetailsOpen?'home':'activity');}}),copy=el('div','companion-copy');
  hero.style.setProperty('--character',identity.color);art.classList.add('hero-character');
  art.disabled=!state.threads[id];
  copy.append(el('div','companion-alias',identity.name),el('h2','companion-headline',visual.headline),el('p','hero-task',row.name||'Las tareas aparecerán aquí.'),el('p','hero-status',visual.label));
  if(state.threads[id]){const model=el('div','hero-model');model.append(el('span','','Modelo seleccionado'),tags(row));copy.append(model);}
  scene.append(art);hero.append(scene,copy);parent.append(hero);
  const metrics=el('div','hero-metrics');metrics.style.setProperty('--character',identity.color);contextMeter(metrics,row,true);
  const quota=button('',()=>{quotaDetailsOpen=!quotaDetailsOpen;activity();},'overview-quota');quota.setAttribute('aria-expanded',String(quotaDetailsOpen));
  const line=el('div','metric-line');line.append(el('span','','Cuota semanal'),el('strong','overview-quota-value'));
  const track=el('div','quota-meter');track.append(el('span'));track.setAttribute('role','progressbar');track.setAttribute('aria-label','Cuota semanal disponible');track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax','100');
  quota.append(line,track);metrics.append(quota);parent.append(metrics);
  if(quotaDetailsOpen){const details=el('div','section quota-expanded');quotaSection(details);parent.append(details);}
  return state.threads[id]?id:null;
}
function refreshOverviewQuota() {
  const node=document.querySelector('.overview-quota');if(!node)return;
  const gauge=C.weeklyQuota(state.accountUsage,!!state.connections),track=node.querySelector('.quota-meter');
  node.querySelector('.overview-quota-value').textContent=gauge.percent===null?'Sin datos':gauge.percent+' % libre';
  node.setAttribute('aria-label',gauge.details);track.classList.toggle('unavailable',gauge.percent===null);track.firstElementChild.style.width=(gauge.percent??0)+'%';
  if(gauge.percent===null)track.removeAttribute('aria-valuenow');else track.setAttribute('aria-valuenow',String(gauge.percent));
}

function setMode(mode,notify=true) {
  if(!['Compact','Expanded','Hidden'].includes(mode))return;
  cancelIslandClose();
  state.ui.mode=mode;peekDismissed=false;closePeek();clearNativeHover();
  document.body.classList.remove('compact','expanded','hidden');document.body.classList.add(mode.toLowerCase());
  $('compact').hidden=mode!=='Compact';$('expanded').hidden=mode!=='Expanded';
  refreshQuota(); // Hidden SVG text has no bounds; measure the newly visible view.
  if(notify){const request=++modeRequest;pendingModeRequest=state.ui.acknowledgesMode?request:0;native({action:'mode',value:mode,request});}
  requestHistory();
  if(mode==='Expanded')renderPage();
  window.monitorBounds();
}
function openPeek(id,force=false) {
  if(peekDismissed && !force)return;peekDismissed=false;
  quotaOpen=false;
  cancelPeekClose();if(!state.threads[id])return;
  peekId=id;$('peek').hidden=false;document.body.classList.add('peek');renderPeek();
}
function renderPeek() {
  const row=state.threads[peekId];if(!row)return closePeek();
  const box=$('peek'),content=el('div','peek-content'),ident=C.identity(row);
  content.style.setProperty('--character',companion(peekId).color);
  const category=el('div','peek-category');category.append(icon(ident[1]),el('span','',ident[0]));
  category.setAttribute('aria-label',ident[0]+' · tipo orientativo · confianza '+(row.agent_confidence || 'sin confirmar'));
  content.append(category,el('div','peek-title',row.name || peekId),tags(row));
  const visual=C.companionState(row,!!state.connections);
  if(!['working','compacting'].includes(visual.kind))content.append(el('div','peek-meta',visual.label));
  contextMeter(content,row,true);
  box.replaceChildren(content);
  $('surface').style.setProperty('--peek-height',(84+content.offsetHeight)+'px');
}
function cancelPeekClose() {clearTimeout(peekTimer);peekTimer=null;}
function schedulePeekClose() {
  // Native pointer samples and DOM leave events may repeat during the grace
  // period. Keep the first deadline; only re-entering the island cancels it.
  if(peekTimer || (!peekId && !quotaOpen))return;
  peekTimer=setTimeout(closePeek,220);
}
function closePeek() {cancelPeekClose();peekId=null;quotaOpen=false;$('peek').hidden=true;document.body.classList.remove('peek');}
function capsuleLimit() {return document.body.classList.contains('camera-wings') ? Math.max(1,Math.min(4,Math.floor((innerWidth-topObstruction().width-24-72-46)/76))) : Math.max(1,Math.min(6,Math.floor((Math.min(430,window.innerWidth)-177)/42)));}
function capsule() {
  const rows=state.threads;
  order=C.stableOrder(order,rows);compactOrder=C.companionOrder(compactOrder,rows);
  const limit=capsuleLimit(),visible=compactOrder.slice(0,limit),host=$('agents');
  $('compact').classList.toggle('multi-agent',compactOrder.length>1);
  // Symmetric wings grow with visible companions; reserve overflow space only when needed.
  const wing=Math.max(76,visible.length*38+(compactOrder.length>limit?23:0));
  const width=document.body.classList.contains('camera-wings') ? topObstruction().width+24+72+2*wing : Math.max(350,Math.min(430,visible.length*42+177));
  $('surface').style.setProperty('--compact-width',width+'px');
  const focus=rows[visible[0]]||{status:'idle'},visual=C.companionState(focus,!!state.connections);
  $('compact-summary').replaceChildren(el('strong','',visual.headline),el('span','',focus.name||'Codex'));
  $('compact-summary').setAttribute('aria-label','Ver agentes · '+(focus.name||visual.label));
  for(const [id,node] of avatars) if(!visible.includes(id)) {
    if(node.classList.contains('leave'))continue;
    if(rows[id])avatar(id,rows[id],null,node);
    node.style.setProperty('--exit-left',node.offsetLeft+'px');
    node.classList.add('leave');
    setTimeout(()=>{if(!compactOrder.slice(0,capsuleLimit()).includes(id)){node.remove();avatars.delete(id);if(!compactOrder.length&&!avatars.size)capsule();}},900);
  }
  host.querySelector('.idle')?.remove();host.querySelector('.overflow')?.remove();
  for(const id of visible) {
    let node=avatars.get(id);
    if(!node) {
      node=avatar(id,rows[id],()=>openPeek(id,true));node.classList.add('enter');
      node.addEventListener('mouseenter',()=>openPeek(id));node.addEventListener('focus',()=>openPeek(id,true));
      avatars.set(id,node);host.append(node);setTimeout(()=>node.classList.remove('enter'),900);
    } else {node.classList.remove('leave');avatar(id,rows[id],null,node);}
  }
  // Never reorder surviving agents. Newly active ones join at the end.
  if(!visible.length&&!avatars.size){const rest=avatar('rest',{status:'idle'},()=>setMode('Expanded'));rest.classList.add('idle');host.append(rest);}
  if(compactOrder.length>limit)host.append(button('+'+(compactOrder.length-limit),()=>setMode('Expanded'),'overflow'));
  if(peekId){if(!compactOrder.includes(peekId))closePeek();else renderPeek();}
}
function showTab(name) {
  if(name!=='activity')appearanceEditing=null;
  if(!['home','activity','history','statistics','settings'].includes(name))return;
  if(name==='home' || name==='activity')agentDetailsOpen=name==='activity';
  currentTab=name;for(const node of document.querySelectorAll('[data-tab]')){node.classList.toggle('selected',node.dataset.tab===name);node.setAttribute('aria-pressed',String(node.dataset.tab===name));}
  $('view-title').textContent=({home:'Inicio',activity:'Agentes',history:'Historial',statistics:'Consumo',settings:'Ajustes'})[name];
  for(const node of document.querySelectorAll('.page'))node.hidden=node.id!==(name==='home'?'activity':name);
  requestHistory();renderPage();
}
function explanation(parent,label,value,kind='') {const box=el('div','reason-card'+(kind?' '+kind:''));box.append(el('h3','',label),el('p','',value || 'Registro anterior sin explicación separada.'));parent.append(box);}
function phaseStatus(value) {return ({proposed:'Fase propuesta',requested:'Cambio solicitado',applied:'Cambio aceptado',rejected:'Cambio rechazado',preserved:'Selección conservada',unchanged:'Sin cambio',requires_new_turn:'Requiere otro turno',unknown_after_timeout:'Cambio sin confirmar',checkpoint_limit:'Límite de fases',cancelled:'Cancelado',accepted:'Aceptada por Codex',active:'Fase activa',observed:'Modelo observado',completed:'Fase completada',blocked:'Cambio bloqueado',failed:'Fase con incidencia'}[value] || 'Fase sin confirmar');}
function historyEvidence(row) {
  const settings=[];
  const different=(model,effort,referenceModel,referenceEffort)=>model&&(model!==referenceModel||effort&&referenceEffort&&effort!==referenceEffort);
  if(row.evidence_confidence==='confirmed'&&row.observed_model)settings.push(['Inferencia confirmada',row.observed_model,row.observed_effort]);
  else if(row.observed_model||row.observed_candidate_model)settings.push(['Observación sin confirmar',row.observed_model||row.observed_candidate_model,row.observed_effort||row.observed_candidate_effort]);
  if(different(row.accepted_model,row.accepted_effort,row.model,row.effort))settings.push(['Ajustes aceptados por Codex',row.accepted_model,row.accepted_effort]);
  if(different(row.configured_model,row.configured_effort,row.accepted_model||row.model,row.accepted_effort||row.effort))settings.push(['Configuración publicada',row.configured_model,row.configured_effort]);
  const phases=(row.phase_events||[]).filter(p=>['applied','rejected','failed','blocked','unknown_after_timeout','requires_new_turn','checkpoint_limit','cancelled'].includes(p.phase_status));
  const samples=Object.values(row.inference_samples||{});
  return {settings,phases,samples};
}
function executionEvidence(parent,row,evidence=historyEvidence(row)) {
  for(const [label,model,effort] of evidence.settings){const item=el('div','history-evidence-setting');item.append(el('h3','',label),tags({model,effort}));parent.append(item);}
  if(evidence.phases.length)explanation(parent,'Cambios registrados',evidence.phases.map(p=>`${p.phase_name||'Fase'} · ${phaseStatus(p.phase_status)}${p.phase_model?' · '+C.model(p.phase_model):''}${p.phase_effort?' · '+(C.efforts[p.phase_effort]||p.phase_effort):''}`).join('\n'));
  if(row.prior_inferences?.length)explanation(parent,'Inferencias anteriores',row.prior_inferences.map(p=>`${C.model(p.model)} · ${C.efforts[p.effort]||'Sin dato de esfuerzo'} · ${p.confidence==='confirmed'?'confirmada':'sin confirmar'}`).join('\n'));
  if(evidence.samples.length)explanation(parent,'Métricas recibidas',evidence.samples.map(s=>{
    const values=[`${s.inference_event_name||'evento'} / ${s.inference_event_kind||'petición'} · ${s.count} registros · ${s.failures||0} fallos`];
    for(const [k,label] of [['inference_input_tokens','tokens entrada'],['inference_output_tokens','tokens salida'],['inference_ttft_ms','TTFT ms'],['inference_duration_ms','duración del evento ms'],['inference_http_status','HTTP']])if(s[k]!==undefined)values.push(`${label}: ${s[k]}`);
    return values.join(' · ');
  }).join('\n')+'\nÚltimo valor por clase de evento; no representa el total del turno.');
}
function historyMeasurements(parent,row) {
  const metrics=el('div','history-measurements');
  const item=(label,value,note)=>{const tile=el('div','history-measurement');tile.append(el('span','small',label),el('strong','',value));if(note)tile.append(el('span','small',note));metrics.append(tile);};
  if(Number.isFinite(row.started)&&row.started>0&&Number.isFinite(row.finished)&&row.finished>=row.started){const seconds=Math.round(row.finished-row.started);item('Tiempo del turno',seconds<60?seconds+' s':Math.floor(seconds/60)+' min '+seconds%60+' s');}
  const sample=C.usageSample(row);
  if(sample.input!==null)item('Tokens de entrada',fmt(sample.input),'Última llamada');
  if(sample.output!==null)item('Tokens de salida',fmt(sample.output),'Última llamada');
  if(Number.isSafeInteger(row.native_retries)&&row.native_retries>0)item('Reintentos de conexión',fmt(row.native_retries));
  if(metrics.children.length)parent.append(metrics);
}
function taskModeControls(parent,id,showHint=true) {
  if(!id)return;
  const mode=state.taskModes?.[id] || 'automatic';
  choices(parent,[['automatic','Automático'],['manual','Manual']],mode,value=>native({action:'taskMode',thread:id,value}));
  if(!showHint && state.config.enabled)return;
  parent.append(el('p','small',!state.config.enabled?'El selector está pausado para todas las tareas.':mode==='manual'?
    'Próximo mensaje: usa el modelo y esfuerzo elegidos en Codex.':'Próximo mensaje: el selector decide modelo y esfuerzo.'));
}
function refreshQuotaBars() {
  const windows=C.quotaWindows(state.accountUsage,!!state.connections);
  for(const node of document.querySelectorAll('[data-quota-window]')) {
    const w=windows[Number(node.dataset.quotaWindow)];if(!w)continue;
    node.querySelector('.quota-value').textContent=w.percent===null?'Sin datos actuales':w.percent+' % disponible';
    const track=node.querySelector('.quota-meter'),fill=track.firstElementChild;
    fill.style.width=(w.percent??0)+'%';track.classList.toggle('unavailable',w.percent===null);
    if(w.percent===null)track.removeAttribute('aria-valuenow');else track.setAttribute('aria-valuenow',String(w.percent));
  }
}
function quotaSection(parent) {
  const section=el('section','account-quota');section.setAttribute('aria-label','Cuota compartida de la cuenta');
  const windows=C.quotaWindows(state.accountUsage,!!state.connections);
  if(!windows.length)section.append(el('p','small','Cuota de la cuenta: sin medición disponible.'));
  windows.forEach((w,index)=>{
    const row=el('div','quota-window');row.dataset.quotaWindow=index;
    row.dataset.duration=String(w.duration_minutes||'unknown');
    const line=el('div','metric-line'),value=el('strong','quota-value',w.percent===null?'Sin datos actuales':w.percent+' % disponible');
    line.append(el('span','',w.label),value);
    const track=el('div','quota-meter'+(w.percent===null?' unavailable':'')),fill=el('span');fill.style.width=(w.percent??0)+'%';
    track.setAttribute('role','progressbar');track.setAttribute('aria-label',w.label+' disponible');track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax','100');if(w.percent!==null)track.setAttribute('aria-valuenow',String(w.percent));track.append(fill);
    row.append(line,track);
    const info=[windows.filter(x=>x.duration_minutes===w.duration_minutes).length>1?w.limit_id:null,Number.isFinite(w.resets_at)?'Se renueva '+when(w.resets_at):null].filter(Boolean).join(' · ');
    if(info)row.append(el('div','small',info));section.append(row);
  });
  parent.append(section);
}
function livePipeline(parent,row) {
  const data=C.executionPipeline(row,!!state.connections);if(!data)return;
  const box=el('section','live-pipeline'),heading=el('div','live-pipeline-heading');
  heading.append(el('h3','',data.source),el('span','small',data.status));box.append(heading);
  const track=el('ol','live-pipeline-track');track.setAttribute('aria-label',data.source);
  data.steps.forEach((step,index)=>{
    const item=el('li','live-pipeline-step '+step.state+(step.animate?' animating':''));
    item.dataset.step=String(index);if(step.state==='active')item.setAttribute('aria-current','step');
    item.setAttribute('aria-label',`${index+1}. ${step.label}: ${step.statusLabel}`);
    const marker=el('span','live-pipeline-marker');marker.setAttribute('aria-hidden','true');
    marker.append(step.state==='completed'?icon('check'):document.createTextNode(String(index+1)));
    item.append(marker,el('span','live-pipeline-label',step.label),el('small','',step.statusLabel));track.append(item);
  });
  box.append(track);parent.append(box);
}
function appearanceFields(value) {
  return Object.fromEntries(['name','color','accessoryColor','roundness','eyes','head','glasses','outfit','neck','detail'].map(key=>[key,value[key]]));
}
function openAppearance(id) {
  if(state.readOnly||state.preview)return;
  if(!appearanceDrafts.has(id))appearanceDrafts.set(id,{value:appearanceFields(companion(id)),reset:false,pending:null,category:'body'});
  appearanceEditing=id;cancelIslandClose();agentsWorkspace();
}
function updateAppearancePreview() {
  const id=appearanceEditing,draft=appearanceDrafts.get(id);if(!draft)return;
  const row=(state.agentThreads??state.threads)[id]||{},value=draft.reset?C.companion(id):draft.value;
  const portrait=$('activity').querySelector('.agent-portrait');
  const key=JSON.stringify([value,row.status,row.context_compaction,state.connections]);
  if(portrait && portrait.dataset.preview!==key){
    const character=avatar(id,row,()=>{},undefined,draft.reset?null:value);
    portrait.dataset.preview=key;portrait.dataset.companion=character.dataset.companion;portrait.dataset.state=character.dataset.state;portrait.dataset.eyes=character.dataset.eyes;portrait.style.cssText=character.style.cssText;
    portrait.replaceChildren(character.querySelector('.character'));
    const copy=$('activity').querySelector('.agent-identity-copy .companion-alias');if(copy)copy.textContent=value.name||'Tu compañero';
  }
  const save=$('activity').querySelector('[data-appearance-save]');if(save)save.disabled=!!draft.pending||!draft.value.name.trim();
}
const appearancePalette=[['Coral','#ff9e88'],['Menta','#81d7bd'],['Lila','#c1a0f0'],['Cielo','#96cfff'],['Miel','#e8c583'],['Rosa','#e9a9c1'],['Salvia','#b3c99b'],['Pizarra','#51698b'],['Crema','#eadbc3']];
function renderAppearanceEditor(detail,id) {
  const draft=appearanceDrafts.get(id),box=el('section','appearance-editor');box.dataset.thread=id;box.setAttribute('aria-label','Personalizar personaje');
  const heading=el('div','routing-heading');heading.append(icon('sliders-horizontal'),el('h3','','Personalizar personaje'));box.append(heading);
  const form=el('div','appearance-fields');
  const add=(label,key,type,options)=>{
    const wrap=el('label','appearance-field'),control=document.createElement(options?'select':'input');wrap.append(el('span','',label));wrap.dataset.field=key;
    if(options)for(const [value,text] of options){const option=el('option','',text);option.value=value;control.append(option);}
    else control.type=type;
    control.setAttribute('aria-label',label);control.dataset.appearanceField=key;control.disabled=!!draft.pending;
    if(type==='checkbox')control.checked=draft.value[key];else control.value=draft.value[key];
    if(key==='name'){control.maxLength=24;control.autocomplete='off';}
    if(type==='range'){control.min=16;control.max=27;control.step=1;}
    control.addEventListener('input',()=>{draft.reset=false;draft.value[key]=type==='checkbox'?control.checked:type==='range'?Number(control.value):control.value;updateAppearancePreview();});
    wrap.append(control);form.append(wrap);
  };
  const palette=(label,key)=>{
    const group=el('div','appearance-field appearance-palette');group.setAttribute('role','group');group.setAttribute('aria-label',label);
    group.append(el('span','',label));const swatches=el('div','appearance-swatches');
    for(const [name,color] of appearancePalette){
      const swatch=button('',()=>{draft.reset=false;draft.value[key]=color;for(const option of swatches.children)option.setAttribute('aria-pressed',String(option===swatch));updateAppearancePreview();},'appearance-swatch');
      swatch.style.backgroundColor=color;swatch.title=name;swatch.setAttribute('aria-label',name);swatch.setAttribute('aria-pressed',String(draft.value[key].toLowerCase()===color));swatch.disabled=!!draft.pending;swatches.append(swatch);
    }
    group.append(swatches);form.append(group);
  };
  const categories=[['body','Cuerpo'],['outfit','Ropa'],['glasses','Gafas'],['head','Cabeza'],['neck','Cuello'],['detail','Detalles']];
  const navigation=el('div','appearance-categories');navigation.setAttribute('role','group');navigation.setAttribute('aria-label','Categorías del personaje');
  const category=draft.category||'body';
  for(const [key,label] of categories){
    const item=button(label,()=>{draft.category=key;detail.replaceChildren();renderAppearanceEditor(detail,id);updateAppearancePreview();fitIsland();},'choice'+(category===key?' selected':''));
    item.setAttribute('aria-pressed',String(category===key));item.disabled=!!draft.pending;navigation.append(item);
  }
  box.append(navigation);
  if(category==='body'){
    add('Nombre del personaje','name','text');palette('Color del cuerpo','color');palette('Color de accesorios','accessoryColor');add('Redondez','roundness','range');
    add('Ojos','eyes',null,[['oval','Ovalados'],['round','Redondos']]);box.append(form);
  }else{
    const options=el('div','appearance-options');options.setAttribute('role','group');options.setAttribute('aria-label',categories.find(([key])=>key===category)[1]);
    for(const [value,label] of C.appearanceSlots[category]){
      const item=button('',()=>{draft.reset=false;draft.value[category]=value;detail.replaceChildren();renderAppearanceEditor(detail,id);updateAppearancePreview();fitIsland();},'appearance-option');
      item.setAttribute('aria-label',label);item.setAttribute('aria-pressed',String(draft.value[category]===value));item.dataset.appearanceChoice=value;item.disabled=!!draft.pending;
      const look={...draft.value,head:'none',glasses:'none',outfit:'none',neck:'none',detail:'none',[category]:value};
      const sample=avatar(id,{status:'active'},()=>{},undefined,look),art=sample.querySelector('.character');
      item.style.setProperty('--character',look.color);item.style.setProperty('--accessory',look.accessoryColor);item.append(art,el('span','',label));options.append(item);
    }
    box.append(options);
  }
  const actions=el('div','choices'),save=button(draft.pending?'Guardando…':'Guardar',()=>saveAppearance(id),'choice selected');save.dataset.appearanceSave='true';
  const cancel=button('Cancelar',()=>{appearanceDrafts.delete(id);appearanceEditing=null;agentsWorkspace();},'choice');
  const reset=button('Restaurar original',()=>{draft.value=appearanceFields(C.companion(id));draft.reset=true;detail.replaceChildren();renderAppearanceEditor(detail,id);updateAppearancePreview();fitIsland();},'choice');
  for(const node of [save,cancel,reset])node.disabled=!!draft.pending;actions.append(save,cancel,reset);box.append(actions);
  const status=el('p','small appearance-save-status',draft.error||'Vista previa · pulsa Guardar para aplicar.');status.setAttribute('aria-live','polite');box.append(status);detail.append(box);
}
function saveAppearance(id) {
  const draft=appearanceDrafts.get(id);if(!draft||draft.pending||state.readOnly||state.preview)return;
  draft.value.name=draft.value.name.trim();if(!draft.value.name)return;
  const request=Date.now()+'-'+(++appearanceRequest);draft.pending=request;draft.error='';
  const detail=$('activity').querySelector('.agent-workspace-detail');detail.replaceChildren();renderAppearanceEditor(detail,id);updateAppearancePreview();
  native({action:'appearance',thread:id,request,value:draft.reset?null:{...draft.value}});
  setTimeout(()=>{if(appearanceDrafts.get(id)?.pending===request)window.monitorAppearanceResult({thread:id,request,ok:false});},16000);
}
window.monitorAppearanceResult=result=>{
  const draft=appearanceDrafts.get(result?.thread);if(!draft||!draft.pending||draft.pending!==result.request)return;
  draft.pending=null;
  if(result.ok===true){
    state.appearances={...state.appearances};if(draft.reset)delete state.appearances[result.thread];else state.appearances[result.thread]={...draft.value};
    appearanceDrafts.delete(result.thread);if(appearanceEditing===result.thread)appearanceEditing=null;
    capsule();renderPage();
  }else{
    draft.error='No se confirmó el guardado. Tu diseño sigue aquí; puedes reintentar.';
    if(appearanceEditing===result.thread){const detail=$('activity').querySelector('.agent-workspace-detail');if(detail){detail.replaceChildren();renderAppearanceEditor(detail,result.thread);updateAppearancePreview();}}
  }
};
function agentsWorkspace() {
  const page=$('activity'),scroll=page.scrollTop,focused=document.activeElement?.dataset.agentControl;
  const pickerScroll=page.querySelector('.agent-picker')?.scrollLeft||0,pickerTop=page.querySelector('.agent-picker')?.scrollTop||0;
  const rows=state.agentThreads ?? state.threads;
  const ids=Object.keys(rows).filter(id=>rows[id].archived!==true && rows[id].isArchived!==true).sort((a,b)=>(Number(rows[b].updated)||0)-(Number(rows[a].updated)||0)||a.localeCompare(b));
  if(selectedWorkspaceAgent && !rows[selectedWorkspaceAgent])selectedWorkspaceAgent=null;
  const id=selectedWorkspaceAgent && ids.includes(selectedWorkspaceAgent)?selectedWorkspaceAgent:ids.includes(selectedAgent)?selectedAgent:ids[0];
  selectedWorkspaceAgent=id||null;
  if(appearanceEditing && appearanceEditing!==id)appearanceEditing=null;
  if(appearanceEditing===id && page.querySelector('.appearance-editor')?.dataset.thread===id){updateAppearancePreview();return;}
  page.replaceChildren();
  const workspace=el('div','agents-workspace'),heading=el('div','agents-heading');
  heading.append(el('h2','','Control por tarea'),el('span','small',ids.length+' '+(ids.length===1?'agente':'agentes')));
  workspace.append(heading);
  if(!id){workspace.append(el('p','empty',state.connections?'No hay tareas disponibles sin archivar.':'Conecta la integración desde Ajustes para ver tus tareas.'));page.append(workspace);fitIsland();return;}
  const layout=el('div','agents-layout'),sidebar=el('aside','agents-sidebar');sidebar.setAttribute('aria-label','Agente y selección de tarea');layout.append(sidebar);workspace.append(layout);
  const identity=companion(id),selectedRow=rows[id],visualState=C.companionState(selectedRow,!!state.connections);
  const identityHeader=el('div','agent-identity'),character=avatar(id,selectedRow,()=>{}),portrait=el('span','avatar agent-portrait'),identityCopy=el('div','agent-identity-copy');
  portrait.dataset.companion=character.dataset.companion;portrait.dataset.state=character.dataset.state;portrait.style.cssText=character.style.cssText;
  portrait.append(character.querySelector('.character'));portrait.setAttribute('aria-hidden','true');
  identityHeader.style.setProperty('--character',identity.color);
  identityCopy.append(el('span','companion-alias',identity.name),el('h3','',selectedRow.name||'Agente'));
  const identityActions=el('div','agent-identity-actions');identityActions.append(el('span','small',visualState.label));
  const customize=button('Personalizar',()=>openAppearance(id),'choice customize-character');customize.prepend(icon('sliders-horizontal'));customize.disabled=!!state.readOnly||!!state.preview;
  identityActions.append(customize);identityCopy.append(identityActions);
  identityHeader.append(portrait,identityCopy);sidebar.append(identityHeader);
  const picker=el('div','agent-picker');picker.setAttribute('aria-label','Elegir tarea');
  for(const key of ids){
    const row=rows[key],visual=C.companionState(row,!!state.connections),item=button('',()=>selectAgent(key),'agent-pick'+(key===id?' selected':''));
    item.dataset.agentControl='select:'+key;item.dataset.agent=key;item.style.setProperty('--character',companion(key).color);
    item.setAttribute('aria-pressed',String(key===id));
    const pickCopy=el('span','agent-pick-copy');pickCopy.append(el('span','',row.name||'Agente'),el('small','',row.catalog_only?'Sin actividad registrada':visual.label));
    item.append(el('i','agent-dot'),pickCopy);
    if(['waiting','error','offline'].includes(visual.kind)){const mark=el('span','agent-attention','!');mark.setAttribute('aria-label',visual.label);item.append(mark);}
    picker.append(item);
  }
  sidebar.append(picker);
  const row=rows[id],detail=el('section','agent-workspace-detail'),mode=el('div','routing-mode');
  detail.setAttribute('aria-label',row.name||'Agente');
  if(appearanceEditing===id){renderAppearanceEditor(detail,id);layout.append(detail);page.append(workspace);updateAppearancePreview();fitIsland();return;}
  const modeHeading=el('div','routing-heading');modeHeading.append(icon('route'),el('h3','','Quién elige el modelo'));
  mode.append(modeHeading);taskModeControls(mode,id,false);
  for(const [index,control] of [...mode.querySelectorAll('button')].entries())control.dataset.agentControl='mode:'+index;
  detail.append(mode);
  const visual=C.companionState(row,!!state.connections);
  let notice= !state.connections?'Sin conexión. Estos son los últimos datos recibidos.':
    visual.attentionLabel?visual.attentionLabel+'.':
    ['waiting','approval','question'].includes(visual.kind)?'Esta tarea espera tu respuesta en Desktop.':
    visual.kind==='error'?'Esta tarea ha registrado una incidencia. Consulta el historial para revisarla.':
    ['blocked','failed','rejected','unknown_after_timeout'].includes(row.phase_status)?phaseStatus(row.phase_status)+'. Consulta el historial para revisar el cambio.':null;
  if(notice){const alert=el('div','routing-attention');alert.append(icon('circle'),el('span','',notice));detail.append(alert);}
  livePipeline(detail,row);
  layout.append(detail);page.append(workspace);
  page.scrollTop=scroll;picker.scrollLeft=pickerScroll;picker.scrollTop=pickerTop;fitIsland();
  if(focused)[...page.querySelectorAll('[data-agent-control]')].find(node=>node.dataset.agentControl===focused)?.focus({preventScroll:true});
}
function activity() {
  if(currentTab==='activity'){agentsWorkspace();return;}
  const page=$('activity'),scroll=page.scrollTop,crewScroll=page.querySelector('.agent-crew')?.scrollLeft||0;
  const focused=page.contains(document.activeElement)?document.activeElement:null,focusedAgent=focused?.dataset.agent,focusedControl=focused?.classList.contains('detail-toggle')?'.detail-toggle':focused?.classList.contains('overview-quota')?'.overview-quota':null;
  page.replaceChildren();
  if(selectedAgent&&!state.threads[selectedAgent]){
    selectedAgent=null;
    if(currentTab==='activity'){showTab('home');return;}
  }
  const home=currentTab==='home',primary=home?el('div','home-primary'):page,others=home?el('aside','home-others'):page;
  if(home){const layout=el('div','home-layout');layout.append(primary,others);page.append(layout);others.setAttribute('aria-label','Otros agentes');}
  const entries=Object.entries(state.threads),heroId=companionHero(primary,entries);
  const rows=entries.filter(([,row])=>C.liveAgent(row));
  const ids=C.companionOrder(order,state.threads);
  const label=el('div','agent-list-heading');label.append(el(home?'strong':'span','',home?'Otros agentes':rows.length+' en curso'));
  if(heroId){const detailButton=button(agentDetailsOpen?'Volver a inicio':'Ver detalles',()=>{selectedAgent=heroId;selectedWorkspaceAgent=heroId;showTab(agentDetailsOpen?'home':'activity');},'detail-toggle');detailButton.setAttribute('aria-expanded',String(agentDetailsOpen));if(home){detailButton.classList.add('hero-details');detailButton.setAttribute('aria-label','Ver detalles del agente');detailButton.replaceChildren(icon('chevron-right'));primary.append(detailButton);}else label.append(detailButton);}
  others.append(label);
  const crew=el('div','agent-crew');crew.setAttribute('aria-label','Elegir agente');
  for(const id of ids) {
    if(home&&id===heroId)continue;
    const row=state.threads[id],identity=companion(id),visual=C.companionState(row,!!state.connections),card=button('',()=>selectAgent(id),'task-row'+(heroId===id?' selected':'')),copy=el('div','agent-copy');
    card.style.setProperty('--character',identity.color);card.dataset.status=C.contextGauge(row).compacting?'compacting':row.status||'unknown';
    card.setAttribute('aria-pressed',String(heroId===id));card.dataset.agent=id;
    const title=el('div','task-title',row.name||'Agente');title.title=row.name||id;
    copy.append(el('div','crew-name',identity.name),title,el('div','task-status',visual.label));
    const art=avatar(id,row,()=>{}),artHost=el('span');artHost.append(...art.childNodes);artHost.className=art.className;artHost.style.cssText=art.style.cssText;artHost.dataset.state=art.dataset.state;artHost.dataset.companion=art.dataset.companion;artHost.setAttribute('aria-hidden','true');
    card.setAttribute('aria-label',`${row.name||'Agente'} · ${visual.label} · ${C.model(C.setting(row,'model'))} · ${C.contextGauge(row).label}`);
    card.append(artHost,copy);crew.append(card);
  }
  if(crew.children.length)others.append(crew);
  else if(home)others.append(el('p','empty','No hay más agentes activos.'));
  if(!ids.length&&!state.connections)page.append(el('p','empty','Comprueba la conexión en Ajustes.'));
  refreshOverviewQuota();page.scrollTop=scroll;crew.scrollLeft=crewScroll;fitIsland();
  const restore=focusedAgent?([...crew.children].find(node=>node.dataset.agent===focusedAgent)||(heroId===focusedAgent?page.querySelector('.hero-character'):null)):focusedControl?page.querySelector(focusedControl):null;restore?.focus({preventScroll:true});
}
const fmt = n => Number(n||0).toLocaleString('es-ES');
const when = n => n ? new Date(n*1000).toLocaleString('es-ES',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : 'Fecha sin confirmar';
const engines = {rules:'Reglas',jev:'Jev',provider:'Proveedor retirado'};
function modelTone(node,value) {
  const family=C.family(value),tint=(C.models[family]||C.neutral)[0];
  node.dataset.modelFamily=family;node.style.setProperty('--agent-tint',tint);node.style.setProperty('--agent-wash',tint+'14');
}
function historyStatus(record) {
  const status=el('span','history-status'),failed=!!record.error_type||['error','failed'].includes(record.status);
  const kind=failed?'error':['completed','done'].includes(record.status)?'done':C.active(record.status)?'active':'idle';
  status.dataset.kind=kind;status.append(icon(kind==='done'?'circle-check':kind==='error'?'bug':kind==='active'?'play':'circle'),el('span','',record.status==='completed'?'Finalizada':C.status(record.status)));
  return status;
}
let historyQuery='',historyOffset=0,historyRenderKey='';
function historyViewKey(){return JSON.stringify([historyRevision,historyOverlayKey,state.readOnly,selectedDecision,selectedThread,historyQuery,historyOffset]);}
function renderHistory() {
  const searchFocus=document.activeElement?.id==='history-search',searchPosition=document.activeElement?.selectionStart;
  const page=$('history');
  if(historyRenderKey===historyViewKey()&&page.querySelector('.history-layout'))return;
  const previousScroll=page.querySelector('.history-list')?.scrollTop || 0;
  const previousDetail=page.querySelector('.history-detail'),detailScroll=previousDetail?.scrollTop || 0,previousId=previousDetail?.dataset.decision;
  const disclosures=new Map([...page.querySelectorAll('details[data-section]')].map(n=>[n.dataset.section,n.open]));
  const focusedRecord=document.activeElement?.dataset.historyRecord;
  page.replaceChildren();
  const detail=el('section','history-detail'),list=el('div','history-list'),sidebar=el('aside','history-sidebar'),layout=el('div','history-layout');
  detail.setAttribute('aria-label','Detalle del registro');sidebar.setAttribute('aria-label','Registros del historial');
  const top=el('div','history-heading');top.append(el('h2','','Historial'),el('span','small',fmt(history.length)+' registros'));page.append(top);
  const group=(label,key,open,build)=>{
    const node=el('details','history-group'),body=el('div','history-group-body');
    node.dataset.section=key;node.open=previousId===selectedDecision&&disclosures.has(key)?disclosures.get(key):open;
    let built=false;const fill=()=>{if(node.open&&!built){built=true;build(body);}};
    node.append(el('summary','',label),body);node.addEventListener('toggle',fill);detail.append(node);fill();
  };
  const chosen=history.find(d=>d.id===selectedDecision) || (selectedThread?history.find(d=>d.thread===selectedThread):null);if(chosen)selectedDecision=chosen.id;
  if(!chosen){const empty=el('div','history-empty');empty.append(icon('history'),el('h3','',history.length?'Cada decisión, en detalle':'Aún no hay registros'),el('p','small',history.length?'Selecciona un trabajo para consultar qué se registró y valorar la elección.':'Las decisiones aparecerán aquí cuando utilices el enrutamiento.'));detail.append(empty);}
  else {
    const summary=el('div','history-summary'),category=el('div','history-category'),meta=el('div','history-meta');
    const origin=({manual:'Elección manual',explicit:'Petición explícita',preserved:'Ajustes de Codex',agent:'Agente'})[chosen.source]||({jev:'Jev',rules:'Motor local'})[chosen.routing_engine];
    modelTone(summary,chosen.model);if(origin)category.append(icon('route'),el('span','',origin));
    meta.append(category,historyStatus(chosen));summary.append(meta,el('h2','',chosen.title || 'Tarea'),el('p','small',when(chosen.started || chosen.time)),el('span','history-model-label','Modelo elegido'),tags(chosen,true));detail.append(summary);
    historyMeasurements(detail,chosen);
    if(chosen.error_type)explanation(detail,'Incidencia registrada',C.errorLabel(chosen),'incident');
    if(chosen.inference_model_mismatch||chosen.inference_effort_mismatch)explanation(detail,'Diferencia registrada','La inferencia vinculada al turno difiere del modelo o esfuerzo esperado. Consulta el diagnóstico.','incident');
    const signals={retry:'Se detectó una petición de reintento posterior.',manual_override:'Se pidió otro modelo en un mensaje posterior.'};
    if(signals[chosen.signal])explanation(detail,'Seguimiento',signals[chosen.signal]);
    group('Valorar esta elección','quality',false,quality=>{
      for(const [aspect,label,key,glyph] of [['overall','Elección global','quality','clipboard-check'],['model','Modelo elegido','model_quality','network'],['effort','Razonamiento elegido','effort_quality','gauge']]){
        const row=el('div','quality-row'),heading=el('div','quality-heading'),title=el('h3'),options=el('div','choices quality-choices');
        title.append(icon(glyph),el('span','',label));heading.append(title);
        if(chosen[key]){const clear=productButton('',()=>native({action:'quality',id:chosen.id,thread:chosen.thread||'',aspect,value:''}),'quality-clear');clear.append(icon('x'));clear.setAttribute('aria-label','Quitar valoración: '+label);clear.title='Quitar valoración';heading.append(clear);}
        options.setAttribute('role','group');options.setAttribute('aria-label',label);
        for(const [value,choiceLabel] of [['insufficient','Insuficiente'],['adequate','Adecuada'],['excessive','Excesiva']]){
          const selected=chosen[key]===value,choice=productButton('',()=>native({action:'quality',id:chosen.id,thread:chosen.thread||'',aspect,value:selected?'':value}),'choice rating-choice'+(selected?' selected':''));
          choice.dataset.rating=value;choice.setAttribute('aria-pressed',String(selected));if(selected)choice.append(icon('check'));choice.append(el('span','',choiceLabel));options.append(choice);
        }
        row.append(heading,options);quality.append(row);
      }
    });

    const evidence=historyEvidence(chosen);
    const comparisons=Object.values(chosen.comparisons||{}).filter(c=>c.engine_active===false||c.engine_failure||c.engine_status&&c.engine_status!=='ok');
    const estimates=Object.values(chosen.usage_estimates||{}).filter(s=>Number.isFinite(s.credits)&&s.credits>=0);
    if(evidence.settings.length||evidence.phases.length||evidence.samples.length||chosen.prior_inferences?.length||comparisons.length||estimates.length){
      group('Diagnóstico','diagnostics',false,diagnostics=>{
        executionEvidence(diagnostics,chosen,evidence);
        if(comparisons.length)explanation(diagnostics,'Comparaciones e incidencias del selector',comparisons.map(c=>{
          const role=c.engine_active===false?'comparación':'intento';
          const failure={account_access_restricted:'acceso restringido',circuit_open:'en pausa por fallos',route_outside_policy:'propuesta fuera de los límites'}[c.engine_failure]||c.engine_failure;
          const result=c.engine_status==='ok'?'respuesta recibida':[c.engine_status,failure].filter(Boolean).join(' · ')||'sin resultado registrado';
          return `${engines[c.routing_engine]||c.routing_engine} · ${role}${c.proposed_model?' → '+C.model(c.proposed_model):''}${c.proposed_effort?' · '+(C.efforts[c.proposed_effort]||c.proposed_effort):''} · ${result}`;
        }).join('\n'));
        if(estimates.length)explanation(diagnostics,'Equivalente Standard estimado',estimates.reduce((n,s)=>n+s.credits,0).toFixed(4)+' créditos Codex'+(estimates.every(s=>Number.isFinite(s.usd)&&s.usd>=0)?' · $'+estimates.reduce((n,s)=>n+s.usd,0).toFixed(6)+' API':'')+'. Estimación de inferencias con uso completo; no es el coste facturado ni el consumo de tu suscripción.');
      });
    }
  }

  const query=historyQuery.toLocaleLowerCase();
  const filtered=query?history.filter(d=>{
    let text=historySearchText.get(d);
    if(text===undefined){text=[d.title,C.model(d.model),C.efforts[d.effort],engines[d.routing_engine],C.status(d.status)].join(' ').toLocaleLowerCase();historySearchText.set(d,text);}
    return text.includes(query);
  }):history;
  historyOffset=Math.min(historyOffset,Math.max(0,Math.floor((filtered.length-1)/40)*40));
  for(const record of filtered.slice(historyOffset,historyOffset+40)) {
    const row=button('',()=>{selectedDecision=record.id;selectedThread=record.thread;renderHistory();},'history-row'+(record.id===selectedDecision?' selected':''));
    modelTone(row,record.model);row.dataset.historyRecord=record.id;row.setAttribute('aria-pressed',String(record.id===selectedDecision));
    const copy=el('div','history-copy'),title=el('div','task-title',record.title || 'Tarea');title.title=record.title || 'Tarea';copy.append(title,el('div','small',when(record.started||record.time)));row.append(copy,tags(record,true),historyStatus(record));list.append(row);
  }
  const search=el('input','history-search');search.id='history-search';search.type='search';search.placeholder='Buscar registros…';search.setAttribute('aria-label','Buscar por tarea, modelo, motor o estado');search.value=historyQuery;
  search.oninput=()=>{historyQuery=search.value;historyOffset=0;renderHistory();};
  const pagination=el('div','choices history-pagination');if(historyOffset)pagination.append(button('Anterior',()=>{historyOffset-=40;renderHistory();},'choice'));
  pagination.append(el('span','small',filtered.length?`${historyOffset+1}–${Math.min(historyOffset+40,filtered.length)} de ${filtered.length}`:'Sin coincidencias'));
  if(historyOffset+40<filtered.length)pagination.append(button('Siguiente',()=>{historyOffset+=40;renderHistory();},'choice'));
  if(!filtered.length)list.append(el('p','history-no-results small',historyQuery?'No hay registros que coincidan con tu búsqueda.':'Todavía no hay decisiones registradas.'));
  detail.dataset.decision=chosen?.id || '';const searchBox=el('div','history-search-box');searchBox.append(icon('search'),search);sidebar.append(searchBox,list,pagination);layout.append(sidebar,detail);page.append(layout);list.scrollTop=previousScroll;
  if(focusedRecord)[...list.children].find(n=>n.dataset.historyRecord===focusedRecord)?.focus({preventScroll:true});
  if(searchFocus){search.focus();if(searchPosition!==null)search.setSelectionRange(searchPosition,searchPosition);}
  if(previousId===chosen?.id)detail.scrollTop=detailScroll;
  historyRenderKey=historyViewKey();
}
function metric(parent,label,value,ratio=1,color='var(--accent)') {
  const box=el('div','metric'),line=el('div','metric-line'),number=el('span','metric-value',value);number.style.color=color;
  line.append(el('span','',label),number);if(parent.classList.contains('diagnostic-content')){box.append(line);parent.append(box);return;}const meter=el('div','meter'),fill=el('span');fill.style.width=Math.max(0,Math.min(1,ratio))*100+'%';fill.style.background=color;meter.append(fill);box.append(line,meter);parent.append(box);
}
function heading(parent,label){parent.append(el('h3','heading',label));}
function breakdown(parent,label,items,getKey,colors={}) {
  if(label)heading(parent,label);const counts={};for(const item of items){const key=getKey(item);if(key)counts[key]=(counts[key]||0)+1;}
  const max=Math.max(1,...Object.values(counts));for(const [key,count] of Object.entries(counts).sort((a,b)=>b[1]-a[1]))metric(parent,key,fmt(count),count/max,colors[key]?.[0] || colors[C.family(key)]?.[0] || C.neutral[0]);
  if(!Object.keys(counts).length)parent.append(el('p','','Sin datos todavía'));
}
function selectConsumptionSection(value) {
  consumptionSection=value;
  for(const group of $('statistics').querySelectorAll('[data-consumption-group]'))group.hidden=group.dataset.consumptionGroup!==value;
  for(const control of $('statistics').querySelectorAll('[data-consumption-section]')){const selected=control.dataset.consumptionSection===value;control.setAttribute('aria-pressed',String(selected));control.classList.toggle('selected',selected);}
  fitIsland();
}
function statistics() {
  const page=$('statistics'),scroll=page.scrollTop,diagnosticsOpen=!!page.querySelector('.consumption-diagnostics')?.open,scopeOpen=!!page.querySelector('.consumption-scope')?.open;page.replaceChildren();
  const summary=el('div','consumption-summary'),header=el('div','workspace-heading');header.append(el('h2','','Consumo'));
  const telemetry=state.telemetry||{},capture=!state.config.inference_telemetry?'Desactivada':!telemetry.enabled?'Reinicio pendiente':telemetry.requests?'Datos recibidos':'Sin registros';
  header.append(el('span','telemetry-status'+(telemetry.enabled?' enabled':''),'Telemetría · '+capture));summary.append(header);page.append(summary);
  const quota=el('section','consumption-quota');quota.append(el('h3','content-heading','Cuota disponible'));quotaSection(quota);summary.append(quota);
  const samples=history.map(d=>({d,usage:C.usageSample(d)})).filter(x=>x.usage.total!==null),totalTokens=samples.reduce((n,x)=>n+x.usage.total,0);
  const readings=el('div','consumption-readings'),tokens=el('div'),coverage=el('div');
  tokens.append(el('span','small','Tokens registrados'),el('div','consumption-total',samples.length?fmt(totalTokens):'—'));
  coverage.append(el('span','small','Decisiones con medición'),el('div','consumption-coverage',samples.length+' / '+history.length));readings.append(tokens,coverage);summary.append(readings);
  const byModel={};for(const {d,usage} of samples){const label=d.model?C.model(d.model):'Sin confirmar';byModel[label]??={tokens:0,model:d.model};byModel[label].tokens+=usage.total;}
  const models=el('section','consumption-models');models.append(el('h3','content-heading','Por modelo elegido'));
  for(const [label,{tokens,model}] of Object.entries(byModel).sort((a,b)=>b[1].tokens-a[1].tokens)){
    const row=el('div','consumption-model'),line=el('div','metric-line'),value=el('span','metric-value',fmt(tokens));line.append(model?badge(model):el('span','small',label),value);
    const track=el('div','meter'),fill=el('span');fill.style.width=tokens/(totalTokens||1)*100+'%';fill.style.background=C.models[C.family(model)]?.[0]||'var(--muted)';track.append(fill);row.append(line,track);models.append(row);
  }
  if(!samples.length)models.append(el('p','small','Todavía no hay mediciones completas.'));summary.append(models);
  const scope=el('details','consumption-scope');scope.open=scopeOpen;scope.append(el('summary','','Qué incluyen estos datos'),el('p','small',`Última llamada por decisión · historial acumulado. Coste facturado: no disponible. Estos tokens no equivalen al consumo de cuota de la suscripción. Agrupar por modelo elegido no confirma el modelo de cada inferencia.`));summary.append(scope);
  if(telemetry.invalid_requests)summary.append(el('p','warning telemetry-alert',fmt(telemetry.invalid_requests)+' lotes rechazados · acumulado. Ver Telemetría en Diagnósticos.'));
  const diagnostics=el('details','consumption-diagnostics'),content=el('div','diagnostic-content');diagnostics.open=diagnosticsOpen;diagnostics.append(el('summary','','Diagnósticos'),content);page.append(diagnostics);
  content.append(el('h2','','Resumen de decisiones'),el('p','','Historial acumulado · se conserva entre sesiones'));
  heading(content,'VERSIONES Y CALIDAD');
  for(const version of [...new Set(history.map(d=>d.product_version || 'Anterior'))]){
    const sample=history.filter(d=>(d.product_version || 'Anterior')===version),rated=sample.filter(d=>d.quality),good=rated.filter(d=>d.quality==='adequate');
    metric(content,version+' · decisiones',sample.length+' · '+rated.length+' valoradas',sample.length/(history.length||1));
    if(rated.length)metric(content,version+' · adecuadas',good.length+' / '+rated.length,good.length/rated.length,'var(--good)');
  }
  content.append(el('p','small','Valoraciones subjetivas con su muestra; disponibilidad y acuerdo entre motores no prueban calidad. Los registros anteriores no confirman una versión.'));
  heading(content,'ENRUTAMIENTO');
  const total=history.length,accepted=history.filter(d=>d.accepted).length,errors=history.filter(d=>d.error_type||['error','failed'].includes(d.status)).length,retries=history.filter(d=>d.signal==='retry').length;
  metric(content,'Decisiones con historial',fmt(total),total?1:0);metric(content,'Envíos aceptados · acumulado',fmt(accepted),accepted/(total||1));
  metric(content,'Incidencias registradas',fmt(errors),errors/(total||1),errors?'var(--warning)':'var(--good)');metric(content,'Reintentos registrados',fmt(retries),retries/(total||1),'var(--good)');
  heading(content,'FASES DE EJECUCIÓN');
  const phaseLabels={proposed:'Propuestas',accepted:'Aceptadas por Codex',active:'Activas',observed:'Inferencias observadas',completed:'Completadas',blocked:'Bloqueadas',failed:'Con incidencia'};
  const phaseRows=history.filter(d=>d.phase_status);
  if(!phaseRows.length)content.append(el('p','','Todavía no hay estados de fase registrados'));
  else for(const [key,label] of Object.entries(phaseLabels)){const count=phaseRows.filter(d=>d.phase_status===key).length;if(count)metric(content,label,fmt(count),count/phaseRows.length,key==='blocked'||key==='failed'?'var(--warning)':'var(--accent)');}
  const configured=history.filter(d=>d.configured_model).length,observed=history.filter(d=>d.observed_model&&d.evidence_confidence==='confirmed').length;
  metric(content,'Configuraciones publicadas',fmt(configured),configured/(total||1),'var(--good)');
  metric(content,'Inferencias confirmadas localmente',fmt(observed),observed/(total||1),observed?'var(--good)':'var(--muted)');
  metric(content,'Coincidencias sin ID de turno',fmt(state.telemetry?.telemetry_probable || 0),1,'var(--muted)');
  heading(content,'TELEMETRÍA LOCAL');
  if(!state.config.inference_telemetry)content.append(el('p','','Desactivada en Ajustes.'));
  else if(!telemetry.enabled)content.append(el('p','warning','Pendiente de reiniciar Desktop para abrir el receptor local.'));
  else {
    const receiving=(telemetry.requests||0)>0;
    metric(content,'Receptor local',receiving?'Recibiendo':'Abierto · sin datos',receiving?1:0,receiving?'var(--good)':'var(--warning)');
    metric(content,'Solicitudes procesadas',fmt(telemetry.requests),Math.min(1,(telemetry.requests||0)/(total||1)));
    metric(content,'Registros con modelo',fmt(telemetry.eligible_records),Math.min(1,(telemetry.eligible_records||0)/Math.max(1,telemetry.records_scanned||0)));
    metric(content,'Finalizaciones exportadas',fmt(telemetry.completion_records),Math.min(1,(telemetry.completion_records||0)/Math.max(1,telemetry.eligible_records||0)));
    metric(content,'Finalizaciones recibidas',fmt(telemetry.telemetry_events),Math.min(1,(telemetry.telemetry_events||0)/Math.max(1,telemetry.eligible_records||0)));
    metric(content,'Inferencias asociadas',fmt(telemetry.telemetry_confirmed),Math.min(1,(telemetry.telemetry_confirmed||0)/Math.max(1,telemetry.telemetry_events||0)),'var(--good)');
    content.append(el('p','small','Diagnósticos por etapa; un evento puede contar en varios motivos.'));
    for(const [key,label] of [['telemetry_missing_thread_id','Sin ID de chat'],['telemetry_missing_turn_id','Sin ID de turno'],['telemetry_missing_timestamp','Sin fecha nativa'],['telemetry_duplicates','Eventos duplicados'],['telemetry_unknown_thread','Chat desconocido'],['telemetry_turn_mismatch','Turno distinto'],['telemetry_stale','Fuera de plazo'],['telemetry_invalid_timestamp','Fecha nativa inválida'],['telemetry_missing_model','Sin modelo nativo'],['telemetry_inactive','Turno inactivo'],['telemetry_no_candidate','Sin turno candidato'],['telemetry_ambiguous','Atribución ambigua'],['telemetry_model_mismatch','Modelo distinto del esperado'],['telemetry_effort_mismatch','Esfuerzo distinto del esperado']])
      if(telemetry[key])content.append(el('p','',`${label}: ${fmt(telemetry[key])}.`));
    const invalid=telemetry.invalid_requests||0;
    metric(content,'Incidencias del receptor',fmt(invalid),invalid?1:0,invalid?'var(--warning)':'var(--good)');
    if(invalid)content.append(el('p','warning',`Tamaño ${fmt(telemetry.invalid_size)} · codificación ${fmt(telemetry.invalid_encoding)} · carga ${fmt(telemetry.invalid_payload)} · E/S ${fmt(telemetry.invalid_io)}.`));
    if(telemetry.invalid_size)content.append(el('p','warning',`Lotes rechazados por tamaño: recibido ${fmt(telemetry.invalid_wire_size)} · descomprimido ${fmt(telemetry.invalid_decoded_size)}. La captura está incompleta.`));
    if(telemetry.invalid_length)content.append(el('p','warning',`Longitud o formato HTTP no admitido: ${fmt(telemetry.invalid_length)}.`));
    if(telemetry.processing_busy)content.append(el('p','warning',`Lotes rechazados por procesamiento ocupado: ${fmt(telemetry.processing_busy)}.`));
    for(const [stage,label] of [['wire','Tamaño recibido'],['decoded','Tamaño descomprimido']]) {
      if(['512k','1m','4m','16m','over16m'].some(bin=>telemetry[`size_${stage}_${bin}`]))
        content.append(el('p','',`${label} · ≤512 KiB: ${fmt(telemetry[`size_${stage}_512k`])} · 512 KiB–1 MiB: ${fmt(telemetry[`size_${stage}_1m`])} · 1–4 MiB: ${fmt(telemetry[`size_${stage}_4m`])} · 4–16 MiB: ${fmt(telemetry[`size_${stage}_16m`])} · >16 MiB: ${fmt(telemetry[`size_${stage}_over16m`])}.`));
    }
    if(telemetry.rejected_connections)content.append(el('p','warning',`Conexiones rechazadas por capacidad: ${fmt(telemetry.rejected_connections)}.`));
    if(!receiving)content.append(el('p','warning','El receptor está abierto, pero no recibe eventos. Esto no significa que no haya agentes trabajando.'));
    else if(!(telemetry.eligible_records||0))content.append(el('p','warning','Se recibieron eventos sin modelo utilizable; no se conserva su contenido.'));
  }
  heading(content,'CAMBIOS ENTRE FASES');
  const transitions={compatible_group:'Cambios compatibles',same_model:'Mismo modelo',blocked_astra_boundary:'Frontera de Astra',unknown_model:'Modelo desconocido',blocked_review_boundary:'Cambio requiere otro turno',unverified_transition:'Transición sin validar'};
  const transitionRows=history.filter(d=>d.phase_transition);
  if(transitionRows.length)for(const [key,label] of Object.entries(transitions)){const count=transitionRows.filter(d=>d.phase_transition===key).length;if(count)metric(content,label,fmt(count),count/transitionRows.length,key==='blocked_astra_boundary'?'var(--warning)':'var(--good)');}
  const estimates=history.flatMap(d=>Object.values(d.usage_estimates||{}));
  if(estimates.length) {
    heading(content,'ESTIMACIÓN STANDARD');
    content.append(el('p','',estimates.reduce((n,e)=>n+e.credits,0).toFixed(4)+' créditos equivalentes · '+fmt(estimates.length)+' inferencias con uso completo. Cobertura parcial; no es el consumo de tu suscripción. Fast y otros modos no se incluyen.'));
  }
  breakdown(content,'MODELOS',history,d=>d.model?C.model(d.model):'',C.models);breakdown(content,'RAZONAMIENTO',history,d=>C.efforts[d.effort],Object.fromEntries(Object.entries(C.efforts).map(([key,label])=>[label,C.effortColors[key]])));breakdown(content,'MOTOR DE ENRUTAMIENTO',history,d=>engines[d.routing_engine]);
  heading(content,'FIABILIDAD DE LOS MOTORES');
  const attempts=history.flatMap(d=>Object.values(d.comparisons));
  if(!attempts.length)content.append(el('p','','Sin clasificaciones externas registradas todavía'));
  for(const key of [...new Set(attempts.map(x=>x.routing_engine))]) {
    const rows=attempts.filter(x=>x.routing_engine===key),valid=rows.filter(x=>['ok','guardrail'].includes(x.engine_status)).length,label=engines[key]||key;
    metric(content,label+' · respuestas válidas',valid+' / '+rows.length,valid/rows.length);
    const latency=rows.filter(x=>x.engine_latency_ms>0);if(latency.length)metric(content,label+' · demora media',Math.round(latency.reduce((n,x)=>n+x.engine_latency_ms,0)/latency.length)+' ms');
    if(latency.length){const values=latency.map(x=>x.engine_latency_ms).sort((a,b)=>a-b);metric(content,label+' · latencia p50 / p95',Math.round(values[Math.ceil(values.length*.5)-1])+' / '+Math.round(values[Math.ceil(values.length*.95)-1])+' ms · n='+values.length);}
    const tokens=rows.reduce((n,x)=>n+(x.engine_input_tokens||0)+(x.engine_output_tokens||0),0);if(tokens)metric(content,label+' · tokens de clasificación',fmt(tokens));
    const confidence=rows.filter(x=>x.engine_confidence>0);if(confidence.length){const average=confidence.reduce((n,x)=>n+x.engine_confidence,0)/confidence.length;metric(content,label+' · confianza media',Math.round(average*100)+'%',average,'var(--good)');}
    const fallbacks=rows.filter(x=>x.engine_active&&x.engine_status!=='ok').length;if(fallbacks)metric(content,label+' · respaldo local',fmt(fallbacks),fallbacks/rows.length,'var(--warning)');
    const failures={};for(const x of rows)if(x.engine_failure)failures[x.engine_failure]=(failures[x.engine_failure]||0)+1;
    for(const [failure,count] of Object.entries(failures))metric(content,label+' · '+failure,fmt(count),count/rows.length,'var(--warning)');
  }
  const shadows=history.flatMap(d=>Object.values(d.comparisons).filter(x=>!x.engine_active&&x.engine_status==='ok').map(x=>({d,x})));
  if(shadows.length){heading(content,'COINCIDENCIA DE COMPARACIONES');const same=shadows.filter(({d,x})=>d.model===x.proposed_model&&d.effort===x.proposed_effort).length;metric(content,'Coinciden con la selección aplicada',same+' / '+shadows.length,same/shadows.length);}
  heading(content,'VALORACIÓN POR MOTOR APLICADO');const rated=history.filter(d=>d.quality);
  if(!rated.length)content.append(el('p','','Valora decisiones para comparar la calidad aplicada'));
  for(const key of [...new Set(rated.map(d=>d.routing_engine||'rules'))]){const rows=rated.filter(d=>(d.routing_engine||'rules')===key),good=rows.filter(d=>d.quality==='adequate').length;metric(content,(engines[key]||key)+' · adecuadas',good+' / '+rows.length,good/rows.length,'var(--good)');}
  heading(content,'VALORACIÓN DE LA ELECCIÓN');metric(content,'Decisiones valoradas',rated.length+' / '+total,rated.length/(total||1));breakdown(content,'',rated,d=>({insufficient:'Insuficiente',adequate:'Adecuada',excessive:'Excesiva'}[d.quality]));
  const modelRated=history.filter(d=>d.model_quality),effortRated=history.filter(d=>d.effort_quality);metric(content,'Modelos valorados',modelRated.length+' / '+total,modelRated.length/(total||1));metric(content,'Razonamientos valorados',effortRated.length+' / '+total,effortRated.length/(total||1));
  const input=history.reduce((n,d)=>n+(d.inputTokens||0),0),output=history.reduce((n,d)=>n+(d.outputTokens||0),0),cached=history.reduce((n,d)=>n+(d.cachedInputTokens||0),0);
  if(input+output){heading(content,'TOKENS · ÚLTIMA LLAMADA OBSERVADA POR REGISTRO');metric(content,'Entrada',fmt(input));metric(content,'Salida',fmt(output),output/(input||1),'var(--good)');metric(content,'Entrada en caché',fmt(cached),cached/(input||1),'var(--muted)');}
  const durations=history.filter(d=>d.started&&d.finished>=d.started);if(durations.length)metric(content,'Duración media',Math.round(durations.reduce((n,d)=>n+d.finished-d.started,0)/durations.length)+' s');
  content.append(el('p','small','Estos datos no demuestran ahorro de cuota ni calidad comparativa por sí solos.'));
  const navigation=el('div','diagnostic-navigation'),groups={};navigation.setAttribute('role','group');navigation.setAttribute('aria-label','Secciones de diagnósticos');
  for(const [key,label] of [['routing','Enrutamiento'],['telemetry','Telemetría'],['quality','Calidad'],['usage','Uso registrado']]){
    const control=button(label,()=>selectConsumptionSection(key),'choice');control.dataset.consumptionSection=key;navigation.append(control);
    const group=el('section','diagnostic-section');group.dataset.consumptionGroup=key;group.setAttribute('aria-label',label);groups[key]=group;
  }
  let group='routing';
  for(const node of [...content.children]){
    if(node.classList.contains('heading')){
      const text=node.textContent;
      if(text.includes('CALIDAD')||text.startsWith('VALORACIÓN'))group='quality';
      else if(text==='TELEMETRÍA LOCAL')group='telemetry';
      else if(text==='ESTIMACIÓN STANDARD'||text.startsWith('TOKENS ·'))group='usage';
      else group='routing';
    }
    groups[group].append(node);
  }
  content.append(navigation,...Object.values(groups));selectConsumptionSection(consumptionSection);page.scrollTop=scroll;
}
function actionCard(parent,title,description,action){const node=button('',action,'settings-action');node.disabled=!!state.readOnly || !!state.preview || !!connectionPending;node.append(el('strong','',title),el('span','',description),icon('chevron-right','ui-glyph action-affordance'));parent.append(node);return node;}
const connectionLabels={doctor:'Comprobando conexión…',install:'Conectando…',uninstall:'Desconectando…'};
function connectionControls() {
  for(const node of $('settings').querySelectorAll('.settings-action')) {
    node.disabled=!!state.readOnly || !!state.preview || !!connectionPending;
    if(!node.dataset.connectionAction)continue;
    const busy=node.dataset.connectionAction===connectionPending;
    node.classList.toggle('busy',busy);node.setAttribute('aria-busy',String(busy));
    node.querySelector('strong').textContent=busy?connectionLabels[connectionPending]:node.dataset.title;
    node.querySelector('span').textContent=busy?'La operación está en curso. Espera el resultado; puede tardar unos segundos.':node.dataset.description;
  }
}
function connectDesktop(value) {
  if(state.readOnly || connectionPending)return;
  connectionPending=value;connectionControls();$('feedback').textContent=connectionLabels[value];
  native({action:'connection',value});
}
function connectionCard(parent,value,title,description) {
  const node=actionCard(parent,title,description,()=>connectDesktop(value));
  Object.assign(node.dataset,{connectionAction:value,title,description});
  const spinner=el('i','action-spinner');spinner.setAttribute('aria-hidden','true');node.append(spinner);
  connectionControls();
}
function choices(parent,options,selected,action,disabled=[]) {const box=el('div','choices');for(const [key,label] of options){const chosen=Array.isArray(selected)?selected.includes(key):selected===key;const node=button('',()=>action(key),'choice'+(chosen?' selected':''));controlLabel(node,chosen?'circle-check':'circle',label);node.setAttribute('aria-pressed',String(chosen));node.disabled=!!state.readOnly || !!state.preview || disabled.includes(key);box.append(node);}parent.append(box);}
const configure = (key,value) => native({action:'config',key,value});
function keySettings(parent,id,label) {
  const ready=state.keys?.[id];
  const editor=el('div','key-editor');editor.hidden=true;
  actionCard(parent,ready?'Clave guardada de '+label:'Añadir clave de '+label,'Se guarda en '+(state.secretStorage||'el almacén seguro de este equipo')+'.',()=>{editor.hidden=!editor.hidden;input.value='';if(!editor.hidden)input.focus();});
  const input=el('input');input.type='password';input.disabled=!!state.readOnly||!!state.preview;input.autocomplete='off';input.setAttribute('aria-label','Clave API de '+label);
  input.dataset.keyId=id;
  editor.append(input);const actions=el('div','choices');actions.append(productButton('Guardar clave',()=>{const value=input.value.trim();if(!value)return;native({action:'secret',provider:id,value});input.value='';editor.hidden=true;},'choice'),button('Cancelar',()=>{input.value='';editor.hidden=true;},'choice'));editor.append(actions);parent.append(editor);
}
function refreshProductVersion() {
  if(!$('product-version'))return;
  const bridgeMismatch=(state.bridgeVersions||[]).filter(v=>v!==state.productVersion);
  $('product-version').textContent='v'+(state.productVersion || state.updates?.installedVersion || '—')+(bridgeMismatch.length?' · puente '+bridgeMismatch.join(', '):state.bridgeBuildMismatch?' · router anterior':state.bridgeBuildUnknown?' · puente sin verificar':'')+(state.restartRequired?' · reinicio pendiente':'');
  $('product-version').title=state.restartRequired?'Hay ajustes pendientes. Reinicia Desktop al terminar tus tareas para cargarlos.':(bridgeMismatch.length||state.bridgeBuildMismatch)?'La versión del router activo difiere de la incluida con este monitor. Reinicia Desktop al terminar tus tareas para cargar la versión instalada.':state.bridgeBuildUnknown?'El puente activo no informa su versión de componente. No se puede determinar si necesita reinicio; el próximo inicio de Desktop permitirá comprobarlo.':'Versión de Codex automático';
}
function refreshRoutingControl() {
  const node=$('pause');if(!node)return;
  node.disabled=!!state.readOnly||!!state.preview||!!connectionPending;
  node.querySelector('strong').replaceChildren(icon(state.config.enabled?'pause':'play'),document.createTextNode(state.config.enabled?'Pausar enrutamiento':'Activar enrutamiento'));
  node.querySelector('span').textContent=state.config.enabled?'El enrutador elige el modelo en cada nuevo mensaje.':'Se respeta la selección manual de Codex.';
}
function updateSettings(box) {
  const update=state.updates||{status:'idle',installedVersion:state.productVersion},busy=['checking','downloading','preparing_install','installing'].includes(update.status);
  heading(box,'ACTUALIZACIONES');
  const statuses={idle:'Sin comprobar',checking:'Comprobando…',available:'Nueva versión disponible',package_unavailable:'Hay una nueva versión; aún no hay instalador publicado para este equipo.',up_to_date:'No hay una versión estable más reciente.',downloading:'Descargando…',downloaded:update.canUpdate?'Descarga verificada. Puedes actualizar cuando quieras.':'Descarga verificada. La instalación desde la aplicación aún no está disponible.',preparing_install:'Preparando la actualización…',installing:'Instalando. El monitor se abrirá de nuevo automáticamente.',completed:'Actualización instalada.',rolled_back:'Se ha recuperado la versión anterior. Tus datos se conservan.',failed:'La actualización no se completó. Revisa la instalación antes de volver a intentarlo.',cancelled:'Operación cancelada.',error:'No se pudo completar la actualización.'};
  const errors={release_unavailable:'No hay una entrega pública accesible.',rate_limited:'GitHub ha limitado las comprobaciones. Vuelve a intentarlo más tarde.',network_error:'Comprueba tu conexión e inténtalo de nuevo.',invalid_release:'La entrega no tiene metadatos válidos para actualizar.',unsupported_platform:'No hay un instalador compatible con este equipo.',unsafe_download:'La dirección de descarga no es válida.',invalid_size:'El tamaño recibido no coincide con el publicado.',integrity_error:'La descarga no coincide con su huella publicada.'};
  Object.assign(errors,{missing_signature:'Esta entrega no incluye una firma verificable.',invalid_signature:'No se pudo verificar la firma de la actualización.',unknown_publisher:'Esta entrega está firmada por una clave desconocida.',signature_expired:'La firma de esta entrega ha caducado; comprueba si hay otra versión.',signature_target_mismatch:'La firma no corresponde a este instalador.',invalid_trust_store:'La instalación no tiene una lista de firmas válida.',signature_support_missing:'Esta instalación necesita el componente de verificación de firmas.',invalid_installation:'El paquete no contiene una aplicación compatible.',installation_read_only:'La aplicación está en una carpeta sin permiso de escritura para este usuario.',active_bridge:'Codex sigue usando esta instalación. Cierra Codex cuando terminen tus tareas y vuelve a actualizar.',launch_failed:'La nueva versión no pudo iniciarse. Se recuperará la versión anterior.'});
  const card=el('div','update-card'),version=el('span','', 'v'+(state.productVersion||update.installedVersion||'—'));const versionHeading=el('strong','','Versión instalada · ');versionHeading.append(version);card.append(versionHeading);
  if(update.latestVersion)card.append(el('p','small','Última estable · '+update.latestVersion));
  card.append(el('p','small',statuses[update.status]||statuses.idle));
  if(update.error)card.append(el('p','warning',errors[update.error]||errors.network_error));
  if(update.publisherVerified)card.append(el('p','small','Firma del proyecto verificada.'));
  if(update.checkedAt)card.append(el('p','small','Comprobado · '+new Date(update.checkedAt*1000).toLocaleString('es-ES')));
  if(update.status==='downloading'){
    const progress=el('progress');progress.max=100;progress.value=Number.isFinite(update.progress)?update.progress:0;progress.setAttribute('aria-label','Progreso de descarga');card.append(progress);
  }
  const actions=el('div','choices');
  const check=button('Comprobar ahora',()=>native({action:'update',value:'check'}),'choice');check.disabled=busy||!!state.preview||!!state.readOnly;actions.append(check);
  if(update.canUpdate){const install=button('Actualizar a '+update.latestVersion,()=>native({action:'update',value:'install'}),'choice');install.disabled=busy||!!state.preview||!!state.readOnly;actions.append(install);}
  else if(update.canDownload){const download=button('Descargar versión '+update.latestVersion,()=>native({action:'update',value:'download'}),'choice');download.disabled=busy||!!state.preview||!!state.readOnly;actions.append(download);}
  if(busy&&!update.shutdownForUpdate){const cancel=button('Cancelar',()=>native({action:'update',value:'cancel'}),'choice');cancel.disabled=!!state.preview||!!state.readOnly;actions.append(cancel);}
  card.append(actions);box.append(card);refreshProductVersion();
  actionCard(box,state.config.updates_auto_check?'Desactivar comprobación diaria':'Activar comprobación diaria','Consulta las versiones públicas de este repositorio en GitHub. No envía tus tareas ni tus ajustes; no instala automáticamente.',()=>configure('updates_auto_check',!state.config.updates_auto_check));
}
function selectSettingsSection(value) {
  settingsSection=value;
  for(const group of $('settings').querySelectorAll('[data-settings-group]'))group.hidden=group.dataset.settingsGroup!==value;
  for(const control of $('settings').querySelectorAll('[data-settings-section]')){const selected=control.dataset.settingsSection===value;control.setAttribute('aria-pressed',String(selected));control.classList.toggle('selected',selected);}
  fitIsland();
}
function settings() {
  const page=$('settings'),scroll=page.scrollTop,config=state.config,catalogOpen=!!page.querySelector('.icon-catalog')?.open;
  const drafts=new Map([...page.querySelectorAll('input[data-key-id]')].map(input=>[input.dataset.keyId,{value:input.value,open:!input.closest('.key-editor').hidden}]));
  const workspace=el('div','settings-workspace'),header=el('div','workspace-heading'),version=el('span','small'),brand=el('div','settings-brand'),brandImage=el('img');brandImage.src='codex.png';brandImage.alt='Codex Model Router';brandImage.width=32;brandImage.height=32;brand.append(brandImage,el('h2','','Ajustes'));version.id='product-version';header.append(brand,version);workspace.append(header);page.replaceChildren(workspace);
  actionCard(workspace,'','',()=>configure('enabled',!state.config.enabled));workspace.lastElementChild.id='pause';workspace.lastElementChild.classList.add('settings-master');refreshRoutingControl();
  const layout=el('div','settings-layout'),navigation=el('div','settings-navigation'),detail=el('div','settings-detail');navigation.setAttribute('role','group');navigation.setAttribute('aria-label','Secciones de ajustes');
  const groups={};
  for(const [key,label] of [['application','Aplicación'],['routing','Enrutamiento'],['data','Datos y privacidad'],['connection','Conexión']]){
    const item=button(label,()=>{selectSettingsSection(key);},'settings-nav-item');item.dataset.settingsSection=key;navigation.append(item);
    const group=el('section','settings-panel');group.dataset.settingsGroup=key;group.setAttribute('aria-label',label);group.append(el('h3','settings-panel-title',label));detail.append(group);groups[key]=group;
  }
  layout.append(navigation,detail);workspace.append(layout);
  let box=groups.application;
  actionCard(box,state.ui.topmost?'Desactivar Mantener delante':'Activar Mantener delante',state.ui.topmost?(state.platform==='linux'?'Solicita al escritorio mantener el monitor delante.':'El monitor permanece sobre otras ventanas.'):'El monitor puede quedar detrás de otras ventanas.',()=>native({action:'topmost',value:!state.ui.topmost}));
  if(state.platform==='linux' && state.desktopCapabilities?.positioning===false)box.append(el('p','small','El escritorio decide la posición y si mantiene el monitor delante. Puedes moverlo con el atajo de ventanas del sistema.'));
  updateSettings(box);
  const catalog=el('details','icon-catalog');catalog.open=catalogOpen;catalog.append(el('summary','','Tipos de tarea · '+Object.keys(C.identities).length+' tipos'));
  const icons=el('div','icon-catalog-grid');for(const [category,[label]] of Object.entries(C.identities)){
    const item=el('div');item.append(icon(C.identities[category][1],'glyph'),el('span','small',label));icons.append(item);
  }catalog.append(icons);box.append(catalog);
  box=groups.routing;
  heading(box,'FASES Y EVIDENCIA');
  box.append(el('p','small',config.phase_routing?'Cambios por fases habilitados. Las tareas nuevas usan checkpoints compatibles tras cargar la configuración.':'Los cambios por fases están desactivados. El modelo se elige entre turnos.'));
  actionCard(box,config.phase_routing?'Desactivar cambios automáticos por fases':'Activar cambios automáticos por fases',config.phase_routing?'Las tareas nuevas podrán cambiar modelo y esfuerzo en checkpoints amplios. Se aplica tras reiniciar Desktop.':'Mantiene el mismo modelo durante cada turno. Se aplica tras reiniciar Desktop.',()=>configure('phase_routing',!config.phase_routing));
  const engine=['rules','jev'].includes(config.routing_engine)?config.routing_engine:'rules';
  heading(box,'MOTOR DE ENRUTAMIENTO');choices(box,[['rules','Reglas'],['jev','Jev']],engine,v=>configure('routing_engine',v));
  box.append(el('p','small',engine==='rules'?'Las reglas locales deciden al instante sin enviar el mensaje a otro servicio.':'El clasificador recibe el mensaje de la tarea. Si falla o responde de forma inválida, se conservan las reglas locales. Puede consumir cuota del proveedor.'));
  heading(box,'COMPARACIÓN EN PARALELO');const comparisons=(config.comparison_engines||[]).filter(x=>['rules','jev'].includes(x));
  choices(box,[['rules','Reglas'],['jev','Jev']],[engine,...comparisons],key=>configure('comparison_engines',comparisons.includes(key)?comparisons.filter(x=>x!==key):[...comparisons,key]),[engine]);
  box.append(el('p','small','El motor activo ya se registra. Marca otros para comparar propuestas; las comparaciones externas también reciben el mensaje.'));
  if(engine==='jev'){
    const jev=config.jev||{},connection=jev.connection||'typesafe';heading(box,'CONEXIÓN DE JEV');
    choices(box,[['vercel','Vercel AI Gateway'],['typesafe','TypeSafe directo']],connection,v=>configure('jev.connection',v));
    box.append(el('p','small',connection==='vercel'?'Usa typesafe-ai/jev mediante Vercel AI Gateway. El acceso puede requerir créditos del proveedor.':'Conecta directamente con api.typesafe.ai usando jev-latest.'));
    keySettings(box,'jev-'+connection,connection==='vercel'?'Vercel AI Gateway':'TypeSafe');
    if(!state.keys?.['jev-'+connection])box.append(el('p','small','Cada conexión necesita su propia clave. Si guardaste una clave en una versión anterior, introdúcela aquí una vez para vincularla a este proveedor.'));
  }
  heading(box,'POLÍTICA ACTUAL');for(const [tier,description] of [['simple','Tareas delimitadas'],['normal','Cambios concretos'],['complex','Ingeniería compleja'],['critical','UX, auditorías y gran alcance']]){const route=config.routes?.[tier];if(route){const row=el('div','policy');row.append(badge(route.model),el('span','',description),badge(route.effort,true));box.append(row);}}
  box=groups.data;
  heading(box,'CONSERVAR HISTORIAL');choices(box,[[30,'30 días'],[90,'90 días'],[180,'180 días'],[0,'Siempre']],config.history_days??90,v=>configure('history_days',v));
  actionCard(box,config.inference_telemetry?'Desactivar telemetría local':'Activar telemetría local','Recoge evidencia del modelo ejecutado. Se aplica tras reiniciar Desktop.',()=>configure('inference_telemetry',!config.inference_telemetry));
  actionCard(box,config.prompt_logging?'Desactivar captura de prompts':'Activar captura de prompts',config.prompt_logging?'Guarda cada nuevo mensaje con su decisión para evaluar el enrutamiento. El cambio se aplica al siguiente mensaje.':'No guarda el texto de los mensajes; las estadísticas agregadas continúan disponibles.',()=>configure('prompt_logging',!config.prompt_logging));
  heading(box,'PRIVACIDAD');box.append(el('p','small',config.prompt_logging?'Además de las métricas, se guarda el texto de tus mensajes en el archivo local privado state/prompts.jsonl para evaluar las decisiones. No guarda respuestas, adjuntos, herramientas ni credenciales. Las claves se almacenan en '+(state.secretStorage || 'el llavero de macOS')+'.':'El historial guarda tareas, ajustes, motivos, estados y contadores. No guarda mensajes, respuestas, adjuntos, herramientas ni credenciales. Las claves se almacenan en '+(state.secretStorage || 'el llavero de macOS')+'.'));
  box=groups.connection;
    box.append(el('p','small','La instalación se detecta al arrancar. Conecta el inicio habitual una vez. Cerrar el monitor no detiene el selector.'));
  connectionCard(box,'doctor','Comprobar conexión','Distingue instalación, registro y conexión observada.');
  connectionCard(box,'install','Conectar al inicio habitual','Prepara el próximo arranque de Desktop. Puedes pulsarlo con tus tareas abiertas.');
  connectionCard(box,'uninstall','Desconectar integración','Restaura el inicio habitual sin borrar ajustes ni historial.');
  for(const input of page.querySelectorAll('input[data-key-id]')){const draft=drafts.get(input.dataset.keyId);if(draft){input.value=draft.value;input.closest('.key-editor').hidden=!draft.open;}}
  selectSettingsSection(settingsSection);refreshProductVersion();page.scrollTop=scroll;
}

function renderPage(){
  if(state.ui.mode!=='Expanded')return;
  fitIsland();
  if(currentTab==='history' || currentTab==='statistics') {
    if(state.ui.lazyHistory && !state.historyLoaded){
      $(currentTab).replaceChildren(el('p','empty','Cargando historial…'));return;
    }
    ensureHistory();
  }
  if(currentTab==='home'||currentTab==='activity')activity();else if(currentTab==='history')renderHistory();else if(currentTab==='statistics')statistics();else settings();
}
window.receive = incoming => {
  const oldReadOnly=state.readOnly,oldPreview=state.preview,oldConfig=JSON.stringify(state.config),oldUi=JSON.stringify(state.ui),oldUpdates=JSON.stringify(state.updates);
  if(incoming.history){historyRevision++;historyDirty=true;incoming={...incoming,historyLoaded:true};}
  if(incoming.threads)historyDirty=true;
  const staleMode=state.ui.acknowledgesMode && Number.isInteger(incoming.ui?.modeRequest) && incoming.ui.modeRequest<modeRequest;
  if((pendingModeRequest || staleMode) && incoming.ui)incoming={...incoming,ui:{...incoming.ui,mode:state.ui.mode}};
  state={...state,...incoming,ui:{...state.ui,...incoming.ui}};
  cameraLayout();
  if(!heightDrag && Number.isFinite(state.ui.panelHeight))panelHeight(state.ui.panelHeight-16);
  document.body.classList.toggle('reduced',!!state.ui.reduced);
  if(!document.body.classList.contains(state.ui.mode.toLowerCase()))setMode(state.ui.mode,false);
  const active=Object.values(state.threads).filter(row=>C.liveAgent(row)).length;
  $('connection').classList.toggle('sr-only',!state.preview&&!state.readOnly);$('connection').querySelector('span').textContent=state.preview?'Vista previa · datos simulados':state.readOnly?'Vista previa · datos reales · solo lectura':state.connections?`${active} ${active===1?'tarea activa':'tareas activas'}`:state.desktopRestartPending?'Conexión preparada · reinicia Desktop':'Sin conexión';$('connection').querySelector('i').classList.toggle('working',active>0);
  refreshProductVersion();
  refreshRoutingControl();
  capsule();
  refreshQuota();
  document.body.classList.toggle('native-glass',!!state.ui.nativeGlass);
  document.body.classList.toggle('reduce-transparency',!!state.ui.reduceTransparency);
  const signature=JSON.stringify([state.readOnly,state.threads,state.agentThreads,historyRevision,state.historyLoaded,state.connections,state.taskModes,state.appearances,state.telemetry,state.accountUsage]);
  const accessChanged=oldReadOnly!==state.readOnly||oldPreview!==state.preview;
  const settingsChanged=accessChanged || oldConfig!==JSON.stringify(state.config) || oldUi!==JSON.stringify(state.ui) || oldUpdates!==JSON.stringify(state.updates);
  if(signature!==dataSignature || settingsChanged){
    dataSignature=signature;
    // Do not discard an API key while the owner is typing it.
    if(currentTab!=='settings' || (settingsChanged && (accessChanged || document.activeElement?.type!=='password')))renderPage();
  }
};

document.addEventListener('visibilitychange',()=>document.body.classList.toggle('motion-hidden',document.hidden));
window.receiveUI = (ui,request=ui.modeRequest ?? null) => {
  if(pendingModeRequest && request!==pendingModeRequest)return;
  if(Number.isInteger(request) && request<modeRequest)return;
  pendingModeRequest=0;state.ui={...state.ui,...ui};
  cameraLayout();capsule();fitIsland();
  document.body.classList.toggle('native-glass',!!state.ui.nativeGlass);document.body.classList.toggle('reduce-transparency',!!state.ui.reduceTransparency);
  if(!heightDrag && Number.isFinite(ui.panelHeight))panelHeight(ui.panelHeight-16);
  if(ui.mode!==undefined && !document.body.classList.contains(ui.mode.toLowerCase()))setMode(ui.mode,false);
  window.monitorBounds();
};
function clearNativeHover() {
  nativeHover?.classList.remove('native-hover');nativeHover=null;
}
window.monitorPointer = (point,inactive=true) => {
  if(!inactive){clearNativeHover();return;}
  // Bounds changes can replace the hit target under a stationary cursor.
  // Only actual pointer movement releases an Escape dismissal.
  if(point){
    if(!lastHoverPoint || point.x!==lastHoverPoint.x || point.y!==lastHoverPoint.y)peekDismissed=false;
    lastHoverPoint={x:point.x,y:point.y};
  }
  const target=point && state.ui.mode!=='Hidden' ? document.elementFromPoint(point.x,point.y) : null;
  islandPointer(!!target?.closest('#surface'));
  const button=target?.closest('button');
  if(button!==nativeHover){clearNativeHover();nativeHover=button;button?.classList.add('native-hover');}
  if(state.ui.mode==='Compact') {
    if(target?.closest('#compact'))cancelPeekClose();
    else schedulePeekClose();
    if(button?.id==='quota' && !quotaOpen)openQuota();
    if(button?.classList.contains('avatar')) {
      const id=[...avatars].find(([,node])=>node===button)?.[0];
      if(id && peekId!==id)openPeek(id);
    }
  }
};
let feedbackTimer;
window.monitorConnectionState = status => { connectionPending=status.pending?status.value:null;connectionControls(); };
window.monitorFeedback = text => { if(!state.ui.connectionProgress){connectionPending=null;connectionControls();}clearTimeout(feedbackTimer);$('feedback').textContent=text;feedbackTimer=setTimeout(()=>{$('feedback').textContent='';},7000); };
$('compact-summary').onclick=()=>setMode('Expanded');
$('expand').onclick=()=>setMode('Expanded');
$('quota').onclick=()=>openQuota(true);
$('quota').addEventListener('mouseenter',()=>openQuota());$('quota').addEventListener('focus',()=>openQuota(true));
window.addEventListener('resize',()=>{cameraLayout();capsule();fitIsland();window.monitorBounds();});
setInterval(refreshQuota,2000);
for(const node of document.querySelectorAll('[data-tab]'))node.onclick=()=>showTab(node.dataset.tab);
$('compact').addEventListener('mouseenter',cancelPeekClose);$('compact').addEventListener('mouseleave',schedulePeekClose);
document.documentElement.addEventListener('mouseleave',()=>{schedulePeekClose();islandPointer(false);});
$('surface').addEventListener('mouseenter',()=>islandPointer(true));
$('surface').addEventListener('mouseleave',()=>islandPointer(false));
$('compact').addEventListener('focusout',event=>{if(!$('compact').contains(event.relatedTarget))schedulePeekClose();});
$('compact').addEventListener('pointermove',event=>{
  if(event.movementX||event.movementY){peekDismissed=false;window.monitorPointer({x:event.clientX,y:event.clientY});}
});
document.addEventListener('keydown',event=>{if(event.key==='Escape'){if(peekId||quotaOpen){peekDismissed=true;closePeek();}else setMode('Compact');}});
let boundsFrame=0;
window.monitorBounds=()=>{
  cancelAnimationFrame(boundsFrame);
  boundsFrame=requestAnimationFrame(()=>{
    boundsFrame=0;
    const r=$('surface').getBoundingClientRect();
    native({action:'bounds',x:r.x,y:r.y,width:r.width,height:r.height});
  });
};
new ResizeObserver(window.monitorBounds).observe($('surface'));
const contentObserver=new ResizeObserver(fitIsland);
for(const node of [$('activity'),$('statistics'),$('settings'),document.querySelector('nav'),$('notices')])contentObserver.observe(node);
for(const node of document.querySelectorAll('[data-icon]'))node.replaceChildren(icon(node.dataset.icon));
native({action:'ready'});
