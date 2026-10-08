# Horizontal Agents workspace — Ubuntu — 2026-10-08

Development branch `feature/dynamic-notch-monitor`, base `48760d78e35c7bd31263308f74cbc39b8a501611`; product baseline `0.9.6`.
Artifact `codex-model-router_0.9.6-1~notch28_all.deb`, SHA-256 `4f0343b4bf0ebe85060aa6be32e2be4955683c5e4cd18d07b9c53c40b0f46642`.

Agents uses a content-sized wide island like Home. The selected companion,
identity and vertically scrollable task picker sit in the left column; per-task
routing controls, evidence and attention/phase information sit in the right.
Below 620px the columns stack and the picker becomes horizontal. Both scroll
axes and keyboard focus survive live refresh. History, Consumption and Settings
retain their resizable panel height. No native host or routing engine change.

| Check | Status | Boundary |
| --- | --- | --- |
| Scoped shared browser checks | PASS | Layout, controls/evidence, preview adapter, interaction and lazy journal fixtures. Preview verifies left/right ordering and content-sized height; control tests retain strict probable/confirmed distinction and native acknowledgement. |
| Visual/size review | PASS | Synthetic 800px screenshot reviewed; 340/432/800px pages have no horizontal overflow. |
| Exact Ubuntu artifact | PASS | Isolated GTK/WebKit/font, packaged launcher/single instance, pointer ownership and missed-exit recovery. |
| Installed activation | PASS | `0.9.6-1~notch28`: one instance and connection, WebKit ready, shared resources match source, settings preserved, no traceback or mismatch/unknown/restart flags. Monitor `b6a93a0942ba720a`; router `7b899c9ef41eedde`. Only monitor restarted. |
| Native Mac/Windows / physical acceptance | NOT_RUN | Shared source applies to all hosts; independent native/owner acceptance remains open. |

The existing intermittent quota Escape issue remains open; this layout change
is not a hover correction. No remote publication. Previous artifact and selected
settings are saved privately; no private data or raw logs in this receipt.
