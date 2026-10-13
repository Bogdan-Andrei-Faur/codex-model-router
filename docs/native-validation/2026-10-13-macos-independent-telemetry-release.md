# Mac independent telemetry client release — 2026-10-13

## Source and immutable artifact

- Stable Latest [v0.9.13](https://github.com/Bogdan-Andrei-Faur/codex-model-router/releases/tag/v0.9.13), published2026-10-13T16:17:20Z.
- Immutable source/tag: `4dfc75369f36e256f3dff8359843f9df7e3d9167`.
- Package: `codex-model-router-0.9.13-macos-arm64.pkg`,18247028bytes.
- SHA256: `eec8a1b05beb7a36c7cbf8b55f1356d9e18869dd3776a98aadef634b4a0d3fe8`.
- Monitor `c2bf3f47727e6582`, router `f909942515875555`, policy8.
- Portable Python3.14.8, PyInstaller6.22.3,98 verified notices.
- Four public assets: package, signed `codex-model-router-update.json`,
  `SHA256SUMS`, sanitized `build-provenance.json`.
- Existing Keychain publisher, verified against actual owner installed0.9.11
  trust. No new key/certificate. Project authenticity is not Apple Developer ID
  or notarization.

## Delivered behavior

Metrics go first in their own batches; messages and raw OTLP share separate
batches and capacity backoff. Class quota saturation does not block the other
lane. Shared network/authentication/physical database failures still affect both.
Exact ACK is required before removing queued rows; consent is checked before
each lane. New diagnostics leave512KiB/256event slots for metrics, without
evicting existing rows. Settings identifies which class quota is blocked.
Permissions, configuration, credentials and existing metrics are preserved;
updating does not enable sharing or backfill previously rejected capture attempts.

The server quota correction was already deployed and actual native sending
recovered separately. See the [backend recovery receipt](2026-10-13-telemetry-quota-recovery.md).

## Verification

-609Python tests,53expected skips, PASS on prepared Python3.14.8. The existing
  synthetic404 cleanup ResourceWarning did not fail the suite.
- Shared browser central-telemetry controls/new scope labels and update controls
  PASS. An initial updater-test command had a filename typo; the correct existing
  test passed without product changes or weakened assertions.
- Candidate source snapshot exactly matches the immutable tagged input tree.
- Exact package smoke PASS: relocated extraction, strict/deep ad-hoc signature,
  empty-PATH frozen runtime/IPC, native WebKit readiness, version forwarding,
  preferences,98notices and6native binaries without non-system dependencies.
  No real Installer, Desktop registration or owner installation.
- Native signed local Settings synthetic0.9.11→0.9.13 PASS: cancel/retry,
  forced rollback, interrupted frozen-helper replay, automatic old host exit,
  new/restored readiness, retained preferences and automatic terminal cleanup
  with exactly one recovery version.
- All four draft assets downloaded byte-identical; combined checksums, installed
  trust signature and local/remote peeled tag/source match before promotion.
- Anonymous production latest discovery selects0.9.13 for installed0.9.11
  Macarm64 and verifies metadata with actual installed trust.
- Fresh native real-GitHub Settings synthetic0.9.11→0.9.13 PASS: production
  discovery/download, exact package match, signed frozen helper, automatic
  close/relaunch/readiness, retained preferences and one-recovery/terminal cleanup.
  No replacement of GitHub transport. Owner installation untouched.
- Source main CI [38428713580](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/38428713580)
  PASS14/14 first attempt. Tag CI38429088204 was13/14 completed/no failures at
  the last observation; the remaining MacPython3.14 job was in checkout. This
  infrastructure wait is not a successful gate; final status remains separate.

## Owner handoff and remaining scope

Use **Ajustes → Aplicación → Comprobar ahora → Actualizar a0.9.13**.
The monitor closes/reopens itself. If the active bridge guard asks, finish tasks
and close Desktop normally; the updater never terminates Desktop/agents.
Actual installed/loaded0.9.13, native sending after update and physical UI/login
acceptance remain separate. Read-only owner plist still0.9.11 with monitor
`eb13b64fc1720b81`/router`7c13745cb0d0cbec` after isolated checks.

No owner configuration, privacy permissions, credentials, real telemetry queue,
Desktop process or registration was changed by this release verification. No
provider inference or real private upload initiated by the fixtures.
Windows/Ubuntu0.9.12 manual installers remain public in the earlier release;
0.9.13 binaries require their own builds and native validation. The new manifest
covers Macarm64 only; no older binaries were renamed or signed as this version.
Existing installer/tag/asset bytes were not overwritten.
