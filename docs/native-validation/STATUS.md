# Real-machine acceptance ledger

Use [the runbook](../NATIVE-VALIDATION.md) and [report template](REPORT-TEMPLATE.md).
This ledger is repository-owned; no external knowledge/memory service is needed.

## Baseline recorded 2026-10-05

Source `02d0be1efe98c9f2c30751b4ee4a532a0c5ed1fb` passed
[all 13 CI jobs](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/37315933675).
Real Linux x86_64/ARM64 Docker jobs each passed 482 tests without skips. Hosted
Python 3.9/3.14 and native monitor/UI checks passed on all three OSes, with two
Ubuntu APT lifecycle jobs. Those are CI results for that source, not acceptance
of the owner's installed Mac/Windows or physical display/sleep behavior.

Ubuntu package 0.8.1-8 activation was verified locally on 2026-10-05 after the
owner's restart: one packaged monitor/bridge, completed native handshake,
authenticated telemetry without unauthorized requests and preserved source data.
This is the historical installed Ubuntu baseline in [VALIDATION.md](../VALIDATION.md).
Recheck the actual installed/loaded identities before extending its acceptance.

## Open real-machine checks

| Check | macOS owner host | Windows owner host | Ubuntu owner host |
| --- | --- | --- | --- |
| ENV: source/installed/loaded identity for new receipt | NOT_RUN | PASS 07/10 owner restart: installed 0.9.6 manifest/monitor and fresh Desktop bridge with matching router build | NOT_RUN for next receipt |
| DKR: local Docker Engine/Desktop full grader suite | NOT_RUN | BLOCKED: Docker CLI unavailable on host-a | PASS at historical local baseline; recheck if engine/runtime changes |
| TEL: three native authenticated layouts | NOT_RUN for latest transport change | PASS: all three isolated layouts on host-a, 2026-10-06 | Historical three-layout probe on 2026-09-28; NOT_RUN for latest source receipt |
| TEL-DESKTOP: active ordinary Desktop uses intended bridge | NOT_RUN for current artifact | PASS 07/10 installed 0.9.6 ordinary Desktop handshake; authenticated requests advance, unauthorized/invalid payloads zero | PASS at historical installed baseline |
| UI-INPUT/VIEWS: installed native focus/tray/views | NOT_RUN for current artifact | NOT_RUN for current artifact | Prior positioning/topmost fixes accepted; new receipt required for any new artifact |
| UI-DATA: live context/compaction/quota observations | NOT_RUN for current artifact | NOT_RUN for current artifact | Record natural observations in new receipt |
| UI-DISPLAY: two physical monitors/different scale | NOT_RUN | NOT_RUN | NOT_RUN |
| UI-SCALE: fractional/DPI interaction and restoration | NOT_RUN | NOT_RUN | NOT_RUN |
| UI-SLEEP: safe suspend/resume | NOT_RUN | NOT_RUN | NOT_RUN |
| UI-START: owner's normal startup/reopen/reboot | NOT_RUN for current artifact | NOT_RUN for current artifact | Prior ordinary restart accepted; recheck alongside physical cases |
| KEY-NATIVE: synthetic native store roundtrip | NOT_RUN for current artifact | PASS 0.9.3 synthetic import/DPAPI; owner's imported cipher decryptable, no provider request | Prior Secret Service synthetic roundtrip; recheck if storage changes |
| INSTALL-LIFECYCLE: native installer in isolated directories | NOT_RUN for owner pkg | PASS exact 0.9.6 frozen/setup fixtures and owner upgrade retaining six data files; clean guest 24 assertions remains 0.9.4 | PASS historical APT fixtures/owner deb; recheck new artifacts |

NOT_RUN means no current owner-host receipt exists for that row; it is not an
assertion that the feature is broken or that historical acceptance never occurred.
Change a row only with a committed receipt naming its source/artifact/loaded code.
For missing hardware use NOT_RUN; for unavailable required infrastructure use
BLOCKED. Keep per-host limitations and historical dates visible.

## Receipt index

The [0.9.6 owner repair](2026-10-07-windows-connection-repair-host-a.md) supersedes
owner installation/registration state below: installed native monitor 0.9.6,
next-launch registration and exact installed protocol preflight PASS. The owner then restarted Desktop; matching installed 0.9.6 handshake and
advancing authenticated telemetry now PASS. No Desktop was stopped by the agent.
The prior 0.9.5 PID fix left an ANSI diagnostic and buffered native input issue,
now reproduced and fixed. New clean-VM/physical/live-installed gates remain open.

