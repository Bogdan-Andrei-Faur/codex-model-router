# History ratings style — Ubuntu — 2026-10-08

## Identity and scope

Development branch `feature/dynamic-notch-monitor`, dirty baseline
`48760d78e35c7bd31263308f74cbc39b8a501611`, product `0.9.6`.
Ubuntu 26.04.1 LTS, x86_64; shared browser and isolated native GTK/WebKit fixtures.
Artifact `codex-model-router_0.9.6-1~notch42_all.deb`, SHA-256
`dd14d56aa83d3bca84ac9e01d12da0055ec2b88a2664fa26ba990be9611d07fd`.
Installed monitor build `d5cfd3777f21bd05`; packaged/connected router
`2fec36051e3ccedb`. Supersedes the installed artifact in the
[detail cleanup receipt](2026-10-08-linux-notch-history-detail.md).

The rating disclosure uses coral, mint and lilac options with tinted idle surfaces,
solid selected surfaces, dark text/checks and thin borders. Aspect headers have
icons and accessible clear controls. Equal-width options use the available row;
the record sidebar shrinks from 260px to preserve readable detail controls in
narrow two-column views. Native action payloads, rating storage, keyboard toggles,
read-only behavior and lazy disclosure rendering are preserved.

## Results

| Mode | Status | Evidence |
| --- | --- | --- |
| Shared browser | PASS | Existing History and layout groups |
| Synthetic visual/computed checks | PASS | Selected colors/checks, no card/button overflow at 800/700/650/621/390px; clear and keyboard-toggle payloads; disabled read-only controls |
| Isolated GTK/WebKit | PASS | Exact extracted package fixture: readiness, bundled font, onboarding cancellation, pointer ownership/exit recovery and single instance |
| Isolated GTK/WebKit | PASS | 650px History: three distinct selected fills, dark checks/text, button fit, retained DOM and strict detail evidence |
| Installed readback | PASS | One connected monitor, WebKit ready, matching UI files, settings preserved, no startup traceback, bridge mismatch=false, bridge unknown=false, restartRequired=false |
| Physical owner interaction | NOT_RUN | Separate from fixture validation |
| Native macOS/Windows execution | NOT_RUN | No native execution on those platforms in this iteration |

Installation used visible Ubuntu authentication and restarted only the monitor.
Desktop and the loaded bridge were not restarted. Previous `1~notch41` artifact
and settings are retained privately for recovery. No remote publication or private
state/logs in this receipt. The existing quota Escape caveat remains open; no fix
is claimed and its dedicated group was not repeated.

## Spacing follow-up

Installed `0.9.6-1~notch43` adds a 12px top margin to a diagnostic card immediately
following an evidence-setting separator. No routing or action changes.
Artifact `codex-model-router_0.9.6-1~notch43_all.deb`, SHA-256
`750fc08d233c0983159ee4e6d1d29bb09c9fdffb2bbcbdaed93be6d529aefa05`.
Shared History fixture PASS. Exact extracted package in isolated GTK/WebKit PASS:
measured 12px gap, retained layout/evidence and rating checks. The broader package
smoke remains the `1~notch42` result; it was not repeated for this CSS-only change.
Installed readback PASS: monitor `2e0a5284b2aa9c8e`, router `2fec36051e3ccedb`, one
connected instance, WebKit ready, matching UI files, preserved settings, no
traceback or bridge mismatch, restartRequired=false. Only the monitor restarted;
previous `1~notch42` package/settings retained privately. Physical and other-OS
acceptance remain open.
