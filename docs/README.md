# Documentation index

Start with [HANDOFF.md](HANDOFF.md) for current source/installed/loaded state,
known failures and continuation. [../README.md](../README.md) is the user-facing
project overview. Historical evidence describes its exact revision/artifact;
it does not validate a later implementation or a different owner's machine.

## Current monitor and implementation

| Guide | Scope |
| --- | --- |
| [MONITOR-UI.md](MONITOR-UI.md) | Five screens, companions, tags, controls, pipeline and useful History |
| [NOTCH-MONITOR.md](NOTCH-MONITOR.md) | Geometry, native hover, preview, live plan, projection and layout contracts |
| [SHARED-MONITOR.md](SHARED-MONITOR.md) | UI/hosts, data/action channels, key custody, caching and packaging |
| [NOTCH-CHANGELOG.md](NOTCH-CHANGELOG.md) | Full 2026-10-08 iteration archive and original receipt links |
| [../CHANGELOG.md](../CHANGELOG.md) | Product releases and current development work |
| [../assets/README.md](../assets/README.md) | Brand provenance, Lucide subset, original companions, Nunito/OFL manifests |

Implementation entry points: `router.py` observes and forwards the app-server
protocol; `thread_inventory.py` provides live and non-archived catalogs;
`phase_tracking.py` projects content-free current-turn plans; `monitor_state.py`
provides data/actions and incremental History snapshots; `monitor_service.py`
serves native private pipes; `monitor-ui/` renders the shared surface. AppKit,
WebView2/WPF and GTK hosts retain window/input/tray/key custody. Development
preview lives in `tools/preview_monitor.py` and `tools/preview-monitor.js`.

## Setup, updates and platform acceptance

- [DESKTOP-INTEGRATION.md](DESKTOP-INTEGRATION.md): connection, actual loading and recovery.
- [INSTALLATION-UPDATES.md](INSTALLATION-UPDATES.md): independent code/data, update preparation and limits.
- [LINUX.md](LINUX.md), [MACOS.md](MACOS.md), [WINDOWS-INSTALLER.md](WINDOWS-INSTALLER.md): platform setup and packaging.
- [NATIVE-VALIDATION.md](NATIVE-VALIDATION.md): safe source/artifact/bridge/physical checks.
- [native-validation/STATUS.md](native-validation/STATUS.md) and [REPORT-TEMPLATE.md](native-validation/REPORT-TEMPLATE.md): exact gates and new receipt format.
- [VALIDATION.md](VALIDATION.md): dated validation history; new delivery links appear first.
- [WINDOWS-WPF-VALIDATION.md](WINDOWS-WPF-VALIDATION.md), [MAC-MONITOR-INTERACTION.md](MAC-MONITOR-INTERACTION.md): native host probes and historical bounds.

## Routing, privacy and evidence

- [MODEL-CATALOG.md](MODEL-CATALOG.md), [MODEL_POLICY.md](MODEL_POLICY.md), [MODEL-ROUTING-REVIEW.md](MODEL-ROUTING-REVIEW.md): catalog, reference policy and review.
- [POLICY9-VALIDATION.md](POLICY9-VALIDATION.md), [PHASE-PROBE.md](PHASE-PROBE.md): candidate evaluation and model-switch boundaries.
- [TELEMETRY-ATTRIBUTION.md](TELEMETRY-ATTRIBUTION.md), [EVIDENCE-COVERAGE.md](EVIDENCE-COVERAGE.md), [TOOL-EVIDENCE.md](TOOL-EVIDENCE.md): selected/accepted/probable/confirmed evidence and coverage.
- [SIDE-CHATS.md](SIDE-CHATS.md): ephemeral/internal conversation scope and retention.
- [KNOWLEDGE-CONTINUITY.md](KNOWLEDGE-CONTINUITY.md): historical continuity; current repository-owned instructions are in HANDOFF/AGENTS.

`state/`, local configuration, credentials, raw logs, prompts, evidence ZIPs and
build outputs remain local. The preview URL and real UI screenshots can expose
private information. Safe receipts publish aggregate results and exact artifact
hashes, not raw conversations or owner data. No release/tag or policy class is
automatically activated by publishing this development branch.

## Experimental evaluations and audits

Docker controls and optional grader execution: [GRADER-SANDBOX.md](GRADER-SANDBOX.md).
The offline Python matrix can skip optional/native checks; hosted Docker x86_64/
ARM64 and native monitor/installer jobs are separate gates. No fixture result
certifies customer/owner tasks or causal savings.

- [AUDIT-2026-09-27](AUDIT-2026-09-27.md)
- [AUDIT-REMEDIATION](AUDIT-REMEDIATION.md)
- [CAUSAL-TRIALS](CAUSAL-TRIALS.md)
- [CODING-TRIALS](CODING-TRIALS.md)
- [EFFORT-TRIALS](EFFORT-TRIALS.md)
- [INTEGRATION-TRIALS](INTEGRATION-TRIALS.md)
- [MULTIFILE-TRIALS](MULTIFILE-TRIALS.md)
- [REPOSITORY-TRIALS](REPOSITORY-TRIALS.md)
- [REVIEW-2026-09-27](REVIEW-2026-09-27.md)
- [REVIEW-TRIALS](REVIEW-TRIALS.md)
- [TOKEN-COUNTER-VALIDATION](TOKEN-COUNTER-VALIDATION.md)

