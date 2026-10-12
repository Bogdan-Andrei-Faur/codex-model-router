"""Small owner-only metrics service. Untrusted anonymous enrollment is not attestation."""
import asyncio
import base64
import hashlib
import hmac
import html
import json
import logging
import os
from pathlib import Path
import re
import time

import psycopg
from psycopg.types.json import Jsonb
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from codex_model_router.telemetry.central_protocol import MAX_BATCH, MAX_EVENTS, HEX, validate_event


def capacity_limits():
    return (int(os.environ.get('MAX_INSTALLATION_BYTES', str(1024**3))),
            int(os.environ.get('MAX_TOTAL_BYTES', str(4*1024**3))),
            int(os.environ.get('MAX_DATABASE_BYTES', str(5*1024**3))))


def capacity_rejected(scope):
    # Literal scope only: never log request bodies, installation IDs or headers.
    logging.getLogger('router.metrics').warning('metrics_ingestion_capacity_rejected scope=%s', scope)
    raise HTTPException(507, scope)


def connect():
    return psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=5, options='-c statement_timeout=10000 -c lock_timeout=5000')


def migrate():
    with connect() as db:
        # schema.sql owns BEGIN/COMMIT; avoid a second implicit BEGIN warning.
        db.autocommit = True
        db.execute(Path(__file__).with_name('schema.sql').read_text())


def replay_deletions():
    """Run after restoring a DB, before re-exposing the API. Ledger is backed up separately."""
    ledger = Path(os.environ['DELETION_LEDGER'])
    with connect() as db:
        db.execute('SELECT pg_advisory_xact_lock(727001)')
        with ledger.open() as source:
            for line in source:
                row = json.loads(line)
                if set(row) != {'installation', 'epoch'} or not HEX.fullmatch(row['installation']) or type(row['epoch']) is not int:
                    raise ValueError('invalid_deletion_ledger')
                delete_rows(db, row['installation'], row['epoch'])


