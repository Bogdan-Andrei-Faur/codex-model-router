# Home controls and Settings cleanup — Ubuntu — 2026-10-08

Source base `48760d78e35c7bd31263308f74cbc39b8a501611`, dirty branch
`feature/dynamic-notch-monitor`; product baseline `0.9.6`.
Artifact `codex-model-router_0.9.6-1~notch24_all.deb`, SHA-256
`3d8487d574bdaba9264c0eb25755d0bd014d4e0f5625e608d1d716e8f3453f49`.

Home's detail action is an accessible icon button in the principal card's
top-right corner. Other-agent cards have stronger neutral backgrounds and
hover/focus contrast. The expanded footer is removed: pause/resume is the first
Settings action, labeled “Pausar enrutamiento” / “Activar enrutamiento”; installed
version and bridge/restart indicators live in the Settings update card.
Transient feedback and preview disclosure remain below navigation, with no
empty notice area. Details, routing actions and read-only behavior are retained.

| Check | Status | Evidence and boundary |
| --- | --- | --- |
| Shared browser groups | PASS with caveat | Layout, interaction, lazy history, glass, Windows channel, updates and preview pass. Usage passed with temporary event diagnostics after repeated intermittent Escape failures; see below. |
| Visual inspection | PASS | Synthetic Home/Settings screenshots reviewed. Detail position measured at principal top-right; footer absent, cards clearer, pause/version inside Settings. |
| Settings behavior | PASS | Pause submits enabled=false; updated disabled state offers activation and submits enabled=true. Preview action stays disabled; version/restart indicators update. |
| Exact Ubuntu package fixture | PASS | GTK/WebKit/font, launcher/single instance, pointer hover recovery and expanded auto-compact fixture. |
| Installed activation | PASS | Visible authentication completed; only monitor restarted. One instance, WebKit ready, shared resources match source, settings unchanged, one connection, no mismatch/unknown/restart flags or traceback. Monitor `9906faad1d8a0025`, router `7b899c9ef41eedde`. |
| Native Mac/Windows / physical owner acceptance | NOT_RUN | Shared code included; independent native/physical acceptance remains open. |

The existing intermittent quota Escape assertion reproduced with quota still
focused and reopened. A diagnostic run passed without a runtime change; the
cause is not confirmed and this is not a hover fix. Temporary event collection
was removed; failure messages now retain safe synthetic viewport/state context.
Do not describe all hover behavior as physically accepted based on this receipt.

No routing engine changes or remote publication. Rollback package/settings saved
privately. No owner state, secrets or raw logs retained in this receipt.
