# Compact crew and visual quota — 2026-10-08 — Ubuntu

## Identity and scope

Source base `48760d78e35c7bd31263308f74cbc39b8a501611`, dirty working tree on
`feature/dynamic-notch-monitor`; baseline `0.9.6`. Artifact:
`codex-model-router_0.9.6-1~notch6_all.deb`; SHA-256
`b22cd4733e1b729b9ba82dc81f73c0e42cc9a6b35327f267ae757e74951dccb0`.

The owner requested a visual quota card and simultaneous compact agents. Shared
HTML/CSS/JS now shows a centered responsive crew of up to six companions and
overflow, reserving the task headline for a single companion. The quota card
uses a large weekly percentage, per-window bars, supplied reset times and an
account-sharing caption. Existing expiry, missing readings, context compaction
and pointer-exit closure semantics are preserved. All three native hosts load
the same shared surface; no routing/official engine changes.

## Results

| Check | Status | Evidence and boundary |
| --- | --- | --- |
| Shared layout suite | PASS | Chromium layout, usage, interaction, history, native glass/message/update fixtures and preview adapter pass. |
| Responsive crew and quota semantics | PASS | 320/390/432/600px and 1/1.25/1.5/2 DPI fixtures show at least three agents, correct overflow and no crew/control overlap. Weekly 76% and short-window 3% retain separate bars; expiry becomes unavailable. |
| Actual preview adapter | PASS | Three simultaneous compact companions, second companion hover opens its own task, quota hover opens the visual card and pointer exit closes it. Polling and lazy history remain read-only. Synthetic screenshots inspected. |
| Exact Linux package | PASS | Isolated GTK/WebKit fixture for `1~notch6` loads the bundled font, closes agent/quota panels without DOM leave and verifies packaged launcher/single instance. |
| Installed activation | PASS | Owner completed visible PolicyKit authentication; installed `0.9.6-1~notch6` and restarted only the monitor. Shared UI matches source; one ready monitor process/window, keep-above acknowledged and configuration/UI/credential namespace byte-identical. |
| Connected data | PASS | One fresh connection and quota available; mismatch/unknown/restart flags false. Installed monitor build `173ffb186559d8a9`, matching installed/loaded router fingerprint `7b899c9ef41eedde`. No runtime traceback. Prior package/state retained privately. |
| Owner physical visual/input acceptance | NOT_RUN | Browser screenshots and Xvfb fixtures are not owner-observed physical acceptance. |
| Mac/Windows native redesign acceptance | NOT_RUN | Shared implementation; independent native checks remain pending. |

Earlier [hover receipt](2026-10-08-linux-notch-hover.md) remains evidence for
`1~notch5`. No private state, raw logs or conversation identifiers included.
Remote publication/CI has not been performed for this branch.
