const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('../monitor-ui/core.js');

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
test('ten distinct task categories and all effort dots have explicit identity',()=>{
  assert.equal(Object.keys(C.identities).length,10);assert.equal(new Set(Object.values(C.identities).map(x=>x[1])).size,10);
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
