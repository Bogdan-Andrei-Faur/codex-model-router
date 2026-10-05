"""Content-free attribution stages shared by the bridge and monitor payload."""
import math
COUNTERS = (
    'telemetry_records', 'telemetry_duplicates', 'telemetry_missing_model',
    'telemetry_missing_thread_id', 'telemetry_missing_turn_id', 'telemetry_missing_timestamp',
    'telemetry_unknown_thread', 'telemetry_turn_mismatch', 'telemetry_stale',
    'telemetry_inactive', 'telemetry_no_candidate', 'telemetry_ambiguous',
    'telemetry_model_mismatch', 'telemetry_effort_mismatch', 'telemetry_invalid_timestamp',
)


def attribute(record, threads, now):
    """Return (candidate, confirmed, rejection); never invent a missing identity.

    Complete native identities select a turn before any expected-model comparison.
    Without both identities, model/effort matching remains only probable evidence.
    """
    exact = bool(record.get('thread_id') and record.get('turn_id'))
    stamp = record.get('timestamp')
    if stamp is not None and (type(stamp) not in (int,float) or not math.isfinite(stamp) or stamp < 0 or stamp > now + 5):
        return None, False, 'invalid_timestamp'
    candidates = []
    rejection = 'no_candidate'
    if record.get('thread_id') and record['thread_id'] not in threads:
        return None, False, 'unknown_thread'
    for tid, row in threads.items():
        if record.get('thread_id') and record['thread_id'] != tid:
            continue
        if record.get('turn_id') and record['turn_id'] != row.get('turn_id'):
            rejection = 'turn_mismatch'
            continue
        if row.get('phase_status') not in ('accepted', 'active', 'completed'):
            rejection = 'inactive'
            continue
        if row.get('phase_status') == 'completed' and now - row.get('completed_at', 0) > 15:
            rejection = 'stale'
            continue
        if stamp is not None and stamp < max(row.get('decision_started_at', 0), row.get('phase_accepted_at', 0)):
            rejection = 'stale'
            continue
        if not exact:
            expected_model = row.get('phase_model') or row.get('accepted_model') or row.get('model')
            expected_effort = row.get('phase_effort') or row.get('accepted_effort') or row.get('effort')
            if record.get('model') != expected_model:
                rejection = 'model_mismatch'
                continue
            if record.get('effort') and expected_effort and record['effort'] != expected_effort:
                rejection = 'effort_mismatch'
                continue
        candidates.append((tid, row))
    if len(candidates) != 1:
        return None, False, 'ambiguous' if len(candidates) > 1 else rejection
    candidate = candidates[0]
    # ObservedTimestamp is collection time, not proof that the inference ran
    # after a settings update. It may correlate a phase but cannot confirm it.
    confirmed = exact and (not candidate[1].get('phase_accepted_at') or
                           (record.get('timestamp') is not None and record.get('timestamp_source') != 'observed'))
    return candidate, bool(confirmed), None
