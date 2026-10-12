# Central telemetry operator runbook

Current recorded state, 2026-10-11: **deployed through Sentinel on P510**, HTTPS
readiness and owner Mac0.9.8 native metrics ingestion verified. See the
[deployment receipt](native-validation/2026-10-11-p510-metrics-deployment.md),
[owner activation](native-validation/2026-10-11-macos-central-sharing.md) and
[current follow-up](FOLLOWUP.md). New installations default to no remote sharing;
this owner's Mac has metrics enabled and remote prompt/raw permissions off at the
last verified snapshot. P510 backup/restore is not integrated. These are dated
observations; no live operator action is implied by reading this runbook.

## Files and operator configuration

- Deployed P510 Compose: `deploy/compose.metrics-p510.yml`; build: `services/metrics/Dockerfile`.
- Same-host reference Compose: `deploy/compose.metrics.yml`. Its external
  `sentinel-public` network/upstream example below is not the P510 topology.
- Sentinel example: `deploy/metrics.sentinel.example.yml`. Replace `repoPath` with
  the checkout path on the actual Sentinel machine. Service type is `http` and
  Compose filename follows Sentinel's `compose.*.yml` convention.
- Endpoint: `https://router.andreifaur.dev`. API listens on8080 inside Docker;
  neither API nor PostgreSQL publishes a host port. Caddy reaches
  `http://router-metrics-api:8080` on external `sentinel-public`.
- Configure `METRICS_DB_PASSWORD` and `METRICS_ADMIN_PASSWORD` **once in Sentinel**,
  as different randomly generated64-character hexadecimal values. Keep them out
  of repository files, chat, screenshots and build arguments. The hexadecimal DB
  password avoids URL-escaping ambiguity. `METRICS_IMAGE_TAG` should identify the
  immutable source revision. No ordinary app user supplies any of these values.
- Owner panel: `/`, HTTP Basic username `owner` and the admin password, over TLS.
  It is read-only, has no cookies or mutating GETs, and accepts no client tokens.
  No public dashboard, tracking scripts or browser persistence is used. Browser
  Basic credentials may remain cached until the browser session is closed.
- API credentials are random, installation-scoped bearer tokens. The server only
  stores their SHA256 hashes. Anonymous enrollment does **not** authenticate a
  real person or official binary. Treat cohorts as untrusted observations.

## Capacity incident and production recovery — 2026-10-12

The owner Mac0.9.10 sender authenticated and acknowledged consent (HTTP200),
then events failed with HTTP507 `storage_capacity`. Read-only P510 aggregates
confirm134,101,327 encoded bytes for the largest/only data-bearing installation,
against the134,217,728-byte quota. Total database size was32,085,683 bytes and
host available space88,242,221,056 bytes. Raw OTLP dominates encoded event bytes;
this was an application quota, not a full disk, expired credential or lost consent.
Existing data/outbox/permissions are preserved. Already rejected capture attempts
cannot be claimed recovered or remotely backfilled.

Deployed95436e8 defaults:1GiB per installation,4GiB aggregate encoded events,5GiB
physical database. Compose operators can set `METRICS_MAX_INSTALLATION_BYTES`,
`METRICS_MAX_TOTAL_BYTES`, `METRICS_MAX_DATABASE_BYTES` in Sentinel; these map to
existing API `MAX_*` settings. No automatic deletion is introduced, and these
ceilings are not disk reservations. Keep disk/DB monitoring active and revisit
quotas as diagnostics grow. API507 reasons distinguish installation, aggregate
and database capacity; HTTP429 remains transient admission/rate pressure.
The private panel shows aggregate capacity use and bytes per kind, without IDs
or diagnostic contents. Sentinel receives a content-free capacity warning.

Client capture rejection preserves the last sender error instead of masking it.
New diagnostics leave512KiB of the8MiB outbox available for metrics; existing
queued rows are never pruned to obtain this reserve. A successful acknowledged
send clears the transport error; pending rows are removed only after exact ACK.

