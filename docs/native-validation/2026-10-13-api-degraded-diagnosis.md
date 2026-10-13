# API degradation diagnosis — 2026-10-13

## Scope and identities

- Read-only observations around05:11–05:18Z; owner Mac, Sentinel controller and P510.
- Router checkout/deployed backend: `611049ee20941a19728d8d9855d1ea51e1add08a`.
- Sentinel deployed source: `09fd0faeb9bbf2ff16b7e7b25191610d5c0e4c13`.
- No restart, deployment, quota/consent/credential change, manual upload or deletion.
- Private payloads/log contents/installation identifiers were not emitted.

## Findings

| Signal | Verified observation | Interpretation |
| --- | --- | --- |
| Public readiness | HTTPS200/ready=true; Sentinel public probe also200 | API process/schema/database/ledger readiness succeeds; not ingestion capacity proof |
| Docker health | API and DB healthy, no API OOM; recent health commands exit0 | No container/process outage observed |
| Sentinel origin probe | Latest checks show no HTTP code, `fetch failed` in3–9ms, while public probe200 | The degraded badge reflects its internal HTTP probe failure |
| Independent origin probes | Controller Python200, controller Node24.16.0 three times200, controller Node26.5.0 and owner LAN probes200 | Current direct route works from fresh processes; exact failure inside the long-running Sentinel process is unconfirmed |
| Monitoring transition | Last healthy00:06:04Z; degraded begins00:06:34Z and persists | Distinct from the earlier ingestion-capacity incident |
| Ingestion quota |1,072,831,654 encoded bytes of1,073,741,824 per-installation limit;910,170bytes left |99.915% full; another quota increase merely delayed saturation |
| Data mix | Raw OTLP1,056,411,092bytes/15,473events; metrics16,369,927bytes/22,480events; prompts50,635bytes/164events | Raw diagnostics account for98.469% of encoded storage |
| Other ceilings | Total encoded1,072,831,654 of4GiB; physical DB112,768,691bytes of5GiB; disk57.4GiB free | Physical disk/DB exhaustion is not the current blocker |
| Actual sender | `installation_capacity`; last sync2026-10-12T16:57:22Z;1071queued/8,388,180bytes | Authenticated delivery remains stalled independently of readiness |
| Next batch |24events/1,010,035bytes exceeds remaining910,170bytes | The batch cannot fit the installation quota |
| Pending mix |943metrics/697,029bytes and128raw/7,691,151bytes | Diagnostics share the admission budget and queue with metrics |
| New capture | Rejected counter26840→27297 during read-only observations | Counter is cumulative enqueue rejections, not a count of unique lost records; no backfill/recovery asserted |
| API safe log aggregates |77installation-capacity warnings over12h; zero sampled traceback/OOM/DB-permission/disk-full classes | Supports quota diagnosis; no raw logs retained in this receipt |

The long-running Sentinel process had56open-descriptor records and no observed
connection to the current P510 web port in the sample. This does not establish
a connection-pool, OS-permission, proxy, DNS or code root cause. The stored error
omits the underlying Fetch cause. Do not hide the badge, disable checks, restart
production or relabel public200 as successful uploads to claim recovery.

## Recommended next work

1. Diagnose the Sentinel process-specific probe with safe underlying error codes
   and target metadata; preserve independent public/origin evidence.
2. Restore bounded ingestion capacity without deleting existing data, then
   separate the metrics budget/admission path from raw diagnostics so a large
   diagnostic history cannot stop ordinary metrics. Keep full raw capture only
   under the existing explicit owner permission; do not silently sample/filter.
3. Confirm actual native ACKs, queue drain and stable capture rejection counters.
   Raising a quota alone is not evidence of restored sending.

The owner requested diagnosis only. No production repair, restart or quota change
was applied. Initial read-only SQL used an incorrect grouping column and aborted;
the corrected aggregate reads use installation byte counters and event sizes.
An initial combined Atlas scope was rejected; repository-scoped Router and
Sentinel retrievals succeeded. No continuity outage remains.

Sentinel continuity now records deployed Router backup integration on09fd0fa;
guided restoration remains separately unvalidated. That supersedes the older
unsupported-integration assumption, without claiming a fresh restore test here.
