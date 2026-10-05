"""Platform-neutral monitor payload/actions using the existing macOS web contract."""
import json
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


class MonitorState:
    def __init__(self, root, code_root=None, preview=False, platform='linux'):
        self.root = Path(root)
        self.state = self.root / 'state'
        self.code_root = Path(code_root or root)
        self.preview = preview
        self.version, self.build = identity(self.code_root)
        self.router_build = router_identity(self.code_root)
        self.history = []
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
            self.journal_revision += 1

    def payload(self, needs_history=True, history_revision=-1):
        with self.lock:
            return self._payload(needs_history, history_revision)

    def _payload(self, needs_history, history_revision):
        threads, versions, connections = {}, set(), 0
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
        if self.preview:
            threads = read_json(self.root / 'preview.json').get('threads', {})
            account_usage = read_json(self.root / 'preview.json').get('account_usage', {})
            connections = 1
        if needs_history:
            self.load_history()
        config = migrate_config(read_json(self.root / 'config.local.json'))
        if not self.preview:
            self.updater.maybe_check(config.get('updates_auto_check') is True)
        safe = {key: config[key] for key in CONFIG_KEYS if key in config}
        for key, default in [('phase_routing', True), ('inference_telemetry', True), ('prompt_logging', True), ('history_days', 0)]:
            safe.setdefault(key, default)
        safe['jev'] = {key: value for key, value in (config.get('jev') or {}).items()
                       if key in ('connection', 'timeout_seconds', 'circuit_seconds', 'circuit_failures')}
        tids = set(threads) | {event['thread'] for event in self.history if needs_history and isinstance(event.get('thread'), str) and 0 < len(event['thread']) <= 200}
        payload = {'productVersion': self.version, 'bridgeVersions': sorted(versions), 'bridgeBuildMismatch': mismatch,
                'bridgeBuildUnknown': unknown, 'restartRequired': (self.state / 'restart-required.json').exists(),
                'threads': threads, 'connections': connections, 'config': safe,
                'taskModes': {tid: read_mode(self.state, tid) for tid in tids}, 'telemetry': telemetry,
                'accountUsage': account_usage, 'updates': self.updater.snapshot(),
                'historyLoaded': history_revision >= 0 or needs_history, 'journalRevision': self.journal_revision,
                'preview': self.preview, 'platform': self.platform,
                'secretStorage': {'linux': 'el llavero de Linux (Secret Service)', 'macos': 'el llavero de macOS',
                                  'windows': 'Windows DPAPI (usuario actual)'}[self.platform]}
        if needs_history and history_revision != self.journal_revision:
            payload['history'] = self.history
        return payload

    def action(self, data):
        """Only product actions; window geometry and credential custody stay native."""
        with self.lock:
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
                if result.returncode or status.get('error'):
                    return 'No se pudo completar la conexión. Tus tareas siguen abiertas.'
                if status.get('connection') == 'desktop_connected':
                    return 'Desktop conectado al selector.'
                if status.get('registered') is True:
                    return 'Conexión instalada. Falta observar el nuevo arranque de Desktop.'
                if data['value'] == 'uninstall':
                    return 'Conexión retirada. Reinicia Desktop para aplicarlo.'
                return 'Desktop detectado; pendiente de confirmar su conexión.'
            else:
                raise ValueError('Acción no válida.')
            return 'Guardado.'

    def configure(self, key, value):
        if self.preview:
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
        if self.preview or value not in ('manual', 'automatic'):
            raise ValueError('Modo no válido o vista previa.')
        path = mode_path(self.state, thread)
        known = set(self.payload()['threads']) | {r.get('thread') for r in self.history}
        if thread not in known:
            raise ValueError('Tarea no disponible.')
        atomic_json(path, {'schema': 1, 'thread': thread, 'mode': value})

    def quality(self, identifier, aspect, value):
        if self.preview or value not in ('', 'insufficient', 'adequate', 'excessive') or aspect not in ('overall', 'model', 'effort'):
            raise ValueError('Valoración no válida o vista previa.')
        self.payload()
        if not any(r.get('decision_id') == identifier for r in self.history):
            raise ValueError('Decisión no disponible.')
        field = {'overall': 'quality', 'model': 'model_quality', 'effort': 'effort_quality'}[aspect]
        append_record(self.state, {'schema': 2, 'event': 'decision_quality', 'decision_id': identifier,
                                  field: value, 'time': time.time(), 'time_iso': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
