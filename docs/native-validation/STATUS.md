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
| ENV: source/installed/loaded identity for new receipt | NOT_RUN | NOT_RUN | NOT_RUN for next receipt |
| DKR: local Docker Engine/Desktop full grader suite | NOT_RUN | NOT_RUN | PASS at historical local baseline; recheck if engine/runtime changes |
| TEL: three native authenticated layouts | NOT_RUN for latest transport change | NOT_RUN for latest transport change | Historical three-layout probe on 2026-09-28; NOT_RUN for latest source receipt |
| TEL-DESKTOP: active ordinary Desktop uses intended bridge | NOT_RUN for current artifact | NOT_RUN for current artifact | PASS at historical installed baseline |
| UI-INPUT/VIEWS: installed native focus/tray/views | NOT_RUN for current artifact | NOT_RUN for current artifact | Prior positioning/topmost fixes accepted; new receipt required for any new artifact |
| UI-DATA: live context/compaction/quota observations | NOT_RUN for current artifact | NOT_RUN for current artifact | Record natural observations in new receipt |
| UI-DISPLAY: two physical monitors/different scale | NOT_RUN | NOT_RUN | NOT_RUN |
| UI-SCALE: fractional/DPI interaction and restoration | NOT_RUN | NOT_RUN | NOT_RUN |
| UI-SLEEP: safe suspend/resume | NOT_RUN | NOT_RUN | NOT_RUN |
| UI-START: owner's normal startup/reopen/reboot | NOT_RUN for current artifact | NOT_RUN for current artifact | Prior ordinary restart accepted; recheck alongside physical cases |
| KEY-NATIVE: synthetic native store roundtrip | NOT_RUN for current artifact | NOT_RUN for current artifact | Prior Secret Service synthetic roundtrip; recheck if storage changes |

NOT_RUN means no current owner-host receipt exists for that row; it is not an
assertion that the feature is broken or that historical acceptance never occurred.
Change a row only with a committed receipt naming its source/artifact/loaded code.
For missing hardware use NOT_RUN; for unavailable required infrastructure use
BLOCKED. Keep per-host limitations and historical dates visible.

## Receipt index

No fresh owner-host receipt has been produced by this documentation change.
The following rows are the empty index structure, not test results:

| UTC date | Host alias / OS | Source / artifact | Receipt | Rows superseded |
| --- | --- | --- | --- | --- |

Add a row with a relative link to each new sanitized report. Do not commit raw
private state or convert another host's CI success into a PASS here.
