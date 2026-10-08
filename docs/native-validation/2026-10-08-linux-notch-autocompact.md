# Header removal and automatic compact mode — Ubuntu — 2026-10-08

Source base `48760d78e35c7bd31263308f74cbc39b8a501611`, dirty branch
`feature/dynamic-notch-monitor`; product baseline `0.9.6`.
Artifact `codex-model-router_0.9.6-1~notch22_all.deb`, SHA-256
`a9eef7ed455252f002321c054692d47036340c2daab32156c3aaa58dbf2d34a9`.

The owner requested removing the task-count/collapse/hide header and compacting
the expanded island on pointer exit. Shared UI now starts with icon navigation.
DOM and native pointer exit start one 320ms deadline; repeated outside samples
cannot postpone it, re-entry cancels it and height dragging defers it until
release. Escape and tray actions remain available. Mode changes retain the
existing request/acknowledgment protection. Unsaved key-editor input survives
collapse/reopen in memory without being persisted or sent. The accessible page
title/connection status remain; preview disclosure stays visible in the footer.

| Check | Status | Evidence and boundary |
| --- | --- | --- |
| Eight shared browser groups | PASS | Layout, quota/context, interaction, lazy history, visual semantics, Windows message channel, updates and preview. |
| New interaction coverage | PASS | Repeated native exit, re-entry, real DOM exit, compact native request, resize deferral, unsaved synthetic input and stale mode acknowledgments. |
| Visual review | PASS | Synthetic 600px screenshot confirms no old header and navigation at the top. |
| Exact Ubuntu package fixture | PASS | GTK/WebKit/font/launcher/single instance; existing hover checks plus expanded-to-compact on native pointer exit. |
| Installed activation | PASS | Visible Ubuntu authentication completed and only monitor restarted. One instance, WebKit ready, shared resources match source, settings unchanged and one connection; no mismatch/unknown/restart flags or traceback. Monitor `d1d22c9d8b077696`, router `7b899c9ef41eedde`. |
| Physical owner / native Mac and Windows | NOT_RUN | Shared code included, independent native/physical acceptance still required. |

The initial new draft-input fixture lacked a Jev configuration and therefore no
key editor existed; supplying that synthetic configuration fixed the fixture.
The initial expanded native check left Xvfb's pointer at its default position,
which fell inside the larger island. Keeping the isolated pointer outside both
window sizes made the exit test valid. No runtime workaround was needed.

No routing/official engine changes or remote publication. Previous package and
selected settings retained privately; no owner data or raw logs in this receipt.
