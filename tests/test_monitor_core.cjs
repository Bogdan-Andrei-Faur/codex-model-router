const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('../monitor-ui/core.js');
test('capsule weekly quota never substitutes a restrictive short window',()=>{
  const usage={remaining_percent:3,valid_until:200,windows:[{duration_minutes:300,remaining_percent:3},{duration_minutes:10080,remaining_percent:68}]};
  assert.equal(C.weeklyQuota(usage,true,100).percent,68);
  assert.match(C.weeklyQuota(usage,true,100).label,/semanal restante/);
  assert.equal(C.weeklyQuota({...usage,windows:usage.windows.slice(0,1)},true,100).percent,null);
  assert.equal(C.weeklyQuota(usage,false,100).percent,null);
  assert.equal(C.weeklyQuota(usage,true,201).percent,null);
  usage.windows[1].remaining_percent=0;assert.equal(C.weeklyQuota(usage,true,100).percent,0);
  usage.windows[1].remaining_percent=101;assert.equal(C.weeklyQuota(usage,true,100).percent,null);
});
test('visible agents include compaction and exclude idle or waiting',()=>{
  const rows={working:{status:'active'},idle:{status:'completed'},waiting:{status:'waiting'},compacting:{status:'completed',context_compaction:{state:'compacting'}}};
  assert.deepEqual(C.stableOrder([],rows),['working','compacting']);
});
test('observed token samples distinguish zero from missing and invalid counters',()=>{
  assert.deepEqual(C.usageSample({tokens:{inputTokens:0,outputTokens:0}}),{input:0,output:0,total:0});
  for(const bad of [undefined,-1,1.5,'12',true,NaN,Infinity])assert.equal(C.usageSample({tokens:{inputTokens:bad,outputTokens:1}}).total,null);
  assert.equal(C.usageSample({inputTokens:12,outputTokens:3}).total,15);
});
test('new category hints preserve explicit existing identities',()=>{
  assert.equal(C.identity({agent_category:'tests',name:'Postgres performance'})[0],'Pruebas');
  for(const [name,label] of [['Investigar latencia','Rendimiento'],['Migrar base de datos','Datos'],['Despliegue de aplicación','Despliegues'],['Resolver conflictos de git','Versiones'],['Configurar webhook','Integraciones'],['Auditar accesibilidad','Accesibilidad']])assert.equal(C.identity({name})[0],label);
});
test('last-call counters are never replaced by cumulative thread snapshots or mixed across updates',()=>{
  const events=[{event:'decision_created',decision_id:'a',time:1},
    {event:'decision_usage',decision_id:'a',inputTokens:12,outputTokens:3,time:2},
    {event:'decision_usage_total',decision_id:'a',inputTokens:1200,outputTokens:300,time:2}];
  assert.equal(C.usageSample(C.decisions(events)[0]).total,15);
  assert.equal(C.decisions(events)[0].native_total_usage.inputTokens,1200);
  events.push({event:'decision_usage',decision_id:'a',inputTokens:20,time:3});
  assert.equal(C.usageSample(C.decisions(events)[0]).total,null);
  assert.equal(C.usageSample(C.decisions(events,{t:{decision_id:'a',tokens:{outputTokens:4}}})[0]).total,null);
});
test('probable events never downgrade confirmed identity and phase changes clear mismatch',()=>{
  const events=[{event:'decision_created',decision_id:'d',time:1},
    {event:'inference_observed',decision_id:'d',phase_id:'p',observed_model:'gpt-6-luna',evidence_confidence:'confirmed',inference_model_mismatch:true,time:2},
    {event:'inference_probable',decision_id:'d',phase_id:'p',observed_candidate_model:'gpt-6.1-sol',evidence_confidence:'probable',inference_model_mismatch:false,time:3}];
  const row=C.decisions(events)[0];assert.equal(row.evidence_confidence,'confirmed');assert.equal(row.observed_model,'gpt-6-luna');
  assert.equal(row.inference_model_mismatch,true);
  events.push({event:'phase_checkpoint',decision_id:'d',phase_id:'q',phase_status:'applied',time:4});
  assert.equal(C.decisions(events)[0].inference_model_mismatch,undefined);
});