Historical receipts below describe their respective observation times.

Windows 0.9.1 corrects the owner's failed 0.9.0 source import. See
[the import-fix receipt](2026-10-06-windows-import-fix-host-a.md): source/frozen
fixtures pass. The [completion receipt](2026-10-06-windows-import-completion-host-a.md)
confirms owner import with 0.9.1; 0.9.2 adds success feedback. Installed bridge
connection/activation remains pending.
The [0.9.3 capsule receipt](2026-10-06-windows-capsule-startup-host-a.md)
records a reproduced stale clip-region bug and passing browser/native fixtures;
the owner installed that exact artifact and confirmed startup capsule visibility.
Other physical display/input/sleep and loaded bridge checks remain separate.
The 07/10 clean Windows VM reproduced a connected-uninstall refusal in 0.9.3.
Version 0.9.4 normalizes native wrapper paths and passes recovery plus the full
production lifecycle repeat. The owner's unchanged 0.9.3 installation and legacy
loaded bridge are distinct from that validated artifact.

The subsequent [owner restart check](2026-10-07-windows-owner-restart-host-a.md)
finds installed 0.9.4 and its running monitor. Desktop still uses the source
wrapper/data root, although that source bridge also reports 0.9.4 and matching
fingerprints. Live authenticated reception advances without transport errors.
Installed registration/activation remains blocked until the owner closes Desktop
and completes the installed Settings connection action.

Subsequent diagnosis reproduced a 0.9.4 migration blocker caused by stale bridge
PIDs reused by unrelated Windows processes. The [0.9.5 correction](2026-10-07-windows-connection-pid-reuse-host-a.md)
passes 45 scoped tests, frozen regression and isolated installer lifecycle. Install
0.9.5 before retrying the owner transfer; simply closing/reopening Desktop did not
resolve the stale PID check in 0.9.4. Physical owner acceptance remains open.

Receipts below close only their named checks on their exact source/artifact.
Source/native fixtures do not establish physical or cross-host acceptance.

| UTC date | Host alias / OS | Source / artifact | Receipt | Rows superseded |
| --- | --- | --- | --- | --- |
| 2026-10-07 | host-a / Windows x64 | Installed 0.9.6 build `611981b0f2d8abd4`, router `b1f4bff15e1556ee` | [Connection repair](2026-10-07-windows-connection-repair-host-a.md) | 50 scoped tests, seven UI groups, exact frozen/setup/protocol fixtures, owner upgrade/registration PASS. Owner restart: live installed handshake/identity/telemetry PASS; physical gates remain open. |
| 2026-10-07 | host-a / Windows x64 | Corrected 0.9.5 build `eba25a11edafef30`; owner remains on 0.9.4 | [Connection PID reuse fix](2026-10-07-windows-connection-pid-reuse-host-a.md) | 45 scoped tests, real frozen regression, native/setup lifecycle PASS; installed activation and 0.9.5 physical/clean-VM gates remain separate. |
| 2026-10-07 | host-a / Windows x64 | Owner installed 0.9.4 build `d042188854998c95`; live source bridge has matching fingerprints | [Owner restart check](2026-10-07-windows-owner-restart-host-a.md) | Installed manifest/monitor and source telemetry PASS; installed registration/bridge activation still BLOCKED; physical gates remain open. |
| 2026-10-07 | host-a / Windows 11 x64 | `50e63b0` plus installer work; validated 0.9.4 build `d042188854998c95`; owner still 0.9.3 | [Windows installation acceptance](2026-10-07-windows-installation-acceptance-host-a.md) | 33 scoped tests, frozen/native/setup/shortcut fixtures, clean guest 24 assertions and connected-uninstall recovery. Owner identity remains 0.9.3; legacy loaded bridge BLOCKED; physical gates separate. |
| 2026-10-06 | host-a / Windows 11 x64 | `50e63b0` plus packaging reference-directory option; build `dadea95e26f96444` | [Windows preparation](2026-10-06-windows-host-a.md) | ENV, isolated TEL, ordinary Desktop activation after owner restart; core/browser/native fixture and portable ZIP results. Physical rows remain open. |
| 2026-10-06 | host-a / Windows 11 x64 | Source plus installer work; 0.9.0 build `32c9543555c53846` | [Windows installer](2026-10-06-windows-installer-host-a.md) | Isolated frozen/native/setup lifecycle and DPAPI import fixtures. Production activation, clean-machine and physical gates remain open. |

Add a row with a relative link to each new sanitized report. Do not commit raw
private state or convert another host's CI success into a PASS here.
