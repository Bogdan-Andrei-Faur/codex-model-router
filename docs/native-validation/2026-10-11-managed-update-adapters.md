# Windows/Ubuntu update adapters — source verification, 2026-10-11

Follow-up corrections and stronger verification are recorded in
[the current receipt](2026-10-11-update-followup.md); this initial receipt retains
its original mocked-test limitations.

## Scope

Local changes based on `d647b3e`, verified on macOS arm64. These changes have not
been committed, published, installed on Windows/Ubuntu or applied to the owner's
running Mac app by this verification. The public Mac0.9.7 Release is unchanged.

## Implemented

- Shared signed download feeds protocol-aware Windows/Ubuntu adapters.
- Old-runtime helper, pre-commit cancellation, native monitor lifecycle lease,
  automatic monitor-only close/relaunch and successful UI snapshot acknowledgement.
- Windows silent per-user Inno transaction, previous runtime selection recovery,
  installer-mutex guard and per-job HKCU login recovery.
- Ubuntu signed payload extraction, strict archive path/type checks, unchanged
  system apt baseline, per-user selector, dependency-contract check and XDG login
  recovery. System bridge remains the stable entry point.
- Foreign/concurrent version changes block commit/recovery. Terminal replay is
  idempotent; data and credentials are outside the update's mutation surface.

## Evidence

| Check | Result | Limit |
| --- | --- | --- |
| Clean portable CPython3.14 full suite | 572 tests, OK, 53 skipped | Platform/dependency skips remain unexecuted |
| Focused portable update suite on final helper changes | 12 tests PASS | Mocked installer/process/native boundaries; not native installation |
| Shared JS core | 33 tests PASS | No native host proof |
| Actual browser Settings update controls | PASS: controls, progress refresh, truthful native gates | Browser fixture; no Windows/Ubuntu installer |
| Changed Windows monitor, C#5 / .NET4.8 / actual WebView2 refs | Cross-compilation PASS | No WPF, Inno or Windows execution on this Mac |
| `git diff --check` | PASS | Formatting only |

The full suite emitted existing fixture HTTPError ResourceWarnings without test
failures. Focused cases cover success, failed UI launch and installer failure,
cancellation before commit, interrupted commit/confirmation, signature/byte
rejection, terminal replay, traversal/link/device/setuid archive rejection,
foreign installation changes and a surviving Windows installer. Mac existing
managed-update tests remain passing in the full suite.

## Open acceptance

All Windows/Ubuntu native and real GitHub transaction gates remain PENDING. No
native package or new release was produced here. A protocol-aware baseline must
be installed once on each host. Complete the exact per-machine scenarios in
[WINDOWS-UBUNTU-UPDATES.md](WINDOWS-UBUNTU-UPDATES.md) before distribution. WPF only
needs validation when using Windows. Keep real login/power-loss recovery,
credentials, ordinary bridge selection and physical input distinct from fixtures.
