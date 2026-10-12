# Central telemetry capacity diagnosis and candidate repair — 2026-10-12

## Scope and identities

Owner requested Sentinel inspection and repair of the current API/sender failure.
Source: main1e3e1bbb33fdc83baa308c57276bb87a9be047b3 plus local candidate changes
and the four pre-existing activation documentation changes, all preserved.
Installed/loaded owner Mac remains0.9.10 (monitor2bf3077b1c3d4782,
routerf50a290841379145, policy8). No replacement, Desktop restart, permission change,
credential reset, server deletion or manual outbox pruning was performed.
Sentinel registered applied source1e3e1bb, P510, both services healthy.

## Production diagnosis

A single controlled sender tick used existing credentials/current consent with
safe stage/status output only. Enrollment200; consent200; events507 with the
old API reason `storage_capacity`. The rejected12-event batch was1,028,804 bytes,
within the1MiB protocol limit. No event was acknowledged or removed.

Read-only PostgreSQL aggregate snapshot:

| Measure | Observation |
| --- | --- |
| Installations |3; only one holds events |
| Largest/total encoded event bytes |134,101,327 |
| Per-installation admission limit |134,217,728 (128MiB) |
| Total encoded event limit |1,073,741,824 |
| Physical database / limit |32,085,683 /5,368,709,120 bytes |
| Host available disk |88,242,221,056 bytes |
| Metrics |6,668 events /4,801,446 bytes |
| Prompts |56 events /13,538 bytes |
| Raw OTLP |3,247 events /129,286,343 bytes |

Root cause confirmed: application-level per-installation quota; current batch
cannot fit. It is not physical disk exhaustion or a failed credential/consent.
API access logging is disabled, so Sentinel API logs showed startup only;
PostgreSQL showed old nested-BEGIN migration warnings, not the quota cause.
The8MiB local outbox is full (233 events) and capture rejection overwrites the
sender's `server_capacity` status in0.9.10, masking the operational cause.
Already rejected captures cannot be claimed recovered; original local journals
were not modified or remotely backfilled.

## Candidate correction

- Configurable defaults:1GiB per installation,4GiB total encoded events, unchanged
  5GiB physical DB ceiling. Both Compose profiles map operator `METRICS_MAX_*`
  variables to API `MAX_*`; no automatic deletion/unbounded storage.
- Separate safe507 reasons for installation/aggregate/database;429 is busy/rate
  pressure. Content-free scope warning is visible to Sentinel. Private panel
  shows aggregate capacity/percent and bytes per kind, without diagnostic bodies.
- Capture preserves sender errors; new diagnostics reserve512KiB of local queue
  space for metrics. No existing queued event is evicted.
- Explicit schema transaction now runs with autocommit to avoid duplicate-BEGIN
  warnings, preserving idempotent schema bootstrap.
- Disposable PostgreSQL readiness waits for TCP, not the entrypoint's temporary
  Unix-socket server. One pre-fix test run failed with database-starting-up before
  any test executed; this is recorded as a fixture race, not a production failure.

## Verification and remaining gates

Final validation:604 Python tests PASS (59 expected optional/platform skips;
15 focused client cases included),11 isolated PostgreSQL integration tests PASS,
shared Settings error-label browser checks PASS. Candidate Docker image built as
non-root; read-only HTTP/dedup/real pg_dump-restore/deletion-ledger replay fixture
PASS. Both Compose profiles resolve operator overrides and bounded defaults;
`git diff --check` PASS. Disposable fixture containers/volume/network were cleaned
by their own runners. No production source or running container changed.

Remaining: owner-authorized main publication, normal Sentinel P510 deployment,
then real preserved outbox drain/ACK and growing server counters. Client error UI
and local reserve require a later signed app update; a backend-only deployment
can restore current0.9.10 delivery without restarting Desktop.
