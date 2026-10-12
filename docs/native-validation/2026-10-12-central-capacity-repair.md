# Central telemetry capacity diagnosis and candidate repair — 2026-10-12

## Scope and identities

Owner requested Sentinel inspection and repair of the current API/sender failure.
Source: main1e3e1bbb33fdc83baa308c57276bb87a9be047b3 plus local candidate changes
and the four pre-existing activation documentation changes, all preserved.
The correction was published as95436e85f64efa95dfaf439d5a9fd1449b6be068 after
explicit owner approval.
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

## Published correction

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
by their own runners. The local fixture checks preceded owner-authorized production activation below.

## Production recovery and independent native acknowledgement

Owner explicitly authorized main publication and P510 deployment. Sentinel's
normal polling deployed95436e85f64efa95dfaf439d5a9fd1449b6be068 successfully:
start10:28:38Z, finish10:29:07Z; no remaining exclusive operation. Running API
and shared client-module hashes match this source. Actual runtime limits are
1,073,741,824 /4,294,967,296 /5,368,709,120 bytes. No database volume was replaced.
[Code CI38236530406](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/38236530406)
completed14/14 successful.

Nine controlled sender ticks delivered all233 originally queued events with
exact server acknowledgements; none remained pending. Queue reached0bytes/0events
at10:29:47Z, with all three sharing flags unchanged. Server aggregate events grew
from134,101,327 to142,553,633 bytes; all prior data remained. Rejected count reached
6,094 during the first drain; these already rejected captures are not recovered.

Installed0.9.10 still had its earlier exponential retry deadline, and new events
continued arriving. Twelve additional bounded assisted ticks preserved delivery
while awaiting its native retry; assistance then stopped when an independent
background ACK was observed. A separate read-only observer (no sending) subsequently
saw four native syncs at10:38:26/35/45/57Z with pending bytes
1,741,939 →834,589 →17,783 →21,613 and pending events50 →25 →1 →3. Rejections stayed6,308
through these native samples. This verifies actual installed worker recovery,
not merely source transport acceptance. New incoming events can legitimately
remain briefly pending. No Desktop/monitor restart or privacy change was needed.

Client error UI/reserved space improvements are source-only until a later signed
app release. Current0.9.10 delivery is restored by the backend correction alone.
No release asset was overwritten; other-platform/backup gates remain separate.
