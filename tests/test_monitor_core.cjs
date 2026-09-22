const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('../monitor-ui/core.js');

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
test('live usage refreshes while a timestamp stays unchanged and pending uses requested settings',()=>{
  const events=[{event:'decision_created',decision_id:'a',time:10,model:'gpt-6-astra',effort:'high'}];
  const row={decision_id:'a',status:'pending',model:'gpt-6-astra',effort:'high',requested_model:'gpt-5.6-terra',requested_effort:'medium',tokens:{inputTokens:40}};
  assert.equal(C.setting(row,'model'),'gpt-5.6-terra');assert.equal(C.decisions(events,{t:row})[0].inputTokens,40);
  row.tokens.inputTokens=55;assert.equal(C.decisions(events,{t:row})[0].inputTokens,55);
  assert.equal(C.setting({status:'pending',model:'gpt-6-astra'},'model'),undefined);
});
test('shadow comparison does not replace the applied routing engine',()=>{
  const events=[{event:'decision_created',decision_id:'a',time:1},{event:'decision_routed',decision_id:'a',routing_engine:'rules',time:2},{event:'engine_comparison',decision_id:'a',routing_engine:'provider',engine_active:false,engine_status:'ok',proposed_model:'gpt-5.6-terra',time:3}];
  const d=C.decisions(events)[0];assert.equal(d.routing_engine,'rules');assert.equal(Object.keys(d.comparisons).length,1);
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
  assert.equal(C.model('gpt-6-astra'),'Astra');assert.equal(C.status('waiting'),'Esperando tu respuesta');
});
test('Windows model and effort badge colors retain readable contrast',()=>{
  const l = hex => {const rgb=hex.slice(1).match(/../g).map(n=>parseInt(n,16)/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;};
  for(const pair of [...Object.values(C.models),...Object.values(C.effortColors)])assert.ok((l(pair[0])+.05)/(l(pair[1])+.05)>=4.5);
});
