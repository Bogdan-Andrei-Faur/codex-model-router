# Windows legacy connection PID reuse — 2026-10-07 — host-a

## Identity and scope

- Windows x64 physical host; source `50e63b07fbe65e182aebeb414e6daea1e1ca599e`
  plus preserved uncommitted installer work.
- Owner installed monitor: 0.9.4. Desktop still uses the legacy source wrapper,
  with a completed handshake and live telemetry in the source data root.
- Installed diagnostic: Desktop 26.1002.6548.0, CLI `0.162.0-alpha.2`, discovery
  ready, version check successful, connection `not_registered`.
- Corrected unsigned local artifact: `codex-model-router-0.9.5-windows-x64-setup.exe`.
  Build `eba25a11edafef30`, router build `f14fa1c8f074614e`, policy 8, SHA-256
  `88b34709f2314908c38dc4c657d6599a4edeab557a87a87ebee492819b5875fa`.
- No owner application stopped, active installation replaced, environment
  registration changed, source snapshots removed or credentials copied by this work.
  Diagnostics write only the normal local connection report. No live inference
  was requested for these checks.

## Reproduced failure and correction

Legacy status files can survive an unclean shutdown without a final
`bridge_stopped` event. The migration guard treated any live process with the
recorded PID as an active bridge. Windows had reused stale PIDs for unrelated
applications, so closing Desktop alone could not satisfy this guard.

Read-only native creation-time checks confirmed reused PIDs in the owner's source
state. Version 0.9.5 queries the current process creation time from a Windows
process handle. A process created more than one second after a snapshot's
heartbeat cannot have produced that snapshot. Such a record no longer blocks
import/connection adoption. Old heartbeats alone are not sufficient: original
live processes, unavailable creation times and invalid/missing timestamps still
block adoption. Source snapshots are retained unchanged.

The second defect was diagnostic: the connection command returned failure on
stderr, while the monitor displayed only a generic failure. Fixed public codes
now distinguish an active source bridge, an old monitor, unreadable state and
unverified connection provenance. Only predefined UI messages are displayed;
unknown errors and private stderr remain hidden.

## Results

| Check | Mode | Result | Scope |
| --- | --- | --- | --- |
| Scoped regressions | Source/native | PASS, 45 tests | Windows ownership/import/disconnect, Desktop, monitor IPC/feedback and build identity; includes real Windows creation-time query |
| Old artifact regression | Frozen 0.9.4 | Reproduced: exit 1, `active_bridge` | Synthetic old snapshot with a currently live reused PID blocks import; source unchanged |
| Corrected artifact regression | Frozen 0.9.5 | PASS: exit 0, import succeeds | Same synthetic reused PID; source unchanged |
| Actual live process guard | Frozen 0.9.5 | PASS: exit 1, `active_bridge` | Fresh snapshot belonging to the current fixture process still blocks import |
| Packaged runtime/native UI | Isolated 0.9.5 payload | PASS | Frozen and native identities, private IPC, preferences, WebView preview, synthetic import and DPAPI retention, no source/developer Python needed |
| Installer lifecycle | Isolated native setups, 0.9.4 to 0.9.5 | PASS | Install, upgrade, locked-file rejection, rollback, uninstall/reinstall, retained history, unique Start-menu shortcuts and cleanup |
| Owner installed bridge | Physical owner host | BLOCKED | Owner still needs to install 0.9.5 and complete Settings connection adoption with Desktop closed |
| Clean production VM / physical input/display/sleep | New 0.9.5 artifact | NOT_RUN | Earlier 0.9.4 clean-VM results remain historical; not transferred to this artifact |

Validation commands: the five scoped unittest modules named above;
`tests/smoke_windows_installer.py` using the 0.9.5 build receipt, pinned compiler,
verified bootstrapper, previous 0.9.4 receipt and `--shortcuts`. The focused frozen
regression invokes each artifact's `import-legacy` with synthetic independent data
roots, then verifies both return codes and preservation of the source snapshot.

## Next owner action

At a convenient task boundary, close Desktop and the monitor, install 0.9.5,
open the installed monitor and select Settings **Conectar al inicio habitual**.
Wait for successful registration before opening Desktop. Verify the actual
installed bridge path/build, handshake and advancing authenticated counters in
the installed data root. Existing imported configuration/history remains valid;
do not re-import into the occupied data root.

No commit, release, public distribution, signing or production installer execution
was performed. Raw diagnostics and process identifiers stay outside this report.
