# Notch hover correction — 2026-10-08 — Ubuntu

## Identity and scope

- Source base: `48760d78e35c7bd31263308f74cbc39b8a501611`, dirty working tree
  on `feature/dynamic-notch-monitor`; product baseline `0.9.6`.
- Artifact: `codex-model-router_0.9.6-1~notch5_all.deb`.
- SHA-256: `8bdb24eb48559482d1750e897168ba8f50c561d5925a375de2deedeb0c49fb97`.
- Owner reported duplicate native tooltips and agent/quota hover panels remaining
  open after pointer exit. The shared UI removes those tooltips, retains accessible
  labels and uses one close deadline. All hosts now project pointer exit even
  while focused; Linux adds X11/XWayland sampling for clipped-window leave loss.
- Routing and official engines are unchanged. No private state/logs are included.

## Results

| Check | Status | Evidence and boundary |
| --- | --- | --- |
| Repeated native exit regression | PASS | Browser regression failed before the timer fix and passes after it for both agent and quota. Re-entry cancels closure; Escape dismisses; compact subtree has no title tooltips. |
| Shared UI fixtures | PASS | `ROUTER_TEST_BROWSER=chromium npm run test:layout`, including layout, interaction, history, quota, Windows message channel, update controls and notch preview. Browser fixtures do not prove native Windows execution. |
| Exact Linux package fixture | PASS | `xvfb-run -a dbus-run-session -- /usr/bin/python3 tests/smoke_package_linux.py dist/notch-hover-fixed/codex-model-router_0.9.6-1~notch5_all.deb`: actual GTK/WebKit closes both synthetic panels with a stationary outside pointer and no DOM leave event, loads bundled Nunito, and verifies packaged launcher/single instance. |
| Intermediate package fixture | FAIL, superseded | `1~notch4` hover fixture had no synthetic active agent; its idle character opened the full overview. Added an explicit preview agent and corrected the new host helper import before building `1~notch5`. The intermediate artifact was not installed. |
| Installed activation | PASS | Owner completed visible PolicyKit authentication. Installed `0.9.6-1~notch5`; restarted only the old monitor, leaving Desktop and bridges running. Installed shared UI/host bytes match source; one monitor process/window, WebKit ready and keep-above acknowledged. |
| Retained state and connection | PASS | Configuration, Linux UI preferences and credential namespace remain byte-identical. Connected thread/quota data available; bridge mismatch/unknown and both restart flags false. Installed monitor build `94e51b62fb76fa8d`; installed/loaded router fingerprint `7b899c9ef41eedde` matches. No runtime traceback. Previous package/state retained privately for rollback. |
| Physical pointer/keyboard interaction | NOT_RUN | Isolated Xvfb input projection does not certify owner-observed GNOME behavior. |
| Native Wayland | NOT_RUN | Uses DOM leave handling; global pointer sampling is intentionally X11/XWayland-only. |
| Native Mac/Windows | NOT_RUN | Source changes are shared/included, but no local native compilation or physical acceptance. |

The previous [activation receipt](2026-10-08-linux-notch-activation.md) remains
historical evidence for `1~notch3`. No remote publication or CI run was requested
for this correction.
