# Agents routing workspace — Ubuntu — 2026-10-08

Development branch `feature/dynamic-notch-monitor`, base `48760d78e35c7bd31263308f74cbc39b8a501611`; product baseline `0.9.6`.
Final artifact `codex-model-router_0.9.6-1~notch26_all.deb`, SHA-256 `abf3af220916bc276c0513d754a5f78f784fe13bb9c9f777ec292cb1566ef108`.

Agents now presents the selected companion, task identity and state at the top,
a compact task picker, per-task automatic/manual routing controls, three
model/effort evidence cards (proposal, acceptance, confirmed inference), and
contextual attention/phase information. Full explanations stay in History;
Home retains context/quota meters. No routing engine change.

The selected character uses the shared identity and animation states. It has no
context meter or redundant click action. Selection, keyboard focus and picker
scroll survive live updates. A probable observation does not fill the confirmed
card. Native acknowledgement controls mode selection; preview stays read-only.

| Check | Status | Boundary |
| --- | --- | --- |
| Shared browser coverage | PASS with separate caveat | Layout, task controls/evidence, interaction, lazy history, Windows channel, updates and preview pass. Layout and controls rerun after portrait addition. |
| Evidence/control regressions | PASS | Probable versus confirmed, accepted-model separation, native mode request/acknowledgement, focus retention, waiting/offline/paused states, disabled preview. |
| Visual checks | PASS | Synthetic 340/432/800px layouts without horizontal page overflow; final portrait screenshot reviewed. |
| Final exact Ubuntu artifact | PASS | Isolated GTK/WebKit, bundled font, launcher/single instance, pointer ownership and hover recovery fixture. |
| Installed readback | PASS | `0.9.6-1~notch26`: one monitor, WebKit ready, UI source matches installed resources, settings unchanged, one connection, no mismatch/unknown/restart flags or traceback. Monitor `6de6e0e4e91a7969`; router `7b899c9ef41eedde`. |
| Native macOS/Windows and physical acceptance | NOT_RUN | Shared source applies to all hosts; owner-machine acceptance is independent. |

The existing intermittent quota Escape assertion reproduced during the full
browser sequence at 390px / 1.25 scale. It remains an open issue; this work does
not claim a hover fix or an entirely passing suite. Separate scoped hover and
native fixtures do not supersede that failure.

The initial workspace artifact `1~notch25` was installed before the owner's
portrait request. Final `1~notch26` includes that refinement. Only the monitor
was restarted; no Desktop restart or remote publication. Rollback artifact
and settings are retained privately. No private state or raw logs in this receipt.

## Follow-up: remove redundant History action

Installed `0.9.6-1~notch27` removes the bottom “Ver historial” action from Agents;
History remains available through top navigation. Its unused helper/style were
removed and the lazy-journal test now exercises navigation and row selection.
Scoped browser fixture PASS (37,000 synthetic records); installed readback PASS:
one connected monitor, WebKit ready, source resources match, settings unchanged,
no mismatch/unknown/restart flags or traceback. Monitor `56036bc555e38871`, router
`7b899c9ef41eedde`. Only the monitor restarted.
Artifact SHA-256 `0ae5ec54052a61fb3c6fcb58964ed3e61882ead4e80d684a16921cc2e3b93d9e`.
The prior exact native fixture belongs to `1~notch26`; it was not repeated for
this button removal. Existing physical/hover and other-platform gates remain open.
