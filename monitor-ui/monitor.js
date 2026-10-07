'use strict';
const C = MonitorCore, $ = id => document.getElementById(id);
let state = {threads:{},history:[],config:{enabled:true},ui:{mode:'Compact',topmost:true},connections:0};
let currentTab = 'activity', order = [], selectedDecision = null, selectedThread = null, peekId = null, peekTimer, reasonOpen = false;
let dataSignature = '', history = [], avatars = new Map(), orbitSequence = 0;
let selectedAgent = null;
let quotaOpen = false, nativeHover = null, modeRequest = 0, pendingModeRequest = 0;
let historyDirty = true, historyRevision = 0;
let connectionPending = null;
function requestHistory() {
  if(state.ui.lazyHistory)native({action:'history',value:state.ui.mode==='Expanded' && ['history','statistics'].includes(currentTab)});
}
function ensureHistory() {
  if(historyDirty){history=C.decisions(state.history,state.threads);historyDirty=false;}
}
function selectAgent(id) {
  selectedAgent=selectedAgent===id?null:id;reasonOpen=false;activity();
  $('activity').querySelector('.agent-detail')?.scrollIntoView({block:'nearest'});
}
const native = message => {
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
  heightGrip.setPointerCapture(event.pointerId);document.body.classList.add('resizing');
  native({action:'resizeStart'});event.preventDefault();
});
heightGrip.addEventListener('pointermove',event=>{
  if(heightDrag)panelHeight(heightDrag.height+heightDrag.y-event.screenY);
});
function finishHeightDrag() {
  if(!heightDrag)return;
  const height=$('surface').getBoundingClientRect().height+16;
  heightDrag=null;document.body.classList.remove('resizing');
  native({action:'resizeEnd',height});
}
heightGrip.addEventListener('pointerup',finishHeightDrag);
heightGrip.addEventListener('pointercancel',finishHeightDrag);
heightGrip.addEventListener('lostpointercapture',finishHeightDrag);
heightGrip.addEventListener('dblclick',()=>{native({action:'resizeReset'});});
heightGrip.addEventListener('keydown',event=>{
  if(event.key==='Home'){native({action:'resizeReset'});event.preventDefault();}
  if(event.key==='ArrowUp'||event.key==='ArrowDown'){
    const height=panelHeight($('surface').getBoundingClientRect().height+(event.key==='ArrowUp'?24:-24));
    native({action:'resizeEnd',height:height+16});event.preventDefault();
  }
});
const el = (tag, cls, text) => { const node = document.createElement(tag); if(cls) node.className=cls; if(text !== undefined) node.textContent=String(text); return node; };
function button(text, action, cls='') { const node=el('button',cls,text);node.addEventListener('click',action);return node; }
function palette(node, colors) {node.style.setProperty('--tint',colors[0]);node.style.setProperty('--face',colors[1]);return node;}
function badge(value, effort=false) { const label=effort ? C.efforts[value] || 'Sin confirmar' : C.model(value);const node=palette(el('span','badge',label), effort ? C.effortColors[value] || C.neutral : C.models[C.family(value)] || C.neutral);node.title=(effort?'Razonamiento: ':'Modelo: ')+label;return node; }
function tags(row, normalized=false) {const box=el('div','tags');box.append(badge(normalized?row.model:C.setting(row,'model')),badge(normalized?row.effort:C.setting(row,'effort'),true));return box;}
function svg(tag, attributes={}) { const node=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value] of Object.entries(attributes))node.setAttribute(key,String(value));return node; }
function icon(name,cls='ui-glyph') {
  const nodes=RouterIcons.nodes[name];if(!nodes)throw new Error('Unknown Lucide icon: '+name);
  const node=svg('svg',{viewBox:'0 0 24 24',class:cls,'data-lucide':name,'aria-hidden':'true',focusable:'false',fill:'none',stroke:'currentColor','stroke-width':2,'stroke-linecap':'round','stroke-linejoin':'round'});
  for(const [tag,attrs] of nodes)node.append(svg(tag,attrs));return node;
}
function controlLabel(node,name,label) {node.replaceChildren(icon(name),el('span','',label));}
function gaugeRing(radius,percent,cls) {
  const ring=svg('svg',{viewBox:'0 0 44 44',class:'usage-ring '+cls,'aria-hidden':'true'}),length=2*Math.PI*radius;
  ring.append(svg('circle',{cx:22,cy:22,r:radius,class:'usage-track',...(percent===null?{'stroke-dasharray':'2 3'}:{})}));
  if(percent!==null)ring.append(svg('circle',{cx:22,cy:22,r:radius,class:'usage-progress',transform:'rotate(-90 22 22)',
    'stroke-dasharray':length,'stroke-dashoffset':length*(1-percent/100),visibility:percent===0?'hidden':'visible'}));
  return ring;
}
function refreshQuota() {
  const gauge=C.weeklyQuota(state.accountUsage,!!state.connections);
  for(const node of [$('quota')]) {
    const ring=gaugeRing(16,gauge.percent,'quota-ring'),label=gauge.percent===null?'—':gauge.percent+'%';
    ring.prepend(svg('circle',{cx:22,cy:22,r:16,class:'quota-face'}));
    const text=svg('text',{x:22,'text-anchor':'middle',class:'quota-number'});text.textContent=label;
    // Center the visible glyphs, rather than the font's line box. The same SVG
    // coordinates place both the arc and number regardless of button layout.
    const context=document.createElement('canvas').getContext('2d');
    const style=getComputedStyle(node);
    context.font=style.fontWeight+' '+style.fontSize+' '+style.fontFamily;
    const metrics=context.measureText(label);
    const offset=Number.isFinite(metrics.actualBoundingBoxAscent) && Number.isFinite(metrics.actualBoundingBoxDescent)?
      (metrics.actualBoundingBoxAscent-metrics.actualBoundingBoxDescent)/2:3.5;
    text.setAttribute('y',22+offset);ring.append(text);node.replaceChildren(ring);
    // SVG middle anchoring uses advance width. Glyph overhang can make the
    // rendered bounds asymmetric (notably with the Windows system font).
    const bounds=text.getBBox();
    if(bounds.width>0)text.setAttribute('x',22+(22-bounds.x-bounds.width/2));
    node.title=gauge.details;node.setAttribute('aria-label',gauge.details);
    node.classList.toggle('unavailable',gauge.percent===null);
  }
  refreshQuotaBars();
  if(quotaOpen)renderQuotaPeek();
}
function renderQuotaPeek() {
  const content=el('div','peek-content');content.append(el('div','peek-category','CUOTA DE LA CUENTA'),el('p','quota-details',C.weeklyQuota(state.accountUsage,!!state.connections).details));
  $('peek').replaceChildren(content);$('surface').style.setProperty('--peek-height',(96+content.offsetHeight)+'px');
}
function openQuota() {
  closePeek();quotaOpen=true;$('peek').hidden=false;document.body.classList.add('peek');renderQuotaPeek();
}
function avatar(id,row,open, existing) {
  const node=existing || button('',open,'avatar');
  node.classList.toggle('working',C.active(row.status));
  node.setAttribute('aria-label',`${row.name || id} · ${C.model(C.setting(row,'model'))} · ${C.efforts[C.setting(row,'effort')] || 'Sin confirmar'} · ${C.status(row.status)}`);
  const colors=C.models[C.family(C.setting(row,'model'))] || C.neutral;palette(node,colors);
  node.style.setProperty('--effort',(C.effortColors[C.setting(row,'effort')] || C.neutral)[0]);
  const identity=C.identity(row);
  if(!existing) {
    const face=el('span','face');face.append(icon(identity[1],'glyph'));
    const track=svg('svg',{viewBox:'0 0 44 44',class:'track'});track.append(svg('circle',{cx:22,cy:22,r:20}));
    const orbit=svg('svg',{viewBox:'0 0 44 44',class:'orbit','aria-hidden':'true'});
    const gradientId='orbit-gradient-'+(++orbitSequence),defs=svg('defs');
    const gradient=svg('linearGradient',{id:gradientId,x1:0,y1:0,x2:1,y2:1});
    gradient.append(svg('stop',{offset:0,'stop-color':'var(--tint)','stop-opacity':0}),svg('stop',{offset:1,'stop-color':'var(--tint)'}));
    defs.append(gradient);orbit.append(defs,svg('path',{d:'M22,2 A20,20 0 0 1 42,22',stroke:'url(#'+gradientId+')'}));
    // A common epoch keeps activity and capsule rings in phase.
    orbit.style.animationDelay=`-${(performance.now()%2800)/1000}s`;
    node.append(face,track,orbit,el('span','effort-dot'));
  } else if(node.querySelector('.glyph').dataset.lucide!==identity[1])node.querySelector('.glyph').replaceWith(icon(identity[1],'glyph'));
  const context=C.contextGauge(row);
  node.classList.toggle('compacting',!!context.compacting);
  if(context.compacting) {
    if(!node.querySelector('.compacting-ring')) {
      node.querySelector('.context-ring')?.remove();
      const ring=svg('svg',{viewBox:'0 0 44 44',class:'usage-ring context-ring compacting-ring','aria-hidden':'true'});
      ring.append(svg('path',{d:'M22,6 A16,16 0 0 1 38,22 M22,38 A16,16 0 0 1 6,22'}));
      ring.style.animationDelay=`-${(performance.now()%1600)/1000}s`;
      node.append(ring);
    }
  } else {
    node.querySelector('.context-ring')?.remove();node.append(gaugeRing(16,context.percent,'context-ring'));
  }
  node.title=context.label;node.setAttribute('aria-label',node.getAttribute('aria-label')+' · '+context.label);
  return node;
}
function setMode(mode,notify=true) {
  if(!['Compact','Expanded','Hidden'].includes(mode))return;
  state.ui.mode=mode;closePeek();clearNativeHover();
  document.body.classList.remove('compact','expanded','hidden');document.body.classList.add(mode.toLowerCase());
  $('compact').hidden=mode!=='Compact';$('expanded').hidden=mode!=='Expanded';
  refreshQuota(); // Hidden SVG text has no bounds; measure the newly visible view.
  if(notify){const request=++modeRequest;pendingModeRequest=state.ui.acknowledgesMode?request:0;native({action:'mode',value:mode,request});}
  requestHistory();
  if(mode==='Expanded')renderPage();
  window.monitorBounds();
}
function openPeek(id) {
  quotaOpen=false;
  clearTimeout(peekTimer);if(!state.threads[id])return;
  peekId=id;$('peek').hidden=false;document.body.classList.add('peek');renderPeek();
}
function renderPeek() {
  const row=state.threads[peekId];if(!row)return closePeek();
  const box=$('peek'),content=el('div','peek-content'),ident=C.identity(row);
  const category=palette(el('div','peek-category',ident[0]),C.models[C.family(C.setting(row,'model'))] || C.neutral);
  category.title='Tipo orientativo · confianza '+(row.agent_confidence || 'sin confirmar');
  content.append(category,el('div','peek-title',row.name || peekId),tags(row),el('div','peek-meta',C.status(row.status)),el('p','',C.contextGauge(row).label));
  box.replaceChildren(content);
  $('surface').style.setProperty('--peek-height',(80+16+content.offsetHeight)+'px');
}
function closePeek() {clearTimeout(peekTimer);peekId=null;quotaOpen=false;$('peek').hidden=true;document.body.classList.remove('peek');}
function capsuleLimit() {return Math.max(1,Math.min(5,Math.floor((Math.min(366,innerWidth-16)-2-22-40-40-48-36)/44)));}
function capsule() {
  const rows=state.threads;
  order=C.stableOrder(order,rows);
  const limit=capsuleLimit(),visible=order.slice(0,limit),host=$('agents');
  for(const [id,node] of avatars) if(!visible.includes(id)) {
    if(node.classList.contains('leave'))continue;
    node.classList.add('leave');
    setTimeout(()=>{if(!order.slice(0,capsuleLimit()).includes(id)){node.remove();avatars.delete(id);if(!order.length&&!avatars.size)capsule();}},420);
  }
  host.querySelector('.idle')?.remove();host.querySelector('.overflow')?.remove();
  for(const id of visible) {
    let node=avatars.get(id);
    if(!node) {
      node=avatar(id,rows[id],()=>openPeek(id));node.classList.add('enter');
      node.addEventListener('mouseenter',()=>openPeek(id));node.addEventListener('focus',()=>openPeek(id));
      avatars.set(id,node);host.append(node);setTimeout(()=>node.classList.remove('enter'),420);
    } else {node.classList.remove('leave');avatar(id,rows[id],null,node);}
  }
  // Never reorder surviving agents. Newly active ones join at the end.
  if(!visible.length&&!avatars.size)host.append(el('span','idle','Todo en calma'));
  if(order.length>limit)host.append(button('+'+(order.length-limit),()=>setMode('Expanded'),'overflow'));
  if(peekId){if(!order.includes(peekId))closePeek();else renderPeek();}
}
function showTab(name) {
  if(!['activity','history','statistics','settings'].includes(name))return;
  currentTab=name;for(const node of document.querySelectorAll('[data-tab]')){node.classList.toggle('selected',node.dataset.tab===name);node.setAttribute('aria-pressed',String(node.dataset.tab===name));}
  $('view-title').textContent=({activity:'Agentes',history:'Historial',statistics:'Consumo',settings:'Ajustes'})[name];
  for(const node of document.querySelectorAll('.page'))node.hidden=node.id!==name;
  requestHistory();renderPage();
}
function openHistory(id) {
  selectedThread=id;
  selectedDecision=state.threads[id]?.decision_id || null;
  showTab('history');
}
function explanation(parent,label,value,kind='') {const box=el('div','reason-card'+(kind?' '+kind:''));box.append(el('h3','',label),el('p','',value || 'Registro anterior sin explicación separada.'));parent.append(box);}
function continuity(value) {return value==='continue'?'Jev identificó trabajo pendiente y reevaluó el modelo y el razonamiento para continuarlo.':value==='reassess'?'Jev consideró que esta petición debía evaluarse de nuevo antes de elegir modelo y razonamiento.':'';}
function phaseStatus(value) {return ({proposed:'Fase propuesta',requested:'Cambio solicitado',applied:'Cambio aceptado',rejected:'Cambio rechazado',preserved:'Selección conservada',unchanged:'Sin cambio',requires_new_turn:'Requiere otro turno',unknown_after_timeout:'Cambio sin confirmar',checkpoint_limit:'Límite de fases',cancelled:'Cancelado',accepted:'Aceptada por Codex',active:'Fase activa',observed:'Modelo observado',completed:'Fase completada',blocked:'Cambio bloqueado',failed:'Fase con incidencia'}[value] || 'Fase sin confirmar');}
function pipeline(parent,row) {
  const phases=Array.isArray(row.phase_pipeline)?row.phase_pipeline:[];
  if(!phases.length)return;
  const dynamic=row.pipeline_mode==='plan_and_observation',box=el('div','pipeline');box.append(el('div','pipeline-title',dynamic?'PLAN DE TRABAJO · OBSERVACIÓN':'PIPELINE · OBSERVACIÓN'));
  for(const phase of phases){const item=el('div','pipeline-step '+phase.state+(phase.evidence==='observed'?' observed':''));const label=phase.state==='planned'?'Planificada':phase.state==='selected'?'Seleccionada':phase.state==='not_observed'?'Pendiente de evidencia':phase.state==='configured'?'Configurada':phaseStatus(phase.state);item.append(el('i',''),el('span','',phase.label),el('small','',label));box.append(item);}
  parent.append(box,el('p','small',dynamic?'Las etapas son un plan. Solo “Ejecución en Codex” se actualiza con evidencia real.':'La evidencia interna de esta ejecución es limitada.'));
}
function executionEvidence(parent,row) {
  if(!row.model && !row.accepted_model && !row.configured_model && !row.observed_model)return;
  const lines=[];
  if(row.status==='interrupted')lines.push('Turno interrumpido; esto no acredita la terminación de todos los procesos de sus herramientas.');
  if(row.model)lines.push('Propuesto por el selector · '+C.model(row.model)+' · '+(C.efforts[row.effort]||'Sin confirmar'));
  if(row.accepted_model)lines.push('Aceptado por Codex · '+C.model(row.accepted_model)+' · '+(C.efforts[row.accepted_effort]||'Sin confirmar'));
  if(row.configured_model)lines.push('Configuración publicada · '+C.model(row.configured_model)+' · '+(C.efforts[row.configured_effort]||'Sin confirmar'));
  if(row.observed_model)lines.push((row.evidence_confidence==='confirmed'?'Inferencia confirmada localmente · ':'Observación anterior sin correlación · ')+C.model(row.observed_model)+' · '+(C.efforts[row.observed_effort]||'Sin confirmar'));
  else lines.push('Inferencia real · sin confirmación disponible todavía');
  if(row.observed_candidate_model)lines.push('Coincidencia probable · '+C.model(row.observed_candidate_model)+' · '+(C.efforts[row.observed_candidate_effort]||'Sin confirmar'));
  explanation(parent,'EVIDENCIA DEL MODELO',lines.join('\n'),'phase');
  if(row.phase_events?.length)explanation(parent,'CAMBIOS DE FASE',row.phase_events.map(p=>`${p.phase_name} · ${phaseStatus(p.phase_status)} · ${C.model(p.phase_model)} · ${C.efforts[p.phase_effort]||'Sin confirmar'}`).join('\n'));
  if(row.prior_inferences?.length)explanation(parent,'INFERENCIAS DE FASES ANTERIORES',row.prior_inferences.map(p=>`${C.model(p.model)} · ${C.efforts[p.effort]||'Sin confirmar'} · ${p.confidence||'sin correlación'}`).join('\n'));
  const samples=Object.values(row.inference_samples||{});
  if(samples.length)explanation(parent,'MÉTRICAS RECIBIDAS',samples.map(s=>{
    const values=[`${s.phase_name||'inicio'} · ${s.inference_event_name||'evento'} / ${s.inference_event_kind||'petición'} · ${s.count} registros · ${s.failures||0} fallos · ${s.evidence_confidence||'sin correlación'}`];
    for(const [k,label] of [['inference_input_tokens','tokens entrada'],['inference_output_tokens','tokens salida'],['inference_ttft_ms','TTFT ms'],['inference_duration_ms','duración del evento ms'],['inference_http_status','HTTP']])if(s[k]!==undefined)values.push(`${label}: ${s[k]}`);
    return values.join(' · ');
  }).join('\n')+'\nValores del último registro de cada clase; las duraciones no se suman como latencia de inferencia.');
}
function taskModeControls(parent,id) {
  if(!id)return;
  const mode=state.taskModes?.[id] || 'automatic';
  choices(parent,[['automatic','Automático'],['manual','Manual']],mode,value=>native({action:'taskMode',thread:id,value}));
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
  section.append(el('div','small','Cuota compartida de la cuenta'));parent.append(section);
}
function agentDetail(parent,id,row) {
  const detail=el('div','agent-detail');detail.append(el('h2','',row.name||'Agente'),tags(row));
  taskModeControls(detail,id);
  detail.append(el('p','confirmation',row.phase_status?phaseStatus(row.phase_status):(row.confirmation||C.status(row.status))),el('p','small',C.contextGauge(row).label));
  const usage=C.usageSample(row);
  detail.append(el('p','small',usage.total===null?'Tokens: sin medición completa disponible.':`Última llamada observada: ${fmt(usage.input)} entrada · ${fmt(usage.output)} salida. No es el total del turno.`));
  detail.append(button('¿Por qué esta elección?',()=>{reasonOpen=!reasonOpen;activity();},'why'));
  if(reasonOpen){explanation(detail,'Modelo elegido',row.model_reason||row.reason,'model');explanation(detail,'Razonamiento elegido',row.effort_reason,'effort');if(row.continuity_strategy)explanation(detail,'Continuidad',continuity(row.continuity_strategy));}
  pipeline(detail,row);executionEvidence(detail,row);detail.append(button('Ver historial',()=>openHistory(id),'why'));parent.append(detail);
}
function activity() {
  const page=$('activity'),scroll=page.scrollTop,attentionOpen=!!page.querySelector('.attention-notice')?.open;page.replaceChildren();
  const quota=el('div','section');quotaSection(quota);page.append(quota);
  const entries=Object.entries(state.threads),rows=entries.filter(([,row])=>C.liveAgent(row));
  const liveIds=rows.map(([id])=>id),stable=order.filter(id=>liveIds.includes(id)).concat(liveIds.filter(id=>!order.includes(id)));
  const attention=entries.filter(([,row])=>!C.liveAgent(row)&&(['waiting','error','failed'].includes(row.status)||!!row.error_type));
  if(attention.length){const notice=el('details','attention-notice');notice.open=attentionOpen;notice.append(el('summary','',attention.length+' '+(attention.length===1?'agente necesita':'agentes necesitan')+' tu atención'));for(const [id,row] of attention)notice.append(button((row.name||'Agente')+' · '+C.status(row.status),()=>{selectedThread=id;selectedDecision=row.decision_id||null;showTab('history');},'attention-item'));page.append(notice);}
  const label=el('div','agent-list-heading');label.append(el('span','',rows.length+' en curso'),el('span','','Tokens · última llamada'));page.append(label);
  if(selectedAgent&&!state.threads[selectedAgent])selectedAgent=null;
  for(const id of stable) {
    const row=state.threads[id],card=button('',()=>selectAgent(id),'task-row'+(selectedAgent===id?' selected':'')),copy=el('div','agent-copy');
    modelTone(card,C.setting(row,'model'));card.dataset.status=C.contextGauge(row).compacting?'compacting':row.status||'unknown';
    card.setAttribute('aria-expanded',String(selectedAgent===id));
    const title=el('div','task-title',row.name||'Agente');title.title=row.name||id;
    const model=tags(row);model.classList.add('agent-model');
    copy.append(model,title,el('div','task-status',C.contextGauge(row).compacting?'Compactando contexto':C.status(row.status)));
    const art=avatar(id,row,()=>{}),artHost=el('span');artHost.append(...art.childNodes);artHost.className=art.className;artHost.style.cssText=art.style.cssText;artHost.setAttribute('aria-hidden','true');
    const usage=C.usageSample(row),value=el('div','agent-usage');value.append(el('strong','',usage.total===null?'—':fmt(usage.total)),el('span','small',usage.total===null?'sin dato':'tokens'));
    card.setAttribute('aria-label',`${row.name||'Agente'} · ${C.model(C.setting(row,'model'))} · ${C.contextGauge(row).label} · ${usage.total===null?'tokens sin dato':fmt(usage.total)+' tokens en la última llamada'}`);
    card.append(artHost,copy,value);page.append(card);
    if(selectedAgent===id)agentDetail(page,id,row);
  }
  if(!rows.length)page.append(el('div','empty-state',state.connections?'Ningún agente trabajando':'Sin conexión con Desktop'),el('p','empty',state.connections?'Los trabajos anteriores están en Historial.':'Comprueba la conexión en Ajustes.'));
  if(selectedAgent&&state.threads[selectedAgent]&&!liveIds.includes(selectedAgent)){const d=el('div','agent-finished');d.append(el('p','small','Este agente ha dejado de trabajar.'),button('Consultar su historial',()=>openHistory(selectedAgent),'why'),button('Cerrar detalle',()=>{selectedAgent=null;activity();},'why'));page.append(d);}
  page.scrollTop=scroll;
}
const fmt = n => Number(n||0).toLocaleString('es-ES');
const when = n => n ? new Date(n*1000).toLocaleString('es-ES',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : 'Fecha sin confirmar';
const engines = {rules:'Reglas',jev:'Jev',provider:'Proveedor retirado'};
function modelTone(node,value) {
  const family=C.family(value),tint=(C.models[family]||C.neutral)[0];
  node.dataset.modelFamily=family;node.style.setProperty('--agent-tint',tint);node.style.setProperty('--agent-wash',tint+'14');
}
let historyQuery='',historyOffset=0;
function renderHistory() {
  const searchFocus=document.activeElement?.id==='history-search',searchPosition=document.activeElement?.selectionStart;
  const page=$('history'),previousScroll=page.querySelector('.history-list')?.scrollTop || 0;
  const previousDetail=page.querySelector('.history-detail'),detailScroll=previousDetail?.scrollTop || 0,previousId=previousDetail?.dataset.decision;
  page.replaceChildren();
  const detail=el('div','history-detail'),list=el('div','history-list');
  const chosen=history.find(d=>d.id===selectedDecision) || (selectedThread?history.find(d=>d.thread===selectedThread):null);if(chosen)selectedDecision=chosen.id;
  if(!chosen){detail.append(el('p','small',history.length?'Selecciona un trabajo para consultar su detalle.':'Aún no hay decisiones registradas.'));taskModeControls(detail,selectedThread);}
  else {
    detail.append(el('h2','',chosen.title || 'Tarea'),tags(chosen,true),el('p','small',when(chosen.started || chosen.time)+' · '+C.status(chosen.status)));
    if(chosen.phase_status) explanation(detail,'ESTADO DE LA FASE',phaseStatus(chosen.phase_status)+(chosen.phase_transition?' · '+chosen.phase_transition:''),'phase');
    pipeline(detail,chosen);executionEvidence(detail,chosen);
    if(chosen.inference_model_mismatch || chosen.inference_effort_mismatch)
      detail.append(el('p','warning','La inferencia vinculada al turno difiere de los ajustes esperados.'));
    taskModeControls(detail,chosen.thread);
    explanation(detail,'Modelo elegido',chosen.model_reason,'model');explanation(detail,'Razonamiento elegido',chosen.effort_reason,'effort');if(chosen.continuity_strategy)explanation(detail,'Decisión de continuidad',continuity(chosen.continuity_strategy),'continuity');
    detail.append(el('h3','quality-label','VALORA ESTA ELECCIÓN'));
    for(const [aspect,label,key] of [['overall','Resultado global','quality'],['model','Modelo elegido','model_quality'],['effort','Razonamiento elegido','effort_quality']]){detail.append(el('p','small',label));const choices=el('div','choices');for(const [value,choiceLabel] of [['insufficient','Insuficiente'],['adequate','Adecuada'],['excessive','Excesiva']])choices.append(button(choiceLabel,()=>native({action:'quality',id:chosen.id,thread:chosen.thread || '',aspect,value:chosen[key]===value?'':value}),'choice'+(chosen[key]===value?' selected':'')));detail.append(choices);if(chosen[key])detail.append(button('Quitar valoración',()=>native({action:'quality',id:chosen.id,thread:chosen.thread || '',aspect,value:''}),'clear-quality'));}
    detail.append(el('p','small','Puedes valorar el resultado global, el modelo y el razonamiento por separado. No se guarda el mensaje ni la respuesta.'));
    detail.append(el('p','small','Motor aplicado: '+(engines[chosen.routing_engine] || 'Sin confirmar')));
    if(chosen.finished>=chosen.started&&chosen.started)detail.append(el('p','small','Duración: '+Math.round(chosen.finished-chosen.started)+' s'));
    const comparisons=Object.values(chosen.comparisons);
    if(comparisons.length)explanation(detail,'MOTORES OBSERVADOS',comparisons.map(comparison=>{
      const role=comparison.engine_active?(comparison.routing_engine===chosen.routing_engine?'aplicado':'intento'):'comparación';
      const failure=comparison.engine_failure==='account_access_restricted'?'Vercel restringe el acceso del plan gratuito; requiere créditos':comparison.engine_failure==='circuit_open'?'En pausa por fallos; se usan reglas locales':comparison.engine_failure;
      const result=comparison.engine_status==='ok'?Math.round(comparison.engine_latency_ms || 0)+' ms':[comparison.engine_status,failure].filter(Boolean).join(' · ') || 'Sin confirmar';
      return `${engines[comparison.routing_engine] || comparison.routing_engine} · ${role} → ${C.model(comparison.proposed_model)} · ${C.efforts[comparison.proposed_effort] || '—'} · ${result}`;
    }).join('\n'));
    if(chosen.inputTokens!==undefined||chosen.outputTokens!==undefined){const sample=C.usageSample(chosen);explanation(detail,'USO OBSERVADO',`Última llamada · ${sample.input===null?'sin dato':fmt(sample.input)} entrada · ${sample.output===null?'sin dato':fmt(sample.output)} salida · ${Number.isSafeInteger(chosen.cachedInputTokens)&&chosen.cachedInputTokens>=0?fmt(chosen.cachedInputTokens):'sin dato'} en caché`);}
    if(chosen.error_type)explanation(detail,'INCIDENCIA',C.errorLabel(chosen));
    if(chosen.native_retries)explanation(detail,'REINTENTOS NATIVOS',String(chosen.native_retries));
    if(chosen.signal)explanation(detail,'SEÑAL DE RESULTADO',chosen.signal==='retry'?'La siguiente petición indicó que el resultado no había resuelto la tarea.':chosen.signal);
  }
  list.append(el('h3','section-title','DECISIONES RECIENTES'));
  if(chosen?.usage_estimates) {
    const samples=Object.values(chosen.usage_estimates);
    explanation(detail,'ESTIMACIÓN STANDARD',samples.reduce((n,s)=>n+s.credits,0).toFixed(4)+' créditos Codex'+(samples.every(s=>Number.isFinite(s.usd))?' · $'+samples.reduce((n,s)=>n+s.usd,0).toFixed(6)+' equivalentes API':' · API sin estimar: falta información de escritura en caché')+'. Solo inferencias con uso completo; no es una factura ni el consumo de tu suscripción. Fast y otros modos no se incluyen.');
  }
  const filtered=history.filter(d=>[d.title,C.model(d.model),C.efforts[d.effort],engines[d.routing_engine],C.status(d.status)].join(' ').toLocaleLowerCase().includes(historyQuery.toLocaleLowerCase()));
  historyOffset=Math.min(historyOffset,Math.max(0,Math.floor((filtered.length-1)/40)*40));
  for(const record of filtered.slice(historyOffset,historyOffset+40)) {
    const row=button('',()=>{selectedDecision=record.id;selectedThread=record.thread;renderHistory();},'history-row'+(record.id===selectedDecision?' selected':''));
    modelTone(row,record.model);
    const copy=el('div','history-copy'),title=el('div','task-title',record.title || 'Tarea');title.title=record.title || 'Tarea';copy.append(title,el('div','small'+(record.error_type?' warning':''),when(record.time)+' · '+C.status(record.status)));row.append(copy,tags(record,true));list.append(row);
  }
  const search=el('input','history-search');search.id='history-search';search.type='search';search.placeholder='Buscar por tarea, modelo, motor o estado';search.setAttribute('aria-label',search.placeholder);search.value=historyQuery;
  search.oninput=()=>{historyQuery=search.value;historyOffset=0;renderHistory();};
  const pagination=el('div','choices');if(historyOffset)pagination.append(button('Anterior',()=>{historyOffset-=40;renderHistory();},'choice'));
  pagination.append(el('span','small',filtered.length?`${historyOffset+1}–${Math.min(historyOffset+40,filtered.length)} de ${filtered.length}`:'Sin coincidencias'));
  if(historyOffset+40<filtered.length)pagination.append(button('Siguiente',()=>{historyOffset+=40;renderHistory();},'choice'));list.append(pagination);
  detail.dataset.decision=chosen?.id || '';page.append(detail,el('div','rule'),search,list);list.scrollTop=previousScroll;
  if(searchFocus){search.focus();if(searchPosition!==null)search.setSelectionRange(searchPosition,searchPosition);}
  if(previousId===chosen?.id)detail.scrollTop=detailScroll;
}
function metric(parent,label,value,ratio=1,color='var(--accent)') {
  const box=el('div','metric'),line=el('div','metric-line'),number=el('span','metric-value',value);number.style.color=color;
  line.append(el('span','',label),number);const meter=el('div','meter'),fill=el('span');fill.style.width=Math.max(0,Math.min(1,ratio))*100+'%';fill.style.background=color;meter.append(fill);box.append(line,meter);parent.append(box);
}
function heading(parent,label){parent.append(el('h3','heading',label));}
function breakdown(parent,label,items,getKey,colors={}) {
  if(label)heading(parent,label);const counts={};for(const item of items){const key=getKey(item);if(key)counts[key]=(counts[key]||0)+1;}
  const max=Math.max(1,...Object.values(counts));for(const [key,count] of Object.entries(counts).sort((a,b)=>b[1]-a[1]))metric(parent,key,fmt(count),count/max,colors[key]?.[0] || colors[C.family(key)]?.[0] || C.neutral[0]);
  if(!Object.keys(counts).length)parent.append(el('p','','Sin datos todavía'));
}
function statistics() {
  const page=$('statistics'),scroll=page.scrollTop,diagnosticsOpen=!!page.querySelector('.consumption-diagnostics')?.open;page.replaceChildren();
  const summary=el('div','section consumption-summary');page.append(summary);quotaSection(summary);
  heading(summary,'TOKENS REGISTRADOS');
  const samples=history.map(d=>({d,usage:C.usageSample(d)})).filter(x=>x.usage.total!==null);
  const totalTokens=samples.reduce((n,x)=>n+x.usage.total,0);
  summary.append(el('div','consumption-total',samples.length?fmt(totalTokens):'—'),el('p','small',`Última llamada por decisión · historial acumulado · ${samples.length} de ${history.length} decisiones con medición completa.`));
  const byModel={};for(const {d,usage} of samples){const label=d.model?C.model(d.model):'Sin confirmar';byModel[label]=(byModel[label]||0)+usage.total;}
  heading(summary,'POR MODELO ELEGIDO');
  for(const [model,tokens] of Object.entries(byModel).sort((a,b)=>b[1]-a[1]))metric(summary,model,fmt(tokens)+' tokens',tokens/(totalTokens||1),C.models[model.split(' ')[0]]?.[0]||'var(--accent)');
  summary.append(el('p','small','Coste facturado: no disponible. Estos contadores no son el total de cada turno ni el consumo de cuota de tu suscripción. Agrupar por modelo elegido no confirma el modelo de cada inferencia.'));
  const diagnostics=el('details','consumption-diagnostics'),content=el('div','section');diagnostics.open=diagnosticsOpen;diagnostics.append(el('summary','','Análisis del enrutamiento y diagnósticos'),content);page.append(diagnostics);
  content.append(el('h2','','Resumen de decisiones'),el('p','','Historial acumulado · se conserva entre sesiones'));
  heading(content,'VERSIONES Y CALIDAD');
  for(const version of [...new Set(history.map(d=>d.product_version || 'Anterior'))]){
    const sample=history.filter(d=>(d.product_version || 'Anterior')===version),rated=sample.filter(d=>d.quality),good=rated.filter(d=>d.quality==='adequate');
    metric(content,version+' · decisiones',sample.length+' · '+rated.length+' valoradas',sample.length/(history.length||1));
    if(rated.length)metric(content,version+' · adecuadas',good.length+' / '+rated.length,good.length/rated.length,'var(--good)');
  }
  content.append(el('p','small','Valoraciones subjetivas con su muestra; disponibilidad y acuerdo entre motores no prueban calidad. Los registros anteriores no confirman una versión.'));
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
  heading(content,'TELEMETRÍA LOCAL');const telemetry=state.telemetry||{};
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
  const transitions={compatible_group:'Cambios compatibles',same_model:'Mismo modelo',blocked_astra_boundary:'Frontera de Astra',unknown_model:'Modelo desconocido',blocked_review_boundary:'Cambio requiere otro turno',unverified_transition:'Transición sin validar'};
  const transitionRows=history.filter(d=>d.phase_transition);
  if(transitionRows.length)for(const [key,label] of Object.entries(transitions)){const count=transitionRows.filter(d=>d.phase_transition===key).length;if(count)metric(content,label,fmt(count),count/transitionRows.length,key==='blocked_astra_boundary'?'var(--warning)':'var(--good)');}
  const estimates=history.flatMap(d=>Object.values(d.usage_estimates||{}));
  if(estimates.length) {
    content.append(el('div','section-label','ESTIMACIÓN STANDARD'));
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
  content.append(el('p','small','Estos datos no demuestran ahorro de cuota ni calidad comparativa por sí solos.'));page.scrollTop=scroll;
}
function actionCard(parent,title,description,action){const node=button('',action,'settings-action');node.disabled=!!connectionPending;node.append(el('strong','',title),el('span','',description),icon('chevron-right','ui-glyph action-affordance'));parent.append(node);return node;}
const connectionLabels={doctor:'Comprobando conexión…',install:'Conectando…',uninstall:'Desconectando…'};
function connectionControls() {
  for(const node of $('settings').querySelectorAll('.settings-action')) {
    node.disabled=!!connectionPending;
    if(!node.dataset.connectionAction)continue;
    const busy=node.dataset.connectionAction===connectionPending;
    node.classList.toggle('busy',busy);node.setAttribute('aria-busy',String(busy));
    node.querySelector('strong').textContent=busy?connectionLabels[connectionPending]:node.dataset.title;
    node.querySelector('span').textContent=busy?'La operación está en curso. Espera el resultado; puede tardar unos segundos.':node.dataset.description;
  }
}
function connectDesktop(value) {
  if(connectionPending)return;
  connectionPending=value;connectionControls();$('feedback').textContent=connectionLabels[value];
  native({action:'connection',value});
}
function connectionCard(parent,value,title,description) {
  const node=actionCard(parent,title,description,()=>connectDesktop(value));
  Object.assign(node.dataset,{connectionAction:value,title,description});
  const spinner=el('i','action-spinner');spinner.setAttribute('aria-hidden','true');node.append(spinner);
  connectionControls();
}
function choices(parent,options,selected,action,disabled=[]) {const box=el('div','choices');for(const [key,label] of options){const chosen=Array.isArray(selected)?selected.includes(key):selected===key;const node=button('',()=>action(key),'choice'+(chosen?' selected':''));controlLabel(node,chosen?'circle-check':'circle',label);node.setAttribute('aria-pressed',String(chosen));node.disabled=disabled.includes(key);box.append(node);}parent.append(box);}
const configure = (key,value) => native({action:'config',key,value});
function keySettings(parent,id,label) {
  const ready=state.keys?.[id];
  const editor=el('div','key-editor');editor.hidden=true;
  actionCard(parent,ready?'Clave guardada de '+label:'Añadir clave de '+label,'La clave se guarda en el llavero de este Mac.',()=>{editor.hidden=!editor.hidden;input.value='';if(!editor.hidden)input.focus();});
  const input=el('input');input.type='password';input.autocomplete='off';input.setAttribute('aria-label','Clave API de '+label);
  editor.append(input);const actions=el('div','choices');actions.append(button('Guardar clave',()=>{const value=input.value.trim();if(!value)return;native({action:'secret',provider:id,value});input.value='';editor.hidden=true;},'choice'),button('Cancelar',()=>{input.value='';editor.hidden=true;},'choice'));editor.append(actions);parent.append(editor);
}
function updateSettings(box) {
  const update=state.updates||{status:'idle',installedVersion:state.productVersion},busy=['checking','downloading'].includes(update.status);
  heading(box,'ACTUALIZACIONES');
  const statuses={idle:'Sin comprobar',checking:'Comprobando…',available:'Nueva versión disponible',package_unavailable:'Hay una nueva versión; aún no hay instalador publicado para este equipo.',up_to_date:'No hay una versión estable más reciente.',downloading:'Descargando…',downloaded:'Descarga verificada. La instalación desde la aplicación aún no está disponible.',cancelled:'Operación cancelada.',error:'No se pudo comprobar o descargar la actualización.'};
  const errors={release_unavailable:'No hay una entrega pública accesible.',rate_limited:'GitHub ha limitado las comprobaciones. Vuelve a intentarlo más tarde.',network_error:'Comprueba tu conexión e inténtalo de nuevo.',invalid_release:'La entrega no tiene metadatos válidos para actualizar.',unsupported_platform:'No hay un instalador compatible con este equipo.',unsafe_download:'La dirección de descarga no es válida.',invalid_size:'El tamaño recibido no coincide con el publicado.',integrity_error:'La descarga no coincide con su huella publicada.'};
  const card=el('div','update-card');card.append(el('strong','','Versión instalada · '+(update.installedVersion||state.productVersion||'Desconocida')));
  if(update.latestVersion)card.append(el('p','small','Última estable · '+update.latestVersion));
  card.append(el('p','small',statuses[update.status]||statuses.idle));
  if(update.error)card.append(el('p','warning',errors[update.error]||errors.network_error));
  if(update.checkedAt)card.append(el('p','small','Comprobado · '+new Date(update.checkedAt*1000).toLocaleString('es-ES')));
  if(update.status==='downloading'){
    const progress=el('progress');progress.max=100;progress.value=Number.isFinite(update.progress)?update.progress:0;progress.setAttribute('aria-label','Progreso de descarga');card.append(progress);
  }
  const actions=el('div','choices');
  const check=button('Comprobar ahora',()=>native({action:'update',value:'check'}),'choice');check.disabled=busy||!!state.preview;actions.append(check);
  if(update.canDownload){const download=button('Descargar versión '+update.latestVersion,()=>native({action:'update',value:'download'}),'choice');download.disabled=busy||!!state.preview;actions.append(download);}
  if(busy){const cancel=button('Cancelar',()=>native({action:'update',value:'cancel'}),'choice');cancel.disabled=!!state.preview;actions.append(cancel);}
  card.append(actions);box.append(card);
  actionCard(box,state.config.updates_auto_check?'Desactivar comprobación diaria':'Activar comprobación diaria','Consulta las versiones públicas de este repositorio en GitHub. No envía tus tareas ni tus ajustes; no instala automáticamente.',()=>configure('updates_auto_check',!state.config.updates_auto_check));
}
function settings() {
  const page=$('settings'),scroll=page.scrollTop,box=el('div','section'),config=state.config,catalogOpen=!!page.querySelector('.icon-catalog')?.open;page.replaceChildren(box);
  box.append(el('h2','','Ajustes'),el('p','','Controla el selector, el motor que decide y cuánto tiempo se conserva su historial local.'));
  updateSettings(box);
  heading(box,'CONEXIÓN CON DESKTOP');
  box.append(el('p','small','La instalación se detecta al arrancar. Conecta el inicio habitual una vez. Cerrar el monitor no detiene el selector.'));
  connectionCard(box,'doctor','Comprobar conexión','Distingue instalación, registro y conexión observada.');
  connectionCard(box,'install','Conectar al inicio habitual','Prepara el próximo arranque de Desktop. Puedes pulsarlo con tus tareas abiertas.');
  connectionCard(box,'uninstall','Desconectar integración','Restaura el inicio habitual sin borrar ajustes ni historial.');
  actionCard(box,config.enabled?'Pausar selección automática':'Activar selección automática',config.enabled?'Codex automático decide en cada nuevo mensaje.':'Se respeta la selección manual de Codex.',()=>configure('enabled',!config.enabled));
  box.lastElementChild.querySelector('strong').prepend(icon(config.enabled?'pause':'play'));
  actionCard(box,state.ui.topmost?'Desactivar Mantener delante':'Activar Mantener delante',state.ui.topmost?(state.platform==='linux'?'Solicita al escritorio mantener el monitor delante.':'El monitor permanece sobre otras ventanas.'):'El monitor puede quedar detrás de otras ventanas.',()=>native({action:'topmost',value:!state.ui.topmost}));
  if(state.platform==='linux' && state.desktopCapabilities?.positioning===false)box.append(el('p','small','El escritorio decide la posición y si mantiene el monitor delante. Puedes moverlo con el atajo de ventanas del sistema.'));
  heading(box,'CONSERVAR HISTORIAL');choices(box,[[30,'30 días'],[90,'90 días'],[180,'180 días'],[0,'Siempre']],config.history_days??90,v=>configure('history_days',v));
  heading(box,'FASES Y EVIDENCIA');
  box.append(el('p','small',config.phase_routing?'Cambios por fases habilitados en la configuración. Tras cargarla, las tareas nuevas pueden usar checkpoints compatibles; las existentes sin checkpoint cambian entre turnos. Una aceptación no confirma una inferencia.':'La pipeline observa la ejecución. Los cambios por fases están desactivados en la configuración; el modelo se elige entre turnos. Una aceptación no confirma una inferencia.'));
  actionCard(box,config.phase_routing?'Desactivar cambios automáticos por fases':'Activar cambios automáticos por fases',config.phase_routing?'Las tareas nuevas podrán cambiar modelo y esfuerzo en checkpoints amplios. Se aplica tras reiniciar Desktop.':'Mantiene el mismo modelo durante cada turno. Se aplica tras reiniciar Desktop.',()=>configure('phase_routing',!config.phase_routing));
  actionCard(box,config.inference_telemetry?'Desactivar telemetría local':'Activar telemetría local',config.inference_telemetry?'Confirma inferencias mediante un receptor temporal en este equipo. Se aplicará al reiniciar Codex.':'Confirma modelo y razonamiento ejecutados. Solo usa un receptor temporal en este equipo; no guarda mensajes ni respuestas.',()=>configure('inference_telemetry',!config.inference_telemetry));
  actionCard(box,config.prompt_logging?'Desactivar captura de prompts':'Activar captura de prompts',config.prompt_logging?'Guarda cada nuevo mensaje con su decisión para evaluar el enrutamiento. El cambio se aplica al siguiente mensaje.':'No guarda el texto de los mensajes; las estadísticas agregadas continúan disponibles.',()=>configure('prompt_logging',!config.prompt_logging));
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
  const catalog=el('details','icon-catalog');catalog.open=catalogOpen;catalog.append(el('summary','','Iconos de los agentes · '+Object.keys(C.identities).length+' tipos'));
  const icons=el('div','icon-catalog-grid');for(const [category,[label]] of Object.entries(C.identities)){
    const item=el('div'),art=avatar('',{agent_category:category,status:'idle'},()=>{}),host=el('span','avatar');host.style.cssText=art.style.cssText;host.append(...art.childNodes);host.setAttribute('aria-hidden','true');host.querySelector('.effort-dot')?.remove();host.querySelector('.context-ring')?.remove();item.append(host,el('span','small',label));icons.append(item);
  }catalog.append(icons);box.append(catalog);
  heading(box,'PRIVACIDAD');box.append(el('p','small',config.prompt_logging?'Además de las métricas, se guarda el texto de tus mensajes en el archivo local privado state/prompts.jsonl para evaluar las decisiones. No guarda respuestas, adjuntos, herramientas ni credenciales. Las claves se almacenan en '+(state.secretStorage || 'el llavero de macOS')+'.':'El historial guarda tareas, ajustes, motivos, estados y contadores. No guarda mensajes, respuestas, adjuntos, herramientas ni credenciales. Las claves se almacenan en '+(state.secretStorage || 'el llavero de macOS')+'.'));
  page.scrollTop=scroll;
}
function renderPage(){
  if(state.ui.mode!=='Expanded')return;
  if(currentTab==='history' || currentTab==='statistics') {
    if(state.ui.lazyHistory && !state.historyLoaded){
      $(currentTab).replaceChildren(el('p','empty','Cargando historial…'));return;
    }
    ensureHistory();
  }
  if(currentTab==='activity')activity();else if(currentTab==='history')renderHistory();else if(currentTab==='statistics')statistics();else settings();
}
window.receive = incoming => {
  const oldConfig=JSON.stringify(state.config),oldUi=JSON.stringify(state.ui),oldUpdates=JSON.stringify(state.updates);
  if(incoming.history){historyRevision++;historyDirty=true;incoming={...incoming,historyLoaded:true};}
  if(incoming.threads)historyDirty=true;
  const staleMode=state.ui.acknowledgesMode && Number.isInteger(incoming.ui?.modeRequest) && incoming.ui.modeRequest<modeRequest;
  if((pendingModeRequest || staleMode) && incoming.ui)incoming={...incoming,ui:{...incoming.ui,mode:state.ui.mode}};
  state={...state,...incoming,ui:{...state.ui,...incoming.ui}};
  if(!heightDrag && Number.isFinite(state.ui.panelHeight))panelHeight(state.ui.panelHeight-16);
  document.body.classList.toggle('reduced',!!state.ui.reduced);
  if(!document.body.classList.contains(state.ui.mode.toLowerCase()))setMode(state.ui.mode,false);
  const active=Object.values(state.threads).filter(row=>C.liveAgent(row)).length;
  $('connection').classList.toggle('disconnected',!state.connections);$('connection').querySelector('span').textContent=state.preview?'Vista previa · datos simulados':state.connections?`${active} ${active===1?'tarea activa':'tareas activas'}`:state.desktopRestartPending?'Conexión preparada · reinicia Desktop':'Sin conexión';$('connection').querySelector('i').classList.toggle('working',active>0);
  controlLabel($('pause'),state.config.enabled?'pause':'play',state.config.enabled?'Pausar selección':'Activar selección');
  const bridgeMismatch=(state.bridgeVersions||[]).filter(v=>v!==state.productVersion);
  $('product-version').textContent='v'+(state.productVersion || '—')+(bridgeMismatch.length?' · puente '+bridgeMismatch.join(', '):state.bridgeBuildMismatch?' · router anterior':state.bridgeBuildUnknown?' · puente sin verificar':'')+(state.restartRequired?' · reinicio pendiente':'');
  $('product-version').title=state.restartRequired?'Hay ajustes pendientes. Reinicia Desktop al terminar tus tareas para cargarlos.':(bridgeMismatch.length||state.bridgeBuildMismatch)?'La versión del router activo difiere de la incluida con este monitor. Reinicia Desktop al terminar tus tareas para cargar la versión instalada.':state.bridgeBuildUnknown?'El puente activo no informa su versión de componente. No se puede determinar si necesita reinicio; el próximo inicio de Desktop permitirá comprobarlo.':'Versión de Codex automático';
  capsule();
  refreshQuota();
  document.body.classList.toggle('native-glass',!!state.ui.nativeGlass);
  document.body.classList.toggle('reduce-transparency',!!state.ui.reduceTransparency);
  const signature=JSON.stringify([state.threads,historyRevision,state.historyLoaded,state.connections,state.taskModes,state.telemetry,state.accountUsage]);
  const settingsChanged=oldConfig!==JSON.stringify(state.config) || oldUi!==JSON.stringify(state.ui) || oldUpdates!==JSON.stringify(state.updates);
  if(signature!==dataSignature || settingsChanged){
    dataSignature=signature;
    // Do not discard an API key while the owner is typing it.
    if(currentTab!=='settings' || (settingsChanged && document.activeElement?.type!=='password'))renderPage();
  }
};
window.receiveUI = (ui,request=ui.modeRequest ?? null) => {
  if(pendingModeRequest && request!==pendingModeRequest)return;
  if(Number.isInteger(request) && request<modeRequest)return;
  pendingModeRequest=0;state.ui={...state.ui,...ui};
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
  const target=point && state.ui.mode!=='Hidden' ? document.elementFromPoint(point.x,point.y) : null;
  const button=target?.closest('button');
  if(button!==nativeHover){clearNativeHover();nativeHover=button;button?.classList.add('native-hover');}
  if(state.ui.mode==='Compact') {
    if(target?.closest('#compact'))clearTimeout(peekTimer);
    else if(peekId || quotaOpen){clearTimeout(peekTimer);peekTimer=setTimeout(closePeek,220);}
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
$('expand').onclick=()=>setMode('Expanded');$('collapse').onclick=()=>setMode('Compact');$('hide').onclick=()=>setMode('Hidden');$('pause').onclick=()=>configure('enabled',!state.config.enabled);
$('quota').onclick=openQuota;
$('quota').addEventListener('mouseenter',openQuota);$('quota').addEventListener('focus',openQuota);
window.addEventListener('resize',()=>{capsule();window.monitorBounds();});
setInterval(refreshQuota,2000);
for(const node of document.querySelectorAll('[data-tab]'))node.onclick=()=>showTab(node.dataset.tab);
$('compact').addEventListener('mouseenter',()=>clearTimeout(peekTimer));$('compact').addEventListener('mouseleave',()=>{peekTimer=setTimeout(closePeek,220);});
document.addEventListener('keydown',event=>{if(event.key==='Escape'){if(peekId||quotaOpen)closePeek();else setMode('Compact');}});
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
for(const node of document.querySelectorAll('[data-icon]'))node.replaceChildren(icon(node.dataset.icon));
controlLabel($('pause'),'pause','Pausar selección');
native({action:'ready'});
