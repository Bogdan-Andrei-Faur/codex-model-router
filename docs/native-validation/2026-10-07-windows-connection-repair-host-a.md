# Native acceptance receipt — 2026-10-07 — Windows — host-a

## Identity and scope

- UTC observations: 2026-10-07, through 10:41 UTC.
- Host: local Windows 11 x64 graphical session; synthetic native/browser fixtures
  and the owner's installed runtime are separate checks.
- Source: `50e63b07fbe65e182aebeb414e6daea1e1ca599e` plus uncommitted installer
  and connection/UI fixes; existing local work preserved.
- Product: 0.9.6. Installed per-user native setup, unsigned local pilot.
- Exact artifact: `codex-model-router-0.9.6-windows-x64-setup.exe`.
- SHA-256: `3619b3d85694c915ccc8f924355fc9bff491ccab0b08a84802f538cd590d8c51`.
- Installed application build: `611981b0f2d8abd4`.
- Installed router build: `b1f4bff15e1556ee`.
- Desktop: `26.1002.6548.0`; official CLI `0.162.0-alpha.2`.
- Native monitor: exact installed 0.9.6 version directory observed running.
- Open ordinary Desktop: fresh legacy source 0.9.5 bridge, not installed 0.9.6.
- Python validation: 3.14. No paid inference or owner task was created.
- Owner repair scope: auxiliary monitor replaced/restarted after announced repair;
  Desktop and its source bridge were not stopped. No reboot or display change.

## Results

| ID | Mode | Status | Evidence | Limit |
| --- | --- | --- | --- | --- |
| CORE-SCOPED | Source/native fixtures | PASS | 50 tests: Windows installation, desktop, monitor service, native disconnect/protocol and build identity | Scoped suite, not all project tests |
| UI-SHARED-FIXTURES | Chromium | PASS | All seven layout/interaction groups, including connection busy/native completion/restart notice | Not physical mouse acceptance |
| PROTOCOL | Compiled native/frozen/installed | PASS | Initialize and model-list respond before stdin EOF; installed registration preflight records both checks | No generated turn/inference |
| INSTALL-LIFECYCLE | Exact frozen/setup fixtures | PASS | Import, synthetic DPAPI, shortcuts, install/upgrade/uninstall/reinstall, rollback and locked-file checks | Production clean VM historical 0.9.4 only |
| OWNER-UPGRADE | Installed | PASS | Setup exit 0; active manifest and running monitor match 0.9.6; six retained config/history/credential files unchanged by setup | Read before connection config adjustment |
| CONNECTION-REGISTER | Installed | PASS | Owned imported registration; user environment selects stable installed wrapper; exact initialize/catalog pass | Applies to next ordinary launch |
| RESTART-NOTICE | Installed service payload | PASS | `desktopRestartPending=true`, `restartRequired=true`, zero installed connections | Native visible rendering still owner acceptance |
| TEL-DESKTOP-ACTIVE | Open Desktop | BLOCKED | Fresh source 0.9.5 Desktop session remains alive; installed doctor reports `restart_pending` | Owner must restart Desktop at safe boundary |
| UI-INPUT/DISPLAY/SCALE/SLEEP/START | Physical | NOT_RUN | No disruptive owner-host checks in this repair | Require separate owner acceptance |

## Reproduced failures and correction

1. The 0.9.5 CLI emitted localized JSON through ANSI Windows pipes; strict UTF-8
   decoding hid the specific active-source error. ASCII JSON escaping now works
   in both encodings, tested through a real cp1252 text stream.
2. Connection adoption reused the offline import active-process guard. Adoption
   prepares the next launch only; it now validates ownership/provenance and
   concurrent changes without requiring a running source bridge to stop. Offline
   import retains its active-process checks. Foreign connections remain protected.
3. The installed native launcher copied stdin without flushing per message.
   Initialize/catalog waited until EOF. A native echo fixture reproduced the
   failure; per-chunk flush fixes it, verified against the exact packaged wrapper.
4. Settings gave no immediate operation state. Connection cards now show progress,
   disable repeated actions until native completion, and keep a restart notice.
   Action cards use visible borders, a pinned Lucide chevron, hover and focus.

## Conclusion and next check

Installed owner upgrade, data retention, registration and protocol gates pass on
the exact 0.9.6 artifact. These supersede prior owner registration blockers;
the 0.9.5 PID-reuse and earlier clean-VM receipts remain historical evidence.

The owner next closes/reopens Desktop when tasks finish. Verify fresh installed
heartbeat, completed Desktop handshake, router build match and advancing
authenticated telemetry in the installed data root. Do not re-import, reinstall
or automatically stop Desktop. Registration alone is not executed inference.

Raw setup logs, receipts and private state remain ignored locally. This document
contains no keys, prompts, conversation IDs, account IDs or personal paths.
No macOS/Linux acceptance, signed distribution or trusted auto-install is claimed.

## Owner restart follow-up — 10:44 UTC

After the owner reported their restart, read-only installed checks now PASS:

- Installed doctor: `desktop_connected`, one Desktop session, discovery ready.
- Fresh installed bridge: product 0.9.6, completed `Codex Desktop` handshake,
  router build `b1f4bff15e1556ee` matching the installed manifest; heartbeat age
  below one second at the first observation.
- Installed monitor payload: one connection, no unknown/mismatched bridge build,
  `desktopRestartPending=false`, `restartRequired=false`.
- Authenticated telemetry enabled: received requests advanced from 12 to 13
  between observations; three model-bearing records and three completion records.
  Unauthorized requests and invalid payload counts both zero.

This closes the installed ordinary Desktop activation/telemetry gate on this
host/artifact. It supersedes the BLOCKED row and next-step instructions above.
No extra restart, registration, import, provider request or task was performed.
Physical display/input/sleep, latest clean-VM and other-host gates stay separate.

## Publication preflight

On the same Windows host, the complete Python suite finished successfully:
510 tests discovered, 455 executed successfully and 55 skipped for platform or
optional infrastructure. The routing corpus passed all 27 cases; JavaScript
core tests passed all 26 cases. The previously recorded seven Chromium groups
and exact installed native/frozen probes remain valid; no runtime source changed
since their artifact was built. These are local checks, not remote CI results.
