# Mac telemetry-client release — 2026-10-12

## Source and immutable artifact

- Stable [v0.9.11](https://github.com/Bogdan-Andrei-Faur/codex-model-router/releases/tag/v0.9.11), promoted as Latest.
- Immutable tag/source:7942e0bb95280fb13913db4398fcf6316023176f.
- Package:codex-model-router-0.9.11-macos-arm64.pkg,18,244,718 bytes.
- SHA256:ba556d718cde99e93189f24e077b6b33699284a906031a1ecdbffdb59cc34b6d.
- Monitor:eb13b64fc1720b81; router:7c13745cb0d0cbec; policy8.
- Portable Python3.14.8, PyInstaller6.22.3,98 verified dependency notices.
- Public assets exactly:package, codex-model-router-update.json, SHA256SUMS,
  build-provenance.json. No private logs/state or other-platform binaries uploaded.
- Existing approved Keychain publisher; signature verified against the public key
  in the actual owner-installed0.9.10 app. No new key was created. This project
  signature is not Apple Developer ID/notarization.

## Client behavior delivered

Settings distinguishes installation, total-event and physical database capacity
from temporary rate/admission pressure. Capture rejections no longer mask the
last sender error. New diagnostics leave512KiB of the8MiB local outbox for metrics;
existing queued events are not evicted. Consent flags, credentials and history
are preserved. No permission is enabled by updating; already discarded captures
are not backfilled. The earlier backend quota incident is independently closed
in the [production recovery receipt](2026-10-12-central-capacity-repair.md).

## Verification

-604 Python tests PASS on the prepared Python3.14.8 build environment,53 expected
  optional/platform skips; shared telemetry Settings and update-control browser
  probes PASS. The first inline signature check omitted PYTHONPATH and failed
  import before checking anything; corrected source-path invocation verified the
  installed trust key. No package or product correction was needed.
- Exact package smoke PASS: extraction/relocation, deep signature, empty-PATH
  runtime/IPC, native packaged WebKit readiness, backend version forwarding,
  preferences,98 notices and6 native binaries without non-system absolute links.
- Exact signed local native Settings0.9.10→0.9.11 success/cancel-retry, forced
  rollback and interrupted helper replay PASS. Success automatically retains one
  recovery bundle and removes all terminal update payloads.
- All4 draft assets downloaded from GitHub and matched byte-for-byte; listed
  checksums, immutable source and signature against installed trust all PASS.
- Anonymous production latest-release discovery selects0.9.11 for Macarm64
  installed0.9.10 and verifies its signed manifest.
- Fresh isolated native Settings0.9.10→0.9.11 real-GitHub probe PASS, with no
  local transport replacement: exact package bytes downloaded, authenticated
  frozen helper, automatic old-host exit/replacement/new readiness, preserved
  fixture preferences, automatic terminal cleanup and one recovery bundle.
  The old version is synthetic; the actual owner app was not replaced.

## CI evidence and retained intermittent failure

Same immutable source main [38238550995](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/38238550995)
passed14/14 on its first attempt. Tag [38238550796](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/38238550796)
initially passed13/14: Ubuntu Python3.14 timed out after8 seconds awaiting the
synthetic bridge SIGTERM exit in test_bridge_preserves_protocol_and_stops_child_on_sigterm.
The exact same source passed main; the isolated failed job was rerun once and
then passed, giving14/14 overall. No test assertion, timeout or product source
was changed to hide the initial result. The specific shutdown timing cause is
not established; investigate separately if repeated. No provider inference ran.

## Owner handoff and boundaries

Use Settings → Updates → Check now → Update to0.9.11. If the active-bridge guard
asks, finish tasks and close Desktop normally; the updater does not terminate
Desktop or owner agents and relaunches its own monitor automatically.
Last read-only owner identity remains installed0.9.10/build2bf3077b1c3d4782.
Actual owner0.9.11 installation/loaded bridge and physical UI acceptance are
separate, pending owner update. No real configuration, credential, consent,
metric, registration or Desktop process was changed by these release probes.
Windows/Ubuntu exact binaries remain on other machines; no new installation
acceptance or managed-update/native sharing result is claimed for them.
Existing0.9.10 and earlier release bytes are immutable and unchanged.
