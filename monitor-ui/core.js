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
    audit: ['Auditoría','M9,2 L15,2 L15,4 L20,4 L20,12 M12,22 L4,22 L4,4 L9,4 Z M8,8 L12,8 M8,12 L10,12 M16,12 A4,4 0 1 1 15.99,12 M19,19 L23,23'],
    tests: ['Pruebas','M8,2 L16,2 M10,2 L10,9 L4,19 Q3,22 6,22 L18,22 Q21,22 20,19 L14,9 L14,2 M7,15 L17,15 M9,18 L10,18 M14,19 L15,19'],
    architecture: ['Arquitectura','M9,2 L15,2 L15,8 L9,8 Z M2,16 L8,16 L8,22 L2,22 Z M16,16 L22,16 L22,22 L16,22 Z M12,8 L12,12 M5,16 L5,12 L19,12 L19,16'],
    correction: ['Corrección','M8,7 L16,7 L17,11 L17,16 A5,5 0 0 1 7,16 L7,11 Z M9,7 L9,4 L15,4 L15,7 M9,4 L7,2 M15,4 L17,2 M3,10 L7,12 M17,12 L21,10 M3,16 L7,16 M17,16 L21,16 M5,22 L8,19 M16,19 L19,22 M12,8 L12,20'],
    text: ['Textos','M4,3 L20,3 M12,3 L12,21 M8,21 L16,21 M4,3 L4,7 M20,3 L20,7'],
    interface: ['Interfaces','M3,3 L21,3 L21,21 L3,21 Z M3,8 L21,8 M8,8 L8,21 M5,5.5 L6,5.5 M9,5.5 L10,5.5'],
    research: ['Investigación','M10,2 A8,8 0 1 1 9.99,2 M16,16 L23,23 M6,10 L14,10 M10,6 L10,14'],
    configuration: ['Configuración','M12,3 L14,6 L18,6 L19,10 L22,12 L19,14 L18,18 L14,18 L12,21 L10,18 L6,18 L5,14 L2,12 L5,10 L6,6 L10,6 Z M12,9 A3,3 0 1 1 11.99,9'],
    automation: ['Automatización','M5,5 L10,5 L12,8 L14,5 L19,5 L19,10 L22,12 L19,14 L19,19 L14,19 L12,16 L10,19 L5,19 L5,14 L2,12 L5,10 Z M9,12 L15,12 M12,9 L12,15'],
    general: ['Tarea','M12,2 A10,10 0 1 1 11.99,2 M12,7 L12,17 M7,12 L17,12']
  };
  const active = status => ['active','inProgress','running','pending'].includes(status);
  const status = value => ({active:'Trabajando',inProgress:'Trabajando',running:'Trabajando',pending:'Enviando',completed:'En espera',idle:'En espera',waiting:'Esperando tu respuesta',error:'Error',failed:'Error',interrupted:'Interrumpida'}[value] || 'Estado sin confirmar');
  const setting = (row, key) => row.status === 'pending' ? row['requested_'+key] : row[key] || row['requested_'+key];
  function model(value) { const name = String(value || 'Sin confirmar').replace(/^gpt-(?:5\.6-|6-)?/,''); return name.charAt(0).toUpperCase()+name.slice(1); }
  function identity(row) {
    if (identities[row.agent_category]) return identities[row.agent_category];
    const text = (row.name || row.model_reason || row.reason || '').toLowerCase();
    for (const [category, regex] of [['audit',/auditor|audit|seguridad|security|accesibilidad/],['tests',/\b(test|tests|prueba|pruebas|e2e)\b|comprobar|verificar|validar/],['architecture',/arquitect|architect|migraci|infraestructura/],['correction',/correg|corrig|error|fallo|bug|arregl|fix/],['text',/traduc|translat|texto|document|resum/],['interface',/interfaz|interfaces|frontend|diseñ|design|cápsula|capsula|\b(ui|ux)\b/],['research',/investig|research|analiz/]]) {
      if (regex.test(text)) return identities[category];
    }
    return identities.general;
  }
  function stableOrder(previous, rows) {
    const keys = Object.keys(rows).filter(key => active(rows[key].status)).sort((a,b)=>(rows[b].updated||0)-(rows[a].updated||0));
    return previous.filter(key => keys.includes(key)).concat(keys.filter(key => !previous.includes(key)));
  }
  function decisions(events, live = {}) {
    const map = new Map();
    for (const event of events) {
      const id = event.decision_id;
      if (typeof id !== 'string' || !id) continue;
      const item = map.get(id) || {id,time:0,accepted:false,comparisons:{}};
      if (event.event !== 'decision_quality') item.time = Math.max(item.time, Number(event.time)||0);
      if (event.event === 'decision_created') item.started = Number(event.time)||0;
      if (['decision_accepted','decision_recovered'].includes(event.event)) item.accepted = true;
      if (['decision_completed','decision_rejected','decision_error'].includes(event.event)) item.finished = Number(event.time)||0;
      for (const key of ['thread','title','model','effort','model_reason','effort_reason','source','status','signal','error_type','quality','routing_engine','engine_model','engine_status','engine_confidence','engine_latency_ms','inputTokens','outputTokens','cachedInputTokens','reasoningOutputTokens']) {
        if (Object.prototype.hasOwnProperty.call(event,key)) item[key] = event[key];
      }
      if (event.event === 'engine_comparison') {
        item.comparisons[event.routing_engine || 'rules'] = {...event};
        // A shadow proposal does not become the applied engine.
        if (item.appliedEngine !== undefined) item.routing_engine = item.appliedEngine;
        else item.routing_engine = event.engine_active === undefined && event.engine_status === 'ok' ? event.routing_engine : 'rules';
      }
      if (event.event === 'decision_routed') item.appliedEngine = item.routing_engine;
      map.set(id,item);
    }
    for (const [id,row] of Object.entries(live)) {
      const item = map.get(row.decision_id);
      if (!item) continue; // Resuming a task is not a new decision.
      item.thread = id; item.title = row.name || item.title; item.status = row.status || item.status;
      for (const key of ['model','effort']) { const value = setting(row,key); if (value) item[key]=value; }
      for (const key of ['model_reason','effort_reason']) if (row[key]) item[key] = row[key];
      for (const key of ['inputTokens','outputTokens','cachedInputTokens','reasoningOutputTokens']) if (row.tokens?.[key] !== undefined) item[key] = row.tokens[key];
    }
    return [...map.values()].sort((a,b)=>b.time-a.time);
  }
  const api = {models,efforts,effortColors,neutral,identities,active,status,setting,model,identity,stableOrder,decisions};
  if (typeof module !== 'undefined') module.exports = api;
  else scope.MonitorCore = api;
})(globalThis);