Sentinel P510 deployed the correction successfully. All233 original pending
events were ACKed; installed0.9.10 native background delivery independently
resumed after backoff. See [recovery receipt](native-validation/2026-10-12-central-capacity-repair.md). Do not reset permissions, re-enroll, delete server events or clear
the outbox as a workaround. The client fix is now delivered in the signed0.9.11 Mac release; owner installation
remains0.9.10 until updating. See [release receipt](native-validation/2026-10-12-macos-telemetry-release.md).

## Sentinel deployment

Current result: P510 backend deployment and public synthetic validation PASS;
see [2026-10-11 deployment receipt](native-validation/2026-10-11-p510-metrics-deployment.md).
Owner Mac0.9.8 release/activation and actual metrics ingestion are also verified
by the newer owner receipt linked above. Other-platform sharing and recovery
remain open. Last deployment receipt records autodeploy at300s; do not replace
that owner-selected setting with historical onboarding defaults below.

### P510 onboarding procedure — historical preparation, 2026-10-11

Sentinel now supports remote application deployment, state, logs and HTTP routing
on P510. The live controller reports `e5864948a84b7704fc86a1aa4c2931cafbf5afaa`;
its remote-deployment contract is documented in Sentinel's
`docs/operations/node-app-deployment.md`. The owner explicitly requested normal
deployment after being told remote backup/restore is **not integrated**. Do not
describe this deployment as backed up or restored through Sentinel.

Use `deploy/compose.metrics-p510.yml` via **Incorporar proyecto Compose**, select
execution node P510, web service `api`, internal port8080 and readiness endpoint
`/health/ready`. Set the two private variables below and leave autodeploy and
backup disabled. The remote profile uses only project-owned networks and named
volumes; no external `sentinel-public` network or host mount is required. Sentinel
assigns container/volume names, exposes only the API on a LAN port and configures
the Mac proxy to reach it. PostgreSQL has no published port.

The remote filename follows Sentinel's single-suffix convention
(`compose.metrics-p510.yml`). Empty variable defaults allow Sentinel to inspect
the Compose before configuring private environment values. They are not usable
credentials: a new PostgreSQL database refuses an empty password and API readiness
rejects an owner password shorter than32 characters. Never enable trust auth.

Remote Sentinel does not support a separate migration command. This profile
explicitly runs the additive/idempotent schema migration before starting Uvicorn;
failure prevents HTTP startup. Future incompatible migrations require a reviewed
upgrade procedure, not automatic rollback. The original same-host profile keeps
its separate operator migration command.

Public clients use HTTPS. The current Sentinel remote ingress forwards HTTP
between the Mac proxy and P510 over the trusted LAN; it does not provide encrypted
node-to-node transport. Restrict access to the trusted home network. Operator
credentials and environment must remain outside source/control logs.

Source preparation is not a deployment receipt. Confirm matching remote commit,
terminal worker receipt with transfer cleanup, actual container health, public
TLS/ingestion and owner panel authentication before recording activation.

### Sentinel onboarding rejection — 2026-10-11

Resolved in installed Sentinel `05cccb553b282588a09fe38881a23f841fed8288`.
The frontend now gates suggestions using the current execution node and excludes
remote-incompatible fields. Owner's live simulation is valid. The analysis below
records the earlier failure, not an active blocker.

The owner reports: “El despliegue en otro equipo requiere modo gestionado y
Compose sin comandos adicionales.” Read-only inspection of Sentinel controller
source `e5864948a84b7704fc86a1aa4c2931cafbf5afaa` identifies this reproducible path:

1. Select P510, then inspect a Compose file containing a database service.
2. `NewComposeProjectPage.tsx:380` auto-populates `baseServices` from databases
   without checking the execution node. The remote form hides this field.
3. `buildPayload` at line537 still sends it for managed remote projects.
4. `apps/server/src/routes/projects.ts` rejects remote onboarding when
   `baseServices` or separate migration/seed commands are nonempty.

Switching to P510 clears the fields once, but a subsequent inspection repopulates
them. The owner's actual request payload was not inspected, so attribution of
that specific rejection remains probable. Do not expose a request body containing
credentials to diagnose it. This validation concerns onboarding fields, not the
API service's startup `command` in our Compose profile.

