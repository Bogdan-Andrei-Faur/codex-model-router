# Portable Mac runtime and native Settings update — 2026-10-09

## Scope and artifact

Local development on public main `c0667cf1cec97f1655b5ef67b50efbd396a7cd52`.
The owner approved completing Mac distribution preparation. This receipt covers
isolated arm64 artifacts; it does not replace the owner's installed monitor or
loaded Desktop bridge. No commit/push, Release, Installer execution, owner import,
Desktop restart, provider inference or real login item registration accompanies it.

The ordinary candidate is an immutable source snapshot with fixture VERSION
`0.9.7`, monitor build `ebb63406880939f4`, router build `0c8570cfccd9a1a8`.
Package SHA-256:
`8e5b26937a71e375f2061cda875af2de655f0fb53b195c2a3d0795b9b5a6d0ab`.
The approved Keychain publisher signed its exact bytes; no private key left the
Keychain. Project authentication is separate from ad-hoc Apple code signing:
Developer ID, notarization and Gatekeeper acceptance are not established.

## Runtime and notices

- Portable CPython **3.14.8**, Astral python-build-standalone release **20261009**,
  aarch64 macOS; install/full archives are pinned by name, size and SHA-256 in
  `tools/packaging/macos-runtime.lock.json`. No system Python was changed.
- Build tools: PyInstaller **6.22.3**, cryptography **50.0.2**, cffi **2.1.1**,
  pycparser **3.11**. The earlier Xcode-Python fixture is not the distribution
  runtime. A prepared portable interpreter and exact notices are now required.
- **98 notice/metadata files**, including CPython/native libraries, PyInstaller
  bootloader exception, wheel notices, **32 Rust registry crates plus OpenSSL
  4.0.3**, and Rust standard-library notices matched to the wheel's compiler
  commit `48a229ceaefd4985c50990b14116b6d856af0985` (Rust **1.98.1**).
- Upstream runtime licensing metadata omits zstd's text; the exact **1.5.7** BSD
  text is supplied separately with a pinned hash. The notice set conservatively
  includes upstream build/all-target dependencies; it is not an exact claim of
  linked modules. Archives are only developer inputs, never app payloads.
- All shipped notice hashes pass after package extraction. All **six** regular
  Mach-O binaries have no non-system absolute library dependency. Empty-PATH
  runtime/IPC, relocation and native WebKit child startup pass.

## Native cases executed

`tests/probe_mac_settings_update.py` builds a disposable old application whose
test-only source snapshot contains a WebKit DOM driver, local transport and fault
injection. None of those hooks are in production code or the new candidate.
It renders the real Settings controls while the window remains hidden, then
clicks their buttons through AppKit/private IPC to the real frozen updater.
It uses an actual project-signed package; neither verification nor permissions
are bypassed. Recovery plist paths are redirected into each fixture root.

| Case | Result |
| --- | --- |
| Check → Update → Cancel → Check → Update | PASS: signed discovery, positive download progress, cancellation acknowledged, retry succeeds |
| Successful replacement | PASS: old native host exits itself normally; installed frozen helper applies; new native WebKit/data readiness acknowledged |
| Failed readiness | PASS: test injects a false readiness result after native launch; real helper restores and relaunches old app |
| Interrupted commit | PASS: helper process exits after first rename; replay of the same frozen helper restores and relaunches old app |
| Retention/isolation | PASS: synthetic config unchanged; owner installation/Desktop untouched; fixture recovery plists removed at terminal result |
| Actual public discovery | Packaged runtime reaches the canonical GitHub check and reports `release_unavailable`; no installer Release exists. This is not a successful real update download |
| Python suite | 560 tests, 53 optional/platform skips, no failures; includes three new notice integrity/path tests and 23 updater tests |

The first driver attempt timed out because hidden mode skips page rendering.
The corrected driver explicitly renders Settings; all three scenarios above
pass. This was a harness issue and does not establish human visual acceptance.

## Remaining gates and next action

1. Coordinate the current-user Installer/Gatekeeper and graphical first-run
   pilot with the owner before replacing an installation or interrupting work.
   Source-backed owner data and connection transfer require their own receipt.
2. Build the release from a fixed reviewed source revision, sign final bytes,
   assemble/review a Release, then prove real GitHub download from Settings.
   Fixture `0.9.7` is not a released product version and must not be uploaded as
   an acceptance shortcut. No Apple Developer account is available.
3. Actual logout/login or reboot recovery remains untested. Process crash/replay
   proves the transaction path, not macOS launchd scheduling after power loss.
4. Windows/Ubuntu apply adapters and native lifecycle evidence remain separate;
   x86_64 input hashes do not prove an Intel Mac build or native acceptance.
   **WPF solo necesita validación si vas a usar Windows.**

See [managed updates](../MANAGED-UPDATES.md) for signing/expiry/rotation and
[HANDOFF](../HANDOFF.md) for the developer-only portable build recipe.

## Subsequent owner-selected Mac pilot

The owner selected a Mac-first pilot in this turn. Source VERSION is now locally
**0.9.7**. A fresh ordinary package (no driver/transport/fault hooks) and project
manifest are prepared under ignored `release/macos-pilot-0.9.7/delivery/`.
The source is uncommitted on the baseline above; no Release or remote changes.

- Monitor `ebb63406880939f4`, router `0c8570cfccd9a1a8`.
- Exact pilot package SHA-256:
  `4d1e015585b857d745675ef4e4e46cd0b0b1879fdb468cbf42c6c30500d825ab`.
- Build-input source snapshot SHA-256:
  `8747b097583ea579e7b78f95280b10c43dd35b3e5f51a1c5c403c0f596be5bcc`.
- Embedded notice inventory SHA-256:
  `0261b027996d8bf55bb3c250b42b7ada91cddfa96586172c97d5ced12fb18dd2`.
- Repeated on these exact signed bytes: all three native Settings lifecycle
  scenarios, package relocation/empty-PATH/native smoke,98 notice hashes and six
  Mach-O dependency checks PASS. Source suite again560 tests/53 skips, no failures.
- `SHA256SUMS`, sanitized `pilot.json` and a Spanish `LEEME.md` accompany the pkg
  and signed manifest. No generated artifacts or local paths enter Git.

A preliminary pilot test invocation used a nonexistent old-fixture path and
failed before launching applications; resolving the recorded build-result path
fixed that invocation. The completed run above uses the actual old artifact.
Follow [the pilot guide](../MACOS-PILOT.md) for coordinated first installation.
