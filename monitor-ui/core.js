/* Shared, DOM-free monitor semantics. Derived from MonitorAnalytics/Agents.cs. */
(function (scope) {
  'use strict';
  const models = {
    Luna: ['#ACDEFF', '#273B4B'], Terra: ['#A4E4C6', '#283E36'],
    Sol: ['#F0D19C', '#423A2A'], Astra: ['#D5C3FF', '#3B304E']
  };
  const efforts = {low:'Ligero', medium:'Medio', high:'Alto', xhigh:'Muy alto', max:'Máx.', ultra:'Ultra'};
  const effortColors = {low:['#BECADD','#313843'], medium:['#ABDDDF','#293E42'], high:['#BCD0FF','#303952'], xhigh:['#D9C5F6','#3C334D'], max:['#F2CEB1','#48372F'], ultra:['#F0BBD5','#493041']};
  const neutral = ['#C5C8D3','#353741'];
  const identities = {
    audit: ['Auditoría','clipboard-check'],
    tests: ['Pruebas','flask-conical'],
    architecture: ['Arquitectura','network'],
    correction: ['Corrección','bug'],
    text: ['Textos','text'],
    interface: ['Interfaces','panels-top-left'],
    research: ['Investigación','search'],
    configuration: ['Configuración','settings-2'],
    automation: ['Automatización','workflow'],
    general: ['Tarea','circle-plus'],
    data: ['Datos','database'],
    performance: ['Rendimiento','gauge'],
    deployment: ['Despliegues','rocket'],
    versioning: ['Versiones','git-branch'],
    integration: ['Integraciones','plug'],
    accessibility: ['Accesibilidad','accessibility']
  };
  const active = status => ['active','inProgress','running','pending'].includes(status);
  const status = value => ({active:'Trabajando',inProgress:'Trabajando',running:'Trabajando',pending:'Enviando',completed:'En espera',idle:'En espera',waiting:'Esperando tu respuesta',error:'Error',failed:'Error',interrupted:'Interrumpida'}[value] || 'Estado sin confirmar');
  const setting = (row, key) => row.status === 'pending' ? row['requested_'+key] : row[key] || row['requested_'+key];
  function model(value) {
    const name=String(value || 'Sin confirmar'), match=/^gpt-(\d+(?:\.\d+)?)-(luna|terra|sol|astra)$/.exec(name);
    return match ? match[2].charAt(0).toUpperCase()+match[2].slice(1)+' '+match[1] : name;
  }
  function family(value) { return model(value).split(' ')[0]; }

  function identity(row) {
    if (identities[row.agent_category]) return identities[row.agent_category];
    const text = (row.name || row.model_reason || row.reason || '').toLowerCase();
    for(const [category,regex] of [['accessibility',/accesibilidad|accessibility|voiceover|lector de pantalla/],['data',/base de datos|database|\bsql\b|postgres|sqlite/],['performance',/rendimiento|performance|latencia|profiling/],['deployment',/desplieg|deploy|publicar versi/],['versioning',/\bgit\b|merge|rebase|conflictos de versi/],['integration',/integraci|integration|webhook|conector/]])if(regex.test(text))return identities[category];
    for (const [category, regex] of [['audit',/auditor|audit|seguridad|security|accesibilidad/],['tests',/\b(test|tests|prueba|pruebas|e2e)\b|comprobar|verificar|validar/],['architecture',/arquitect|architect|migraci|infraestructura/],['correction',/correg|corrig|error|fallo|bug|arregl|fix/],['text',/traduc|translat|texto|document|resum/],['interface',/interfaz|interfaces|frontend|diseñ|design|cápsula|capsula|\b(ui|ux)\b/],['research',/investig|research|analiz/]]) {
      if (regex.test(text)) return identities[category];
    }
    return identities.general;
  }
  function stableOrder(previous, rows) {
    const keys = Object.keys(rows).filter(key => liveAgent(rows[key])).sort((a,b)=>(rows[b].updated||0)-(rows[a].updated||0));
    return previous.filter(key => keys.includes(key)).concat(keys.filter(key => !previous.includes(key)));
  }
  function companionOrder(previous,rows) {
    const keys=Object.keys(rows).filter(id=>liveAgent(rows[id]) || ['waiting','error','failed'].includes(rows[id].status)).sort((a,b)=>(rows[b].updated||0)-(rows[a].updated||0));
    return previous.filter(id=>keys.includes(id)).concat(keys.filter(id=>!previous.includes(id)));
  }
  function decisions(events, live = {}) {
    const map = new Map();
    for (const event of events) {
      if(event.event==='monitor_decision_snapshot' && typeof event.record?.id==='string' && event.record.id){map.set(event.record.id,{...event.record});continue;}
      const id = event.decision_id;
      if (typeof id !== 'string' || !id) continue;
      const item = map.get(id) || {id,time:0,accepted:false,comparisons:{}};
      // Thread totals are cumulative snapshots, not a decision's last call.
      if(event.event==='decision_usage_total') {
        item.native_total_usage={inputTokens:event.inputTokens,outputTokens:event.outputTokens,cachedInputTokens:event.cachedInputTokens};
        map.set(id,item);continue;
      }
      if(event.event==='decision_usage')for(const key of ['inputTokens','outputTokens','cachedInputTokens','reasoningOutputTokens'])delete item[key];
      if(event.event==='inference_observed' && event.evidence_confidence==='confirmed' && event.estimate_basis==='standard_equivalent_not_billed' && event.inference_event_id) {
        (item.usage_estimates ||= {})[event.inference_event_id]={usd:event.estimated_api_standard_usd,credits:event.estimated_codex_standard_credits};
      }
      if (event.event === 'phase_checkpoint') {
        (item.phase_events ||= []).push({...event});
        if (event.phase_status === 'applied') {
          if (item.observed_model) (item.prior_inferences ||= []).push({model:item.observed_model,effort:item.observed_effort,phase_id:item.phase_id,confidence:item.evidence_confidence});
          for (const key of ['observed_model','observed_effort','observed_candidate_model','observed_candidate_effort','evidence_confidence','inference_source','inference_model_mismatch','inference_effort_mismatch']) delete item[key];
          item.accepted_model=event.accepted_model || event.phase_model;
          item.accepted_effort=event.accepted_effort || event.phase_effort;
        }
      }
      if (['inference_metric','inference_observed','inference_probable'].includes(event.event)) {
        const observedModel=event.observed_model || event.observed_candidate_model;
        const observedEffort=event.observed_effort || event.observed_candidate_effort || '';
        const kind=(event.phase_id ? event.phase_id+':' : '')+(event.inference_event_name || 'unknown')+':'+(event.inference_event_kind || 'unknown')+(observedModel ? ':'+observedModel+':'+observedEffort : '');
        const samples=item.inference_samples ||= {};
        const previous=samples[kind] || {count:0};
        samples[kind]={...event,count:previous.count+(event.inference_sample_count||1),failures:(previous.failures||0)+(event.inference_failure_count||0)};
        for (const [key,value] of Object.entries(event)) if(key.startsWith('inference_') && !['inference_model_mismatch','inference_effort_mismatch'].includes(key))item[key]=value;
        // Request/stream metrics never replace inference identity evidence.
        if(event.event==='inference_metric'){map.set(id,item);continue;}
        if(event.event==='inference_probable' && item.evidence_confidence==='confirmed'){map.set(id,item);continue;}
      }
      if (event.event === 'native_turn_error') {
        if (event.will_retry === true) item.native_retries = (item.native_retries || 0) + 1;
        map.set(id,item);
        continue;
      }
      if (event.event === 'decision_completed') for (const key of ['error_type','error_code','error_http_status','error_source']) delete item[key];
      if(event.phase_id && (event.event!=='phase_checkpoint' || event.phase_status==='applied'))item.phase_id=event.phase_id;
      if (event.event !== 'decision_quality') item.time = Math.max(item.time, Number(event.time)||0);
      if (event.event === 'decision_created') item.started = Number(event.time)||0;
      if (event.event === 'decision_created') for (const key of ['product_version','build_id','routing_policy_version','request_kind','quality_floor','min_effort']) item[key]=event[key];
      if (['decision_accepted','decision_recovered'].includes(event.event)) item.accepted = true;
      if (['decision_completed','decision_rejected','decision_error'].includes(event.event)) item.finished = Number(event.time)||0;
      for (const key of ['thread','title','model','effort','model_reason','effort_reason','continuity_strategy','source','status','signal','error_type','quality','model_quality','effort_quality','routing_engine','engine_model','engine_status','engine_confidence','engine_latency_ms','inputTokens','outputTokens','cachedInputTokens','reasoningOutputTokens','phase_name','phase_status','phase_model','phase_effort','phase_transition','observed_model','observed_effort','observed_candidate_model','observed_candidate_effort','configured_model','configured_effort','accepted_model','accepted_effort','pipeline_mode','phase_pipeline','inference_source','evidence_confidence']) {
        if (event.event === 'engine_comparison' && (key.startsWith('engine_') || key === 'routing_engine' || key === 'continuity_strategy')) continue;
        if (Object.prototype.hasOwnProperty.call(event,key)) item[key] = event[key];
      }
      if (event.event === 'engine_comparison') {
        item.comparisons[event.routing_engine || 'rules'] = {...event};
        // A shadow proposal does not become the applied engine.
        if (item.appliedEngine !== undefined) item.routing_engine = item.appliedEngine;
        else item.routing_engine = event.engine_active === undefined && event.engine_status === 'ok' ? event.routing_engine : 'rules';
      }
      if (event.event === 'decision_routed') item.appliedEngine = item.routing_engine;
      for (const key of ['error_code','error_http_status','error_source']) if (Object.prototype.hasOwnProperty.call(event,key)) item[key] = event[key];
      for(const key of ['inference_model_mismatch','inference_effort_mismatch'])if(Object.prototype.hasOwnProperty.call(event,key))item[key]=event[key];
      map.set(id,item);
    }
    return withLiveDecisions([...map.values()],live);
  }
  function withLiveDecisions(records,live={}) {
    const map=new Map(records.map(item=>[item.id,item]));
    for (const [id,row] of Object.entries(live)) {
      const original = map.get(row.decision_id);
      const item = original && {...original};
      if (!item) continue; // Resuming a task is not a new decision.
      if(row.phase_id && row.phase_id!==item.phase_id)for(const key of ['observed_model','observed_effort','evidence_confidence','inference_source','inference_model_mismatch','inference_effort_mismatch'])delete item[key];
      if(row.phase_id)item.phase_id=row.phase_id;
      item.thread = id; item.title = row.name || item.title; item.status = row.status || item.status;
      for (const key of ['model','effort']) { const value = setting(row,key); if (value) item[key]=value; }
      for (const key of ['model_reason','effort_reason']) if (row[key]) item[key] = row[key];
      for (const key of ['phase_name','phase_status','phase_model','phase_effort','phase_transition','observed_model','observed_effort','configured_model','configured_effort','accepted_model','accepted_effort','pipeline_mode','phase_pipeline','inference_source','evidence_confidence']) if (row[key]) item[key] = row[key];
      for(const key of ['inference_model_mismatch','inference_effort_mismatch'])if(Object.prototype.hasOwnProperty.call(row,key))item[key]=row[key];
      if(row.tokens)for(const key of ['inputTokens','outputTokens','cachedInputTokens','reasoningOutputTokens']) {
        delete item[key];if(row.tokens[key]!==undefined)item[key]=row.tokens[key];
      }
      map.set(item.id,item);
    }
    return [...map.values()].sort((a,b)=>b.time-a.time);
  }
  function featuredThread(threads, selection, now) {
    if(selection && now < selection.until && threads[selection.id])return selection.id;
    return Object.keys(threads).sort((a,b)=>(Number(threads[b].updated)||0)-(Number(threads[a].updated)||0) || a.localeCompare(b))[0] || null;
  }
  function errorLabel(row) {
    const type = row.error_type === 'unknown' ? 'Causa no proporcionada por Codex' : row.error_type;
    return (type || '') + (row.error_http_status !== undefined ? ' · HTTP '+row.error_http_status : '') +
      (row.error_code !== undefined ? ' · RPC '+row.error_code : '');
  }
  function contextGauge(row) {
    const phase=(row.context_compaction || {}).state;
    if(phase==='compacting')return {percent:null,compacting:true,label:'Compactando contexto…'};
    if(phase==='awaiting_usage')return {percent:null,compacting:false,label:'Contexto: esperando nueva medición tras compactar'};
    const usage=row.context_window || {},value=usage.used_percent;
    const known=Number.isFinite(value) && value>=0 && Number.isFinite(usage.capacity_tokens) && usage.capacity_tokens>0;
    const percent=known?Math.min(100,value):null;
    return {percent,label:known?`Contexto usado: ${Number(percent.toFixed(1))} % · ${usage.used_tokens} / ${usage.capacity_tokens} tokens · última medición`:'Contexto: sin medición disponible'};
  }
  function quotaGauge(usage={},connected=true,now=Date.now()/1000) {
    const value=usage.remaining_percent;
    const fresh=connected && Number.isFinite(usage.valid_until) && now<usage.valid_until;
    const percent=fresh && Number.isFinite(value) && value>=0?Math.min(100,value):null;
    const lines=(usage.windows || []).map(w=>{
      const minutes=w.duration_minutes;
      const duration=minutes===10080?'semanal':minutes && minutes%1440===0?`${minutes/1440} días`:minutes && minutes%60===0?`${minutes/60} h`:minutes?`${minutes} min`:w.window;
      return `${w.limit_id} · ${duration}: ${w.remaining_percent} % disponible`+(w.resets_at?` · se renueva ${new Date(w.resets_at*1000).toLocaleString('es-ES')}`:'');
    });
    const label=percent===null?'Cuota de Codex: sin datos actuales':`Cuota disponible: ${percent} % · límite más restrictivo`;
    if(usage.ordinary_usage_allowed===false)lines.push('Codex informa que el uso incluido no está disponible.');
    return {percent,label,details:[label,...lines,...(!fresh && lines.length?['Última lectura; pendiente de actualizar.']:[])].join('\n')};
  }
  function liveAgent(row) { return active(row.status) || contextGauge(row).compacting === true; }
  function usageSample(row) {
    const source=row.tokens || row;
    const valid=value=>Number.isSafeInteger(value)&&value>=0;
    const input=valid(source.inputTokens)?source.inputTokens:null,output=valid(source.outputTokens)?source.outputTokens:null;
    const total=input!==null&&output!==null&&valid(input+output)?input+output:null;
    return {input,output,total};
  }
  function quotaWindows(usage={},connected=true,now=Date.now()/1000) {
    const fresh=connected && Number.isFinite(usage.valid_until) && now<usage.valid_until;
    return (Array.isArray(usage.windows)?usage.windows:[]).map(w=>{
      const value=w.remaining_percent,percent=fresh&&Number.isFinite(value)&&value>=0&&value<=100?value:null;
      const minutes=w.duration_minutes,label=minutes===10080?'Cuota semanal':minutes===300?'Ventana de 5 horas':minutes&&minutes%1440===0?`Ventana de ${minutes/1440} días`:minutes&&minutes%60===0?`Ventana de ${minutes/60} h`:minutes?`Ventana de ${minutes} min`:'Ventana sin confirmar';
      return {...w,percent,label};
    });
  }
  function weeklyQuota(usage={},connected=true,now=Date.now()/1000) {
    const windows=quotaWindows(usage,connected,now).filter(w=>w.duration_minutes===10080),known=windows.filter(w=>w.percent!==null);
    const percent=known.length===windows.length&&known.length?Math.min(...known.map(w=>w.percent)):null;
    const label=percent===null?'Cuota semanal restante: sin datos actuales':`Cuota semanal restante: ${percent} % disponible`;
    return {percent,label,details:label+'\nCuota compartida de la cuenta.'+windows.map(w=>`\n${w.limit_id||'Codex'} · semanal: ${w.percent===null?'sin datos actuales':w.percent+' % disponible'}${Number.isFinite(w.resets_at)?' · se renueva '+new Date(w.resets_at*1000).toLocaleString('es-ES'):''}`).join('')};
  }
  // Stable visual aliases depend on the conversation, never on routing choices.
  function companion(id) {
    let hash=2166136261;
    for(const char of String(id)){hash^=char.codePointAt(0);hash=Math.imul(hash,16777619);}
    const variants=[['coral','Milo','#ff9e88'],['mint','Lumi','#81d7bd'],['lilac','Nori','#c1a0f0']];
    const [variant,name,color]=variants[(hash>>>0)%variants.length];
    return {variant,name,color};
  }
  function companionState(row={},connected=true) {
    if(!connected)return {kind:'offline',headline:'Sin noticias.',label:'Sin conexión · última lectura'};
    if(row.catalog_only)return {kind:'idle',headline:'Un respiro.',label:'Sin actividad registrada'};
    if(contextGauge(row).compacting)return {kind:'compacting',headline:'Poniendo orden.',label:'Compactando contexto'};
    if(['waiting','error','failed'].includes(row.status))return {kind:row.status==='waiting'?'waiting':'error',headline:'Te necesita.',label:status(row.status)};
    if(active(row.status))return {kind:'working',headline:'En ello.',label:status(row.status)};
    if(row.status==='completed')return {kind:'done',headline:'Todo listo.',label:'Tarea terminada'};
    if(row.status==='idle' || !row.status)return {kind:'idle',headline:'Un respiro.',label:'En reposo'};
    return {kind:'unknown',headline:'A la espera.',label:status(row.status)};
  }
  function executionPipeline(row={},connected=true) {
    const live=row.live_plan,ended=['completed','failed','error','interrupted'].includes(row.status);
    const stopped=['failed','error','interrupted'].includes(row.status)||['failed','blocked','rejected'].includes(row.phase_status);
    let steps,source;
    if(row.status!=='pending' && live?.turn_id && live.turn_id===row.turn_id && Array.isArray(live.steps) && live.steps.length){
      source='Plan del agente';
      steps=live.steps.map(step=>({...step,state:step.state==='active'&&ended?(stopped?'stopped':'unknown'):step.state}));
    }else{
      if(row.catalog_only || (!row.model&&!row.accepted_model&&!row.phase_status&&!active(row.status)))return null;
      source='Ejecución';
      const accepted=!!row.accepted_model || ['accepted','active','observed','completed'].includes(row.phase_status);
      const started=['active','inProgress','running','completed','failed','interrupted','waiting'].includes(row.status) || ['active','observed','completed'].includes(row.phase_status);
      const finished=row.status==='completed';
      steps=[
        {label:'Selección',state:row.model?'completed':!accepted&&!started?'active':'unknown'},
        {label:'Aceptación',state:accepted?'completed':!started?'active':'unknown'},
        {label:'Ejecución',state:finished?'completed':stopped?'stopped':started?'active':'pending'},
        {label:'Finalización',state:finished?'completed':stopped?'stopped':'pending'}
      ];
      if(!row.model && !accepted && !started)steps[1].state='pending';
    }
    const labels={completed:'Completado',active:'En curso',pending:'Pendiente',stopped:row.status==='interrupted'?'Interrumpido':'Con incidencia',unknown:'Sin confirmar'};
    const waiting=row.status==='waiting';
    return {source,steps:steps.map(step=>({...step,animate:connected&&!waiting&&step.state==='active',
      statusLabel:!connected&&step.state==='active'?'Última lectura':waiting&&step.state==='active'?'En espera':labels[step.state]||'Sin confirmar'})),
      status:!connected?'Sin conexión':row.status==='interrupted'?'Interrumpida':stopped?'Con incidencia':row.status==='completed'?'Turno terminado':waiting?'En espera':''};
  }
  const api = {withLiveDecisions,executionPipeline,companion,companionState,companionOrder,models,efforts,effortColors,neutral,identities,active,status,setting,model,family,identity,stableOrder,decisions,featuredThread,errorLabel,contextGauge,quotaGauge,liveAgent,usageSample,quotaWindows,weeklyQuota};
  if (typeof module !== 'undefined') module.exports = api;
  else scope.MonitorCore = api;
})(globalThis);
