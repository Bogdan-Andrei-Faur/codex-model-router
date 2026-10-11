# macOS automatic-retention release — 2026-10-11

## Published source and artifact

- Stable Release: https://github.com/Bogdan-Andrei-Faur/codex-model-router/releases/tag/v0.9.9
- Immutable tag/source: `053446764d4f085612b78fe41df1f0d70206306e`.
- Package: `codex-model-router-0.9.9-macos-arm64.pkg`, 18,243,962 bytes.
- SHA-256: `3f97614f3d173f4fd7a1874a38e002503af98bd3f0b72da449bd0afd420c53e9`.
- Monitor `6ddbcff3a85a04c4`; router `3fd9739ca60ade9f`.
- Portable Python3.14.8, PyInstaller6.22.3 and98 verified notice files.
- Approved existing Keychain publisher signs the update manifest. Its signature
  verifies against the public key shipped in the owner's installed0.9.8.
- Public assets: Mac arm64 package, signed manifest, SHA256SUMS and sanitized build
  provenance. No Windows/Ubuntu/Intel installers, private logs or state uploaded.

## Verification

-49 focused update tests and one product-version test PASS, no skips.
- Exact package smoke PASS: relocation, empty-PATH runtime/IPC, native WebKit
  readiness, bridge version forwarding, synthetic preferences and six native
  binaries; no non-system absolute library dependencies.
- Signed local native Settings success/cancel-retry, rollback and interrupted
  recovery replay PASS with the exact0.9.9 package. Automatic cleanup is performed
  by the new frozen monitor, retaining one previous app and small receipts.
- Downloaded all draft assets from GitHub before promotion; all listed hashes,
  local bytes and installed-key signature match.
- Public anonymous latest-release discovery returns0.9.9 and a valid arm64 update
  candidate for0.9.8. The public manifest verifies with the installed keyring.
- Isolated native Settings0.9.8 →0.9.9 through production anonymous GitHub
  transport PASS: exact downloaded package, signed frozen helper, automatic old
  host exit, new native readiness, preferences retained and automatic cleanup.
  No local transport replacement; no owner installation touched.

## Owner handoff and limits

The owner's app remains0.9.8, monitor `e5bdb664cc13a783`; its automatic version
check setting is enabled. Settings → Updates → Check now can discover0.9.9
immediately. Installation remains an owner action: finish tasks and close
Codex/ChatGPT normally if the active-bridge guard requests it, then retry Update.
The monitor closes/relaunches itself. Do not stop agents to demonstrate an update.
After applying0.9.9, retention keeps the previous0.9.8 and prunes the older
identified0.9.7 backup when no helper/recovery needs it.

Actual owner0.9.9 installation, loaded bridge after restart and human acceptance
are not asserted. Real login/power-loss recovery and other-platform update QA
remain separate. No Apple Developer ID/notarization or CI success is asserted.
The earlier source-only retention delivery pending is superseded by this Release.
