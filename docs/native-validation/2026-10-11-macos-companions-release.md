# macOS automatic-companions release — 2026-10-11

## Published source and artifact

- Stable [v0.9.10](https://github.com/Bogdan-Andrei-Faur/codex-model-router/releases/tag/v0.9.10).
- Immutable tag/source: `1de9269b1eba16fc18bc633df21234421901370e`.
- Package: `codex-model-router-0.9.10-macos-arm64.pkg`, 18,244,204 bytes.
- SHA-256: `20dd586b54d9132331fe6f494c0d2b133f88dbf683f7a0de805de854e70dc870`.
- Monitor `2bf3077b1c3d4782`; router `f50a290841379145`.
- Portable Python3.14.8, PyInstaller6.22.3 and98 verified notice files.
- Existing approved Keychain publisher; manifest verifies against the public key
  already shipped in the owner's installed app. No new signing key was created.
- Public assets: arm64 package, signed manifest, SHA256SUMS and sanitized build
  provenance. Existing release bytes were not overwritten; no private state or
  Windows/Ubuntu installer was uploaded.

## Verification

-601 Python tests PASS (53 optional/platform skips),34 JS core tests,17 browser
  groups and27/27 routing corpus PASS. Python initially inherited installed0.9.8
  resource paths; rerunning with only the three PERSONAL_CODEX_ROUTER path
  overrides removed passed, including23 focused version/registration tests.
- Appearance coverage includes saved/legacy priority, deterministic automatic
  assignment, editor reset and14,976 rigid wardrobe/pose/color/time samples.
  Capsule pixel checks cover fractional centering at1/1.25/1.5/2x.
- Exact package smoke PASS: relocation, empty-PATH runtime/IPC, native WebKit
  readiness, bridge version forwarding, preferences,98 notices and six native
  binaries without non-system absolute library dependencies.
- Signed local native Settings success/cancel-retry, rollback and interrupted
  helper replay PASS with the exact package; confirmed success retains one
  recovery bundle and cleans terminal payloads automatically.
- All four draft assets were downloaded from GitHub and compared byte-for-byte;
  every listed checksum, source revision and installed-key signature matched.
- Anonymous latest-release discovery returns0.9.10 and a valid signed Mac arm64
  candidate for0.9.9.
- Isolated native production-GitHub Settings0.9.9 →0.9.10 PASS: exact downloaded
  bytes, signed helper, automatic host exit/replacement/readiness, preferences and
  automatic cleanup. No local transport replacement or owner installation change.

## Harness findings and CI

The first real-GitHub probe asserted cleanup after the helper directory vanished,
while sequential deletion of the remaining directories was still in progress.
Those directories subsequently disappeared. The corrected probe keeps the same
85-second deadline and waits for all five payloads, including the checked package;
the repeated full GitHub update passed. Cleanup remains performed by the frozen
production monitor, never by the test driver.

First source [main CI38173934017](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/38173934017)
completed13/14: Windows failed opening the fixture's runtime with an exclusive
handle, before running the blocked-upgrade check. The old assertion did not record
the Win32 error, so a specific locker/root cause is not established. The same
source's [tag CI38174024670](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/38174024670)
completed14/14 successfully. The follow-up test retries only sharing/lock errors
32/33 for at most10seconds, fails other errors immediately and reports the error.
Syntax/diff checks PASS; the follow-up main CI is independently observable. These
two probe changes do not alter the immutable published product or installer.

## Owner handoff and limits

Use Settings → Updates → Check now → Update. Finish active tasks and close
Codex/ChatGPT normally if requested by the active-bridge guard; the monitor handles
its own close/relaunch. The last verified owner installation/bridge remains0.9.8,
not a new live observation. Actual owner0.9.10 installation, loaded bridge and
visual/physical acceptance are not asserted. Actual login/power-loss recovery and
other-platform managed update acceptance remain separate. The project signature
is not Apple Developer ID or notarization.