test('request samples retain separate models without claiming completion mismatches',()=>{
  const events=[{event:'decision_created',decision_id:'d',time:1},
    ...['gpt-6-luna','gpt-6.1-sol'].map(model=>({event:'inference_metric',decision_id:'d',phase_id:'p',observed_candidate_model:model,inference_event_name:'codex.api_request',inference_model_mismatch:true}))];
  const row=C.decisions(events)[0];
  assert.equal(Object.keys(row.inference_samples).length,2);
  assert.equal(row.inference_model_mismatch,undefined);
  assert.equal(row.observed_model,undefined);
});

test('context gauges distinguish unknown, empty, full and latest measurement',()=>{
  assert.equal(C.contextGauge({}).percent,null);
  assert.equal(C.contextGauge({context_window:{used_percent:0,capacity_tokens:100,used_tokens:0}}).percent,0);
  assert.equal(C.contextGauge({context_window:{used_percent:180,capacity_tokens:100,used_tokens:180}}).percent,100);
  assert.match(C.contextGauge({context_window:{used_percent:37.2,capacity_tokens:1000,used_tokens:372}}).label,/37.2 %.*372 \/ 1000.*última medición/);
});

test('compaction supersedes token usage and remains distinct from missing measurements',()=>{
  const row={context_window:{used_percent:90,capacity_tokens:100,used_tokens:90},context_compaction:{state:'compacting'}};
  assert.equal(C.contextGauge(row).percent,null);
  assert.equal(C.contextGauge(row).compacting,true);
  assert.match(C.contextGauge(row).label,/Compactando contexto/);
  row.context_compaction.state='awaiting_usage';
  assert.equal(C.contextGauge(row).percent,null);
  assert.equal(C.contextGauge(row).compacting,false);
  assert.match(C.contextGauge(row).label,/esperando nueva medición/);
  delete row.context_compaction;
  assert.equal(C.contextGauge(row).percent,90);
  assert.match(C.contextGauge({}).label,/sin medición/);
});

test('quota expires without a new snapshot and disconnected or missing means unknown',()=>{
  const usage={remaining_percent:76,valid_until:200,windows:[{limit_id:'codex',window:'primary',duration_minutes:10080,remaining_percent:76,resets_at:200}]};
  assert.equal(C.quotaGauge(usage,true,199).percent,76);
  assert.equal(C.quotaGauge(usage,true,200).percent,null);
  assert.equal(C.quotaGauge(usage,false,100).percent,null);
  assert.equal(C.quotaGauge({},true,100).percent,null);
  assert.match(C.quotaGauge(usage,true,100).details,/semanal: 76 % disponible/);
  assert.equal(C.quotaGauge({...usage,remaining_percent:0},true,100).percent,0);
  assert.equal(C.quotaGauge({...usage,remaining_percent:100},true,100).percent,100);
  assert.match(C.quotaGauge({...usage,ordinary_usage_allowed:false},true,100).details,/uso incluido no está disponible/);
});

test('phase replay updates acceptance, separates old inference and retains metrics by class',()=>{
  const events=[{event:'decision_created',decision_id:'d',model:'gpt-5.6-terra',time:1},
    {event:'decision_accepted',decision_id:'d',accepted_model:'gpt-5.6-terra',time:2},
    {event:'inference_observed',decision_id:'d',observed_model:'gpt-5.6-terra',evidence_confidence:'confirmed',inference_input_tokens:120,inference_ttft_ms:35,time:3},
    {event:'phase_checkpoint',decision_id:'d',phase_id:'p',phase_status:'applied',phase_model:'gpt-5.6-sol',phase_effort:'high',time:4},
    {event:'inference_metric',decision_id:'d',inference_event_name:'codex.api_request',inference_http_status:503,evidence_confidence:'probable',time:5}];
  const row=C.decisions(events)[0];
  assert.equal(row.accepted_model,'gpt-5.6-sol');
  assert.equal(row.observed_model,undefined);
  assert.equal(row.evidence_confidence,undefined);
  assert.equal(row.prior_inferences[0].model,'gpt-5.6-terra');
  assert.equal(row.inference_input_tokens,120);
  assert.equal(row.inference_ttft_ms,35);
  assert.equal(row.inference_samples['codex.api_request:unknown'].inference_http_status,503);
  assert.equal(row.phase_events.length,1);
});

