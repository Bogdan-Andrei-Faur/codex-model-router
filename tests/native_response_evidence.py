"""Content-free native completion evidence shared by isolated probes."""
from collections import Counter

TOKEN_FIELDS=('inputTokens','cachedInputTokens','outputTokens','reasoningOutputTokens','totalTokens','cacheWriteInputTokens')


class RawEvidence:
    """Retain only safe metadata; never response items, IDs or arbitrary values."""
    def __init__(self):
        self.thread=None;self.turn=None;self.seen=set();self.counts=Counter()
        self.methods=Counter();self.shapes=Counter();self.models=Counter();self.totals=Counter()
        self.missing_usage=0;self.model_linked=0

    def consume(self,message):
        method=message.get('method');params=message.get('params') or {}
        # Native legacy events use params.msg; no raw items are traversed.
        payload=params.get('msg') if isinstance(params.get('msg'),dict) else params
        event_type=payload.get('type')
        if method not in ('rawResponse/completed','codex/event/raw_response_completed') and event_type!='raw_response_completed':return
        self.methods[method if method in ('rawResponse/completed','codex/event/raw_response_completed') else 'other_method']+=1
        # Schema-defined camelCase only. Legacy snake_case fields require an
        # explicitly reviewed adapter, not a guess based on matching values.
        for key in ('responseId','threadId','turnId','usage','usageMetadata','model','reasoningEffort'):
            value=payload.get(key);self.shapes[(key,type(value).__name__)]+=1
        if not (self.thread and self.turn and payload.get('threadId')==self.thread and payload.get('turnId')==self.turn):
            self.counts['unjoined']+=1;return
        response=payload.get('responseId')
        if not isinstance(response,str) or not response:self.counts['missing_response_id']+=1;return
        if response in self.seen:self.counts['duplicates']+=1;return
        self.seen.add(response);self.counts['joined']+=1
        usage=payload.get('usage')
        if (isinstance(usage,dict) and all(type(usage.get(k)) is int and 0<=usage[k]<=1_000_000_000 for k in TOKEN_FIELDS[:-1])
                and usage['cachedInputTokens']<=usage['inputTokens'] and usage['reasoningOutputTokens']<=usage['outputTokens']
                and usage['totalTokens']==usage['inputTokens']+usage['outputTokens']):
            for k in TOKEN_FIELDS:
                if type(usage.get(k)) is int and 0<=usage[k]<=1_000_000_000:self.totals[k]+=usage[k]
        else:self.missing_usage+=1
        metadata=payload.get('usageMetadata')
        if isinstance(metadata,dict):
            # Amount units and arbitrary provider metadata have no established
            # identity/currency semantics. Only their structural types survive.
            for k in ('amount','metadata'):self.shapes[('usageMetadata.'+k,type(metadata.get(k)).__name__)]+=1
            body=metadata.get('metadata')
            if isinstance(body,dict):
                known={'model','model_slug','model_name','service_tier','reasoning_effort','cost','credits','currency',
                    'input_tokens','output_tokens','cached_input_tokens','usage','rate_limit','rate_limit_usage'}
                for k,v in body.items():
                    self.shapes[('usageMetadata.metadata.'+(k if k in known else 'other_key'),type(v).__name__)]+=1

    def report(self):
        return {'methods':dict(self.methods),'counts':dict(self.counts),
            'field_types':[{'key':k[0],'type':k[1],'count':v} for k,v in sorted(self.shapes.items())],
            'response_tokens_sum':dict(self.totals) or None,'responses_missing_usage':self.missing_usage,
            'model_linked_responses':self.model_linked,
            'complete_inference_cost_coverage':'unknown','raw_payloads_saved':False,'identity_values_saved':False}
