# Central telemetry candidate — 2026-10-11

Status: **IMPLEMENTED_AND_LOCALLY_VERIFIED**, not deployed or installed.
Base source: `395a4498a9cce91201fb370448753da0902cea28` plus uncommitted changes.
Existing owner app, Desktop processes, published0.9.7 release, Sentinel services,
DNS and local capture preferences were not replaced or activated.

## Implemented

- `services/metrics`: FastAPI/PostgreSQL enrollment, consent epochs, scoped bearer
  authentication, transactional idempotent ingestion, capacity limits, health,
  owner-only panel, diagnostic attachments, revocation and deletion-ledger replay.
- `telemetry/central_*`: native credential custody, private bounded SQLite outbox,
  stable installation pseudonyms, new-write capture, independent prompt/raw
  consent, retries and acknowledgement. Default off; no historical backfill.
- Shared Settings: master/extra permissions, synchronization and rejection state,
  explicit in-app delete/cancel confirmation, read-only/preview guards. No URL,
  token or account input for end users. Local capture remains independent.
- `deploy/compose.metrics.yml` and Sentinel example: private PostgreSQL,
  `sentinel-public` API, migrations, health, resource limits and backup inventory.
  Diagnostic data is in PostgreSQL; the extra volume holds deletion intents.

## Verification completed on this Mac

| Check | Evidence / boundary |
| --- | --- |
| General Python suite |587 tests,53 skipped; portable Python3.14 clean environment |
| Central client tests |12 passing: default-off, no backfill, field scrubbing, independent consent, epoch purge, lost-ack durable retry, pause race, bounded queue, deletion, read-only, real journal/OTLP hooks, local-config independence and sanitized HTTP failure |
| PostgreSQL integration |9 passing on isolated PostgreSQL17: schema rerun, auth/isolation, strict schema and atomic reject, duplicates/conflicts, diagnostic permission, caps, revocation, deletion/replay and synthetic client→DB |
| Container |Pinned-base image builds; real HTTP/readiness/admin401; read-only non-root API; duplicate retry; private source inputs excluded |
| Actual backup/restore |`pg_dump` before deletion, `pg_restore` into a second disposable DB, replay latest ledger; deleted event count1→0 |
| Mac credentials |Isolated Keychain create/read matched; no plaintext credential file; fixture entry removed |
| Shared JS |33 core tests pass;15 existing layout/browser scripts pass plus new central Settings script; affected Settings/update checks rerun after final UI edits |
| UI interaction |Separate action payloads, status-only refresh, cancel/confirm deletion and disabled read-only controls pass. Manual Playwright fixture also inspected; missing fixture-only favicon/brand URLs were not product script errors |
| Packaging/consistency |Compose parses with private DB, no host ports, expected ledger volume; `git diff --check` passes |

All upload data and credentials used in tests were synthetic. No production
endpoint was contacted. No commit, push or Sentinel configuration write occurred.
The native owner UI was not restarted. The new source requires a future client
package and a fresh bridge load before raw capture works on an installed client.

## Publication and placement follow-up

The owner subsequently authorized source publication to main and requested P510
placement through Sentinel. Read-only checks found P510 reachable with Docker
and Sentinel32a4768 installed on the Mac controller, but no project execution-node
selector or remote deployment executor. The owner explicitly chose to defer
deployment rather than expand Sentinel now. No backend containers, credentials,
DNS, routes or Sentinel configuration were created. Publication is separate from
the local verification above and from future native/production acceptance.

### Remote support follow-up (supersedes deployment hold)

Native Sentinel now reports `e5864948a84b7704fc86a1aa4c2931cafbf5afaa` and exposes
an enabled P510 deployment target in the actual onboarding UI. The owner requested
normal deployment after the lack of remote backup/restore support was disclosed.
The new `deploy/compose.metrics-p510.yml` removes the external network requirement
and explicitly migrates before HTTP startup. Both Compose profiles now quote the
tmpfs option containing a comma; without quoting, YAML made it a second invalid
mount. An isolated real Compose start of the remote profile passed migration,
API/DB readiness, private DB/no published port, owned networks and unauthenticated
owner-panel401. Only UUID-owned disposable containers/networks/volumes were
removed. This verifies the profile locally, not public or P510 activation.

Actual onboarding compatibility checks also required Sentinel's single-suffix
filename and inspectable empty interpolation defaults; credentials still fail
closed at PostgreSQL startup/API readiness. The current remote source95787fc
includes these corrections and Git exclusions for private deployment env files.
Sentinel cloned the dedicated controller checkout, inspected both services and
detected the two privately generated credentials. Its form is prepared; owner
credential import/submission remains pending. Cloudflared acknowledged domain
CNAME creation, without immediate local DNS/public-readiness confirmation. No
remote backend container or public synthetic ingestion is claimed by this receipt.

## Limits and remaining gates

Collection is best-effort research telemetry: the local journal and outbox are
separate commits; crash/SQLite lock/disk failures can lose remote samples. Cumulative
token snapshots are not incremental billed usage. Accepted settings are not proof
of subsequent inference. Raw OTLP is sensitive original content, capped at256KiB
per event and sent only with the additional permission. Larger records are counted
as rejected, not silently truncated. No automatic server retention is enabled.

Run [the operator procedure](../CENTRAL-TELEMETRY-OPERATIONS.md) for actual Sentinel
registration, private variables, DNS/TLS, public synthetic acceptance, edge traffic
controls/capacity and backup-provider restoration. Native Windows DPAPI/WPF and
Ubuntu Secret Service/GTK acceptance remain pending; previous installer acceptance
does not cover this feature. Mac packaged-client opt-in/restart remains pending,
despite the isolated Keychain and shared-code evidence above.