def record_deletion(db, installation, current):
    previous = db.execute('SELECT epoch FROM deletions WHERE installation=%s', (installation,)).fetchone()
    if previous and previous[0] >= current:
        return
    ledger = Path(os.environ['DELETION_LEDGER'])
    if ledger.exists() and ledger.stat().st_size >= 128 * 1024 * 1024:
        raise HTTPException(507, 'deletion_ledger_capacity')
    flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(ledger, flags, 0o600)
    with os.fdopen(fd, 'a', encoding='utf-8') as stream:
        stream.write(json.dumps({'installation': installation, 'epoch': current}) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(ledger.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def operate(action, installation):
    if not HEX.fullmatch(installation):
        raise ValueError('invalid_installation')
    with connect() as db:
        db.execute('SELECT pg_advisory_xact_lock(727001)')
        row = db.execute('SELECT epoch FROM installations WHERE id=%s FOR UPDATE', (installation,)).fetchone()
        if not row:
            raise ValueError('installation_not_found')
        if action == 'revoke':
            db.execute('UPDATE installations SET revoked=true WHERE id=%s', (installation,))
        else:
            current = row[0] + 1
            record_deletion(db, installation, current)
            delete_rows(db, installation, current)


def delete_rows(db, installation, epoch):
    db.execute('INSERT INTO deletions(installation,epoch) VALUES (%s,%s) ON CONFLICT(installation) DO UPDATE SET epoch=GREATEST(deletions.epoch,EXCLUDED.epoch)', (installation, epoch))
    db.execute('DELETE FROM events WHERE installation=%s AND epoch<=%s', (installation, epoch))
    db.execute('UPDATE installations SET epoch=GREATEST(epoch,%s), enabled=CASE WHEN epoch<=%s THEN false ELSE enabled END, prompts=CASE WHEN epoch<=%s THEN false ELSE prompts END,raw_otlp=CASE WHEN epoch<=%s THEN false ELSE raw_otlp END,bytes=(SELECT COALESCE(SUM(size),0) FROM events WHERE installation=%s) WHERE id=%s', (epoch, epoch, epoch, epoch, installation, installation))


def identity(body, request):
    installation = body.get('installation')
    token = request.headers.get('authorization', '')
    if not isinstance(installation, str) or not HEX.fullmatch(installation) or not re.fullmatch(r'Bearer [a-f0-9]{64}', token):
        raise HTTPException(401, 'unauthorized')
    return installation, hashlib.sha256(token[7:].encode()).hexdigest()


def epoch(body):
    value = body.get('epoch')
    if type(value) is not int or not 1 <= value <= 2**53:
        raise HTTPException(400, 'invalid_epoch')
    return value


def authenticate(db, installation, token_hash):
    row = db.execute('SELECT token_hash,epoch,enabled,prompts,raw_otlp,revoked,bytes,rate_minute,rate_count FROM installations WHERE id=%s FOR UPDATE', (installation,)).fetchone()
    if not row or not hmac.compare_digest(row[0], token_hash) or row[5]:
        raise HTTPException(401, 'unauthorized')
    minute = int(time.time() // 60)
    count = row[8] + 1 if row[7] == minute else 1
    if count > 120:
        raise HTTPException(429, 'rate_limited')
    db.execute('UPDATE installations SET rate_minute=%s,rate_count=%s WHERE id=%s', (minute, count, installation))
    return row


def process(path, body, installation, token_hash):
    with connect() as db:
        # Serialize admission/capacity/deletion, not every read in the dashboard.
        db.execute('SELECT pg_advisory_xact_lock(727001)')
        if path == 'enroll':
            if set(body) != {'installation'}:
                raise HTTPException(400, 'invalid_enrollment')
            old = db.execute('SELECT token_hash,revoked FROM installations WHERE id=%s', (installation,)).fetchone()
            if old:
                if not hmac.compare_digest(old[0], token_hash) or old[1]:
                    raise HTTPException(401, 'unauthorized')
            else:
                count, recent = db.execute("SELECT COUNT(*),COUNT(*) FILTER(WHERE created_at>now()-interval '1 hour') FROM installations").fetchone()
                if count >= int(os.environ.get('MAX_INSTALLATIONS', '10000')) or recent >= int(os.environ.get('ENROLLMENTS_PER_HOUR', '60')):
                    raise HTTPException(429, 'enrollment_capacity')
                db.execute('INSERT INTO installations(id,token_hash) VALUES (%s,%s)', (installation, token_hash))
            return {'enrolled': True}
        row = authenticate(db, installation, token_hash)
        current = epoch(body)
        if current < row[1]:
            raise HTTPException(409, 'obsolete_consent')
        if path == 'delete':
            if set(body) != {'installation', 'epoch'}:
                raise HTTPException(400, 'invalid_delete')
            # Durable intent precedes DB deletion/ack; replay is idempotent.
            record_deletion(db, installation, current)
            delete_rows(db, installation, current)
            return {'deleted': True}
        if path == 'consent':
            if set(body) != {'installation', 'epoch', 'enabled', 'prompts', 'raw_otlp'} or any(type(body.get(k)) is not bool for k in ('enabled', 'prompts', 'raw_otlp')):
                raise HTTPException(400, 'invalid_consent')
            flags = tuple(body[k] for k in ('enabled', 'prompts', 'raw_otlp'))
            if not flags[0] and any(flags[1:]):
                raise HTTPException(400, 'invalid_consent')
            if current == row[1] and flags != row[2:5]:
                raise HTTPException(409, 'conflicting_consent')
            deleted = db.execute('SELECT epoch FROM deletions WHERE installation=%s', (installation,)).fetchone()
            if deleted and current <= deleted[0] and flags[0]:
                raise HTTPException(409, 'deleted_epoch')
            db.execute('UPDATE installations SET epoch=%s,enabled=%s,prompts=%s,raw_otlp=%s WHERE id=%s', (current, *flags, installation))
            return {'consent': current}
        if path != 'events' or set(body) != {'installation', 'epoch', 'events'}:
            raise HTTPException(400, 'invalid_batch')
        if not row[2] or current != row[1]:
            raise HTTPException(409, 'consent_required')
        events = body['events']
        if not isinstance(events, list) or not 1 <= len(events) <= MAX_EVENTS:
            raise HTTPException(400, 'invalid_batch')
        accepted, seen = [], set()
        total = db.execute('SELECT COALESCE(SUM(bytes),0) FROM installations').fetchone()[0]
        db_size = db.execute('SELECT pg_database_size(current_database())').fetchone()[0]
        installation_limit, total_limit, database_limit = capacity_limits()
        if db_size >= database_limit:
            capacity_rejected('database_capacity')
        for event in events:
            try:
                encoded = validate_event(event)
            except (ValueError, TypeError, KeyError, RecursionError):
                raise HTTPException(400, 'invalid_event') from None
            if event['id'] in seen:
                raise HTTPException(400, 'duplicate_batch_id')
            seen.add(event['id'])
            if (event['kind'] == 'prompts' and not row[3]) or (event['kind'] == 'raw_otlp' and not row[4]):
                raise HTTPException(403, 'diagnostic_consent_required')
            size = len(encoded.encode())
            existing = db.execute('SELECT kind,data,epoch FROM events WHERE installation=%s AND id=%s', (installation, event['id'])).fetchone()
            if existing:
                if existing != (event['kind'], event['data'], current):
                    raise HTTPException(409, 'event_conflict')
            else:
                if row[6] + size > installation_limit:
                    capacity_rejected('installation_capacity')
                if total + size > total_limit:
                    capacity_rejected('total_capacity')
                db.execute('INSERT INTO events(installation,id,epoch,kind,data,size) VALUES (%s,%s,%s,%s,%s,%s)', (installation, event['id'], current, event['kind'], Jsonb(event['data']), size))
                db.execute('UPDATE installations SET bytes=bytes+%s WHERE id=%s', (size, installation))
                row = row[:6] + (row[6] + size,) + row[7:]
                total += size
            accepted.append(event['id'])
        return {'accepted': accepted}


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware('http')
async def protect(request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        response = JSONResponse({'detail': 'service_unavailable'}, status_code=503)
    response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
        'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        'Referrer-Policy': 'no-referrer'})
    return response


@app.exception_handler(Exception)
async def safe_error(request, exc):
    return JSONResponse({'detail': 'service_unavailable'}, status_code=503, headers={'Cache-Control': 'no-store'})


@app.get('/health/live')
def live():
    return {'live': True}


@app.get('/health/ready')
def ready():
    try:
        with connect() as db:
            if db.execute('SELECT MAX(version) FROM schema_version').fetchone()[0] != 1:
                raise ValueError()
        if len(os.environ.get('ADMIN_PASSWORD', '')) < 32:
            raise ValueError()
        ledger = Path(os.environ['DELETION_LEDGER'])
        fd = os.open(ledger, os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        os.close(fd)
        return {'ready': True}
    except Exception:
        raise HTTPException(503, 'not_ready') from None


@app.post('/v1/{path}')
async def ingest(path: str, request: Request):
    if path not in ('enroll', 'consent', 'events', 'delete'):
        raise HTTPException(404, 'not_found')
    if request.headers.get('content-encoding', 'identity') != 'identity':
        raise HTTPException(415, 'unsupported_encoding')
    if request.headers.get('content-type', '').split(';')[0] != 'application/json':
        raise HTTPException(415, 'json_required')
    async def read():
        chunks, size = [], 0
        async for part in request.stream():
            size += len(part)
            if size > MAX_BATCH:
                raise HTTPException(413, 'batch_too_large')
            chunks.append(part)
        return b''.join(chunks)
    try:
        body = json.loads(await asyncio.wait_for(read(), timeout=10))
        if not isinstance(body, dict):
            raise ValueError()
    except (ValueError, RecursionError, asyncio.TimeoutError):
        raise HTTPException(400, 'invalid_body') from None
    installation, token_hash = identity(body, request)
    return await run_in_threadpool(process, path, body, installation, token_hash)


def admin(request):
    password = os.environ.get('ADMIN_PASSWORD', '')
    try:
        scheme, encoded = request.headers.get('authorization', '').split(' ', 1)
        user, supplied = base64.b64decode(encoded, validate=True).decode().split(':', 1)
        if scheme.lower() == 'basic' and user == 'owner' and len(password) >= 32 and hmac.compare_digest(supplied.encode(), password.encode()):
            return
    except (ValueError, UnicodeError):
        pass
    raise HTTPException(401, 'owner_auth_required', headers={'WWW-Authenticate': 'Basic realm="Router owner", charset="UTF-8"'})


@app.get('/', response_class=HTMLResponse)
def panel(request: Request):
    admin(request)
    with connect() as db:
        installations = db.execute('SELECT COUNT(*),COALESCE(SUM(bytes),0) FROM installations').fetchone()
        largest = db.execute('SELECT COALESCE(MAX(bytes),0) FROM installations').fetchone()[0]
        db_size = db.execute('SELECT pg_database_size(current_database())').fetchone()[0]
        content_bytes = db.execute('SELECT kind,COUNT(*),COALESCE(SUM(size),0) FROM events GROUP BY kind ORDER BY kind').fetchall()
        accepted = db.execute("SELECT COALESCE(data->>'accepted_model',data->>'model','unknown'),COUNT(*) FROM events WHERE kind='metrics' AND data->>'event'='decision_accepted' GROUP BY 1 ORDER BY 2 DESC").fetchall()
        evidence = db.execute("SELECT data->>'event',COALESCE(data->>'evidence_confidence','unknown'),COUNT(*) FROM events WHERE kind='metrics' AND data->>'event' IN ('inference_observed','inference_probable','phase_checkpoint','decision_completed','decision_quality') GROUP BY 1,2 ORDER BY 1,2").fetchall()
        cohorts = db.execute("SELECT COALESCE(data->>'product_version','unknown'),COALESCE(data->>'execution_platform','unknown'),COUNT(*) FROM events WHERE kind='metrics' AND data->>'event'='decision_created' GROUP BY 1,2 ORDER BY 3 DESC").fetchall()
        # Only the latest cumulative snapshot per installation/decision, never SUM of polls.
        usage = db.execute("""SELECT COUNT(*),SUM((data->>'inputTokens')::numeric),SUM((data->>'outputTokens')::numeric) FROM
            (SELECT DISTINCT ON (installation,data->>'decision_id') data FROM events
             WHERE kind='metrics' AND data->>'event'='decision_usage' AND data ? 'decision_id'
             ORDER BY installation,data->>'decision_id',COALESCE((data->>'time')::numeric,0) DESC,received_at DESC) AS latest""").fetchone()
    limits = capacity_limits()
    capacity_rows = [(label, used, limit, f'{used/limit:.1%}' if limit > 0 else 'Desconocido')
                     for label, used, limit in zip(('Mayor instalación', 'Eventos totales', 'Base de datos'),
                                                   (largest, installations[1], db_size), limits)]
    def table(title, headings, rows):
        return '<h2>'+html.escape(title)+'</h2><table><thead><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in headings)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v) if v is not None else 'Desconocido')+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table>'
    return '<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Router · Métricas privadas</title><style>body{font:16px system-ui;background:#121319;color:#eee;max-width:960px;margin:40px auto;padding:24px}h2{margin-top:32px}table{width:100%;border-collapse:collapse}td,th{padding:12px;text-align:left;border-bottom:1px solid #343641}p{color:#bfc4d4}</style><h1>Métricas del enrutador</h1><p>Panel privado · Sin borrado automático. Instalaciones anónimas y no verificadas; no representan a todos los usuarios.</p>'+table('Recogida', ['Instalaciones','Bytes de eventos'], [installations])+table('Capacidad',['Ámbito','Bytes usados','Límite en bytes','Uso'],capacity_rows)+table('Contenido almacenado',['Tipo','Eventos','Bytes'],content_bytes)+table('Modelos aceptados',['Modelo','Registros'],accepted)+table('Evidencia y resultados',['Evento','Confianza','Muestras'],evidence)+table('Versiones y sistemas',['Versión','Sistema','Registros'],cohorts)+table('Últimos contadores por decisión',['Decisiones con muestra','Entrada','Salida'],[usage])+'<p>Aceptación no prueba inferencia. Los contadores pueden incluir contexto anterior al permiso; no son facturación ni consumo incremental. Coste facturado: desconocido. Los diagnósticos no se muestran en esta página.</p></html>'


@app.get('/admin/diagnostic/{installation}/{event_id}')
def diagnostic(installation: str, event_id: str, request: Request):
    admin(request)
    if not HEX.fullmatch(installation) or not HEX.fullmatch(event_id):
        raise HTTPException(404)
    with connect() as db:
        row = db.execute("SELECT data FROM events WHERE installation=%s AND id=%s AND kind IN ('prompts','raw_otlp')", (installation, event_id)).fetchone()
    if not row:
        raise HTTPException(404)
    return Response(json.dumps(row[0], ensure_ascii=False), media_type='application/json', headers={'Content-Disposition': 'attachment; filename="diagnostic.json"'})


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['migrate']:
        migrate()
    elif sys.argv[1:] == ['replay-deletions']:
        replay_deletions()
    elif len(sys.argv) == 3 and sys.argv[1] in ('revoke', 'delete-installation'):
        operate(sys.argv[1], sys.argv[2])
    else:
        raise SystemExit('Use migrate, replay-deletions, revoke ID or delete-installation ID')