Suggested Sentinel correction: restrict database suggestions to local execution,
serialize empty local-only fields for remote nodes, and test P510 selection
followed by inspection and reinspection of a database-bearing Compose file. Keep
the backend rejection as a guard. The owner will coordinate with the Sentinel
agent; no Sentinel changes, submission retry or deployment were performed here.

### Remote upstream warning / pre-deployment review — 2026-10-11 (historical)

The valid live simulation still warns that upstream does not contain
`router-metrics-api`. In Sentinel `05cccb5`, `buildOnboardComposePlan` applies this
warning without restricting it to local execution, while `buildPayload` correctly
sends an empty remote upstream. Remote routes are created disabled with a dummy
upstream; successful `remote-deploy.ts` finalization obtains the chosen service's
published port, installs the node's IP/port, enables the initial route and applies
Caddy. The warning does not invalidate the simulation and is not evidence of a
broken remote route. Sentinel should gate this warning on local execution.

Read-only controller checks passed with the actual private environment without
printing values: distinct64-hex credentials, file mode0600, Compose normalization,
no published database port, API read-only, explicit startup migration and owned
named volumes/networks. P510 still has no metrics containers. Public DNS/TLS now
work, but `/health/ready` returns `Sentinel Caddy is running`; even HTTP200 here
is not backend readiness. Verify the backend's expected JSON after deployment.

The reviewed form selects P510/api8080 and `/health/ready`, with initial deploy
off. It currently has autodeploy every300s enabled, unlike the earlier manual-only
preparation. Owner submission with new credentials remains a browser-tool handoff;
after project creation the owner explicitly authorizes deployment without another
permission request. No registration/deployment/ingestion is claimed by this review.

### Historical deployment hold (superseded)

The owner selected **P510**, not the Mac mini, and explicitly chose to leave
deployment pending after the placement limitation was confirmed. Publishing
source does not activate collection, provision credentials or change DNS.

Read-only checks confirmed P510 SSH access, Linux, Docker29.1.3, about84GiB
available on the root filesystem, no failed systemd units and only the existing
Sentinel CI runner container. The native Sentinel controller and current remote
source both identify revision `32a476809498deb4f860ab1e6c6c72762c76bd7f`.
Its node observer supports bounded read-only collection, while its project
deployment and Docker client still operate on the controller's local checkout
and Docker socket; projects have no execution-node selector. Node visibility or
CI execution is not proof of application deployment support.

Before resuming, implement and validate explicit P510 project placement in
Sentinel, including remote execution/provenance, private environment handling,
health, backup/restore and cancellation. Then adapt the public ingress path:
`sentinel-public` is a Docker network on one host, not a cross-host network.
The example below assumes a colocated controller/proxy and workload; do not
import it unchanged on the Mac mini or publish a database port as a workaround.
No direct SSH deployment, remote Docker socket exposure or Sentinel source
change was performed. Fresh access/capacity checks are required when resumed.

1. Publish/review the candidate source through the normal owner workflow. Register
   the example in Sentinel/UI using the correct host checkout. Keep autodeploy off
   for the first delivery. Set the private variables there and confirm
   `sentinel-public` and the domain's DNS/TLS route on that host.
2. Build the image and database using Sentinel's deployment environment. The
   explicit migration command is:
   `docker compose -f deploy/compose.metrics.yml run --rm api python -m services.metrics.app migrate`.
   It requires the image to have been built and the DB to be healthy. Migration1
   is additive/idempotent. Startup never silently migrates or clears a database.
3. Require API readiness and database health before accepting the delivery.
   `/health/live` checks the process; `/health/ready` checks schema, DB access,
   minimum admin-secret length and writable deletion ledger. The domain route
   must be HTTPS; do not expose Basic/Bearer authentication through public HTTP.
4. From a synthetic client, verify enrollment→consent→batch→duplicate retry,
   private panel401 without admin auth, disallowed diagnostics403, opt-out and
   explicit deletion. Verify neither logs nor UI exposes tokens or raw payloads.
