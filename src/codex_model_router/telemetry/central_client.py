"""Opt-in, bounded durable outbox. Only the monitor worker contacts the service.

Capture is best effort after the local journal commit: a process crash between
these commits can lose a remote sample, never corrupt local routing history.
"""
import json
import random
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from pathlib import Path
from codex_model_router.storage.state_store import private_directory, private_open, file_lock
from codex_model_router.telemetry.central_protocol import ENDPOINT, MAX_BATCH, MAX_EVENTS, MAX_EVENT, validate_event
from codex_model_router.telemetry.evidence import scrub, pseudonym

MAX_QUEUE_BYTES = 8 * 1024 * 1024
MAX_QUEUE_EVENTS = 4096


@contextmanager
def database(root, create=False):
    folder = Path(root) / 'state/central-telemetry'
    path = folder / 'outbox.sqlite3'
    if create:
        private_directory(folder)
        with private_open(path, 'a+b'):
            pass
    if not path.exists() or path.is_symlink():
        raise OSError('outbox_unavailable')
    db = sqlite3.connect(str(path), timeout=.05)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA secure_delete=ON')
        with db:
            if create:
                db.executescript('''CREATE TABLE IF NOT EXISTS control (
                    id INTEGER PRIMARY KEY CHECK(id=1), epoch INTEGER NOT NULL,
                    enabled INTEGER NOT NULL, prompts INTEGER NOT NULL, raw_otlp INTEGER NOT NULL,
                    salt TEXT NOT NULL, dirty INTEGER NOT NULL, delete_pending INTEGER NOT NULL,
                    status TEXT NOT NULL, last_sync REAL, rejected INTEGER NOT NULL DEFAULT 0);
                    CREATE TABLE IF NOT EXISTS queue (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, epoch INTEGER NOT NULL,
                    body TEXT NOT NULL, size INTEGER NOT NULL);''')
                db.execute("INSERT OR IGNORE INTO control VALUES (1,0,0,0,0,?,0,0,'disabled',NULL,0)", (secrets.token_hex(32),))
                db.commit()
            yield db
    finally:
        db.close()


def capture(root, kind, data):
    """Never raise into inference or persist content without independent consent."""
    try:
        with database(root) as db:
            db.execute('BEGIN IMMEDIATE')
            c = dict(db.execute('SELECT * FROM control').fetchone())
            if not c['enabled'] or (kind != 'metrics' and not c.get(kind)):
                return
            key = bytes.fromhex(c['salt'])
            if kind == 'metrics':
                data = scrub(data, key)
                if data is None:
                    return
            elif kind == 'prompts':
                data = {'prompt': data.get('prompt'), 'decision_id': pseudonym(key, 'decision_id', str(data.get('decision_id', 'unknown')))}
            elif kind == 'raw_otlp':
                if len(data) > MAX_EVENT:
                    db.execute("UPDATE control SET rejected=rejected+1,status='capacity_or_invalid'")
                    return
                data = data.decode('utf-8') if isinstance(data, bytes) else data
            try:
                body = validate_event({'id': uuid.uuid4().hex, 'kind': kind, 'data': data})
                size = len(body.encode())
                total, count = db.execute('SELECT COALESCE(SUM(size),0), COUNT(*) FROM queue').fetchone()
                if total + size > MAX_QUEUE_BYTES or count >= MAX_QUEUE_EVENTS:
                    raise ValueError('queue_full')
            except (ValueError, TypeError, RecursionError):
                db.execute("UPDATE control SET rejected=rejected+1,status='capacity_or_invalid'")
                return
            db.execute('INSERT INTO queue(epoch,body,size) VALUES (?,?,?)', (c['epoch'], body, size))
    except (OSError, sqlite3.Error, ValueError, TypeError):
        # Remote collection must not break the local journal or inference.
        return


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise OSError('redirect_rejected')


def transport(path, body, token):
    payload = json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    if len(payload) > MAX_BATCH:
        raise ValueError('batch_too_large')
    request = urllib.request.Request(ENDPOINT + path, data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, method='POST')
    try:
        response = urllib.request.build_opener(NoRedirect()).open(request, timeout=8)
    except urllib.error.HTTPError as error:
        code = error.code
        error.close()
        raise OSError('server_capacity' if code in (429, 507) else 'access_rejected' if code in (401, 403) else 'retrying') from None
    with response:
        raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError('invalid_response')
        return json.loads(raw)


