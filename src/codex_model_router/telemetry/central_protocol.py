"""Versioned, content-free metrics contract shared by the client and service."""
import json
import re
from codex_model_router.telemetry.evidence import scrub, IDENTITIES

SCHEMA = 1
ENDPOINT = 'https://router.andreifaur.dev'
MAX_EVENT = 256 * 1024
MAX_BATCH = 1024 * 1024
MAX_EVENTS = 100
KINDS = ('metrics', 'prompts', 'raw_otlp')
HEX = re.compile(r'^[a-f0-9]{32}$')


def validate_event(event):
    if not isinstance(event, dict) or set(event) != {'id', 'kind', 'data'}:
        raise ValueError('invalid_event')
    if not isinstance(event['id'], str) or not HEX.fullmatch(event['id']) or event['kind'] not in KINDS:
        raise ValueError('invalid_event')
    data = event['data']
    if event['kind'] == 'metrics':
        if not isinstance(data, dict):
            raise ValueError('invalid_metrics')
        clean = scrub(data, b'validation-only')
        if clean is None:
            raise ValueError('invalid_metrics')
        # Identifiers have already been installation-scoped by the sender.
        for key in IDENTITIES:
            if key in data:
                if not isinstance(data[key], str) or not HEX.fullmatch(data[key]):
                    raise ValueError('invalid_identity')
                clean[key] = data[key]
        if 'trial_required_checks' in data:
            checks = data['trial_required_checks']
            if not isinstance(checks, list) or len(checks) > 100 or any(not isinstance(x, str) or not HEX.fullmatch(x) for x in checks):
                raise ValueError('invalid_identity')
            clean['trial_required_checks'] = checks
        if clean != data:
            raise ValueError('invalid_metrics')
    elif event['kind'] == 'prompts':
        if not isinstance(data, dict) or set(data) != {'prompt', 'decision_id'} or not isinstance(data['prompt'], str) or not isinstance(data['decision_id'], str) or not HEX.fullmatch(data['decision_id']):
            raise ValueError('invalid_prompt')
    else:
        if not isinstance(data, str) or not isinstance(json.loads(data), dict):
            raise ValueError('invalid_otlp')
    encoded = json.dumps(event, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    if len(encoded.encode()) > MAX_EVENT:
        raise ValueError('event_too_large')
    return encoded
