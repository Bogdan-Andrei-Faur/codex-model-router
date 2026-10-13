# Central telemetry quota recovery — 2026-10-13 — Mac and P510

## Publication and deployment

Owner expressly authorized main publication, normal Sentinel P510 deployment
and real sending verification. Remote main advanced todf1a1e4 with Windows and
Ubuntu distribution/activation documentation; those changes were integrated
without losing the local quota correction. A recoverable local stash retains
its pre-integration copy; it was not pushed.

Correction commit `b81fe18804639e962bdbe89dd9447785b1a1ec99` was pushed to main.
Sentinel recorded successful normal polling deployment15:50:34–15:51:04Z,
execution node P510, with no remaining operation lease. A browser deploy action
was also submitted; the completed authoritative record identifies polling.
Running API/source module SHA-256 values match this checkout:

- `services/metrics/app.py`: `ce3b5cc42c1957b3faf787bd38357bd06e4cc608fa7982e2878ebe1c0e44f025`.
- `src/codex_model_router/telemetry/central_client.py`: `1f9110ad9e33c970fc9e75c5f63dc153cdc677b1c574539d633a4df2de8d3f87`.

Runtime limits verified: metrics1GiB/installation and4GiB aggregate;
diagnostics8GiB/installation and32GiB aggregate; physical database5GiB,
diagnostic admission headroom256MiB. API/DB healthy, public readiness200.
No quota warnings, tracebacks or error lines in the bounded post-deploy sample.

## Real outbox recovery and independent native sending

At15:49:13Z the Mac retained1071events/8,388,180bytes:943metrics and128raw OTLP.
Status was installation_capacity and last-sync2026-10-12T16:57:22Z. Existing
sharing flags remained enabled; rejected capture counter33975 at this snapshot.
The original pending identifiers were held only in private local evidence and
were never printed or committed.

A bounded source-assisted sender used existing credentials and consent. Ten
ticks/38successful requests received exact API ACKs for all1071original events;
queue reached zero at15:52:30Z. No credential creation, re-enrollment, configure,
queue purge, sampling or Desktop/monitor restart. Assistance then stopped.
This alone proves assisted recovery, not native background recovery.

A read-only observer made no network sends after assistance stopped. Independently
observed native last-sync times advanced at15:58:11Z,15:58:43Z and15:59:15Z.
The new queue fell from280events/2,991,211bytes at15:57:46Z to37/931,311 at
15:58:16Z, zero at15:58:46Z and3/169,497 at15:59:16Z. Status remained synced.
The rejected-capture counter stayed34166 throughout this no-send observation;
epoch and all sharing/deletion flags were unchanged. This separately verifies
actual installed background recovery after its existing retry backoff.

Already rejected capture attempts are not recovered historical records. No
local-journal backfill was attempted. The installed application remains0.9.11;
backend quota separation restores its existing mixed-batch sender. Full new
client lane isolation and new warnings need a subsequent signed client release
and owner update; no installed files were hotpatched here.

## Source and operational checks

609Python tests/53expected skips pass after remote integration. Existing targeted
20client,14realPostgreSQL, browser and containerHTTP/pg_dump/restore/deletion
fixtures passed as recorded in the [implementation receipt](2026-10-13-telemetry-quota-isolation.md).
[CI38425389094](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/38425389094)
for exact correction b81fe18 completed14/14 successful, first attempt.

Sentinel currently shows healthy origin/API and DB. This observation supersedes
the earlier degraded status; no Sentinel probe fix or exact root cause is claimed
by this Router change. Current Sentinel source isb4d3865; other work recovered
connectivity independently.

The Compose environment change invalidated the reviewed source build-context
exclusion in backup inventory. Reviewed controller checkout clean; only ignored
.env is present, covered by encrypted project configuration and excluded from
this image by its Dockerfile-specific allowlist. Reaffirmed the existing Git
source exclusion, retained PostgreSQL plus deletion-ledger inclusion and unchanged
backup schedule/retention. Copias no longer blocked. Four older verified copies
remain. No production restore or new backup was initiated by this verification.

Sentinel continuity records guided same-version P510 recovery delivered and a
real isolated Router preparation/cleanup verified earlier today. That is separate
from applying a production restore or historical-version/configuration rollback.
Windows/Ubuntu0.9.12 manual installers and owner activation are recorded in their
new repository receipts; production updater metadata still requires Mac signing.

No prompts, raw OTLP, credential values, conversation/installation identifiers,
private paths or raw logs are included in this receipt.
