"""Common metadata-only evidence export and externally reported outcome checks.

No prompts, responses, credentials, account usage or raw OTLP are exported.
Legacy execution provenance is unknown, even when a collection platform is known.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import hmac
import json
import math
import re
from pathlib import Path
from codex_model_router.paths import resource_root
import secrets
import struct
import sys
import time
import uuid
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

from codex_model_router.telemetry.inference_attribution import COUNTERS
from codex_model_router.routing.model_catalog import MODELS
from codex_model_router.evaluation.outcome_evaluation import evaluate_checks, record_check
from codex_model_router.evaluation.trial_evaluation import evaluate_trials, record_attempt
from codex_model_router.telemetry.error_diagnostics import ERROR_TYPES, HTTP_ERRORS
from codex_model_router.storage.state_store import private_open

SCHEMA = 'router-evidence/2'
MAX_FILE = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_MEMBERS = 1024
MAX_LINES = 100000
MAX_RECORDS = 50000
MAX_SNAPSHOTS = 10000
MAX_LINE = 256 * 1024
MAX_JSON = 2 * 1024 * 1024
MAX_OUTPUT = 64 * 1024 * 1024
MAX_CENTRAL_DIRECTORY = 1024 * 1024


class EvidenceBudget:
    def __init__(self):
        self.bytes = self.members = self.lines = self.output = 0

    def consume(self, field, count, maximum):
        value = getattr(self, field) + count
        if value > maximum:
            raise ValueError('evidence_budget_exceeded')
        setattr(self, field, value)

    def lines_from(self, stream):
        first = True
        while True:
            line = stream.readline(MAX_LINE + 1)
            if not line:
                return
            self.consume('bytes', len(line), MAX_TOTAL_BYTES)
            self.consume('lines', 1, MAX_LINES)
            if len(line) > MAX_LINE:
                raise ValueError('evidence_line_too_large')
            yield line.decode('utf-8-sig' if first else 'utf-8')
            first = False

    def json_from(self, stream):
        data = stream.read(MAX_JSON + 1)
        self.consume('bytes', len(data), MAX_TOTAL_BYTES)
        if len(data) > MAX_JSON:
            raise ValueError('evidence_json_too_large')
        return json.loads(data.decode('utf-8-sig'))


def check_zip_budget(stream):
    """Bound central-directory allocation before ZipFile builds Python objects."""
    stream.seek(0, 2)
    size = stream.tell()
    if size > MAX_TOTAL_BYTES:
        raise ValueError('evidence_budget_exceeded')
    stream.seek(max(0, size - 65557))
    tail = stream.read(65557)
    start = tail.rfind(b'PK\x05\x06')
    if start < 0 or len(tail) - start < 22:
        raise BadZipFile('missing_directory')
    _, disk, directory_disk, local_count, count, directory_bytes, _, comment = struct.unpack_from('<4s4H2LH', tail, start)
    if len(tail) - start != 22 + comment or disk or directory_disk or local_count != count:
        raise BadZipFile('unsupported_directory')
    # ZipFile may override even small classic EOCD fields from a ZIP64 record.
    # Evidence's budgets do not need ZIP64: reject it before metadata parsing.
    end_offset = size - len(tail) + start
    if end_offset >= 20:
        stream.seek(end_offset - 20)
        if stream.read(4) == b'PK\x06\x07':
            raise ValueError('zip64_evidence_not_supported')
    if count > MAX_MEMBERS or directory_bytes > MAX_CENTRAL_DIRECTORY:
        raise ValueError('evidence_budget_exceeded')
    stream.seek(0)
IDENTITIES = ('decision_id','thread','turn_id','phase_id','session','runtime_instance','inference_event_id',
              'evaluation_id','workload_id','check_id','trial_run_id','engine_comparison_id')
ENUMS = {
    'event': {'decision_created','decision_recovered','decision_routed','decision_accepted','decision_completed',
              'decision_usage','decision_quality','engine_comparison','phase_checkpoint','phase_started',
              'inference_observed','inference_probable','inference_metric','native_turn_error','outcome_check',
              'policy_comparison','policy_comparison_jev','trial_attempt','decision_usage_total','decision_usage_baseline'},
    'status': {'pending','completed','failed','interrupted','accepted','active','error'},
    'evidence_confidence': {'confirmed','correlated','probable','legacy_unknown'},
    'phase_status': {'requested','applied','unchanged','preserved','requires_new_turn','failed','accepted','active','completed'},
    'phase_transition': {'same_model','compatible_group','blocked_astra_boundary','blocked_review_boundary','unverified_transition','unknown_model'},
    'risk_basis': {'current','inherited','legacy_uncertain','none'},
    'phase_complexity': {'simple','normal','complex','critical'},
    'inference_timestamp_source': {'event','observed'},
    'routing_engine': {'jev','rules','provider'}, 'engine_status': {'ok','unavailable','error','timeout','disabled','invalid','not_configured','skipped','abstained'},
    'quality': {'adequate','insufficient','excessive',''}, 'model_quality': {'adequate','insufficient','excessive',''},
    'effort_quality': {'adequate','insufficient','excessive',''},
    'execution_platform': {'darwin','linux','win32','unknown'},
    'workload_origin': {'real','synthetic','unknown'}, 'evaluation_arm': {'baseline','candidate'},
    'check_result': {'passed','failed'}, 'check_source': {'external_reported'},
    'usage_scope': {'last_native_update','thread_total_snapshot'}, 'estimate_basis': {'standard_equivalent_not_billed'},
    'policy_mode': {'reference','compare','validated'}, 'candidate_status': {'compared','applied','unavailable'},
    'work_class': {'mechanical','bounded','engineering','demanding','exceptional','critical'},
    'failure_class': {'none','infrastructure','external_check','unknown'},
    'trial_split': {'adjustment','held_out'},
    'error_type': set(ERROR_TYPES) | set(HTTP_ERRORS) | {'unknown','activeTurnNotSteerable'},
}
MODEL_FIELDS = ('model','accepted_model','phase_model','phase_source_model','previous_model','observed_model',
                'observed_candidate_model','expected_model','proposed_model')
EFFORT_FIELDS = ('effort','accepted_effort','phase_effort','phase_source_effort','observed_effort','observed_candidate_effort','expected_effort','proposed_effort')
NUMBERS = ('time','routing_policy_version','candidate_policy_version','attempt_index','engine_provider_cost_usd','engine_latency_ms','engine_input_tokens','engine_output_tokens','engine_cached_tokens',
           'inputTokens','outputTokens','cachedInputTokens','reasoningOutputTokens',
           'inference_input_tokens','inference_output_tokens','inference_cached_tokens','inference_reasoning_tokens',
           'inference_duration_ms','inference_ttft_ms','inference_attempt','inference_sample_count','inference_failure_count',
           'estimated_api_standard_usd','estimated_codex_standard_credits',
           'usage_baseline_inputTokens','usage_baseline_cachedInputTokens','usage_baseline_outputTokens',
           'native_total_inputTokens','native_total_cachedInputTokens','native_total_outputTokens')
BOOLS = ('engine_active','engine_applied','will_retry','inference_model_mismatch','inference_effort_mismatch','risk_active','legacy_uncertain')


def pseudonym(key, field, value):
    return hmac.new(key, (field+'\0'+value).encode(), hashlib.sha256).hexdigest()[:32]


def scrub(row, key):
    if not isinstance(row,dict) or row.get('event') not in ENUMS['event']:
        return None
    result = {}
    for field in IDENTITIES:
        if isinstance(row.get(field),str) and row[field]:
            result[field] = pseudonym(key, field, row[field])
    checks = row.get('trial_required_checks')
    if isinstance(checks,list) and len(checks) <= 100 and all(isinstance(v,str) and v for v in checks):
        result['trial_required_checks'] = [pseudonym(key,'check_id',v) for v in checks]
    for field, allowed in ENUMS.items():
        if isinstance(row.get(field),str) and row[field] in allowed:
            result[field] = row[field]
    for field in MODEL_FIELDS:
        if isinstance(row.get(field),str) and row[field] in MODELS:
            result[field] = row[field]
    for field in EFFORT_FIELDS:
        if row.get(field) in ('low','medium','high','xhigh','max','ultra'):
            result[field] = row[field]
    for field in NUMBERS:
        value = row.get(field)
        if type(value) in (int,float) and math.isfinite(value) and 0 <= value <= 10**12:
            result[field] = value
    for field in BOOLS:
        if type(row.get(field)) is bool:
            result[field] = row[field]
    version = row.get('product_version')
    if isinstance(version,str) and re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}',version):
        result['product_version'] = version
    for field in ('build_id','router_build_id'):
        value = row.get(field)
        if isinstance(value,str) and re.fullmatch('[a-f0-9]{16}',value):
            result[field] = value
    if row.get('event') == 'inference_observed' and 'evidence_confidence' not in result:
        result['evidence_confidence'] = 'legacy_unknown'
    return result


def summarize(records):
    created = {}; terminal = {}; usage = {}; comparisons = {}; estimates = {}; checks = []
    for row in records:
        kind, decision = row.get('event'), row.get('decision_id')
        if kind == 'decision_created' and decision:
            created[decision] = row
        if kind == 'decision_completed':
            terminal[decision] = row.get('status','unknown')
        if kind == 'decision_usage':
            # Native usage updates are snapshots. A sequence is never added up.
            usage[decision] = {k:row[k] for k in ('inputTokens','outputTokens','cachedInputTokens','reasoningOutputTokens') if k in row}
        if kind == 'engine_comparison' and row.get('engine_active') is True:
            comparisons[(decision,row.get('routing_engine'))] = row
        if kind == 'inference_observed' and row.get('evidence_confidence') == 'confirmed' and row.get('estimate_basis') == 'standard_equivalent_not_billed' and row.get('inference_event_id'):
            estimates[row['inference_event_id']] = row
        if kind == 'outcome_check':
            checks.append(row)
    pairs = defaultdict(dict)
    for row in records:
        if row.get('event') == 'phase_checkpoint':
            pairs[(row.get('thread'),row.get('turn_id'),row.get('phase_id'))][row.get('phase_status')] = row
    applied = [r for r in records if r.get('event') == 'phase_checkpoint' and r.get('phase_status') == 'applied']
    model_changes = sum(r.get('phase_transition') == 'compatible_group' and r.get('phase_source_model') != r.get('phase_model') for r in applied)
    return {'created_decisions':len(created), 'terminal_status':dict(Counter(terminal.get(d,'not_recorded') for d in created)),
            'event_counts':dict(Counter(r.get('event') for r in records)),
            'versions':dict(Counter(r.get('product_version','unknown') for r in created.values())),
            'execution_provenance':dict(Counter(r.get('execution_platform','unknown') for r in created.values())),
            'usage_snapshot_decisions':len(set(created)&set(usage)),
            'last_native_usage_totals':{k:sum(usage.get(d,{}).get(k,0) for d in created) for k in ('inputTokens','outputTokens','cachedInputTokens','reasoningOutputTokens')},
            'usage_limit':'Last native snapshot per decision; not per-model billing or total task cost.',
            'classifier_input_tokens':sum(r.get('engine_input_tokens',0) for r in comparisons.values()),
            'classifier_output_tokens':sum(r.get('engine_output_tokens',0) for r in comparisons.values()),
            'classifier_metric_coverage':sum('engine_input_tokens' in r or 'engine_output_tokens' in r for r in comparisons.values()),
            'classifier_active_comparisons':len(comparisons),
            'retry_notifications':sum(r.get('event') == 'native_turn_error' and r.get('will_retry') is True for r in records),
            'confirmed_inference_events':sum(r.get('event') == 'inference_observed' and r.get('evidence_confidence') == 'confirmed' for r in records),
            'legacy_observed_events':sum(r.get('event') == 'inference_observed' and r.get('evidence_confidence') == 'legacy_unknown' for r in records),
            'phase_settings_applied':len(applied), 'model_changes_applied':model_changes,
            'same_model_settings_applied':sum(r.get('phase_transition') == 'same_model' for r in applied),
            'effort_only_changes_applied':sum(bool(r.get('phase_transition') == 'same_model' and r.get('phase_source_effort') and r.get('phase_effort') and r['phase_source_effort'] != r['phase_effort']) for r in applied),
            'estimated_standard_api_usd':sum(r.get('estimated_api_standard_usd',0) for r in estimates.values()),
            'estimate_event_coverage':len(estimates), 'billed_cost_observed':False,
            'objective_checks':evaluate_checks(records), 'paired_trials':evaluate_trials(records), 'causal_savings_demonstrated':False}


def export(source, output, platform='unknown', version=None):
    source, output = Path(source), Path(output)
    if platform not in ('macos','ubuntu','windows','unknown') or (version is not None and (not isinstance(version,str) or not re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}',version))):
        raise ValueError('invalid_export_scope')
    key = secrets.token_bytes(32); cutoff = time.time(); records = []; snapshots = []; malformed = 0; duplicates = 0; seen = set()
    budget = EvidenceBudget()
    def history(stream):
        nonlocal malformed, duplicates
        for line in budget.lines_from(stream):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                row = scrub(raw,key)
            except (ValueError, TypeError, RecursionError):
                malformed += 1; continue
            if row is None or row.get('time',0) > cutoff:
                continue
            fingerprint = hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':')).encode()).digest()
            if fingerprint in seen:
                duplicates += 1; continue
            if len(records) >= MAX_RECORDS:
                raise ValueError("evidence_budget_exceeded")
            encoded = json.dumps(row, separators=(",", ":"))
            budget.consume("output", len(encoded.encode("utf-8")) + 1, MAX_OUTPUT)
            seen.add(fingerprint); records.append(row)
    def snapshot(raw):
        if not isinstance(raw,dict):
            return
        result = {'counter_semantics':'cumulative_per_process_not_additive_over_time'}
        heartbeat = raw.get('heartbeat')
        if type(heartbeat) in (int,float) and math.isfinite(heartbeat):
            result['heartbeat'] = heartbeat
            result['fresh_heartbeat_at_collection'] = 0 <= cutoff-heartbeat <= 120
        result['process_liveness_checked'] = False
        for field in ('stats','telemetry'):
            values = raw.get(field)
            result[field] = {k:v for k,v in values.items() if k in SNAPSHOT_FIELDS and type(v) in (int,float) and math.isfinite(v) and 0 <= v <= 10**12} if isinstance(values,dict) else {}
        if not result["stats"] and not result["telemetry"] and "heartbeat" not in result:
            return
        if len(snapshots) >= MAX_SNAPSHOTS:
            raise ValueError("evidence_budget_exceeded")
        budget.consume("output", len(json.dumps(result).encode("utf-8")), MAX_OUTPUT)
        snapshots.append(result)
    if source.is_dir():
        for filename in ('history.jsonl','history.recovered.jsonl'):
            path = source/filename
            if path.exists():
                budget.consume('members', 1, MAX_MEMBERS)
                with path.open('rb') as stream:
                    import os
                    if os.fstat(stream.fileno()).st_size > MAX_FILE:
                        raise ValueError('history_file_too_large')
                    history(stream)
        for path in source.glob('status-*.json'):
            budget.consume('members', 1, MAX_MEMBERS)
            with path.open('rb') as stream:
                try:
                    raw = budget.json_from(stream)
                except (json.JSONDecodeError, UnicodeError, RecursionError):
                    malformed += 1
                    continue
                snapshot(raw)
    else:
        with source.open('rb') as archive:
            check_zip_budget(archive)
            with ZipFile(archive) as z:
                names = z.namelist()
                if len(names) > MAX_MEMBERS:
                    raise ValueError('evidence_budget_exceeded')
                if len(names) != len(set(names)):
                    raise ValueError('duplicate_archive_members')
                for name in names:
                    budget.consume('members', 1, MAX_MEMBERS)
                    info = z.getinfo(name)
                    if info.file_size > MAX_FILE:
                        raise ValueError('archive_member_too_large')
                    if name.endswith(('data/history.jsonl','data/history.recovered.jsonl')) or name == 'events.jsonl':
                        with z.open(info) as stream:
                            history(stream)
                    elif name.endswith('data/bridge_snapshots.jsonl'):
                        with z.open(info) as stream:
                            for line in budget.lines_from(stream):
                                try:
                                    raw = json.loads(line)
                                except (ValueError, RecursionError):
                                    malformed += 1
                                    continue
                                snapshot(raw)
                    elif ('/status/status-' in name and name.endswith('.json')) or name == 'snapshots.json':
                        with z.open(info) as stream:
                            try:
                                raw = budget.json_from(stream)
                            except (json.JSONDecodeError, UnicodeError, RecursionError):
                                malformed += 1
                                continue
                        if name == 'snapshots.json':
                            if not isinstance(raw, list):
                                raise ValueError('invalid_snapshot_array')
                            if len(raw) > MAX_SNAPSHOTS:
                                raise ValueError('evidence_budget_exceeded')
                            for row in raw:
                                snapshot(row)
                        else:
                            snapshot(raw)
    if version:
        selected = {r.get('decision_id') for r in records if r.get('event') == 'decision_created' and r.get('product_version') == version}
        records = [r for r in records if r.get('product_version') == version or (r.get('decision_id') in selected and 'product_version' not in r)]
    records.sort(key=lambda r:r.get('time',0))
    summary = summarize(records)
    manifest = {'schema':SCHEMA, 'collection_id':uuid.uuid4().hex,'collected_at_unix':cutoff,'collection_platform':platform,
                'historical_execution_platform':'unknown_unless_stored_on_event', 'selected_version':version,
                'identity_semantics':'HMAC pseudonyms consistent only within this export; key discarded.',
                'snapshot_semantics':'Sequential bounded reads; not a globally atomic snapshot.',
                'origin_semantics':'Legacy and unlabelled workload origin is unknown; external check origin is supplied.',
                'malformed_records':malformed,'exact_duplicate_records_removed':duplicates,
                'excludes':['prompts','titles','responses','secrets','raw_otlp','account_usage','paths','freeform_errors'],
                'limitations':['Completion is not correctness.','Native settings acceptance is not posterior inference proof.',
                               'Different platforms/workloads/windows are descriptive, not a controlled platform experiment.',
                               'Token snapshots and standard estimates are not billed cost.']}
    contents = {'events.jsonl':''.join(json.dumps(r,separators=(',',':'))+'\n' for r in records),
                'summary.json':json.dumps(summary,indent=2), 'snapshots.json':json.dumps(snapshots,separators=(',',':'))}
    # Every successful export must be readable under the same import budgets.
    if len(contents['snapshots.json'].encode('utf-8')) > MAX_JSON:
        raise ValueError('evidence_json_too_large')
    manifest['sha256'] = {name:hashlib.sha256(value.encode()).hexdigest() for name,value in contents.items()}
    # Exclusive output creation preserves prior exports and avoids replacing input.
    if sum(len(value.encode('utf-8')) for value in contents.values()) > MAX_OUTPUT:
        raise ValueError('evidence_budget_exceeded')
    with private_open(output, 'xb') as stream:
        with ZipFile(stream,'w',ZIP_DEFLATED) as z:
            for name,value in contents.items(): z.writestr(name,value)
            z.writestr('manifest.json',json.dumps(manifest,indent=2))
    return summary


SNAPSHOT_FIELDS = set(COUNTERS) | {'telemetry_events','telemetry_confirmed','telemetry_probable','telemetry_unattributed',
                                 'requests','records_scanned','eligible_records','invalid_requests','invalid_size','completion_records','accepted','identity_conflicts'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    exp = sub.add_parser('export')
    exp.add_argument('--source',type=Path,required=True,help='State directory or evidence ZIP (read-only).')
    exp.add_argument('--output',type=Path,required=True)
    exp.add_argument('--platform',choices=('macos','ubuntu','windows','unknown'),default='unknown')
    exp.add_argument('--version')
    check = sub.add_parser('record-check')
    check.add_argument('--state',type=Path,default=resource_root()/'state')
    for name in ('decision-id','evaluation-id','workload-id','check-id'): check.add_argument('--'+name,required=True)
    check.add_argument('--arm',choices=('baseline','candidate'),required=True)
    check.add_argument('--result',choices=('passed','failed'),required=True)
    check.add_argument('--origin',choices=('real','synthetic'),required=True)
    attempt = sub.add_parser('record-attempt')
    attempt.add_argument('--state',type=Path,required=True)
    for name in ('decision-id','evaluation-id','workload-id','run-id'):
        attempt.add_argument('--'+name,required=True)
    attempt.add_argument('--arm',choices=('baseline','candidate'),required=True)
    attempt.add_argument('--attempt',type=int,required=True)
    attempt.add_argument('--origin',choices=('real','synthetic'),required=True)
    attempt.add_argument('--split',choices=('adjustment','held_out'),required=True)
    attempt.add_argument('--check',action='append',required=True)
    evaluate = sub.add_parser('evaluate-trials')
    evaluate.add_argument('--state',type=Path,required=True)
    args = parser.parse_args()
    try:
        if args.command == 'export':
            print(json.dumps(export(args.source,args.output,args.platform,args.version),indent=2))
        elif args.command == 'record-check':
            record_check(args.state,args.decision_id,args.evaluation_id,args.workload_id,args.check_id,args.arm,args.result,args.origin)
            print('External check result recorded; not independently attested.')
        elif args.command == 'record-attempt':
            record_attempt(args.state,args.decision_id,args.evaluation_id,args.workload_id,args.run_id,args.arm,args.attempt,args.origin,args.check,args.split)
            print('Trial attempt bound; no check or quality result inferred.')
        else:
            from codex_model_router.storage.state_store import read_records
            print(json.dumps(evaluate_trials(list(read_records(args.state/'history.jsonl'))),indent=2))
    except (ValueError, OSError, BadZipFile):
        parser.exit(1,'Evidence operation failed; check inputs and use a new output path.\n')

if __name__ == '__main__':
    main()
