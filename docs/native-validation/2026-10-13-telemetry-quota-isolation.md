# Telemetry quota isolation — 2026-10-13 — local source and isolated fixtures

## Scope and identity

Owner requested restoring sending by separating metrics and diagnostic quotas.
Candidate is an uncommitted working-tree change over main
`611049ee20941a19728d8d9855d1ea51e1add08a`, VERSION0.9.12. This is not a new
release, installed client or production recovery receipt. Preserve the earlier
[production diagnosis](2026-10-13-api-degraded-diagnosis.md) as historical evidence.

## Change

- Metrics:1GiB per installation/4GiB total encoded events. Diagnostics (prompts
  plus raw OTLP):8GiB per installation/32GiB total encoded events.
- Shared physical database guard remains5GiB; diagnostics stop256MiB earlier
  to leave admission headroom for metrics. Encoded and physical sizes differ;
  these are not filesystem reservations or unlimited-retention guarantees.
- Usage is computed from existing event-size metadata. No schema migration,
  data deletion, consent reset or sampling. Existing aggregate counters remain
  compatible with older source. Duplicate events retain exact ACK at capacity;
  new mixed batches remain atomic.
- New client uses separate metrics-first batches and independent capacity
  backoff. Each lane removes only exact ACKed rows and rechecks consent. New
  diagnostics reserve512KiB/256queue slots for metrics without evicting rows.
- Private panel and shared Settings distinguish quota scopes without content.

## Verification

| Gate | Evidence | Boundary |
| --- | --- | --- |
| Core Python |609tests,53expected skips; Python3.14.8 | Local source only |
| Central client |20tests PASS, including blocked diagnostics, FIFO bypass, reverse quota blockage, opt-out between lanes, invalid ACK and event-slot reserve | Synthetic queue and transport |
| PostgreSQL service |14tests PASS against disposable PostgreSQL17, including actual new client→API→DB lane isolation, capacity recovery, exact retry, consent and deletion | Isolated real database, no production data |
| Browser Settings | Existing permission/deletion/read-only gates plus all five new quota labels PASS | Shared UI in browser, not physical owner acceptance |
| Container lifecycle | Real image/HTTP, read-only container, pg_dump/restore and deletion replay PASS | Disposable containers; production=false |
| Static | JavaScript syntax and Git whitespace checks PASS | No CI run claimed |

The first PostgreSQL run exposed a private-panel variable collision; it was fixed
and the complete14test fixture passed on rerun. No production data was involved.
The container lifecycle fixture used the candidate image before a subsequent
cosmetic panel-label clarification; application behavior is unchanged by that label.

## Delivery and remaining acceptance

No commit, push, deployment, owner installation change, assisted real send or
native background recovery occurred in this receipt. Publication awaits explicit
owner approval under the standing no-commit/push instruction at that time.
The owner subsequently authorized main publication, Sentinel P510 deployment and
real sending verification; the deployment receipt will record actual results.

After normal Sentinel deployment on P510, verify loaded source/limits, original
pending-event ACKs, queue trend and native last-sync advancing without consent
changes. Backend budgets should restore the current legacy mixed-batch sender;
full independent-lane behavior and specific new labels require a subsequent
signed client release and owner update. Do not hotpatch the installed client.

Already rejected capture attempts are not recovered historical events. The
Sentinel process-specific origin `fetch failed` diagnosis remains separate;
readiness200 and successful ingestion do not by themselves resolve that badge.

Windows/Ubuntu owner installation acceptance remains closed. Their actual
sharing, signed update/cancel/recovery gates remain
separate. No new platform-native acceptance is claimed here.

Subsequent owner-authorized publication, deployment and actual native recovery
are verified in the [production receipt](2026-10-13-telemetry-quota-recovery.md).
