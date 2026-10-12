# Mac Settings release — 2026-10-12

## Source and immutable artifact

- Stable Latest [v0.9.12](https://github.com/Bogdan-Andrei-Faur/codex-model-router/releases/tag/v0.9.12), published2026-10-12T18:04:18Z.
- Immutable source/tag: `fb360d77daae21e2043e7d7f5dc9b388a89be97a`.
- Package: `codex-model-router-0.9.12-macos-arm64.pkg`,18,246,056bytes.
- SHA256: `a4ea8b8b44ed74190cb414bd8259561ca311666ff8da532eabd5a40095042ff5`.
- Monitor `1d63ab96da79c087`, router `766899a8e0e070d3`, policy8.
- Portable Python3.14.8, PyInstaller6.22.3,98 verified notices.
- Four public assets only: package, signed `codex-model-router-update.json`,
  `SHA256SUMS`, sanitized `build-provenance.json`.
- Existing Keychain publisher; manifest verified against trust in actual owner
  installed0.9.11. No new key. Project signing is not Developer ID/notarization.

## Delivered behavior

Shared Settings has concise Aplicación/Modelos/Privacidad/Conexión navigation,
descriptive switches, tinted rounded cards and original Lucide icons. Technical
details are collapsible. Local and remote permissions remain independent;
sensitive-content/retention warnings and deletion confirmation stay explicit.
Drafts, disclosure state and keyboard focus survive refreshes; preview cannot
save keys. No updating permission enablement or data reset. See the
[implementation receipt](2026-10-12-settings-ux.md).

## Verification

-604Python tests,53 expected skips, PASS on prepared Python3.14.8. The synthetic
  private-response404 fixture emitted a cleanup ResourceWarning; suite succeeded.
-34JS core tests and all17 browser groups PASS in the implementation turn;
  final update/preferences probes after refinements PASS. Browser screenshots
  reviewed; responsive Settings320–800px and existing1–2x layout checks PASS.
- Exact package smoke PASS: extraction/relocation, strict/deep signature,
  empty-PATH frozen runtime/IPC, native WebKit readiness, backend version
  forwarding, preferences,98 notices and6 native binaries without non-system
  absolute dependencies. No Desktop registration or owner installation.
- Signed native local Settings0.9.11→0.9.12 success/cancel-retry, forced rollback
  and interrupted helper replay PASS. Preferences retained, automatic old-host
  exit/new readiness, one recovery bundle and all terminal payloads cleaned.
- Four draft assets downloaded and matched byte-for-byte; checksums, installed
  trust signature and local/remote peeled tag/source verified before promotion.
- Anonymous production latest discovery selects0.9.12 for installed0.9.11
  Macarm64 and verifies signed metadata against installed trust.
- Fresh native real-GitHub Settings0.9.11→0.9.12 PASS: production fetch/download,
  exact downloaded package match, signed frozen helper, automatic exit/relaunch,
  readiness, preserved preferences, one recovery and terminal cleanup. No local
  transport replacement. Synthetic old installation; owner app untouched.
- Source main CI [38288007772](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/38288007772)
  and tag CI [38288243140](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/38288243140)
  each PASS14/14 on first attempt, no retries or weakened checks.

## Owner handoff and limits

Owner app remains0.9.11 at last read-only check. Use **Ajustes → Aplicación →
Comprobar ahora → Actualizar a0.9.12**. If the active-bridge guard asks, finish
tasks and close Desktop normally; the updater never terminates Desktop/agents.
The monitor closes/reopens itself. Actual owner0.9.12 installed/loaded identity,
physical UI/login and other-platform acceptance remain separate.

No owner configuration, credentials, sharing consent, metrics, Desktop process
or registration changed. No provider inference or real telemetry upload was
initiated. Windows/Ubuntu exact tested binaries remain on other computers;
their installer publication still awaits transfer. Existing releases unchanged.
