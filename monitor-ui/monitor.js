'use strict';
const C = MonitorCore, $ = id => document.getElementById(id);
let state = {threads:{},history:[],config:{enabled:true},ui:{mode:'Compact',topmost:true},connections:0};
let currentTab = 'activity', order = [], selectedDecision = null, selectedThread = null, peekId = null, peekTimer, reasonOpen = false;
let dataSignature = '', history = [], avatars = new Map(), orbitSequence = 0;
const native = message => window.webkit?.messageHandlers?.monitor?.postMessage(message);
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
function badge(value, effort=false) { const label=effort ? C.efforts[value] || 'Sin confirmar' : C.model(value);const node=palette(el('span','badge',label), effort ? C.effortColors[value] || C.neutral : C.models[label] || C.neutral);node.title=(effort?'Razonamiento: ':'Modelo: ')+label;return node; }
function tags(row, normalized=false) {const box=el('div','tags');box.append(badge(normalized?row.model:C.setting(row,'model')),badge(normalized?row.effort:C.setting(row,'effort'),true));return box;}
function svg(tag, attributes={}) { const node=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value] of Object.entries(attributes))node.setAttribute(key,String(value));return node; }
function avatar(id,row,open, existing) {
  const node=existing || button('',open,'avatar');
  node.classList.toggle('working',C.active(row.status));
  node.setAttribute('aria-label',`${row.name || id} · ${C.model(C.setting(row,'model'))} · ${C.efforts[C.setting(row,'effort')] || 'Sin confirmar'} · ${C.status(row.status)}`);
  const colors=C.models[C.model(C.setting(row,'model'))] || C.neutral;palette(node,colors);
  node.style.setProperty('--effort',(C.effortColors[C.setting(row,'effort')] || C.neutral)[0]);
  const identity=C.identity(row);
  if(!existing) {
    const face=el('span','face'),glyph=svg('svg',{viewBox:'0 0 24 24',class:'glyph'});glyph.append(svg('path',{d:identity[1]}));face.append(glyph);
    const track=svg('svg',{viewBox:'0 0 44 44',class:'track'});track.append(svg('circle',{cx:22,cy:22,r:20}));
    const orbit=svg('svg',{viewBox:'0 0 44 44',class:'orbit','aria-hidden':'true'});
    const gradientId='orbit-gradient-'+(++orbitSequence),defs=svg('defs');
    const gradient=svg('linearGradient',{id:gradientId,x1:0,y1:0,x2:1,y2:1});
    gradient.append(svg('stop',{offset:0,'stop-color':'var(--tint)','stop-opacity':0}),svg('stop',{offset:1,'stop-color':'var(--tint)'}));
    defs.append(gradient);orbit.append(defs,svg('path',{d:'M22,2 A20,20 0 0 1 42,22',stroke:'url(#'+gradientId+')'}));
    // A common epoch keeps activity and capsule rings in phase.
    orbit.style.animationDelay=`-${(performance.now()%2800)/1000}s`;
    node.append(face,track,orbit,el('span','effort-dot'));
  } else node.querySelector('.glyph path').setAttribute('d',identity[1]);
  return node;
}
function setMode(mode,notify=true) {
  if(!['Compact','Expanded','Hidden'].includes(mode))return;
  state.ui.mode=mode;closePeek();
  document.body.classList.remove('compact','expanded','hidden');document.body.classList.add(mode.toLowerCase());
  $('compact').hidden=mode!=='Compact';$('expanded').hidden=mode!=='Expanded';
  if(notify)native({action:'mode',value:mode});
  if(mode==='Expanded')renderPage();
}
function openPeek(id) {
  clearTimeout(peekTimer);if(!state.threads[id])return;
  peekId=id;$('peek').hidden=false;document.body.classList.add('peek');renderPeek();
}
function renderPeek() {
  const row=state.threads[peekId];if(!row)return closePeek();
  const box=$('peek'),content=el('div','peek-content'),ident=C.identity(row);
  const category=palette(el('div','peek-category',ident[0]),C.models[C.model(C.setting(row,'model'))] || C.neutral);
  category.title='Tipo orientativo · confianza '+(row.agent_confidence || 'sin confirmar');
  content.append(category,el('div','peek-title',row.name || peekId),tags(row),el('div','peek-meta',C.status(row.status)));
  box.replaceChildren(content);
  $('surface').style.setProperty('--peek-height',(80+16+content.offsetHeight)+'px');
}
function closePeek() {clearTimeout(peekTimer);peekId=null;$('peek').hidden=true;document.body.classList.remove('peek');}
function capsule() {
  const rows=state.threads;
  order=C.stableOrder(order,rows);
  const visible=order.slice(0,5),host=$('agents');
  for(const [id,node] of avatars) if(!visible.includes(id)) {
    if(node.classList.contains('leave'))continue;
    node.classList.add('leave');
    setTimeout(()=>{if(!order.slice(0,5).includes(id)){node.remove();avatars.delete(id);if(!order.length&&!avatars.size)capsule();}},420);
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
  if(order.length>5)host.append(button('+'+(order.length-5),()=>setMode('Expanded'),'overflow'));
  $('count').textContent=order.length ? `${order.length} ${order.length===1?'tarea activa':'tareas activas'}` : 'Sin tareas activas';
  if(peekId){if(!order.includes(peekId))closePeek();else renderPeek();}
}
function showTab(name) {
  currentTab=name;for(const node of document.querySelectorAll('[data-tab]'))node.classList.toggle('selected',node.dataset.tab===name);
  for(const node of document.querySelectorAll('.page'))node.hidden=node.id!==name;
  renderPage();
}
function openHistory(id) {
  selectedThread=id;
  selectedDecision=history.find(item=>item.thread===id)?.id || null;
  showTab('history');
}
function explanation(parent,label,value,kind='') {const box=el('div','reason-card'+(kind?' '+kind:''));box.append(el('h3','',label),el('p','',value || 'Registro anterior sin explicación separada.'));parent.append(box);}
function continuity(value) {return value==='continue'?'Jev identificó trabajo pendiente y reevaluó el modelo y el razonamiento para continuarlo.':value==='reassess'?'Jev consideró que esta petición debía evaluarse de nuevo antes de elegir modelo y razonamiento.':'';}
function phaseStatus(value) {return ({proposed:'Fase propuesta',accepted:'Aceptada por Codex',active:'Fase activa',observed:'Modelo observado',completed:'Fase completada',blocked:'Cambio bloqueado',failed:'Fase con incidencia'}[value] || 'Fase sin confirmar');}
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
  if(row.model)lines.push('Propuesto por el selector · '+C.model(row.model)+' · '+(C.efforts[row.effort]||'Sin confirmar'));
  if(row.accepted_model)lines.push('Aceptado por Codex · '+C.model(row.accepted_model)+' · '+(C.efforts[row.accepted_effort]||'Sin confirmar'));
  if(row.configured_model)lines.push('Configuración publicada · '+C.model(row.configured_model)+' · '+(C.efforts[row.configured_effort]||'Sin confirmar'));
  if(row.observed_model)lines.push((row.evidence_confidence==='confirmed'?'Inferencia confirmada localmente · ':'Observación anterior sin correlación · ')+C.model(row.observed_model)+' · '+(C.efforts[row.observed_effort]||'Sin confirmar'));
  else lines.push('Inferencia real · sin confirmación disponible todavía');
  explanation(parent,'EVIDENCIA DEL MODELO',lines.join('\n'),'phase');
}
function taskModeControls(parent,id) {
  if(!id)return;
  const mode=state.taskModes?.[id] || 'automatic';
  choices(parent,[['automatic','Automático'],['manual','Manual']],mode,value=>native({action:'taskMode',thread:id,value}));
  parent.append(el('p','small',!state.config.enabled?'El selector está pausado para todas las tareas.':mode==='manual'?
    'Próximo mensaje: usa el modelo y esfuerzo elegidos en Codex.':'Próximo mensaje: el selector decide modelo y esfuerzo.'));
}
function activity() {
  const page=$('activity'),scroll=page.scrollTop;page.replaceChildren();
  const rows=Object.entries(state.threads).sort((a,b)=>Number(C.active(b[1].status))-Number(C.active(a[1].status))+(C.active(a[1].status)===C.active(b[1].status)?((b[1].updated||0)-(a[1].updated||0)):0));
  const featured=el('div','section');featured.append(el('h3','','TAREA DESTACADA'));
  if(!rows.length) {
    featured.append(el('h2','',state.connections?'Todo en calma':'Esperando conexión'),el('p','',state.connections?'Las tareas aparecerán cuando se observe actividad.':'Comprueba la conexión en Ajustes. Si está instalada, vuelve a abrir Desktop desde su acceso habitual cuando terminen tus tareas.'));
  } else {
    const [id,row]=rows[0],line=el('div','featured-row'),copy=el('div','featured-copy');
    const title=el('div','featured-title',row.name || id);title.title=row.name || id;
    copy.append(title,tags(row));line.append(avatar(id,row,()=>openHistory(id)),copy);featured.append(line);
    taskModeControls(featured,id);
    featured.append(el('div','confirmation',row.phase_status?phaseStatus(row.phase_status):(row.status==='pending'?'Selección pendiente de confirmar':row.confirmation || 'Sin confirmar')));
    featured.append(button('¿Por qué esta elección?',()=>{reasonOpen=!reasonOpen;activity();},'why'));
    if(reasonOpen){const detail=el('div','explanation');detail.append(el('h3','','POR QUÉ EL MODELO'),el('p','',row.model_reason || row.reason || 'Sin explicación registrada.'),el('h3','','POR QUÉ EL RAZONAMIENTO'),el('p','',row.effort_reason || 'Sin explicación registrada.'));if(row.continuity_strategy)detail.append(el('h3','','DECISIÓN DE CONTINUIDAD'),el('p','',continuity(row.continuity_strategy)));featured.append(detail);}
    pipeline(featured,row);
  }
  page.append(featured,el('div','rule'),el('h3','section-title','ACTIVIDAD'));
  for(const [id,row] of rows.slice(1)) {
    const card=button('',()=>openHistory(id),'task-row'),copy=el('div');copy.style.minWidth='0';
    const title=el('div','task-title',row.name || id);title.title=row.name || id;
    copy.append(title,el('div','task-status',C.status(row.status)+(row.phase_status?' · '+phaseStatus(row.phase_status):'')));
    const art=avatar(id,row,()=>{});art.tabIndex=-1;
    const badges=el('div','row-tags');badges.append(badge(C.setting(row,'model')),badge(C.setting(row,'effort'),true));
    // Avoid nested interactive controls while preserving the shared avatar.
    const artHost=el('span');artHost.append(...art.childNodes);artHost.className=art.className;artHost.style.cssText=art.style.cssText;
    card.append(artHost,copy,badges);page.append(card);
  }
  if(rows.length<=1)page.append(el('div','empty','No hay otras tareas observadas.'));
  page.scrollTop=scroll;
}
const fmt = n => Number(n||0).toLocaleString('es-ES');
const when = n => n ? new Date(n*1000).toLocaleString('es-ES',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : 'Fecha sin confirmar';
const engines = {rules:'Reglas',jev:'Jev',provider:'Proveedor retirado'};
let historyQuery='',historyOffset=0;
function renderHistory() {
  const searchFocus=document.activeElement?.id==='history-search',searchPosition=document.activeElement?.selectionStart;
  const page=$('history'),previousScroll=page.querySelector('.history-list')?.scrollTop || 0;
  const previousDetail=page.querySelector('.history-detail'),detailScroll=previousDetail?.scrollTop || 0,previousId=previousDetail?.dataset.decision;
  page.replaceChildren();
  const detail=el('div','history-detail'),list=el('div','history-list');
  const chosen=history.find(d=>d.id===selectedDecision) || (selectedThread?history.find(d=>d.thread===selectedThread):history[0]);if(chosen)selectedDecision=chosen.id;
  if(!chosen){detail.append(el('h2','','Aún no hay decisiones registradas'),el('p','','Las nuevas ejecuciones se guardan aquí y se conservan al cerrar Codex. Abrir una conversación antigua no crea una decisión nueva.'));taskModeControls(detail,selectedThread);}
  else {
    detail.append(el('h2','',chosen.title || 'Tarea'),tags(chosen,true),el('p','small',when(chosen.started || chosen.time)+' · '+C.status(chosen.status)));
    if(chosen.phase_status) explanation(detail,'ESTADO DE LA FASE',phaseStatus(chosen.phase_status)+(chosen.phase_transition?' · '+chosen.phase_transition:''),'phase');
    pipeline(detail,chosen);executionEvidence(detail,chosen);
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
      const result=comparison.engine_status==='ok'?Math.round(comparison.engine_latency_ms || 0)+' ms':comparison.engine_status || 'Sin confirmar';
      return `${engines[comparison.routing_engine] || comparison.routing_engine} · ${role} → ${C.model(comparison.proposed_model)} · ${C.efforts[comparison.proposed_effort] || '—'} · ${result}`;
    }).join('\n'));
    if(chosen.inputTokens!==undefined||chosen.outputTokens!==undefined)explanation(detail,'USO OBSERVADO',`Última llamada · ${fmt(chosen.inputTokens)} entrada · ${fmt(chosen.outputTokens)} salida · ${fmt(chosen.cachedInputTokens)} en caché`);
    if(chosen.error_type)explanation(detail,'INCIDENCIA',chosen.error_type);
    if(chosen.signal)explanation(detail,'SEÑAL DE RESULTADO',chosen.signal==='retry'?'La siguiente petición indicó que el resultado no había resuelto la tarea.':chosen.signal);
  }
  list.append(el('h3','section-title','DECISIONES RECIENTES'));
  const filtered=history.filter(d=>[d.title,C.model(d.model),C.efforts[d.effort],engines[d.routing_engine],C.status(d.status)].join(' ').toLocaleLowerCase().includes(historyQuery.toLocaleLowerCase()));
  historyOffset=Math.min(historyOffset,Math.max(0,Math.floor((filtered.length-1)/40)*40));
  for(const record of filtered.slice(historyOffset,historyOffset+40)) {
    const row=button('',()=>{selectedDecision=record.id;selectedThread=record.thread;renderHistory();},'history-row'+(record.id===selectedDecision?' selected':''));
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
  const max=Math.max(1,...Object.values(counts));for(const [key,count] of Object.entries(counts).sort((a,b)=>b[1]-a[1]))metric(parent,key,fmt(count),count/max,colors[key]?.[0] || C.neutral[0]);
  if(!Object.keys(counts).length)parent.append(el('p','','Sin datos todavía'));
}
function statistics() {
  const page=$('statistics'),scroll=page.scrollTop,content=el('div','section');page.replaceChildren(content);
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
    metric(content,'Solicitudes recibidas',fmt(telemetry.requests),Math.min(1,(telemetry.requests||0)/(total||1)));
    metric(content,'Registros con modelo',fmt(telemetry.eligible_records),Math.min(1,(telemetry.eligible_records||0)/Math.max(1,telemetry.records_scanned||0)));
    metric(content,'Finalizaciones recibidas',fmt(telemetry.telemetry_events),Math.min(1,(telemetry.telemetry_events||0)/Math.max(1,telemetry.eligible_records||0)));
    metric(content,'Inferencias asociadas',fmt(telemetry.telemetry_confirmed),Math.min(1,(telemetry.telemetry_confirmed||0)/Math.max(1,telemetry.telemetry_events||0)),'var(--good)');
    if(!receiving)content.append(el('p','warning','El receptor está abierto, pero no recibe eventos. Esto no significa que no haya agentes trabajando.'));
    else if(!(telemetry.eligible_records||0))content.append(el('p','warning','Se recibieron eventos sin modelo utilizable; no se conserva su contenido.'));
  }
  const transitions={compatible_group:'Cambios compatibles',same_model:'Mismo modelo',blocked_astra_boundary:'Frontera de Astra',unknown_model:'Modelo desconocido'};
  const transitionRows=history.filter(d=>d.phase_transition);
  if(transitionRows.length)for(const [key,label] of Object.entries(transitions)){const count=transitionRows.filter(d=>d.phase_transition===key).length;if(count)metric(content,label,fmt(count),count/transitionRows.length,key==='blocked_astra_boundary'?'var(--warning)':'var(--good)');}
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
function actionCard(parent,title,description,action){const node=button('',action,'settings-action');node.append(el('strong','',title),el('span','',description));parent.append(node);}
function choices(parent,options,selected,action,disabled=[]) {const box=el('div','choices');for(const [key,label] of options){const chosen=Array.isArray(selected)?selected.includes(key):selected===key;const node=button((chosen?'●  ':'○  ')+label,()=>action(key),'choice'+(chosen?' selected':''));node.disabled=disabled.includes(key);box.append(node);}parent.append(box);}
const configure = (key,value) => native({action:'config',key,value});
function keySettings(parent,id,label) {
  const ready=state.keys?.[id];
  const editor=el('div','key-editor');editor.hidden=true;
  actionCard(parent,ready?'Clave guardada de '+label:'Añadir clave de '+label,'La clave se guarda en el llavero de este Mac.',()=>{editor.hidden=!editor.hidden;input.value='';if(!editor.hidden)input.focus();});
  const input=el('input');input.type='password';input.autocomplete='off';input.setAttribute('aria-label','Clave API de '+label);
  editor.append(input);const actions=el('div','choices');actions.append(button('Guardar clave',()=>{const value=input.value.trim();if(!value)return;native({action:'secret',provider:id,value});input.value='';editor.hidden=true;},'choice'),button('Cancelar',()=>{input.value='';editor.hidden=true;},'choice'));editor.append(actions);parent.append(editor);
}
function settings() {
  const page=$('settings'),scroll=page.scrollTop,box=el('div','section'),config=state.config;page.replaceChildren(box);
  box.append(el('h2','','Ajustes'),el('p','','Controla el selector, el motor que decide y cuánto tiempo se conserva su historial local.'));
  heading(box,'CONEXIÓN CON DESKTOP');
  box.append(el('p','small','La instalación se detecta al arrancar. Conecta el inicio habitual una vez. Cerrar el monitor no detiene el selector.'));
  actionCard(box,'Comprobar conexión','Distingue instalación, registro y conexión observada.',()=>native({action:'connection',value:'doctor'}));
  actionCard(box,'Conectar al inicio habitual','Se aplicará al volver a abrir Desktop; conserva las tareas en curso.',()=>native({action:'connection',value:'install'}));
  actionCard(box,'Desconectar integración','Restaura el inicio habitual sin borrar ajustes ni historial.',()=>native({action:'connection',value:'uninstall'}));
  actionCard(box,config.enabled?'Ⅱ  Pausar selección automática':'▶  Activar selección automática',config.enabled?'Codex automático decide en cada nuevo mensaje.':'Se respeta la selección manual de Codex.',()=>configure('enabled',!config.enabled));
  actionCard(box,state.ui.topmost?'Desactivar Mantener delante':'Activar Mantener delante',state.ui.topmost?'El monitor permanece sobre otras ventanas.':'El monitor puede quedar detrás de otras ventanas.',()=>native({action:'topmost',value:!state.ui.topmost}));
  heading(box,'CONSERVAR HISTORIAL');choices(box,[[30,'30 días'],[90,'90 días'],[180,'180 días'],[0,'Siempre']],config.history_days??90,v=>configure('history_days',v));
  heading(box,'FASES Y EVIDENCIA');
  box.append(el('p','small','La pipeline es de observación: no cambia el modelo durante una tarea. El panel separa la propuesta, la aceptación y la configuración publicada; una inferencia solo se marca como confirmada cuando existe telemetría local segura.'));
  actionCard(box,config.inference_telemetry?'Desactivar telemetría local':'Activar telemetría local',config.inference_telemetry?'Confirma inferencias mediante un receptor temporal en este equipo. Se aplicará al reiniciar Codex.':'Confirma modelo y razonamiento ejecutados. Solo usa un receptor temporal en este equipo; no guarda mensajes ni respuestas.',()=>configure('inference_telemetry',!config.inference_telemetry));
  const engine=['rules','jev'].includes(config.routing_engine)?config.routing_engine:'rules';
  heading(box,'MOTOR DE ENRUTAMIENTO');choices(box,[['rules','Reglas'],['jev','Jev']],engine,v=>configure('routing_engine',v));
  box.append(el('p','small',engine==='rules'?'Las reglas locales deciden al instante sin enviar el mensaje a otro servicio.':'El clasificador recibe el mensaje de la tarea. Si falla o responde de forma inválida, se conservan las reglas locales. Puede consumir cuota del proveedor.'));
  heading(box,'COMPARACIÓN EN PARALELO');const comparisons=(config.comparison_engines||[]).filter(x=>['rules','jev'].includes(x));
  choices(box,[['rules','Reglas'],['jev','Jev']],[engine,...comparisons],key=>configure('comparison_engines',comparisons.includes(key)?comparisons.filter(x=>x!==key):[...comparisons,key]),[engine]);
  box.append(el('p','small','El motor activo ya se registra. Marca otros para comparar propuestas; las comparaciones externas también reciben el mensaje.'));
  if(engine==='jev'){
    const jev=config.jev||{},connection=jev.connection||'typesafe';heading(box,'CONEXIÓN DE JEV');
    choices(box,[['vercel','Vercel AI Gateway'],['typesafe','TypeSafe directo']],connection,v=>configure('jev.connection',v));
    box.append(el('p','small',connection==='vercel'?'Usa el modelo virtual vmc/jev de Vercel durante las pruebas.':'Conecta directamente con api.typesafe.ai usando jev-latest.'));
    keySettings(box,'jev-'+connection,connection==='vercel'?'Vercel AI Gateway':'TypeSafe');
    if(!state.keys?.['jev-'+connection])box.append(el('p','small','Cada conexión necesita su propia clave. Si guardaste una clave en una versión anterior, introdúcela aquí una vez para vincularla a este proveedor.'));
  }
  heading(box,'POLÍTICA ACTUAL');for(const [tier,description] of [['simple','Tareas delimitadas'],['normal','Cambios concretos'],['complex','Ingeniería compleja'],['critical','UX, auditorías y gran alcance']]){const route=config.routes?.[tier];if(route){const row=el('div','policy');row.append(badge(route.model),el('span','',description),badge(route.effort,true));box.append(row);}}
  heading(box,'PRIVACIDAD');box.append(el('p','small','El historial guarda tareas, ajustes, motivos, estados y contadores. No guarda mensajes, respuestas, adjuntos, herramientas ni credenciales. Las claves se almacenan en el llavero de macOS.'));
  page.scrollTop=scroll;
}
function renderPage(){if(currentTab==='activity')activity();else if(currentTab==='history')renderHistory();else if(currentTab==='statistics')statistics();else settings();}
window.receive = incoming => {
  const oldConfig=JSON.stringify(state.config),oldUi=JSON.stringify(state.ui);
  state={...state,...incoming};history=C.decisions(state.history,state.threads);
  if(!heightDrag && Number.isFinite(state.ui.panelHeight))panelHeight(state.ui.panelHeight-16);
  document.body.classList.toggle('reduced',!!state.ui.reduced);
  if(!document.body.classList.contains(state.ui.mode.toLowerCase()))setMode(state.ui.mode,false);
  const active=Object.values(state.threads).filter(row=>C.active(row.status)).length;
  $('connection').classList.toggle('disconnected',!state.connections);$('connection').querySelector('span').textContent=state.preview?'Vista previa · datos simulados':state.connections?`${active} ${active===1?'tarea activa':'tareas activas'}`:'Sin conexión';$('connection').querySelector('i').classList.toggle('working',active>0);
  $('pause').textContent=state.config.enabled?'Ⅱ  Pausar selección':'▶  Activar selección';
  const bridgeMismatch=(state.bridgeVersions||[]).filter(v=>v!==state.productVersion);
  $('product-version').textContent='v'+(state.productVersion || '—')+(bridgeMismatch.length?' · puente '+bridgeMismatch.join(', '):state.bridgeBuildMismatch?' · reinicio pendiente':'');
  $('product-version').title=(bridgeMismatch.length||state.bridgeBuildMismatch)?'Reinicia Desktop al terminar tus tareas para cargar la versión instalada.':'Versión de Codex automático';
  capsule();
  const signature=JSON.stringify([state.threads,state.history,state.connections,state.taskModes,state.telemetry]);
  const settingsChanged=oldConfig!==JSON.stringify(state.config) || oldUi!==JSON.stringify(state.ui);
  if(signature!==dataSignature || settingsChanged){
    dataSignature=signature;
    // Do not discard an API key while the owner is typing it.
    if(currentTab!=='settings' || (settingsChanged && document.activeElement?.type!=='password'))renderPage();
  }
};
window.monitorFeedback = text => { $('feedback').textContent=text;setTimeout(()=>{$('feedback').textContent='';},7000); };
$('expand').onclick=()=>setMode('Expanded');$('collapse').onclick=()=>setMode('Compact');$('hide').onclick=()=>setMode('Hidden');$('pause').onclick=()=>configure('enabled',!state.config.enabled);
for(const node of document.querySelectorAll('[data-tab]'))node.onclick=()=>showTab(node.dataset.tab);
$('compact').addEventListener('mouseenter',()=>clearTimeout(peekTimer));$('compact').addEventListener('mouseleave',()=>{peekTimer=setTimeout(closePeek,220);});
document.addEventListener('keydown',event=>{if(event.key==='Escape'){if(peekId)closePeek();else setMode('Compact');}});
new ResizeObserver(()=>{const r=$('surface').getBoundingClientRect();native({action:'bounds',x:r.x,y:r.y,width:r.width,height:r.height});}).observe($('surface'));
native({action:'ready'});
