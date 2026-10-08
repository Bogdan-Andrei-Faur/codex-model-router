"""Platform-neutral monitor payload/actions using the existing macOS web contract."""
import json
import copy
import math
import os
from pathlib import Path
import time
import subprocess
import sys
import threading

from build_identity import identity, router_identity
from model_catalog import migrate_config
from state_store import atomic_json, append_record, file_lock
from task_modes import read_mode, mode_path
from inference_attribution import COUNTERS as ATTRIBUTION_COUNTERS
from updates import UpdateManager
from application_layout import manifest, runtime_command


class MonitorJournal:
    """Append-only JSONL cache. Keep complete rows through transient I/O errors."""
    def __init__(self):
        self.rows = []
        self.offset = self.bytes_read = 0
        self.signature = None
        self.pending = b''

    def update(self, path):
        try:
            with Path(path).open('rb') as source:
                stat = os.fstat(source.fileno())
                signature = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
                reset = (self.signature is None or signature[:2] != self.signature[:2]
                         or stat.st_size < self.offset
                         or (stat.st_size == self.offset and signature != self.signature))
                if not reset and stat.st_size == self.offset:
                    return False
                source.seek(0 if reset else self.offset)
                chunk = source.read()
        except FileNotFoundError:
            changed = self.signature is not None
            self.rows = []; self.pending = b''; self.offset = 0; self.signature = None
            return changed
        except OSError:
            return False
        if reset:
            self.rows = []; self.pending = b''; self.offset = 0
        self.offset += len(chunk)
        self.bytes_read += len(chunk)
        self.signature = signature
        parts = (self.pending + chunk).split(b'\n')
        self.pending = parts.pop()
        for line in parts:
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    self.rows.append(value)
            except (ValueError, UnicodeError):
                pass
        return True

FIELDS = ('thread title model effort model_reason effort_reason continuity_strategy source status signal error_type quality model_quality effort_quality routing_engine engine_model engine_status engine_confidence engine_latency_ms inputTokens outputTokens cachedInputTokens reasoningOutputTokens phase_name phase_status phase_model phase_effort phase_transition observed_model observed_effort observed_candidate_model observed_candidate_effort configured_model configured_effort accepted_model accepted_effort pipeline_mode phase_pipeline inference_source evidence_confidence').split()
IDENTITY_FIELDS = ('observed_model observed_effort observed_candidate_model observed_candidate_effort evidence_confidence inference_source inference_model_mismatch inference_effort_mismatch').split()
USAGE_FIELDS = ('inputTokens outputTokens cachedInputTokens reasoningOutputTokens').split()


