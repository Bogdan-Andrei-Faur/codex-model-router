# Development receipt — 2026-10-08 — Linux — bundled typography

## Identity and scope

- Source base: `48760d78e35c7bd31263308f74cbc39b8a501611`; dirty working tree
  on `feature/dynamic-notch-monitor`.
- Product baseline: `0.9.6`; artifact revision: `1~notch3` (development preview).
- Artifact: `dist/notch-typography/codex-model-router_0.9.6-1~notch3_all.deb`.
- Artifact SHA-256: `3d9ae114d6efa40afb9c92eba0fbf41ae6a2e6afe547c59be159d907be1ccc2f`.
- Contains the content-sized overview, horizontal crew and technical inspector,
  plus Nunito variable with full OFL license and pinned upstream/hash manifest.
- No owner installation replacement, Desktop restart, registration or data import.

## Results

| Check | Status | Evidence and limit |
| --- | --- | --- |
| Shared Chromium UI | PASS | All eight layout/interaction groups; responsive widths/DPI, quota expiration, context compaction, reduced motion, keyboard, history and controls. Does not execute native Mac/Windows. |
| Read-only preview | PASS | Three scoped Python tests; GET-only tokenized loopback, strict same-origin/asset allowlist and local font response. Browser adapter confirms Nunito actually loaded. |
| Exact Ubuntu package | PASS | Extracted package and launcher exercised under isolated Xvfb/dbus; GTK onboarding fixtures, shared WebKit readiness, local Nunito load and single-instance checks. |
| Visual review | PASS for development review | Live read-only preview inspected. Safe simulated screenshots remain ignored in `dist/notch-typography/review/`; owner aesthetic acceptance remains pending. |
| Installed/physical Ubuntu | NOT_RUN | Position, focus, click-through, startup, scale and sleep need owner-coordinated activation. |
| Native Mac/Windows | NOT_RUN | Shared font is copied by both builders; compilation/loading and physical interaction require each host's receipt. |

The latest artifact supersedes earlier `1~notch2` packaging proof for these UI
files. Routing/official engine code is unchanged. Remote CI has not been run for
this unpublished branch. Continue with [NOTCH-MONITOR.md](../NOTCH-MONITOR.md) and
[NATIVE-VALIDATION.md](../NATIVE-VALIDATION.md); keep artifact, installed state,
loaded bridge and human acceptance separate.
