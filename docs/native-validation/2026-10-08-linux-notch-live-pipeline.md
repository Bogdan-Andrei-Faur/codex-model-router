# Live horizontal pipeline — Ubuntu — 2026-10-08

Development branch `feature/dynamic-notch-monitor`, base `48760d78e35c7bd31263308f74cbc39b8a501611`; baseline `0.9.6`.
Artifact `codex-model-router_0.9.6-1~notch31_all.deb`; SHA-256
`3b907f89436707760e987d7ec777740339925d827eddcca622265b3cec0da8ec`.

Agents has a horizontal connected-node pipeline driven by native plan updates,
with an observed lifecycle fallback. The old generic phase row is removed.
Confirmed inference is hidden unless evidence is confirmed and a model exists.
See NOTCH-MONITOR.md for projection/privacy and completion boundaries.

| Check | Status | Boundary |
| --- | --- | --- |
| Protocol contract | PASS | Local installed CLI generated TurnPlanUpdatedNotification schema: threadId, turnId, plan steps with pending/inProgress/completed. Generation only; no provider request or official code changes. |
| Python regressions | PASS | 78 tests across router, phase tracking, native plan projection, inventory and monitor service. Native events forward normally; updates refresh snapshots; wrong/ended turns rejected; next turn resets; no raw plan prose retained. |
| Core semantics | PASS | 30 JS tests, including observed steps, completion boundaries, interruption, offline/waiting, turn mismatch and lifecycle fallback. |
| Browser regression / visual | PASS | Controls/live plan updates, layout and preview. Screenshot review at 800px and 340px; narrow pipeline scrolls horizontally. |
| Exact Ubuntu artifact | PASS | Isolated GTK/WebKit/font, launcher, single instance and native hover/pointer recovery. |
| Installed monitor | PASS | `1~notch31`, one monitor/connection, WebKit ready, source matches installed UI, settings preserved, no traceback. Monitor `3d8f35e82b886f73`, packaged router `2fec36051e3ccedb`. Old active bridge mismatch remains until Desktop restart; unknown/stored restart flags false. Only monitor restarted. |
| Actual owner-task plan stream | NOT_RUN | Requires Desktop restart/new bridge and a task that publishes native plan updates. Synthetic event replay is not physical acceptance. |
| Native Mac/Windows / physical interaction | NOT_RUN | Shared implementation; independent machine gates remain open. |

Existing intermittent quota Escape issue remains open. No remote publication.
Rollback package and settings retained privately; no private owner logs here.

## Filled compact drops follow-up

Artifact `codex-model-router_0.9.6-1~notch32_all.deb`, SHA-256 `473b0c4ef51dab267df65ecb35c8559089b2ad80079b94ff8d742bb85376cc8b`.
Shared CSS reduces nodes from 42px to 30px, uses filled semantic colors with
black checks/numbers, curved 16px connector necks and a 360px maximum track.
The active node uses mint and gentle scaling; reduced motion suppresses it.
Synthetic screenshot review and existing controls/live-step regression PASS.
No event listener or routing change. Exact GTK/WebKit package fixture PASS.
Installed `1~notch32` readback PASS: one monitor/connection, WebKit ready, UI
matches source, settings unchanged, no traceback. Monitor `68bcbac9f3e2d8fa`,
router `2fec36051e3ccedb`. Existing old live bridge mismatch still requires
Desktop restart; native Mac/Windows and owner visual acceptance remain pending.

## Uniform green and thinner necks follow-up

Installed `0.9.6-1~notch33`, SHA-256 `6915fec9b08a1248cc4c34353143f5d834a126c0eb8160ba7068776f9f95d8b9`.
Connector necks are now 12px instead of 16px; the active node has the completed
node's green and no animation. Numbers/checks remain black. Synthetic visual
review and computed-style checks PASS. Installed readback PASS: one connected
monitor, WebKit ready, resources match source, settings unchanged, no traceback.
Monitor `8cb355c82a17c148`, router `2fec36051e3ccedb`. Only monitor restarted.
No repeated native fixture for this CSS-only refinement; that fixture belongs
to `1~notch32`. Existing live bridge mismatch/restart and physical gates remain.