class HistoryProjection:
    """Match MonitorCore.decisions without transferring/replaying raw telemetry."""
    def __init__(self):
        self.records = {}
        self.events_processed = 0

    def apply(self, events):
        for event in events:
            self.events_processed += 1
            identifier = event.get('decision_id')
            if not isinstance(identifier, str) or not identifier:
                continue
            item = self.records.setdefault(identifier, {'id': identifier, 'time': 0, 'accepted': False, 'comparisons': {}})
            kind = event.get('event')
            if kind == 'decision_usage_total':
                item['native_total_usage'] = {key: event[key] for key in USAGE_FIELDS[:3] if key in event}
                continue
            if kind == 'decision_usage':
                for key in USAGE_FIELDS:
                    item.pop(key, None)
            if kind == 'inference_observed' and event.get('evidence_confidence') == 'confirmed' and event.get('estimate_basis') == 'standard_equivalent_not_billed' and event.get('inference_event_id'):
                item.setdefault('usage_estimates', {})[event['inference_event_id']] = {
                    key: event[source] for key, source in [('usd', 'estimated_api_standard_usd'), ('credits', 'estimated_codex_standard_credits')] if source in event}
            if kind == 'phase_checkpoint':
                item.setdefault('phase_events', []).append(event.copy())
                if event.get('phase_status') == 'applied':
                    if item.get('observed_model'):
                        previous = {key: item[source] for key, source in [('model', 'observed_model'), ('effort', 'observed_effort'), ('phase_id', 'phase_id'), ('confidence', 'evidence_confidence')] if source in item}
                        item.setdefault('prior_inferences', []).append(previous)
                    for key in IDENTITY_FIELDS:
                        item.pop(key, None)
                    for key, fallback in [('accepted_model', 'phase_model'), ('accepted_effort', 'phase_effort')]:
                        value = event.get(key) or event.get(fallback)
                        if value is not None:
                            item[key] = value
                        else:
                            item.pop(key, None)
            if kind in ('inference_metric', 'inference_observed', 'inference_probable'):
                model = event.get('observed_model') or event.get('observed_candidate_model')
                effort = event.get('observed_effort') or event.get('observed_candidate_effort') or ''
                sample_key = ((str(event['phase_id']) + ':') if event.get('phase_id') else '') + (event.get('inference_event_name') or 'unknown') + ':' + (event.get('inference_event_kind') or 'unknown') + ((':' + model + ':' + effort) if model else '')
                samples = item.setdefault('inference_samples', {})
                previous = samples.get(sample_key, {})
                samples[sample_key] = dict(event, count=previous.get('count', 0) + (event.get('inference_sample_count') or 1), failures=previous.get('failures', 0) + (event.get('inference_failure_count') or 0))
                item.update({key: value for key, value in event.items() if key.startswith('inference_') and key not in ('inference_model_mismatch', 'inference_effort_mismatch')})
                if kind == 'inference_metric' or (kind == 'inference_probable' and item.get('evidence_confidence') == 'confirmed'):
                    continue
            if kind == 'native_turn_error':
                if event.get('will_retry') is True:
                    item['native_retries'] = item.get('native_retries', 0) + 1
                continue
            if kind == 'decision_completed':
                for key in ('error_type', 'error_code', 'error_http_status', 'error_source'):
                    item.pop(key, None)
            if event.get('phase_id') and (kind != 'phase_checkpoint' or event.get('phase_status') == 'applied'):
                item['phase_id'] = event['phase_id']
            if kind != 'decision_quality':
                value = event.get('time', 0)
                try:
                    value = float(value or 0)
                except (ValueError, TypeError):
                    value = 0
                item['time'] = max(item['time'], value)
            if kind == 'decision_created':
                item['started'] = value
                for key in ('product_version', 'build_id', 'routing_policy_version', 'request_kind', 'quality_floor', 'min_effort'):
                    if key in event:
                        item[key] = event[key]
                    else:
                        item.pop(key, None)
            if kind in ('decision_accepted', 'decision_recovered'):
                item['accepted'] = True
            if kind in ('decision_completed', 'decision_rejected', 'decision_error'):
                item['finished'] = value
            for key in FIELDS:
                if kind == 'engine_comparison' and (key.startswith('engine_') or key in ('routing_engine', 'continuity_strategy')):
                    continue
                if key in event:
                    item[key] = event[key]
            if kind == 'engine_comparison':
                item['comparisons'][event.get('routing_engine') or 'rules'] = event.copy()
                item['routing_engine'] = item.get('appliedEngine') if 'appliedEngine' in item else event.get('routing_engine') if 'engine_active' not in event and event.get('engine_status') == 'ok' else 'rules'
            if kind == 'decision_routed':
                if 'routing_engine' in item:
                    item['appliedEngine'] = item['routing_engine']
            for key in ('error_code', 'error_http_status', 'error_source', 'inference_model_mismatch', 'inference_effort_mismatch'):
                if key in event:
                    item[key] = event[key]

    def snapshot(self):
        # A detached transport value is also safe across callers/revision caching.
        return [{'event': 'monitor_decision_snapshot', 'record': copy.deepcopy(item)} for item in self.records.values()]


CONFIG_KEYS = ('enabled', 'inference_telemetry', 'phase_routing', 'prompt_logging', 'history_days', 'routing_engine', 'comparison_engines', 'routes', 'policy_mode', 'policy_classes', 'candidate_jev_comparison', 'updates_auto_check')
TELEMETRY_COUNTERS = (
    'requests', 'records_scanned', 'eligible_records', 'events_without_model', 'unrecognized_records',
    'invalid_requests', 'unexpected_path', 'invalid_size', 'invalid_wire_size', 'invalid_decoded_size',
    'invalid_length', 'invalid_encoding', 'invalid_payload', 'invalid_io', 'unauthorized_requests',
    'rejected_connections', 'processing_busy', 'completion_records', 'failure_records', 'api_request_records', 'stream_records', 'identity_conflicts',
    'size_wire_512k', 'size_wire_1m', 'size_wire_4m', 'size_wire_16m', 'size_wire_over16m',
    'size_decoded_512k', 'size_decoded_1m', 'size_decoded_4m', 'size_decoded_16m', 'size_decoded_over16m',
    'telemetry_events', 'telemetry_confirmed', 'telemetry_probable', 'telemetry_unattributed') + ATTRIBUTION_COUNTERS


