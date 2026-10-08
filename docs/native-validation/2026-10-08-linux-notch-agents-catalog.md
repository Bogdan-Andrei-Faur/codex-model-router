# Non-archived Agents catalog — Ubuntu — 2026-10-08

Development branch `feature/dynamic-notch-monitor`, base `48760d78e35c7bd31263308f74cbc39b8a501611`; baseline `0.9.6`.
Artifact `codex-model-router_0.9.6-1~notch29_all.deb`; SHA-256 `585fb3522afada5524ff32ad12ad1d666ded409da9e1be6df83d105265e7d4fb`.

Agents now includes inactive conversations and has its own selection. Home and
compact mode retain their existing live/attention filters and data projection.
The bridge exports a separate monitor-only `agent_threads` snapshot from its
existing non-archived paginated inventory. Persistent catalog entries with no
observed routing state carry only identity, inactive status and `catalog_only`;
no model, context or inference is fabricated. Archive/delete removes entries;
unarchive restores them. Internal ephemeral visibility rules remain intact.
MonitorState projects `agentThreads` and task modes identically on three hosts.
Older bridges fall back to observed conversations. Loading the complete catalog
requires a Desktop restart with the new bridge; monitor-only restart is insufficient.

| Check | Status | Boundary |
| --- | --- | --- |
| Python regressions | PASS | 15 inventory/service tests: catalog-only entries, archive/unarchive, late pages, routing/Home isolation and equal three-platform projection/task modes. |
| Shared browser regressions | PASS | Layout, controls, lazy journal and preview. Idle selection, archived exclusion, replacement of archived selection and Home selection isolation verified. |
| Exact Ubuntu package | PASS | Isolated GTK/WebKit/font, launcher/single-instance, pointer/hover recovery fixture. |
| Installed monitor readback | PASS for successor `1~notch30` | Owner subsequently authorized installation. One monitor and connection, WebKit ready, UI matches source, settings unchanged, no traceback. Monitor `c37af6658e8effe4`; packaged router `c4de855b9dd73913`. |
| New live bridge/catalog | PENDING | Owner must restart Desktop; do not interrupt ongoing tasks to force activation. |
| Native Mac/Windows / physical acceptance | NOT_RUN | Shared implementation; independent real-machine gates remain open. |

The existing intermittent quota Escape issue remains open. No remote publication,
official engine changes or private data in this receipt. Rollback artifact and
selected settings are saved privately.

## Text cleanup follow-up

Prepared `1~notch30` additionally removes the routine next-message hint and the
acceptance/inference explanation paragraph from Agents. History retains its
mode hints; Agents retains the warning when routing is paused. Shared controls,
strict evidence and read-only browser regression PASS. Artifact SHA-256
`add08903dfac61897da182eb570bf68f0174b862855d7e64425ae66818780186`.
The owner clarified that the defer-install choice was accidental and explicitly
authorized installation. `1~notch30` is installed and only the monitor restarted.
The exact native fixture above belongs to `1~notch29`; no full native rerun for
the two-paragraph removal. Live bridge mismatch is expected: the existing bridge
has the old router fingerprint until Desktop restarts. `bridgeBuildUnknown` and
the stored `restartRequired` flag are false, but the mismatch still requires a
Desktop restart to activate the complete catalog. Until then Agents includes
observed inactive conversations through the compatibility fallback.