5. Back up PostgreSQL **and** the deletion ledger volume through Sentinel, then
   perform the restore procedure below on an isolated destination. Only after
   that should an updated desktop package expose this delivery to users.

The example contains a placeholder path and operator-owned secrets are missing
on purpose. It is not itself proof of Sentinel registration or production TLS.
Do not edit Sentinel's generated Caddyfile or database directly. The repository
checkout354464b integration contract was inspected; deployed Sentinel can differ.

## Storage, admission and failure behavior

Metrics and consented diagnostic JSON are stored in PostgreSQL, not public files.
The only separate volume is `/data/deletions.jsonl`, a content-free deletion
intent ledger needed for recovery. The database backup includes diagnostics.
Nothing is deleted automatically by elapsed time. Defaults:

| Limit | Default |
| --- | --- |
| Enrollment |60 new installations/hour globally,10,000 total |
| Authenticated operations |120/minute per installation (successful operations) |
| Request |1MiB decoded JSON, no compressed request bodies |
| Event / batch |256KiB /100 events |
| Stored events |1GiB per installation,4GiB total encoded event bytes (production updated2026-10-12) |
| Database |5GiB database size admission ceiling |
| Container resources |512MiB/1CPU each;32 concurrent API requests |
| Desktop outbox |8MiB or4096 events, whichever comes first |
| Deletion ledger |128MiB admission ceiling; requires operator attention if full |

Tune limits explicitly in Compose after reviewing capacity. Reaching capacity
returns507 or429; retained records are not evicted. Bytes count encoded event
payloads, not all PostgreSQL/index/WAL overhead; the DB-size limit is a second
admission check, not a filesystem reservation. Monitor actual host free space,
DB/WAL and backup growth in Sentinel. Global anonymous admission limits bound
storage but can be exhausted by abusive clients; an Internet exposure review and
edge traffic limits are still required before broad public rollout.

The desktop retries with jitter/backoff up to10minutes. HTTP errors never display
server bodies. No redirect is followed with client credentials. TLS uses platform
certificate verification. Backend access logging is off. Do not enable request
body/header logging at the reverse proxy. Raw OTLP is **not redacted**; collection
requires its own permission and may contain sensitive content. Over256KiB
records are explicitly counted as dropped, not truncated or partially uploaded.

## Desktop implementation and limitations

- One shared Python outbox/uploader and one shared Settings UI serve Mac, Ubuntu
  and Windows. Remote consent is in a private SQLite control record, independent
  of `config.local.json` local capture settings; no old local flag opts users in.
- New primary journal writes feed the outbox; no historical backfill is performed.
  Metadata reuses `evidence.scrub` with a persistent local HMAC salt. Prompts send
  only the message and pseudonymous decision ID, not the whole prompt record.
- Raw capture receives the decoded original UTF8 OTLP JSON body, preserving its
  whitespace/content; HTTP headers are never included. Compressed wire bytes are
  not retained. The first upgraded bridge must load this callback through a normal
  owner-approved Desktop restart. The old installed bridge cannot acquire it live.
- Changing any permission clears the old queued permission epoch. Master-off also
  clears extra permissions. Re-enabling does not restore them. The worker checks
  epoch before batching; an already dispatched request can still finish. The next
  server consent update rejects the older epoch. Off does not erase server data.
- `Eliminar mis datos enviados` disables capture, clears queued samples and retries
  authenticated deletion when connected. A deletion barrier prevents replay of
  that epoch after restoration. A fresh later permission epoch may collect again.
- macOS uses Keychain Security.framework; Windows uses per-user DPAPI; Ubuntu
  uses the existing Secret Service adapter. Secret-store failure blocks enrollment
  rather than falling back to plaintext or a universal application secret.
- The monitor owns network work. Closing it stops the worker; an active bridge may
  fill the bounded queue until the monitor returns. No collector network operation
  blocks inference. Queue appends use a50ms SQLite lock budget and never propagate
  failure into routing. This is best-effort research telemetry: a crash between
  local-journal/outbox commits or a disk/lock failure can lose a remote sample.
  The dropped-size/format/capacity counter is exact for committed rejections;
  it cannot count failures to write the counter itself. Do not claim audit-grade
  delivery or complete coverage.
