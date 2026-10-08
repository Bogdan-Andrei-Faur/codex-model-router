# Home opening space — Ubuntu — 2026-10-08

Artifact `codex-model-router_0.9.6-1~notch37_all.deb`, SHA-256
`775c136cfeeae57f22d792352a5f90fe3447114f63047ba1cc704513ab987a04`.
Development branch `feature/dynamic-notch-monitor`; baseline `0.9.6`.

Real GTK/WebKit reproduced stale metric-grid height after the width animation:
99px instead of its natural 57px. Aligning children at the bottom therefore left
42px of empty space above them until a later refresh. An equal-column flex row
keeps natural height through reflow and preserves track alignment. No timing
workaround or changes to agent selection, measurements or routing.
Includes the pending `1~notch36` Agents picker spacing and centered pipeline.

PASS: existing metric alignment and preview browser fixtures. New isolated
GTK/WebKit regression samples 135 opening/reopening frames across known,
unknown and compacting context. It fails against extracted `1~notch35` with
42px excess height and passes against source and exact extracted `1~notch37`.
The baseline process also emitted a native allocator shutdown diagnostic after
its expected failed assertion; source and successor runs exited cleanly.
No live owner state was used for these fixtures.

Installed readback PASS: `0.9.6-1~notch37`, one monitor, WebKit ready, matching
UI files, preserved settings, no startup traceback and one bridge connection.
Monitor build `d4c77d8725682366`; packaged router `2fec36051e3ccedb`.
Only the monitor was restarted. Live bridge mismatch remains true with a known
build; stored restartRequired=false does not close that activation gate. Physical owner acceptance, native macOS/
Windows validation, prior bridge activation and the separate intermittent quota
Escape issue remain open. No remote publication.
