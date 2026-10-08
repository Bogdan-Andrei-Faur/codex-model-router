# History redesign — Ubuntu — 2026-10-08

Artifact `codex-model-router_0.9.6-1~notch38_all.deb`, SHA-256
`7b24b9911695804c38c41a612d14893314ab90c0ac26cfd0ba5bc84135e19305`.
Development branch `feature/dynamic-notch-monitor`; baseline `0.9.6`.

Removes the redundant Home hint about older work. History now shares the wide
island, rounded cards and model/effort palette of Home/Agents: searchable records
left, selected detail right, responsive stack on small screens. Reason cards lead;
evidence, ratings, task controls and diagnostics remain available in disclosures.
No journal format, routing policy or attribution changes. Updating read-only state
now invalidates the UI signature so visible controls also update immediately.

PASS: scoped layout, new History interactions, lazy journal (37,000 synthetic
records), shared controls, metric alignment, interaction, Windows message-channel,
update controls and preview fixtures. History verifies pagination, keyboard
selection, search focus, disclosure persistence, rating payloads and read-only
controls. Chromium screenshot reviewed. Isolated GTK/WebKit confirms columns,
no inner horizontal overflow, bounded rows and disclosure persistence. Exact
packaged GTK fixture passes onboarding, loading, fonts, pointer and single-instance
checks. This is not physical owner acceptance or native Mac/Windows execution.

Full `test:layout` is NOT green: the previously documented quota Escape assertion
failed, including a scoped retry, and remains open. A preview navigation timeout
passed unchanged on retry; the fixture now explicitly moves the pointer inside
when switching from wide History to narrower Settings to avoid intentional
pointer-exit auto-compaction during Playwright's animation wait.

Installed readback PASS: `0.9.6-1~notch38`, one monitor, WebKit ready, no startup
traceback, source UI matches, settings preserved and one connection. Monitor
build `68bf6d59766fb9dc`; packaged router `2fec36051e3ccedb`. The connected bridge
now matches (mismatch=false, unknown=false, restartRequired=false). This closes
the earlier fingerprint mismatch, not physical plan delivery or acceptance.
Only the monitor was restarted; Desktop was not restarted by this update.
Physical/native-platform acceptance gates remain open.
No private state or remote publication in this receipt.
