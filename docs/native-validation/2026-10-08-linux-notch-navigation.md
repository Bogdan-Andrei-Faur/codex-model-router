# Notch icon navigation — Ubuntu — 2026-10-08

Source base `48760d78e35c7bd31263308f74cbc39b8a501611`, dirty branch
`feature/dynamic-notch-monitor`; product baseline `0.9.6`.
Artifact `codex-model-router_0.9.6-1~notch20_all.deb`, SHA-256
`b136d8f9a3a684d451ad3f6bd23545aac79010d33ab7c2a17ddfc465ecd86f38`.

Shared navigation now has five named icon buttons: Inicio, Agentes, Historial,
Consumo and Ajustes. The selected icon has a rounded neutral background; Settings
is at the right edge and no longer duplicated in the header. Home restores the
content-sized overview; Agents opens the selected agent inspector. Detail actions
update the active navigation destination. If the selected agent disappears, the
monitor returns to Home instead of leaving stale detail. No native tooltips added.
Five additional original Lucide icons use the existing pinned, integrity-checked
vendor pipeline; generated shared/WPF data and the manifest are synchronized.

| Check | Status | Evidence and boundary |
| --- | --- | --- |
| Eight shared browser groups | PASS | Layout, usage, interaction, lazy history, visual semantics, Windows message channel, updates and preview adapter. Icon names, single selected destination and keyboard Home/Agents transitions covered. |
| Synthetic visual inspection | PASS | 320px and 600px screenshots inspected; no navigation overflow or overlap, Settings aligned right. |
| Exact Ubuntu package fixture | PASS | GTK/WebKit/font ready, shared payload, packaged launcher/single instance and hover pointer recovery. |
| Installed activation | PASS | Visible Ubuntu authentication completed; monitor-only restart, one instance and WebKit ready. Shared HTML/CSS/JS/icons match source, settings unchanged; one connection, no mismatch/unknown/restart flags or runtime traceback. Monitor `12e4800d495747a7`, router `7b899c9ef41eedde`. |
| Native Mac/Windows / physical acceptance | NOT_RUN | Shared implementation included; no physical cross-platform acceptance claimed. |

During the first full run, the quota fixture expired its ten-second sample while
the host was busy. Its clock now pauses after navigation and advances explicitly;
the expiry assertions are retained and the scoped rerun passes. The initial
selected-agent-removal regression also exposed inconsistent navigation state;
the implementation now restores Home and its existing assertion passes.

No routing or official engine changes, no remote publication and no private data
retained in this receipt. Previous artifact and settings backed up privately.

## Top navigation follow-up

Owner requested the navigation at the top rather than below the content. The
shared DOM now places it immediately after the header, before the scrollable
pages; visual and keyboard order agree. Scoped glass/navigation and layout
fixtures PASS. Synthetic 600px screenshot reviewed; at 320px/460px, the navigation
fits and stays fixed while Settings scrolls. Artifact
`codex-model-router_0.9.6-1~notch21_all.deb`, SHA-256
`ade61402dae007456e1382fc11f87042efeb5785126f95c0b7938af725f21e23`.
Installed readback PASS after visible Ubuntu authentication and monitor-only
restart: one instance, WebKit ready, shared resources match source, settings
unchanged and connected without mismatch/unknown/restart flags or traceback.
Monitor `02d52c2aeaa56e5d`, router `7b899c9ef41eedde`. The exact native package
fixture is not rerun for this DOM ordering adjustment; physical acceptance and
native Mac/Windows gates remain pending.