- The owner dashboard reports accepted models, evidence confidence, status,
  cohorts and latest token snapshots. Snapshots are never summed across polls;
  tokens may include pre-consent context and are not incremental billed usage.
  Missing values/costs remain unknown. No ranking of model quality is inferred
  from popularity alone. Raw diagnostics have an authenticated attachment endpoint
  `/admin/diagnostic/{installation}/{event_id}`, not inline HTML rendering.

## Revocation, backup, restore and rollback

To revoke a compromised installation, use Sentinel's authenticated operator shell
and `docker compose -f deploy/compose.metrics.yml run --rm api python -m services.metrics.app revoke INSTALLATION_ID`. Tokens then cannot ingest or delete; handle an owner-verified
manual deletion request with the corresponding `delete-installation INSTALLATION_ID`
command, which writes the deletion ledger before deleting; never use an unlogged SQL DELETE. Credential loss has no anonymous account-recovery shortcut.

Before a DB restore, disable public admission and stop the API through Sentinel.
Preserve the **latest** deletion ledger independently from the older DB backup;
restoring an old ledger alone can resurrect deliberately deleted content.
Restore PostgreSQL and merge preserved/newer ledger entries (duplicates are safe),
then run with the same private environment:

```
docker compose -f deploy/compose.metrics.yml run --rm api python -m services.metrics.app replay-deletions
```

Replay removes events at or before each recorded deletion epoch, recalculates
retained byte counts and closes older permission epochs. A malformed/truncated
ledger makes replay fail; recover its last complete copy/intent before exposing
the service. Take a new verified backup and validate synthetic deleted records
are absent before reopening ingress. Backups may still contain historical data;
restrict operator access and keep the ledger with every recovery plan.

Rollback uses a recorded previous image with a compatible schema. Do not roll
back the database blindly or start an old writer against an incompatible future
schema. Keep backups and ledger until deliberate owner disposal. No automatic
retention policy or destructive cleanup command is installed.

## Reproducible local verification

Use an isolated Python environment with
`services/metrics/requirements-test.txt`, then:

```
PYTHONPATH=src python -m unittest discover -s tests -p test_central_telemetry.py
python services/metrics/run_fixture.py
docker build -f services/metrics/Dockerfile -t router-metrics:fixture-20261011 .
python services/metrics/run_container_fixture.py
npm test
node tests/test_monitor_central_telemetry.cjs
```

`run_fixture.py` creates/removes only its UUID-named disposable PostgreSQL17
container, binds a random loopback port and generates synthetic credentials.
Its tests reject ordinary production DB URLs; never bypass that guard. The
private panel fixture verifies isolation, deduplication, consent, quotas, deletion
ledger replay and synthetic client→database delivery. The container fixture uses
a real `pg_dump`/`pg_restore` into a second disposable DB and replays the current
ledger before checking absence of the deleted event. It does not validate a
production backup provider, public TLS, real prompts, Windows DPAPI or Ubuntu
Secret Service. Native and Sentinel activation checks remain separate gates.

## Remaining acceptance per environment

- **Sentinel host:** actual registration/private variables, source/image provenance,
  DNS/TLS, public synthetic roundtrip, host capacity monitoring, backup-provider
  restore plus current deletion-ledger replay. No deployment has been performed.
- **Mac:** install a package containing this source in an owner-approved window;
  verify Keychain access, Settings opt-in/off, monitor restart/retry and a freshly
  loaded bridge's raw callback using synthetic content. Preserve the active app.
- **Windows:** same consent/restart/queue cases plus native DPAPI read/write and
  WPF shared Settings rendering. WPF only needs validation when using Windows.
- **Ubuntu:** same cases plus Secret Service availability/locked-keyring behavior
  and native GTK Settings. There is no plaintext credential fallback.
- Installation acceptance for existing Windows/Ubuntu installers does not close
  these new telemetry gates; those packages predate this implementation.