class CentralTelemetry:
    def __init__(self, root, *, disabled=False, send=transport, secret=None):
        self.root = Path(root)
        self.disabled = disabled
        self.send = send
        if secret is None:
            from codex_model_router.telemetry.central_secret import credential
            secret = credential
        self.secret = secret
        self.wake = threading.Event()
        self.stop = threading.Event()
        self.thread = None
        self.guard = threading.Lock()
        self.failures = 0
        self.next_attempt = 0
        if not disabled and (self.root / 'state/central-telemetry/outbox.sqlite3').exists():
            self.start()

    def start(self):
        with self.guard:
            if self.thread is None and not self.disabled:
                self.thread = threading.Thread(target=self.run, name='central-telemetry', daemon=True)
                self.thread.start()
        self.wake.set()

    def snapshot(self):
        try:
            with database(self.root) as db:
                c = dict(db.execute('SELECT * FROM control').fetchone())
                count, size = db.execute('SELECT COUNT(*),COALESCE(SUM(size),0) FROM queue').fetchone()
            return {k: bool(c[k]) for k in ('enabled', 'prompts', 'raw_otlp', 'delete_pending')} | {
                'status': c['status'], 'lastSync': c['last_sync'], 'pending': count,
                'queuedBytes': size, 'rejected': c['rejected'], 'canDelete': c['status'] != 'deleted'}
        except (OSError, sqlite3.Error, TypeError, ValueError):
            status = 'unavailable' if (self.root / 'state/central-telemetry/outbox.sqlite3').exists() else 'disabled'
            return {'enabled': False, 'prompts': False, 'raw_otlp': False, 'status': status, 'pending': 0, 'rejected': 0}

    def configure(self, key, value):
        if self.disabled or key not in ('enabled', 'prompts', 'raw_otlp', 'delete') or type(value) is not bool:
            raise ValueError('Ajuste de envío no válido.')
        with database(self.root, create=True) as db:
            db.execute('BEGIN IMMEDIATE')
            c = dict(db.execute('SELECT * FROM control').fetchone())
            if key != 'delete' and c['delete_pending']:
                raise ValueError('Espera a que termine la eliminación pendiente.')
            if key in ('prompts', 'raw_otlp') and not c['enabled']:
                raise ValueError('Activa primero el envío de métricas.')
            if key == 'delete':
                if not value:
                    return
                c.update(enabled=0, prompts=0, raw_otlp=0, delete_pending=1)
            else:
                c[key] = int(value)
                if key == 'enabled' and not value:
                    c.update(prompts=0, raw_otlp=0)
            # Purge every previous permission epoch, even if only one permission changed.
            db.execute('DELETE FROM queue')
            db.execute('UPDATE control SET epoch=epoch+1, enabled=?,prompts=?,raw_otlp=?,dirty=1,delete_pending=?,status=?',
                       (c['enabled'], c['prompts'], c['raw_otlp'], c['delete_pending'], 'pending' if c['enabled'] else 'disabled'))
        self.next_attempt = 0
        self.start()

    def tick(self):
        if self.disabled:
            return
        # Multiple monitor processes share one durable queue, one sender at a time.
        with file_lock(self.root / 'state/central-telemetry/sender.lock', timeout=.05):
            with database(self.root) as db:
                c = dict(db.execute('SELECT * FROM control').fetchone())
                pending = db.execute('SELECT COUNT(*) FROM queue').fetchone()[0]
            if not c['dirty'] and not c['delete_pending'] and (not c['enabled'] or not pending):
                return
            auth = self.secret(self.root)
            if auth is None:
                if not c['enabled']:
                    with database(self.root) as db:
                        db.execute('UPDATE control SET dirty=0,delete_pending=0,status=? WHERE epoch=?', ('deleted' if c['delete_pending'] else 'disabled', c['epoch']))
                    return
                auth = self.secret(self.root, {'installation': uuid.uuid4().hex, 'token': secrets.token_hex(32)})
                if auth is None:
                    raise OSError('credential_unavailable')
            base = {'installation': auth['installation'], 'epoch': c['epoch']}
            if c['delete_pending']:
                self.send('/v1/delete', base, auth['token'])
                with database(self.root) as db:
                    db.execute("UPDATE control SET dirty=0,delete_pending=0,status='deleted' WHERE epoch=?", (c['epoch'],))
                return
            self.send('/v1/enroll', {'installation': auth['installation']}, auth['token'])
            self.send('/v1/consent', base | {k: bool(c[k]) for k in ('enabled', 'prompts', 'raw_otlp')}, auth['token'])
            with database(self.root) as db:
                now = dict(db.execute('SELECT * FROM control').fetchone())
                if now['epoch'] != c['epoch']:
                    return
                if not now['enabled']:
                    db.execute("UPDATE control SET dirty=0,status='disabled' WHERE epoch=?", (c['epoch'],))
                    return
                rows = db.execute('SELECT * FROM queue WHERE epoch=? ORDER BY seq LIMIT ?', (c['epoch'], MAX_EVENTS)).fetchall()
            selected, size = [], 512
            for row in rows:
                if size + row['size'] > MAX_BATCH - 1024:
                    break
                selected.append(row)
                size += row['size'] + 1
            if selected:
                reply = self.send('/v1/events', base | {'events': [json.loads(r['body']) for r in selected]}, auth['token'])
                if reply.get('accepted') != [json.loads(r['body'])['id'] for r in selected]:
                    raise ValueError('invalid_ack')
            with database(self.root) as db:
                for row in selected:
                    db.execute('DELETE FROM queue WHERE seq=? AND epoch=?', (row['seq'], c['epoch']))
                db.execute("UPDATE control SET dirty=0,status='synced',last_sync=? WHERE epoch=?", (time.time(), c['epoch']))

    def run(self):
        while not self.stop.is_set():
            if time.monotonic() >= self.next_attempt:
                try:
                    self.tick()
                    self.failures = 0
                    self.next_attempt = time.monotonic() + 10
                except Exception as error:
                    # Never expose network bodies, tokens or diagnostic content to IPC/logs.
                    self.failures += 1
                    self.next_attempt = time.monotonic() + min(600, 2 ** min(self.failures, 9)) + random.random()
                    try:
                        with database(self.root) as db:
                            status = str(error) if str(error) in ('credential_unavailable', 'server_capacity', 'access_rejected') else 'retrying'
                            db.execute('UPDATE control SET status=? WHERE enabled=1 OR delete_pending=1', (status,))
                    except (OSError, sqlite3.Error):
                        pass
            self.wake.wait(2)
            self.wake.clear()

    def close(self):
        self.stop.set()
        self.wake.set()
