# Current follow-up — 2026-10-11

This is the current work list. Read it with [HANDOFF.md](HANDOFF.md) and the
[native acceptance ledger](native-validation/STATUS.md). Dated receipts retain
their original observations; an old pending statement is not a new blocker.
No installation or live service was changed during this reconciliation.

## Closed or explicitly accepted

| Item | Evidence and exact scope |
| --- | --- |
| CI repairs | Main `023665a5b38989c735b84e7dbce4d2165a60fd78`; [run38169713976](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/38169713976) completed14/14. Native Windows/WebView2/installer and Ubuntu GTK package fixtures passed; no owner-host acceptance inferred. |
| Shared monitor implementation | One `monitor-ui` and common Python state/actions with native AppKit, WebView2/WPF and GTK hosts. Source/runtime fixture delivery is complete; physical/DPI/login checks remain separate. [Architecture](SHARED-MONITOR.md). |
| Public Mac0.9.9 delivery | Signed Mac arm64 package and exact-package real-GitHub Settings update/automatic retention verified in isolation. [Receipt](native-validation/2026-10-11-macos-retention-release.md). |
| P510 deployment and Mac metrics activation | Deployment, HTTPS and real owner-Mac0.9.8 Settings enable/sync/disable/re-enable passed. [Deployment](native-validation/2026-10-11-p510-metrics-deployment.md), [activation](native-validation/2026-10-11-macos-central-sharing.md). |
| Windows/Ubuntu installation | ACCEPTED_BY_OWNER. No installation retest required. Exact tested binaries still await transfer. [Decision](native-validation/2026-10-11-owner-installation-acceptance.md). |
| Clean-Mac prerequisite | WAIVED_BY_OWNER for this delivery; not a technical PASS and not a delivery blocker. Same [decision](native-validation/2026-10-11-owner-installation-acceptance.md). |

## Remaining work

| Workstream | Next action | Boundary / dependency |
| --- | --- | --- |
| Mac owner update | Owner applies0.9.9 from Settings when convenient, then record installed/loaded identities. | Last verified owner state is0.9.8; do not stop Desktop or agents. CI repairs published after the immutable0.9.9 package are source changes, not replacement release bytes. |
| Windows/Ubuntu distribution | Transfer the owner-tested EXE/DEB and any build receipts; inspect version/architecture/hash, sign matching metadata and publish under existing authority. | Files are on other computers. Never rename binary version identity or overwrite immutable Mac assets. |
| Managed update acceptance | On those machines exercise actual Settings update/cancel/recovery and login-specific cases. | Installation acceptance and CI lifecycle fixtures do not close these cases. Use the [machine checklist](native-validation/WINDOWS-UBUNTU-UPDATES.md). |
| Central telemetry | Validate installed Windows/Ubuntu sharing; exercise offline/retry and deletion only on disposable installations unless owner explicitly requests deleting real samples. | Core Mac ingestion is closed; remote prompt/raw consent remains off at the last verified snapshot. Preserve accumulated real metrics. |
| P510 data recovery | Add Sentinel remote backup/restore integration and verify database plus deletion-intent restoration. | Unsupported in the recorded deployed configuration; owner accepted normal deployment with this limit. This reconciliation does not inspect or modify Sentinel. |
| Routing evidence | Collect representative ordinary-work outcomes, model evidence and cost observations; later compare local/JEV decisions. | Probable inference is not confirmed identity, tokens are not billed charges, and the old6native/2JEV experiment allocation is exhausted. No new paid experiments authorized here. |
| UI and activity acceptance | Review current companions/wardrobe and natural activity delivery during use; record specific physical input/visual issues. | Implementation, package/native fixtures and CI pass. No fresh owner visual, DPI, sleep/login or every-state natural coverage is claimed. Older glass-design iterations are historical. |
| Isolated Mac glass probe | If this development probe is needed again, reproduce its historical initial-bounds failure against current source. | No new run or proven root cause. Later native Settings/readiness/ingestion pass, so the old fixture failure is not evidence that the deployed app is broken. [Original receipt](native-validation/2026-10-08-macos-consumption-settings.md). |

The full NOT_RUN inventory records evidence gaps, not known bugs or mandatory
preconditions for every release. **WPF only needs validation when using Windows.**
Apple Developer ID/notarization remains unavailable without an owner account;
the application's update signature does not replace Apple signing. See the
[distribution plan](DISTRIBUTION-PLAN.md).

## Tracking reconciliation

The shared-monitor implementation task is closed using current native CI and
recorded installation evidence. Installer, telemetry, routing and the three UI/
activity tasks retain only their independently open scopes. Old0.8.1 restart,
missing native-CI and undeployed-backend statements are historical, superseded
by the receipts above; no historical report or experiment artifact was rewritten.
