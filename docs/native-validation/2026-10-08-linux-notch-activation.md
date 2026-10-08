# Owner-host activation receipt — 2026-10-08 — Ubuntu — dynamic notch

## Identity and authorization

The owner approved activation after reviewing the bundled Nunito typography.
Source base: `48760d78e35c7bd31263308f74cbc39b8a501611`, dirty working tree on
`feature/dynamic-notch-monitor`; product baseline `0.9.6`.

Installed artifact: `codex-model-router_0.9.6-1~notch3_all.deb`.
SHA-256: `3d9ae114d6efa40afb9c92eba0fbf41ae6a2e6afe547c59be159d907be1ccc2f`.
Installed monitor build: `9023175c083da5c9`.
Installed/loaded router fingerprint: `7b899c9ef41eedde` (matching).
The Debian development suffix sorts below the previous `0.9.6-1` package;
this was an intentional installation of the approved development artifact.

Only `monitor_linux.py`, `monitor_state.py` and shared UI/resources differed from
the previous installed package. Routing and official engine code are unchanged.
The previous package was verified against installed files and retained privately
with resource/config backups. No private backup path, contents, IDs or logs are
included here.

The exact package was installed through the owner's visible PolicyKit
administrative authentication. Only the old monitor was stopped; the packaged
monitor launcher opened the replacement. Desktop and active bridges were not
restarted, re-registered or imported.

## Observed results

| Check | Status | Evidence and boundary |
| --- | --- | --- |
| Installed UI/source parity | PASS | Shared HTML/CSS/JS and Nunito font/license/manifest match the validated artifact/source. |
| Native WebKit readiness | PASS | Installed monitor reports shared-page readiness; the exact artifact's isolated GTK/WebKit font-loading fixture passed in the typography receipt. |
| Single instance | PASS | One installed monitor process and one app window; a second actual launcher invocation exits successfully and reuses that instance. |
| Native positioning | PASS for current display | Actual X11/XWayland window geometry matches the selected display's work-area top center. This does not accept all display/scaling combinations. |
| Keep above | PASS | GNOME acknowledges `_NET_WM_STATE_ABOVE`; saved `topmost=true` is retained. |
| Input region | PASS for server-side region | The X server reports a shaped input region excluding the transparent viewport. Hover expansion changes its height normally; physical clicking through shoulders/corners remains pending. |
| Connected live data | PASS | Fresh connected bridge, real thread/context snapshots and account quota available. No bridge mismatch, unknown build or restart-required flag. No private titles/counters/IDs retained. |
| Saved state | PASS | Configuration, Linux UI preferences and credential namespace remain byte-identical to the pre-install copies. |
| Owner visual/input acceptance | PENDING | User approved the design preview; installed hover/click/keyboard behavior still needs ordinary use or explicit confirmation. |
| Startup/sleep/fractional scale/multiple displays | NOT_RUN | Do not interrupt owner work to exercise these gates. |
| Native Mac/Windows | NOT_RUN | Shared implementation only; each independent host needs its own receipt. |

## Continuation

Ubuntu's latest design is installed and connected. No further data migration,
Desktop registration or restart is needed for this UI-only activation. Use the
[NATIVE-VALIDATION.md](../NATIVE-VALIDATION.md) runbook for remaining physical
checks, preserving the owner installation and tasks. Remote publication/CI has
not been performed for this branch.