def read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def alive(pid):
    if type(pid) is not int or pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            return False
        try:
            return kernel.WaitForSingleObject(handle, 0) == 258
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else 0


def appearance_value(value):
    """Cosmetic data only: never accept markup, paths or arbitrary properties."""
    required = {'name', 'color', 'accessoryColor', 'roundness', 'eyes', 'head', 'glasses'}
    optional = {'scarf', 'outfit', 'neck', 'detail'}
    if not isinstance(value, dict) or not required <= set(value) or set(value) - required - optional:
        raise ValueError('Personaje no válido.')
    if not isinstance(value['name'], str) or not 1 <= len(value['name'].strip()) <= 24 or not value['name'].isprintable():
        raise ValueError('El nombre debe tener entre 1 y 24 caracteres.')
    for key in ('color', 'accessoryColor'):
        color = value[key]
        if not isinstance(color, str) or len(color) != 7 or color[0] != '#' or any(c not in '0123456789abcdefABCDEF' for c in color[1:]):
            raise ValueError('Color no válido.')
    if type(value['roundness']) is not int or not 16 <= value['roundness'] <= 27:
        raise ValueError('Redondez no válida.')
    result = dict(value, name=value['name'].strip())
    if type(result['glasses']) is bool:
        result['glasses'] = 'rectangle' if result['glasses'] else 'none'
    if 'scarf' in result and type(result['scarf']) is not bool:
        raise ValueError('Accesorio no válido.')
    result.setdefault('neck', 'scarf' if result.get('scarf') else 'none')
    result.pop('scarf', None)
    result.setdefault('outfit', 'none')
    result.setdefault('detail', 'none')
    slots = {
        'eyes': ('oval', 'round'),
        'head': ('none', 'cap', 'antenna', 'beanie', 'beret', 'hat', 'headphones'),
        'glasses': ('none', 'round', 'rectangle', 'sunglasses', 'visor'),
        'outfit': ('none', 'tee', 'sweater', 'hoodie', 'overalls', 'vest', 'jacket', 'labcoat'),
        'neck': ('none', 'bandana', 'scarf', 'tie', 'bowtie'),
        'detail': ('none', 'pocket', 'buttons', 'pin', 'patch'),
    }
    if any(type(result[key]) is not str or result[key] not in choices for key, choices in slots.items()):
        raise ValueError('Accesorio no válido.')
    return result