## Development and native receipts

Current companion states: [observed activity contract](COMPANION-ACTIVITY.md),
[synthetic pose board](design/companion-activity-poses.png), and
[Mac activation/validation receipt](native-validation/2026-10-08-macos-companion-activity.md).

The complete receipt directory is indexed below. New dynamic-notch receipts are
safe metadata/fixture records; installed readback and physical acceptance remain
independent. The older [design record](design/DECISION.md) and
[2026-10-03 UI archive](design/MONITOR-UI-2026-10-03.md) are historical.

- [2026-10-06-windows-capsule-startup-host-a](native-validation/2026-10-06-windows-capsule-startup-host-a.md)
- [2026-10-06-windows-host-a](native-validation/2026-10-06-windows-host-a.md)
- [2026-10-06-windows-import-completion-host-a](native-validation/2026-10-06-windows-import-completion-host-a.md)
- [2026-10-06-windows-import-fix-host-a](native-validation/2026-10-06-windows-import-fix-host-a.md)
- [2026-10-06-windows-installer-host-a](native-validation/2026-10-06-windows-installer-host-a.md)
- [2026-10-07-windows-connection-pid-reuse-host-a](native-validation/2026-10-07-windows-connection-pid-reuse-host-a.md)
- [2026-10-07-windows-connection-repair-host-a](native-validation/2026-10-07-windows-connection-repair-host-a.md)
- [2026-10-07-windows-installation-acceptance-host-a](native-validation/2026-10-07-windows-installation-acceptance-host-a.md)
- [2026-10-07-windows-owner-restart-host-a](native-validation/2026-10-07-windows-owner-restart-host-a.md)
- [2026-10-08-linux-notch-activation](native-validation/2026-10-08-linux-notch-activation.md)
- [2026-10-08-linux-notch-agents-catalog](native-validation/2026-10-08-linux-notch-agents-catalog.md)
- [2026-10-08-linux-notch-agents-horizontal](native-validation/2026-10-08-linux-notch-agents-horizontal.md)
- [2026-10-08-linux-notch-agents-simplified](native-validation/2026-10-08-linux-notch-agents-simplified.md)
- [2026-10-08-linux-notch-agents-spacing](native-validation/2026-10-08-linux-notch-agents-spacing.md)
- [2026-10-08-linux-notch-agents-workspace](native-validation/2026-10-08-linux-notch-agents-workspace.md)
- [2026-10-08-linux-notch-autocompact](native-validation/2026-10-08-linux-notch-autocompact.md)
- [2026-10-08-linux-notch-category-quota](native-validation/2026-10-08-linux-notch-category-quota.md)
- [2026-10-08-linux-notch-context](native-validation/2026-10-08-linux-notch-context.md)
- [2026-10-08-linux-notch-crew](native-validation/2026-10-08-linux-notch-crew.md)
- [2026-10-08-linux-notch-history-detail](native-validation/2026-10-08-linux-notch-history-detail.md)
- [2026-10-08-linux-notch-history-performance](native-validation/2026-10-08-linux-notch-history-performance.md)
- [2026-10-08-linux-notch-history-ratings](native-validation/2026-10-08-linux-notch-history-ratings.md)
- [2026-10-08-linux-notch-history](native-validation/2026-10-08-linux-notch-history.md)
- [2026-10-08-linux-notch-home-cleanup](native-validation/2026-10-08-linux-notch-home-cleanup.md)
- [2026-10-08-linux-notch-home-spacing](native-validation/2026-10-08-linux-notch-home-spacing.md)
- [2026-10-08-linux-notch-horizontal-home](native-validation/2026-10-08-linux-notch-horizontal-home.md)
- [2026-10-08-linux-notch-hover](native-validation/2026-10-08-linux-notch-hover.md)
- [2026-10-08-linux-notch-live-pipeline](native-validation/2026-10-08-linux-notch-live-pipeline.md)
- [2026-10-08-linux-notch-metric-alignment](native-validation/2026-10-08-linux-notch-metric-alignment.md)
- [2026-10-08-linux-notch-navigation](native-validation/2026-10-08-linux-notch-navigation.md)
- [2026-10-08-linux-notch-pointer](native-validation/2026-10-08-linux-notch-pointer.md)
- [2026-10-08-linux-notch-preview](native-validation/2026-10-08-linux-notch-preview.md)
- [2026-10-08-linux-notch-tags](native-validation/2026-10-08-linux-notch-tags.md)
- [2026-10-08-linux-notch-typography](native-validation/2026-10-08-linux-notch-typography.md)
- [2026-10-08 documentation delivery](native-validation/2026-10-08-documentation-delivery.md)
