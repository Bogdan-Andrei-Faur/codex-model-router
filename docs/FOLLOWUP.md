# Current follow-up — 2026-10-12

This is the current work list. Read it with [HANDOFF.md](HANDOFF.md) and the
[native acceptance ledger](native-validation/STATUS.md). Dated receipts retain
their original observations; an old pending statement is not a new blocker.
No installation or live service was changed during this reconciliation.

## Closed or explicitly accepted

| Item | Evidence and exact scope |
| --- | --- |
| CI repairs | Main `023665a5b38989c735b84e7dbce4d2165a60fd78`; [run38169713976](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/38169713976) completed14/14. Native Windows/WebView2/installer and Ubuntu GTK package fixtures passed; no owner-host acceptance inferred. |
| Intermittent Ubuntu hover smoke | Reproduced the later500ms startup race; native delivery/deadline synchronization preserves all eight assertions. Four native DEB/Xvfb runs and negative controls PASS. [Timing receipt](native-validation/2026-10-11-ubuntu-hover-ci.md); published repair CI remains a separate check. |
| Shared monitor implementation | One `monitor-ui` and common Python state/actions with native AppKit, WebView2/WPF and GTK hosts. Source/runtime fixture delivery is complete; physical/DPI/login checks remain separate. [Architecture](SHARED-MONITOR.md). |
| Public Mac0.9.10 delivery | Automatic companions and capsule seam repair; signed Mac arm64 package, real-GitHub Settings update and automatic retention verified in isolation. [Receipt](native-validation/2026-10-11-macos-companions-release.md). Earlier0.9.9 assets remain immutable. |
| Public Mac0.9.11 client diagnostics | Signed Macarm64 release, package smoke, native cancellation/recovery and real-GitHub isolated Settings0.9.10→0.9.11 PASS. [Release receipt](native-validation/2026-10-12-macos-telemetry-release.md). Actual owner installed/loaded0.9.11 and healthy native sending now verified; only0.9.10 recovery retained. [Activation receipt](native-validation/2026-10-12-macos-0.9.11-activation.md). |
| Owner Mac0.9.10 activation | Owner update/restart completed; installed/loaded identities, handshake and one retained recovery version verified. [Historical receipt](native-validation/2026-10-12-macos-0.9.10-activation.md). The later0.9.11 activation and healthy sender observations supersede its incident snapshot. |
| Central capacity recovery | Production quota cause identified;95436e8 deployed through Sentinel,233 original queued events ACKed and installed0.9.10 background sending independently resumed. CI14/14. [Receipt](native-validation/2026-10-12-central-capacity-repair.md). Client diagnostics/reserve fixes and actual owner activation are now verified in0.9.11. |
| P510 deployment and Mac metrics activation | Deployment, HTTPS and real owner-Mac0.9.8 Settings enable/sync/disable/re-enable passed. [Deployment](native-validation/2026-10-11-p510-metrics-deployment.md), [activation](native-validation/2026-10-11-macos-central-sharing.md). |
| Windows/Ubuntu installation | ACCEPTED_BY_OWNER. No installation retest required. Exact tested binaries still await transfer. [Decision](native-validation/2026-10-11-owner-installation-acceptance.md). |
| Clean-Mac prerequisite | WAIVED_BY_OWNER for this delivery; not a technical PASS and not a delivery blocker. Same [decision](native-validation/2026-10-11-owner-installation-acceptance.md). |

## Remaining work

| Workstream | Next action | Boundary / dependency |
| --- | --- | --- |
| Settings simplification | Owner visual review; then publish the local shared UI in a signed client release when authorized. |34 core tests and17 browser groups PASS; concise descriptive switches/cards, privacy warnings preserved. Installed0.9.11 unchanged. [Receipt](native-validation/2026-10-12-settings-ux.md). |
| Windows/Ubuntu distribution | Transfer the owner-tested EXE/DEB and any build receipts; inspect version/architecture/hash, sign matching metadata and publish under existing authority. | Files are on other computers. Never rename binary version identity or overwrite immutable Mac assets. |
| Managed update acceptance | On those machines exercise actual Settings update/cancel/recovery and login-specific cases. | Installation acceptance and CI lifecycle fixtures do not close these cases. Use the [machine checklist](native-validation/WINDOWS-UBUNTU-UPDATES.md). |
| Central telemetry | Validate Windows/Ubuntu sharing and disposable offline/retry/deletion cases. Monitor capacity growth as diagnostics accumulate. | Owner0.9.11 installed/loaded and native sending verified. Quota incident is closed by95436e8 deployment and actual native recovery.1GiB/installation,4GiB total,5GiB physical DB; no automatic deletion. Existing metrics/prompts/raw flags and credentials preserved. Already rejected captures are not backfilled. [Receipt](native-validation/2026-10-12-central-capacity-repair.md). |
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
