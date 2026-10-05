import json
import unittest
from tests.probe_inference_identity import IdentityShapes


def attr(key,value):
    return {'key':key,'value':{'stringValue':value}}


class IdentityProbeTests(unittest.TestCase):
    def test_raw_usage_identity_does_not_invent_model_or_retain_response_content(self):
        shapes=IdentityShapes();shapes.native_thread='private-thread';shapes.native_turn='private-turn'
        params=dict(threadId='private-thread',turnId='private-turn',responseId='private-response',
                    usage={'inputTokens':10},items=['PRIVATE_CONTENT'],
                    usageMetadata={'amount':'PRIVATE_AMOUNT','metadata':{'secret-key':'SECRET_VALUE'}})
        shapes.consume_raw({'method':'rawResponse/completed','params':params})
        shapes.consume_raw({'method':'rawResponse/completed','params':params})
        shapes.consume_raw({'method':'rawResponse/completed','params':dict(params,turnId='older-turn')})
        report=shapes.report()
        raw=report['raw_response_evidence']
        self.assertEqual(raw['counts'],dict(joined=1,duplicates=1,unjoined=1))
        self.assertEqual(raw['methods'],{'rawResponse/completed':3})
        self.assertEqual(raw['model_linked_responses'],0)
        self.assertIn({'key':'usageMetadata.metadata.other_key','type':'str','count':1},raw['field_types'])
        for value in ('private-thread','private-turn','private-response','PRIVATE_CONTENT',
                      'PRIVATE_AMOUNT','secret-key','SECRET_VALUE'):
            self.assertNotIn(value,json.dumps(report))

    def test_posterior_model_tags_require_own_conversation_and_deduplicate_logs(self):
        shapes=IdentityShapes();shapes.native_thread='private-thread'
        record={'event_kind':'response.completed','thread_id':'private-thread',
                'model':'gpt-6-luna','event_id':'private-event','response_text':'PRIVATE_OUTPUT'}
        shapes.consume(record);shapes.consume(record)
        shapes.consume(dict(record,event_id='other',thread_id='other-thread',model='gpt-6-astra'))
        shapes.consume(dict(record,event_id='unknown',model='PRIVATE_MODEL'))
        report=shapes.report()
        self.assertEqual(report['posterior_model_log_records'],{'gpt-6-luna':1})
        self.assertEqual(report['complete_inference_cost_coverage'],'unknown')
        self.assertFalse(report['policy_activation_eligible'])
        for value in ('private-thread','private-event','PRIVATE_OUTPUT','PRIVATE_MODEL'):
            self.assertNotIn(value,json.dumps(report))

    def test_native_usage_replaces_cumulative_snapshots_without_inventing_turn_identity(self):
        shapes=IdentityShapes();shapes.native_thread='private-thread';shapes.native_turn='private-turn'
        def event(total,**extra):
            return dict(threadId=shapes.native_thread,tokenUsage={'total':total},**extra)
        shapes.consume_usage(event({'inputTokens':100,'outputTokens':10,'private':'SECRET'}))
        shapes.consume_usage(event({'inputTokens':120,'outputTokens':14,'cachedInputTokens':True,'reasoningOutputTokens':-1}))
        shapes.consume_usage(event({'inputTokens':999},turnId='different-turn'))
        shapes.consume_usage({'threadId':'other-thread','tokenUsage':{'total':{'inputTokens':999}}})
        report=shapes.report()
        self.assertEqual(report['native_thread_total_tokens'],{'inputTokens':120,'outputTokens':14})
        self.assertEqual(report['native_usage_updates'],2)
        self.assertEqual(report['native_usage_updates_with_turn_id'],0)
        self.assertNotIn('SECRET',json.dumps(report))

    def test_raw_shape_diagnostics_do_not_expose_values_or_unknown_keys(self):
        shapes=IdentityShapes();shapes.native_thread='thread-private-value';shapes.native_turn='turn-private-value'
        payload={'resourceLogs':[{'resource':{'attributes':[attr('private-resource','PRIVATE_RESOURCE')]},
            'scopeLogs':[{'logRecords':[{'attributes':[attr('conversation.id',shapes.native_thread),
                attr('private-secret-key',shapes.native_turn),attr('prompt','PRIVATE_PROMPT')]}]}]}]}
        shapes.inspect(payload)
        result=json.dumps(shapes.report())
        for private in ('thread-private-value','turn-private-value','private-secret-key','PRIVATE_RESOURCE','PRIVATE_PROMPT'):
            self.assertNotIn(private,result)
        self.assertEqual(shapes.report()['native_rpc_matches'][1]['key'],'other_key')

    def test_turn_span_never_links_a_completion_without_native_trace_context(self):
        shapes=IdentityShapes();shapes.native_turn='turn-private-value'
        shapes.inspect({'resourceLogs':[{'scopeLogs':[{'logRecords':[{'attributes':[attr('event.kind','response.completed')]}]}]}],
            'resourceSpans':[{'scopeSpans':[{'spans':[{'traceId':'a'*32,'spanId':'b'*16,
                'attributes':[attr('turn.id',shapes.native_turn)]}]}]}]})
        report=shapes.report()
        self.assertEqual(report['trace_spans'],1)
        self.assertEqual(report['completions_with_trace_context'],0)
        self.assertEqual(report['completions_linked_to_native_turn_span'],0)

    def test_trace_join_requires_explicit_context_and_follows_parent_without_cycles(self):
        shapes=IdentityShapes();shapes.native_turn='turn-private-value'
        trace='a'*32;parent='b'*16;child='c'*16
        shapes.inspect({'resourceLogs':[{'scopeLogs':[{'logRecords':[{'traceId':trace,'spanId':child,
            'attributes':[attr('event.kind','response.completed')]}]}]}],
            'resourceSpans':[{'scopeSpans':[{'spans':[
                {'traceId':trace,'spanId':child,'parentSpanId':parent,'attributes':[]},
                {'traceId':trace,'spanId':parent,'parentSpanId':child,'attributes':[attr('turn.id',shapes.native_turn)]}]}]}]})
        self.assertEqual(shapes.report()['completions_linked_to_native_turn_span'],1)
        shapes.native_turn='different';shapes.spans[(trace,parent)]=(child,False)
        self.assertEqual(shapes.report()['completions_linked_to_native_turn_span'],0)
