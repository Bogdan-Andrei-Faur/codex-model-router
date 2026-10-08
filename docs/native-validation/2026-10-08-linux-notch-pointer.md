# XWayland pointer ownership correction — 2026-10-08 — Ubuntu

## Scope and identity

The owner reported that agent details still sometimes stayed open on installed
`1~notch6`. Earlier fixtures accepted unchanged outside coordinates but did not
model coordinates remaining inside while the pointer belongs to another window.
Do not treat the earlier automated passes as physical acceptance.

Source base: `48760d78e35c7bd31263308f74cbc39b8a501611`, dirty branch
`feature/dynamic-notch-monitor`; product `0.9.6`.
Artifact: `codex-model-router_0.9.6-1~notch7_all.deb`.
SHA-256: `58a0adf03c4e4e686409da775206d12054d1a0682aa645f48f87ec8266528d36`.

The Linux host now requires `get_window_at_position()` to return a window whose
toplevel is the monitor before projecting an inside point. Coordinates alone
cannot preserve hover. Outside state is repeated every 250ms, so missed or late
delivery is recovered even with a stationary pointer. The shared non-resetting
220ms grace period still permits moving into the detail panel.

This is a Linux host correction; no Mac/Windows code, routing policy or official
engine is changed by this follow-up. Native Wayland remains on the DOM fallback.

## Results

| Check | Status | Evidence and boundary |
| --- | --- | --- |
| Previous package regression | FAIL reproduced | The updated package fixture fails against `1~notch6`: stale inside coordinates with no owned window keep projecting an inside point. |
| Exact corrected package fixture | PASS | `xvfb-run -a dbus-run-session -- /usr/bin/python3 tests/smoke_package_linux.py dist/notch-pointer-ownership/codex-model-router_0.9.6-1~notch7_all.deb`: synthetic stale/overlapping foreign window rejection and missed-exit recovery; real mapped GTK pointer ownership; actual WebKit closure for agent/quota, bundled font and packaged single instance. |
| Shared interaction regression | PASS | Chromium repeated outside samples, re-entry, Escape, native hover and mode acknowledgement fixtures pass. |
| Installed activation | PASS | Visible PolicyKit authentication completed and `1~notch7` installed. Only the old monitor was stopped/reopened; WebKit ready, host bytes match source, settings byte-identical and live connection healthy with mismatch/unknown/restart flags false. Monitor build `0f5e4ea931be3c7d`; installed/loaded router fingerprint `7b899c9ef41eedde`. No Python traceback at readback. Prior artifact/state retained privately. |
| Owner physical acceptance | NOT_RUN | User must observe natural pointer crossing in GNOME; synthetic stale-coordinate reproduction is not confirmation of the exact sequence on the owner's desktop. |

Prior [crew/quota receipt](2026-10-08-linux-notch-crew.md) remains historical
evidence for `1~notch6`. The new regression narrows the earlier acceptance gap.
No private window names, raw logs or conversation identifiers are retained.