test('native retries do not finish or fail a decision and successful completion clears stale error',()=>{
  const events=[{event:'decision_created',decision_id:'r',time:1},
    {event:'decision_accepted',decision_id:'r',time:2,status:'inProgress'},
    {event:'native_turn_error',decision_id:'r',time:3,error_type:'responseStreamDisconnected',error_http_status:502,will_retry:true}];
  let row=C.decisions(events)[0];
  assert.equal(row.native_retries,1);assert.equal(row.error_type,undefined);assert.equal(row.finished,undefined);
  assert.equal(row.status,'inProgress');
  events.push({event:'decision_error',decision_id:'r',time:4,error_type:'thread_error'});
  events.push({event:'decision_completed',decision_id:'r',time:5,status:'completed'});
  row=C.decisions(events)[0];assert.equal(row.error_type,undefined);assert.equal(row.status,'completed');assert.equal(row.finished,5);
});

test('native failure category and bounded codes are available in history details',()=>{
  const row=C.decisions([{event:'decision_created',decision_id:'e',time:1},
    {event:'native_turn_error',decision_id:'e',time:2,error_type:'responseStreamDisconnected',will_retry:false},
    {event:'decision_completed',decision_id:'e',time:3,status:'failed',error_type:'httpConnectionFailed',error_http_status:503,error_source:'native'}])[0];
  assert.equal(row.native_retries,undefined);assert.equal(row.error_source,'native');
  assert.equal(C.errorLabel(row),'httpConnectionFailed · HTTP 503');
  assert.equal(C.errorLabel({error_type:'turn_rejected',error_code:-32603}),'turn_rejected · RPC -32603');
  assert.equal(C.errorLabel({error_type:'unknown'}),'Causa no proporcionada por Codex');
});

test('shadow response never overwrites active continuity, latency or classifier identity',()=>{
  const rows=C.decisions([
    {event:'decision_created',decision_id:'x',time:1,product_version:'0.3.0',build_id:'first'},
    {event:'decision_routed',decision_id:'x',time:2,routing_engine:'jev',continuity_strategy:'continue',engine_latency_ms:50},
    {event:'engine_comparison',decision_id:'x',time:3,routing_engine:'rules',engine_active:false,continuity_strategy:'reassess',engine_latency_ms:0,build_id:'later'}
  ]);
  assert.equal(rows[0].routing_engine,'jev');assert.equal(rows[0].continuity_strategy,'continue');
  assert.equal(rows[0].engine_latency_ms,50);assert.equal(rows[0].build_id,'first');
});

