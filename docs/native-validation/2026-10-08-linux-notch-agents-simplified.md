# Agents simplification — Ubuntu — 2026-10-08

Artifact `codex-model-router_0.9.6-1~notch35_all.deb`, SHA-256
`71e4eb9ddd254831f534702a6354bd220f63f18b0f8ea3ef0f684b73c8885ed4`.
Development branch `feature/dynamic-notch-monitor`; baseline `0.9.6`.

Removed the complete Agents turn-selection heading and its proposed, accepted
and confirmed model/effort cards, including their unused styles. The selected
companion, task picker, routing controls, attention notices and live pipeline
remain. History attribution and router evidence are unchanged.
Includes the Home opening metric alignment fix from `1~notch34`.

PASS: existing shared controls fixture, metric alignment regression and preview
browser fixture. Obsolete assertions for removed cards were deleted; remaining
mode acknowledgements, keyboard focus, attention and live plan refresh checks pass.

Installed readback PASS: version `0.9.6-1~notch35`, one monitor, WebKit ready,
no startup traceback, source UI matches, settings preserved and one bridge
connection. Monitor build `6089b956a1183bf5`, packaged router `2fec36051e3ccedb`.
Only the monitor was restarted. Live bridge mismatch remains true (known build);
the stored restart flag is false and does not close the activation gate.
Before this update,
`dpkg-query` confirmed `1~notch34` installed on disk; no monitor restart was
performed between it and this successor. Native GTK fixture was not repeated
for this UI removal. Physical owner acceptance and Mac/Windows native checks
remain open. Desktop was not restarted; the earlier bridge activation gate
and intermittent quota Escape issue remain separate pending items.
No remote publication or private data in this receipt.
