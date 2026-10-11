# Owner Mac central metrics sharing — 2026-10-11

## Installed and loaded identities

Owner completed the managed update and normal Desktop restart. The installed app
is0.9.8, monitor `e5bdb664cc13a783`, router `100ad6ea0e4db975`, matching the
public package from source `6f1aabf4d49c77195724ab591242fb5b72f5ed85`.
The private update transaction records old0.9.7 →0.9.8 as `completed`.
One live bridge snapshot reports0.9.8 with the matching router identity and a
completed handshake. These observations establish activation, not inference
attribution or login/power-loss recovery.

## Actual Settings and production backend

Used the real installed application's native Settings → Data and privacy.
Before activation, no central outbox existed and the server had two disabled
synthetic installation records, zero events and no diagnostic permissions.

| Action | Native client evidence | P510 server evidence |
| --- | --- | --- |
| Share metrics | New local outbox; epoch1, enabled, prompts/raw off, dirty0, synced; UI says synchronized, zero pending/discarded | Third installation enrolled automatically; exactly one enabled; real metrics arrive |
| Stop sharing | Epoch2, disabled, dirty0; queue zero; UI says sending disabled | All three installations disabled; prompt/raw permissions remain false |
| Share metrics again | Epoch3, enabled, synced; queue zero, discarded0; UI independently confirms synchronized | Exactly one installation enabled again; metrics ingestion continues |

At the recorded post-reactivation snapshot, the server held12 real metric
events: four each of `decision_usage`, `decision_usage_total` and
`inference_probable`. No prompt or raw OTLP events existed. These are natural
events from the running installed Router, not manually inserted test events.
Counts continue increasing during normal work. Inspected only aggregate counts,
event categories, consent states and safe installed/update metadata; no messages,
titles, credentials, raw payloads or conversation identifiers were exposed.

`inference_probable` remains probable evidence; successful delivery does not
upgrade it to confirmed model attribution. The early sample does not establish
coverage of new-turn routing/completion events or comparative routing quality.

## Final state and remaining boundaries

**Metrics sharing is enabled** on this Mac to the owner-selected HTTPS backend
at `router.andreifaur.dev`, with **prompt and raw OTLP sharing disabled**.
Existing local prompt capture remains an independent, previously enabled setting.
No client credentials, URL or account were entered manually; the installed
client used its normal native credential/enrollment path.

No data deletion was requested or performed against these real samples. Native
owner deletion/offline-retry acceptance is separate from prior synthetic protocol
tests. Windows/Ubuntu installed-client sharing and managed-update acceptance
remain independent; their exact installer transfer is still pending. Remote
backup/restore integration remains unsupported as previously accepted.

This closes the owner Mac updated-client activation and real Settings
enable/sync/disable/re-enable ingestion gates. It does not claim native acceptance
on other systems, confirmed inference attribution or comprehensive recovery QA.
