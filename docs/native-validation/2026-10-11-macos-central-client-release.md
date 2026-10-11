# macOS central telemetry client delivery — 2026-10-11

## Source and artifact

- Public release/tag: `v0.9.8`, source
  `6f1aabf4d49c77195724ab591242fb5b72f5ed85`.
- Package: `codex-model-router-0.9.8-macos-arm64.pkg`, 18,236,351 bytes.
- SHA-256: `8915418171b2a25be1fca192604a2fb932e346540d39e02631518bf9484f4b8a`.
- Monitor `e5bdb664cc13a783`; router `100ad6ea0e4db975`.
- Portable Python3.14.8, PyInstaller6.22.3,98 runtime notice files verified.
- Existing Keychain publisher signs the manifest; verification uses the keyring
  shipped in the owner's installed0.9.7. No private key exported.
- Release includes only the Mac arm64 package, signed manifest, SHA256SUMS and
  public build provenance. Other-platform binaries remain pending transfer.

## Verified

-12 central telemetry tests, one product-version test and37 update/trust tests.
- JS Settings checks: default opt-out, independent permissions, sync refresh,
  deletion confirmation, read-only controls and update progress.
- Exact package native smoke: relocation, empty-PATH runtime/IPC, WebKit ready,
  version forwarding, preserved synthetic preferences,98 notices and six native
  binaries. No non-system absolute runtime dependencies.
- Downloaded the draft assets from GitHub, checked every checksum and verified
  the manifest against the installed publisher before stable promotion.
- Public anonymous latest-release discovery returns0.9.8. Tag points to the
  exact source above.
- Isolated native Settings probe with synthetic old0.9.7 downloads the exact
  public0.9.8 package, verifies its signature, exits the old monitor, replaces
  and relaunches automatically, acknowledges readiness and preserves preferences.
  Production GitHub transport; no local transport replacement. This is not the
  owner's installation, physical-input or real-login acceptance.

## Owner installation: safe block, not update success

Operated the real installed app's Settings: Check now detected0.9.8 and displayed
the verified project signature. Update downloaded the exact package (size/digest
checked in the owned update cache), then refused replacement because Codex still
uses this installation. The UI explicitly asks to finish tasks, close Codex and
retry. Several owner agents were active; none was stopped or interrupted.

The installed app remains0.9.7, monitor `992cea11bb136ed0`, expected router
`0c8570cfccd9a1a8`. The central metrics outbox does not exist in the owner data
root. No real metrics, prompts or raw OTLP were shared in this turn. Published
source, tested isolated app, installed app and loaded bridge remain separate.

## Next owner-host acceptance

1. Owner finishes active work and closes Codex/ChatGPT normally.
2. Router Settings → Application → Update to0.9.8. The monitor should replace
   and relaunch itself; reopen Codex normally afterward.
3. In0.9.8 Settings → Data and privacy, enable **metrics only**, verify native
   consent/sync and backend aggregate acknowledgement after an ordinary event.
   Prompts and raw OTLP permissions stay off unless separately requested.
4. Check opt-out and requested deletion with honest server/client evidence;
   never imply deleting events removes retained revocation/tombstone metadata.
5. Windows/Ubuntu native sharing/update validation remains independent.

No Apple Developer ID/notarization, power-loss/login recovery or CI success is
asserted. The owner previously waived a clean-Mac prerequisite. Backend remote
backup/restore integration remains unsupported as disclosed.
