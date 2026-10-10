# Managed update follow-up — 2026-10-11

Source: reviewed working tree based on `d647b3e`, including the accompanying
portable adapters and tests. Owner Mac remains the published0.9.7 artifact
(monitor992cea11bb136ed0, router0c8570cfccd9a1a8). No owner app replacement,
Desktop restart, key migration, logout or production installer publication.

## Corrections

- Preserve signed manifest bytes across preparation and copied-helper verification.
  Previous mocked tests missed a real serialization/type mismatch which prevented
  all portable handoffs. A new test uses actual ephemeral Ed25519 signatures through
  both boundaries, on both platform branches, without mocking verification.
- Windows login recovery uses the stable launcher to avoid repeating the long
  copied-worker path. Reject Run commands beyond260 UTF-16 code units before
  closing the monitor; preserve custom roots and validate the token/owned worker.
  [Microsoft documents the Run limit](https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys).
  Actual Windows login/launcher compatibility remains pending.
- Immediate rollback rechecks active bridge and foreign selector changes before
  restoring; it must not overwrite a concurrently selected installation.
- Reconfirmed restored ordinary Mac connection: one live session, completed
  Desktop handshake and expected0.9.7 build identities. Removal cause unknown;
  no inference/model-attribution claim. See [repair](2026-10-11-macos-missing-bridge.md).

## Verification

| Check | Observed result | Boundary |
| --- | --- | --- |
| Portable CPython3.14 suite | 575 tests OK,53 skips | Optional/platform skips remain unexecuted; fixture HTTPError ResourceWarnings remain |
| JS and Settings browser | 33 core tests PASS; update controls/progress/native gates PASS | Browser fixture, not native Windows Settings |
| Windows monitor and stable launcher | C#5/.NET4.8 with actual WebView2 references cross-compile PASS | No execution of WPF, Inno, registry or DPAPI |
| Fresh Mac Settings probe | success, launch-failure rollback, interrupted-helper replay PASS; native DOM clicks, cancel/retry, automatic exit/relaunch, readiness and preference retention | Current-source synthetic0.9.6 old app and exact published0.9.7 package/signature over local fixture transport; no actual login or new GitHub transport proof |
| Ubuntu24.04 arm64 Docker | Three real signed .deb/helper scenarios PASS: success, failed-start rollback, killed-helper replay; new GTK/WebKit acknowledgement on success, restored monitor lease on recovery, config preservation, recovery entry removed | Direct helper preparation, not Settings click; Xvfb/DBus, not physical GNOME/Wayland/login/Secret Service acceptance |

Ubuntu proof is reproducible using `tests/probe_linux_managed_update.py` as an
unprivileged user. It stages explicit source, creates a signing key only in memory,
trusts it only in fixture packages, builds distinct0.0.1/0.0.2 versions and mutates
only its disposable roots. Neither apt's database nor `/usr` is modified. Startup
failure and delay are injected only into disposable candidate source. Recovery
replays the actual copied helper after killing only its own process group. The
restored monitor lease is observed; restored-window visual acceptance is not
asserted. Docker's `--init` is required for reliable Xvfb startup signalling.

Local private fixture outputs are deliberately excluded from Git. No alternate
feed, test key or crash injection is added to the installed product.

## Handoff / still open

Follow [Windows/Ubuntu acceptance](WINDOWS-UBUNTU-UPDATES.md). Windows requires
native installer, stable recovery dispatcher, WPF/WebView2, locked files and
login recovery. **WPF only needs validation when using Windows.** Ubuntu requires
Settings actions, actual session/login, XDG/keyring and apt baseline coexistence,
ordinary bridge selection and public transport. Both require validated immutable
packages before publication; the public0.9.7 release still has only Mac arm64.
Mac still needs clean-machine download quarantine/Gatekeeper, actual login and
physical acceptance; do not close these gates with hidden fixtures.