class MonitorState:
    def __init__(self, root, code_root=None, preview=False, platform='linux', read_only=False):
        self.root = Path(root)
        self.state = self.root / 'state'
        self.code_root = Path(code_root or root)
        self.preview = preview
        self.read_only = read_only
        self.version, self.build = identity(self.code_root)
        self.router_build = router_identity(self.code_root)
        self.history = []
        self.ui_history = []
        self.history_projection = HistoryProjection()
        self.projected_primary = None
        self.projected_count = 0
        self.projected_recovered = False
        if platform not in ('linux', 'macos', 'windows'):
            raise ValueError('Plataforma no válida.')
        self.platform = platform
        self.journals = [MonitorJournal(), MonitorJournal()]
        self.journal_revision = 0
        self.lock = threading.RLock()
        self.updater = UpdateManager(self.root, self.version, self.platform)

    def close(self):
        self.updater.close()

    def load_history(self):
        changed = False
        for journal, name in zip(self.journals, ('history.jsonl', 'history.recovered.jsonl')):
            changed |= journal.update(self.state / name)
        if changed:
            self.history = [row for journal in self.journals for row in journal.rows]
            primary, recovered = self.journals
            if self.projected_primary is primary.rows and not recovered.rows and not self.projected_recovered:
                self.history_projection.apply(primary.rows[self.projected_count:])
            else:
                self.history_projection = HistoryProjection()
                self.history_projection.apply(self.history)
            self.projected_primary = primary.rows
            self.projected_count = len(primary.rows)
            self.projected_recovered = bool(recovered.rows)
            self.ui_history = self.history_projection.snapshot()
            self.journal_revision += 1

    def payload(self, needs_history=True, history_revision=-1):
        with self.lock:
            return self._payload(needs_history, history_revision)

    def _payload(self, needs_history, history_revision):
        threads, agent_threads, versions, connections = {}, {}, set(), 0
        telemetry = {'enabled': False}
        account_usage = {}
        mismatch = unknown = False
        for path in sorted(self.state.glob('status-*.json')):
            data = read_json(path)
            if data.get('client_name') == 'other' or not alive(data.get('pid')):
                continue
            if abs(time.time() - number(data.get('heartbeat'))) >= 12 or not isinstance(data.get('threads'), dict):
                continue
            if any(e.get('event') == 'bridge_stopped' for e in data.get('events', []) if isinstance(e, dict)):
                continue
            connections += 1
            usage = data.get('account_usage')
            if isinstance(usage, dict) and number(usage.get('updated')) >= number(account_usage.get('updated')):
                account_usage = usage
            versions.add(str(data.get('product_version', 'desconocida')))
            build = data.get('router_build_id')
            mismatch |= bool(build and build != self.router_build)
            unknown |= not bool(build)
            health = data.get('telemetry') or {}
            stats = data.get('stats') or {}
            telemetry['enabled'] |= health.get('enabled') is True
            for key in TELEMETRY_COUNTERS:
                telemetry[key] = telemetry.get(key, 0) + number(health.get(key)) + number(stats.get(key))
            for tid, row in data['threads'].items():
                if isinstance(row, dict) and number(row.get('updated')) >= number(threads.get(tid, {}).get('updated')):
                    threads[tid] = row
            for tid, row in (data.get('agent_threads') or data['threads']).items():
                if isinstance(row, dict) and number(row.get('updated')) >= number(agent_threads.get(tid, {}).get('updated')):
                    agent_threads[tid] = row
        if self.preview:
            threads = read_json(self.root / 'preview.json').get('threads', {})
            agent_threads = threads
            account_usage = read_json(self.root / 'preview.json').get('account_usage', {})
            connections = 1
        if needs_history:
            self.load_history()
        config = migrate_config(read_json(self.root / 'config.local.json'))
        if not self.preview and not self.read_only:
            self.updater.maybe_check(config.get('updates_auto_check') is True)
        safe = {key: config[key] for key in CONFIG_KEYS if key in config}
        for key, default in [('phase_routing', True), ('inference_telemetry', True), ('prompt_logging', True), ('history_days', 0)]:
            safe.setdefault(key, default)
        safe['jev'] = {key: value for key, value in (config.get('jev') or {}).items()
                       if key in ('connection', 'timeout_seconds', 'circuit_seconds', 'circuit_failures')}
        tids = set(threads) | set(agent_threads) | {event['thread'] for event in self.history if needs_history and isinstance(event.get('thread'), str) and 0 < len(event['thread']) <= 200}
        desktop_restart_pending = not self.preview and not connections and read_json(self.state / 'desktop-integration.json').get('status') == 'registered'
        payload = {'productVersion': self.version, 'bridgeVersions': sorted(versions), 'bridgeBuildMismatch': mismatch,
                'bridgeBuildUnknown': unknown, 'restartRequired': (self.state / 'restart-required.json').exists() or desktop_restart_pending,
                'desktopRestartPending': desktop_restart_pending,
                'threads': threads, 'agentThreads': agent_threads, 'connections': connections, 'config': safe,
                'taskModes': {tid: read_mode(self.state, tid) for tid in tids}, 'telemetry': telemetry,
                'appearances': self.appearances(),
                'accountUsage': account_usage, 'updates': self.updater.snapshot(),
                'historyLoaded': history_revision >= 0 or needs_history, 'journalRevision': self.journal_revision,
                'preview': self.preview, 'readOnly': self.read_only, 'platform': self.platform,
                'secretStorage': {'linux': 'el llavero de Linux (Secret Service)', 'macos': 'el llavero de macOS',
                                  'windows': 'Windows DPAPI (usuario actual)'}[self.platform]}
        if needs_history and history_revision != self.journal_revision:
            payload['history'] = self.ui_history
        return payload

    def action(self, data):
        """Only product actions; window geometry and credential custody stay native."""
        with self.lock:
            if self.read_only:
                raise ValueError('Vista previa de solo lectura.')
            action = data.get('action')
            if action == 'update':
                if self.preview:
                    raise ValueError('Los cambios están desactivados en la vista previa.')
                return self.updater.start(data.get('value'))
            elif action == 'config':
                self.configure(data.get('key'), data.get('value'))
            elif action == 'taskMode':
                self.task_mode(data.get('thread'), data.get('value'))
                return 'Modo guardado para el próximo mensaje de esta tarea.'
            elif action == 'appearance':
                if 'value' not in data:
                    raise ValueError('Personaje no válido.')
                self.save_appearance(data.get('thread'), data.get('value'))
                return 'Personaje guardado.'
            elif action == 'quality':
                self.quality(data.get('id'), data.get('aspect', 'overall'), data.get('value'))
            elif action == 'connection':
                if self.preview or data.get('value') not in ('doctor', 'install', 'uninstall'):
                    raise ValueError('Acción no válida o vista previa.')
                config = read_json(self.root / 'config.local.json')
                command = (runtime_command('desktop', self.code_root, self.root) if manifest(self.code_root)
                           else [str(self.code_root / config.get('desktop_runtime', 'bin/codex-desktop-core.exe'))]
                           if getattr(sys, 'frozen', False) else [sys.executable, str(self.code_root / 'desktop.py')])
                result = subprocess.run(command + [data['value']],
                                        cwd=self.root, capture_output=True, timeout=100,
                                        env=dict(os.environ, PERSONAL_CODEX_ROUTER_ROOT=str(self.root),
                                                 PERSONAL_CODEX_ROUTER_CONFIG=str(self.root / 'config.local.json')),
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                # Tool output may contain private details; expose only known public states.
                try:
                    status = json.loads(result.stdout)
                except (ValueError, UnicodeError):
                    status = {}
                if not isinstance(status, dict):
                    status = {}
                if result.returncode or status.get('error'):
                    try:
                        failure = json.loads(result.stderr)
                    except (ValueError, UnicodeError):
                        failure = {}
                    code = failure.get('code') if isinstance(failure, dict) else None
                    messages = {
                        'source_monitor_open': 'Cierra el monitor de la instalación anterior y vuelve a conectar desde este monitor.',
                        'source_bridge_active': 'Desktop todavía usa la instalación anterior. Termina tus tareas, cierra Desktop por completo y vuelve a conectar.',
                        'source_status_unreadable': 'No se puede leer el estado de la instalación anterior. Revisa su diagnóstico antes de volver a conectar.',
                        'source_connection_unverified': 'No se pudo verificar la conexión anterior. Comprueba que importaste la instalación que estaba conectada a Desktop.',
                    }
                    if isinstance(code, str) and code in messages:
                        return messages[code]
                    return 'No se pudo completar la conexión. Tus tareas siguen abiertas.'
                if status.get('connection') == 'desktop_connected':
                    return 'Desktop conectado al selector.'
                if status.get('registered') is True:
                    return 'Conexión preparada. Reinicia Desktop cuando terminen tus tareas.'
                if data['value'] == 'uninstall':
                    return 'Conexión retirada. Reinicia Desktop para aplicarlo.'
                return 'Desktop detectado; pendiente de confirmar su conexión.'
            else:
                raise ValueError('Acción no válida.')
            return 'Guardado.'

    def appearances(self):
        document = read_json(self.state / 'agent-appearances.json')
        if document.get('version') != 1 or not isinstance(document.get('agents'), dict):
            return {}
        result = {}
        for key, value in document['agents'].items():
            try:
                if isinstance(key, str) and 0 < len(key) <= 200:
                    result[key] = appearance_value(value)
            except (ValueError, TypeError):
                pass
        return result

    def save_appearance(self, thread, value):
        if self.preview or self.read_only:
            raise ValueError('Los cambios están desactivados en la vista previa.')
        if not isinstance(thread, str) or not 0 < len(thread) <= 200 or not thread.isprintable():
            raise ValueError('Agente no válido.')
        normalized = None if value is None else appearance_value(value)
        path = self.state / 'agent-appearances.json'
        with file_lock(self.state / 'agent-appearances.lock'):
            # Reject corrupt/unknown formats rather than destroying other agents.
            document = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'version': 1, 'agents': {}}
            if not isinstance(document, dict) or document.get('version') != 1 or not isinstance(document.get('agents'), dict):
                raise ValueError('No se pudo leer el archivo de personajes; se conserva sin cambios.')
            if normalized is None:
                document['agents'].pop(thread, None)
            else:
                document['agents'][thread] = normalized
            atomic_json(path, document)

    def configure(self, key, value):
        if self.preview or self.read_only:
            raise ValueError('Los cambios están desactivados en la vista previa.')
        valid = False
        if key in ('enabled', 'phase_routing', 'prompt_logging', 'inference_telemetry', 'updates_auto_check'):
            valid = type(value) is bool
        elif key == 'history_days':
            valid = type(value) is int and value in (0, 30, 90, 180)
        elif key == 'routing_engine':
            valid = value in ('rules', 'jev')
        elif key == 'policy_mode':
            valid = value in ('reference', 'compare')
        elif key == 'candidate_jev_comparison':
            valid = type(value) is bool
        elif key == 'policy_classes':
            from candidate_policy import CLASSES
            valid = isinstance(value, list) and len(value) <= len(CLASSES) and all(type(x) is str and x in CLASSES for x in value) and len(set(value)) == len(value)
        elif key == 'comparison_engines':
            valid = isinstance(value, list) and len(value) <= 2 and all(type(x) is str and x in ('rules', 'jev') for x in value) and len(set(value)) == len(value)
        elif key == 'jev.connection':
            valid = value in ('typesafe', 'vercel')
        if not valid:
            raise ValueError('Ajuste no válido.')
        with file_lock(self.state / 'config.lock'):
            config = read_json(self.root / 'config.local.json')
            if not config:
                raise ValueError('No se pudo leer la configuración.')
            if key == 'jev.connection':
                config.setdefault('jev', {})['connection'] = value
            else:
                config[key] = value
            atomic_json(self.root / 'config.local.json', config)
            if key in ('phase_routing', 'inference_telemetry'):
                atomic_json(self.state / 'restart-required.json', {k: config.get(k) is True for k in ('phase_routing', 'inference_telemetry')})

    def task_mode(self, thread, value):
        if self.preview or self.read_only or value not in ('manual', 'automatic'):
            raise ValueError('Modo no válido o vista previa.')
        path = mode_path(self.state, thread)
        known = set(self.payload()['threads']) | {r.get('thread') for r in self.history}
        if thread not in known:
            raise ValueError('Tarea no disponible.')
        atomic_json(path, {'schema': 1, 'thread': thread, 'mode': value})

    def quality(self, identifier, aspect, value):
        if self.preview or self.read_only or value not in ('', 'insufficient', 'adequate', 'excessive') or aspect not in ('overall', 'model', 'effort'):
            raise ValueError('Valoración no válida o vista previa.')
        self.payload()
        if not any(r.get('decision_id') == identifier for r in self.history):
            raise ValueError('Decisión no disponible.')
        field = {'overall': 'quality', 'model': 'model_quality', 'effort': 'effort_quality'}[aspect]
        append_record(self.state, {'schema': 2, 'event': 'decision_quality', 'decision_id': identifier,
                                  field: value, 'time': time.time(), 'time_iso': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})


def notch_inset(width, height, y):
    shoulder = min(20, width / 2)
    radius = min(32, max(0, (width - 2 * shoulder) / 2), height / 2)
    inset = shoulder
    if y < shoulder:
        inset = math.sqrt(max(0, shoulder ** 2 - (shoulder - y) ** 2))
    if y > height - radius:
        inset += radius - math.sqrt(max(0, radius ** 2 - (y - height + radius) ** 2))
    return inset