test('resumed tasks do not create history; recovered decisions merge without duplication',()=>{
  assert.equal(C.decisions([], {task:{name:'Old task',status:'idle'}}).length,0);
  const events=[{event:'decision_created',decision_id:'a',thread:'t',time:10},{event:'decision_accepted',decision_id:'a',time:11},{event:'decision_recovered',decision_id:'b',time:5},{event:'decision_recovered',decision_id:'b',time:5}];
  const rows=C.decisions(events);assert.equal(rows.length,2);assert.equal(rows.filter(x=>x.accepted).length,2);
});
test('rating and clearing survive replay without changing execution order',()=>{
  const events=[{event:'decision_created',decision_id:'a',time:10},{event:'decision_created',decision_id:'b',time:20},{event:'decision_quality',decision_id:'a',time:30,quality:'adequate'}];
  assert.equal(C.decisions(events)[0].id,'b');assert.equal(C.decisions(events)[1].quality,'adequate');
  events.push({event:'decision_quality',decision_id:'a',time:40,quality:''});assert.equal(C.decisions(events)[1].quality,'');assert.equal(C.decisions(events)[1].time,10);
});
test('model and reasoning ratings remain independent from the overall result',()=>{
  const events=[{event:'decision_created',decision_id:'a',time:10},{event:'decision_quality',decision_id:'a',time:20,quality:'adequate'},{event:'decision_quality',decision_id:'a',time:21,model_quality:'insufficient'},{event:'decision_quality',decision_id:'a',time:22,effort_quality:'excessive'}];
  const row=C.decisions(events)[0];
  assert.equal(row.quality,'adequate');assert.equal(row.model_quality,'insufficient');assert.equal(row.effort_quality,'excessive');
  events.push({event:'decision_quality',decision_id:'a',time:23,model_quality:''});
  assert.equal(C.decisions(events)[0].model_quality,'');assert.equal(C.decisions(events)[0].quality,'adequate');
});
test('live usage refreshes while a timestamp stays unchanged and pending uses requested settings',()=>{
  const events=[{event:'decision_created',decision_id:'a',time:10,model:'gpt-6-astra',effort:'high'}];
  const row={decision_id:'a',status:'pending',model:'gpt-6-astra',effort:'high',requested_model:'gpt-5.6-terra',requested_effort:'medium',tokens:{inputTokens:40}};
  assert.equal(C.setting(row,'model'),'gpt-5.6-terra');assert.equal(C.decisions(events,{t:row})[0].inputTokens,40);
  row.tokens.inputTokens=55;assert.equal(C.decisions(events,{t:row})[0].inputTokens,55);
  assert.equal(C.setting({status:'pending',model:'gpt-6-astra'},'model'),undefined);
});
test('shadow comparison does not replace the applied routing engine',()=>{
  const events=[{event:'decision_created',decision_id:'a',time:1},{event:'decision_routed',decision_id:'a',routing_engine:'rules',time:2},{event:'engine_comparison',decision_id:'a',routing_engine:'jev',engine_active:false,engine_status:'ok',proposed_model:'gpt-5.6-terra',time:3}];
  const d=C.decisions(events)[0];assert.equal(d.routing_engine,'rules');assert.equal(Object.keys(d.comparisons).length,1);
});
test('phase lifecycle metadata is retained without changing the decision model',()=>{
  const plan=[{id:'preparation',state:'configured'},{id:'execution',state:'accepted'}];
  const events=[{event:'decision_created',decision_id:'p',thread:'t',model:'gpt-5.6-terra',effort:'medium',time:1},{event:'decision_accepted',decision_id:'p',phase_status:'accepted',phase_transition:'compatible_group',accepted_model:'gpt-5.6-terra',phase_pipeline:plan,time:2},{event:'phase_settings_published',decision_id:'p',phase_status:'accepted',phase_model:'gpt-5.6-terra',phase_effort:'medium',configured_model:'gpt-5.6-terra',configured_effort:'medium',time:3}];
  const row=C.decisions(events)[0];assert.equal(row.model,'gpt-5.6-terra');assert.equal(row.phase_status,'accepted');assert.equal(row.phase_transition,'compatible_group');assert.equal(row.phase_model,'gpt-5.6-terra');
  assert.equal(row.accepted_model,'gpt-5.6-terra');assert.equal(row.configured_model,'gpt-5.6-terra');assert.deepEqual(row.phase_pipeline,plan);assert.equal(row.observed_model,undefined);
});
test('correlated checkpoint lifecycle updates its originating decision',()=>{
  const events=[{event:'decision_created',decision_id:'p',thread:'t',model:'gpt-5.6-terra',effort:'medium',time:1},
    {event:'phase_checkpoint',decision_id:'p',thread:'t',turn_id:'turn',phase_status:'applied',phase_transition:'compatible_group',phase_model:'gpt-5.6-sol',phase_effort:'high',time:2}];
  const row=C.decisions(events)[0];
  assert.equal(row.phase_status,'applied');assert.equal(row.phase_model,'gpt-5.6-sol');assert.equal(row.model,'gpt-5.6-terra');
});
test('active agent ordering remains stable through refresh and reactivation',()=>{
  const rows={b:{status:'active'},a:{status:'running'},c:{status:'idle'}};
  assert.deepEqual(C.stableOrder(['a','b'],rows),['a','b']);
  rows.d={status:'pending'};assert.deepEqual(C.stableOrder(['a','b'],rows),['a','b','d']);
  rows.a.status='completed';assert.deepEqual(C.stableOrder(['a','b','d'],rows),['b','d']);
});
test('sixteen distinct task categories and all effort dots have explicit identity',()=>{
  assert.equal(Object.keys(C.identities).length,16);assert.equal(new Set(Object.values(C.identities).map(x=>x[1])).size,16);
  for(const key of Object.keys(C.efforts))assert.equal(C.effortColors[key].length,2);
  assert.equal(C.identity({agent_category:'interface',name:'Audit'})[0],'Interfaces');
  assert.equal(C.model('gpt-6-astra'),'Astra 6');assert.equal(C.status('waiting'),'Esperando tu respuesta');
});
test('Windows model and effort badge colors retain readable contrast',()=>{
  const l = hex => {const rgb=hex.slice(1).match(/../g).map(n=>parseInt(n,16)/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;};
  for(const pair of [...Object.values(C.models),...Object.values(C.effortColors)])assert.ok((l(pair[0])+.05)/(l(pair[1])+.05)>=4.5);
});


test('model generations stay distinct while preserving family palette',()=>{
  assert.equal(C.model('gpt-6.1-sol'),'Sol 6.1');
  assert.equal(C.model('gpt-6-sol'),'Sol 6');
  assert.equal(C.model('gpt-5.6-sol'),'Sol 5.6');
  for(const id of ['gpt-6.1-sol','gpt-6-sol','gpt-5.6-sol']) assert.deepEqual(C.models[C.family(id)],C.models.Sol);
});

test('usage estimates deduplicate completions and exclude unconfirmed evidence',()=>{
  const event={event:'inference_observed',decision_id:'d',inference_event_id:'response1',evidence_confidence:'confirmed',estimate_basis:'standard_equivalent_not_billed',estimated_api_standard_usd:.02,estimated_codex_standard_credits:.5};
  const row=C.decisions([event,event,{...event,event:'inference_probable',inference_event_id:'response2'}])[0];
  assert.deepEqual(row.usage_estimates,{response1:{usd:.02,credits:.5}});
});

test('companion identity is stable and independent of routing metadata',()=>{
  const identities=Array.from({length:100},(_,i)=>C.companion('conversation-'+i));
  assert.equal(new Set(identities.map(i=>i.variant)).size,3);
  assert.deepEqual(C.companion('stable'),C.companion('stable'));
  for(const item of identities){assert.match(item.color,/^#[a-f0-9]{6}$/);assert.ok(item.name);}
});
test('companion state distinguishes compaction, waiting, completion and disconnection',()=>{
  assert.equal(C.companionState({status:'completed',context_compaction:{state:'compacting'}}).kind,'compacting');
  assert.equal(C.companionState({status:'waiting'}).kind,'waiting');
  assert.equal(C.companionState({status:'completed'}).kind,'done');
  assert.equal(C.companionState({status:'active'},false).kind,'offline');
  assert.equal(C.companionState({status:'interrupted'}).kind,'unknown');
});
test('compact companions keep waiting/error visible without treating them as live',()=>{
  const rows={working:{status:'active'},waiting:{status:'waiting'},failed:{status:'error'},done:{status:'completed'}};
  assert.deepEqual(C.stableOrder([],rows),['working']);
  assert.deepEqual(C.companionOrder([],rows),['working','waiting','failed']);
  assert.deepEqual(C.companionOrder(['waiting','working'],rows),['waiting','working','failed']);
});

test('live pipeline follows native steps, resets by turn and never completes a plan from turn end',()=>{
 const row={turn_id:'one',status:'active',live_plan:{turn_id:'one',steps:[{label:'Investigar',state:'completed'},{label:'Implementar',state:'active'},{label:'Validar',state:'pending'}]}};
 assert.deepEqual(C.executionPipeline(row).steps.map(s=>s.state),['completed','active','pending']);
 assert.equal(C.executionPipeline(row).steps[1].animate,true);
 assert.equal(C.executionPipeline(row,false).steps[1].animate,false);
 assert.equal(C.executionPipeline({...row,status:'waiting'}).steps[1].statusLabel,'En espera');
 assert.deepEqual(C.executionPipeline({...row,status:'completed'}).steps.map(s=>s.state),['completed','unknown','pending']);
 assert.equal(C.executionPipeline({...row,status:'interrupted'}).steps[1].state,'stopped');
 assert.equal(C.executionPipeline({...row,turn_id:'two'}).source,'Ejecución');
 assert.equal(C.executionPipeline({catalog_only:true}),null);
 assert.equal(C.executionPipeline({status:'completed',model:'gpt-6.1-sol',accepted_model:'gpt-6.1-sol'}).steps.at(-1).state,'completed');
});

test('live overlays never mutate cached historical evidence or token counters',()=>{
  const base=C.decisions([{event:'decision_created',decision_id:'d',time:1,phase_id:'p',model:'gpt-6-luna'},
    {event:'inference_observed',decision_id:'d',phase_id:'p',observed_model:'gpt-6-luna',evidence_confidence:'confirmed',time:2},
    {event:'decision_usage',decision_id:'d',inputTokens:10,outputTokens:2,time:3}]);
  const cached=structuredClone(base);
  const live=C.withLiveDecisions(base,{t:{decision_id:'d',name:'Updated task',phase_id:'q',tokens:{outputTokens:0}}});
  assert.equal(live[0].observed_model,undefined);
  assert.equal(live[0].inputTokens,undefined);
  assert.equal(live[0].outputTokens,0);
  assert.deepEqual(base,cached);
  assert.deepEqual(C.withLiveDecisions(base,{}),cached);
});
