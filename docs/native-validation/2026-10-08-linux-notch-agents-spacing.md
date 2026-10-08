# Agents spacing — Ubuntu — 2026-10-08

Artifact `codex-model-router_0.9.6-1~notch36_all.deb`, SHA-256
`a798f422e31a589ddb8d03af13b0c1100484b9190349b0452ff1f6204d9d1b7a`.
Development branch `feature/dynamic-notch-monitor`; baseline `0.9.6`.

Centers the capped-width live pipeline within its detail column. Widens the
Agents sidebar from 220px to 260px, reduces column gap and divider padding,
and gives the picker a stable scrollbar gutter plus card clearance for overlay
scrollbars. Cards stretch to available width. Narrow views retain horizontal
navigation with bottom clearance. Home and routing behavior are unchanged.

PASS: existing layout, shared controls and preview browser fixtures. Synthetic
seven-task geometry check at 800/650px confirms centered track, no horizontal
picker overflow and 22px card-to-picker-edge clearance (including scrollbar).
At 390px the picker remains horizontal with 12px bottom clearance. Screenshot
review confirms wider cards and centered pipeline. No new implementation-mirroring
test was added for this reversible CSS adjustment.

The standalone installation was dismissed (pkexec exit 126). This change was
subsequently installed with `1~notch37`; see the Home opening space receipt
for the successful installed readback. Native GTK fixture was not repeated for this
spacing-only change. Physical owner interaction and Mac/Windows native gates
remain open. The earlier bridge activation and intermittent quota Escape items
remain separate; Desktop is not restarted by this update.
