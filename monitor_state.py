"""Platform-neutral monitor payload/actions using the existing macOS web contract."""
import json
import math
import os
from pathlib import Path
import time

from build_identity import identity, router_identity
from state_store import atomic_json, append_record, file_lock, read_records
from task_modes import read_mode, mode_path

CONFIG_KEYS = ('enabled', 'inference_telemetry', 'phase_routing', 'prompt_logging', 'history_days', 'routing_engine', 'comparison_engines', 'routes')
TELEMETRY_COUNTERS = (
    'requests', 'records_scanned', 'eligible_records', 'events_without_model', 'unrecognized_records',
    'invalid_requests', 'unexpected_path', 'invalid_size', 'invalid_wire_size', 'invalid_decoded_size',
    'invalid_length', 'invalid_encoding', 'invalid_payload', 'invalid_io', 'unauthorized_requests',
    'rejected_connections', 'processing_busy', 'completion_records', 'failure_records', 'api_request_records', 'stream_records',
    'size_wire_512k', 'size_wire_1m', 'size_wire_4m', 'size_wire_16m', 'size_wire_over16m',
    'size_decoded_512k', 'size_decoded_1m', 'size_decoded_4m', 'size_decoded_16m', 'size_decoded_over16m',
    'telemetry_events', 'telemetry_confirmed', 'telemetry_probable', 'telemetry_unattributed')


def read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
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
    def __init__(self, root, code_root=None, preview=False):
        self.root = Path(root)
        self.state = self.root / 'state'
        self.code_root = Path(code_root or root)
        self.preview = preview
        self.version, self.build = identity(self.code_root)
        self.router_build = router_identity(self.code_root)
        self.history = []
        self.signature = None

    def payload(self):
        threads, versions, connections = {}, set(), 0
        telemetry = {'enabled': False}
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
            connections = 1
        paths = [self.state / name for name in ('history.jsonl', 'history.recovered.jsonl')]
        signature = []
        for path in paths:
            try:
                stat = path.stat()
                signature.append((stat.st_ino, stat.st_size, stat.st_mtime_ns))
            except OSError:
                signature.append(None)
        if signature != self.signature:
            self.history = [record for path in paths for record in read_records(path)]
            self.signature = signature
        config = read_json(self.root / 'config.local.json')
        safe = {key: config[key] for key in CONFIG_KEYS if key in config}
        for key, default in [('phase_routing', True), ('inference_telemetry', True), ('prompt_logging', True), ('history_days', 0)]:
            safe.setdefault(key, default)
        safe['jev'] = {key: value for key, value in (config.get('jev') or {}).items()
                       if key in ('connection', 'timeout_seconds', 'circuit_seconds', 'circuit_failures')}
        tids = set(threads) | {event['thread'] for event in self.history if isinstance(event.get('thread'), str) and 0 < len(event['thread']) <= 200}
        return {'productVersion': self.version, 'bridgeVersions': sorted(versions), 'bridgeBuildMismatch': mismatch,
                'bridgeBuildUnknown': unknown, 'restartRequired': (self.state / 'restart-required.json').exists(),
                'threads': threads, 'connections': connections, 'history': self.history, 'config': safe,
                'taskModes': {tid: read_mode(self.state, tid) for tid in tids}, 'telemetry': telemetry,
                'preview': self.preview, 'platform': 'linux', 'secretStorage': 'el llavero de Linux (Secret Service)'}

    def configure(self, key, value):
        if self.preview:
            raise ValueError('Los cambios están desactivados en la vista previa.')
        valid = False
        if key in ('enabled', 'phase_routing', 'prompt_logging', 'inference_telemetry'):
            valid = type(value) is bool
        elif key == 'history_days':
            valid = type(value) is int and value in (0, 30, 90, 180)
        elif key == 'routing_engine':
            valid = value in ('rules', 'jev')
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
