# Dynamic-notch documentation and source delivery — 2026-10-08

## Scope and identities

Repository `Bogdan-Andrei-Faur/codex-model-router`, development branch
`feature/dynamic-notch-monitor`, based on
`48760d78e35c7bd31263308f74cbc39b8a501611`. Product baseline remains `0.9.6`;
publication of this branch does not create a release/tag or merge into `main`.
The published Git revision and its CI run are recorded below after push.

This delivery includes all pending shared/native notch work, monitor-only inactive
agent catalog and live native-plan projection, incremental History snapshots,
practical details/ratings, read-only preview, local Nunito/OFL and Lucide assets,
regression fixtures and safe iteration receipts. Current documentation now covers
the five screens, controls, architecture/data contracts, installation, privacy,
platform limitations and continuation. The original UI guide and iteration
handoffs are preserved as dated archives rather than discarded.

Entry points: [documentation index](../README.md), [HANDOFF](../HANDOFF.md),
[monitor UI](../MONITOR-UI.md), [notch contract](../NOTCH-MONITOR.md),
[shared architecture](../SHARED-MONITOR.md), [acceptance ledger](STATUS.md).
No private state, credentials, raw logs, conversation data, temporary preview URLs,
build outputs or dependency directories belong to this delivery.

## Local verification

Ubuntu 26.04.1 x86_64. Child test environments remove installed router root/config
overrides; native fixtures use synthetic data and isolated D-Bus/Xvfb windows.
No owner Desktop/monitor restart, installation replacement, credential request or
provider inference was needed for this publication task.

| Check | Result | Boundary |
| --- | --- | --- |
| Python discovery | PASS: 518 tests, 37 skipped | Optional Docker/platform requirements skipped locally; skips are not acceptance |
| JavaScript core | PASS: 31/31 | Shared logic |
| Chromium UI | PASS: all 10 groups | Layout, metric alignment, usage, interaction, lazy History, History, glass, Windows message channel, updates, preview |
| Routing corpus | PASS: 27/27 | Offline policy fixtures |
| JEV smoke | PASS: six constraint cases | Offline, no provider request |
| Exact `1~notch43` package smoke | PASS | GTK/WebKit readiness, bundled font, onboarding cancellation/new/import/refusal, pointer ownership/exit recovery, launcher and single-instance behavior |
| Exact `1~notch43` Home metrics | PASS: 135 opening/reopening frame samples | Known/unknown/compacting context, no stale metric height and aligned tracks in real WebKit |
| Asset manifests | PASS: Nunito font/license and all 33 Lucide SVG hashes | Vendored local assets and licenses |

The metric probe initially timed out when GTK inherited the caller's Wayland
session despite Xvfb. Repeating with `GDK_BACKEND=x11` passed. The standalone probe
now forces X11 before GTK initialization; its documented Xvfb invocation therefore
owns the test window and does not depend on the owner's compositor. This is a
fixture correction, not a new runtime layout fix.

The dedicated quota Escape group passed this run. A previously reproduced
intermittent failure still has no demonstrated root fix, so its physical/input
acceptance remains open. Shared browser success does not close it.

## Installed artifact and native acceptance

Previously installed Ubuntu pilot: `codex-model-router_0.9.6-1~notch43_all.deb`,
SHA-256 `750fc08d233c0983159ee4e6d1d29bb09c9fdffb2bbcbdaed93be6d529aefa05`.
Monitor build `2e0a5284b2aa9c8e`; packaged/connected router `2fec36051e3ccedb`.
Its last installed readback and History spacing/rating evidence are in
[the ratings receipt](2026-10-08-linux-notch-history-ratings.md). The full package
smoke and Home metric checks above extend fixture coverage to that exact artifact;
they do not replace the earlier readback with a new physical acceptance claim.

The artifact is distinct from the new source commit. Owner-host macOS/Windows
redesign execution, physical display/DPI/input/sleep/startup and natural live-data
acceptance remain separate gates in [STATUS.md](STATUS.md). No official engine
patch, routing-policy activation or model-attribution confirmation is claimed.

## Remote CI and publication

Previous baseline source `48760d78e35c7bd31263308f74cbc39b8a501611`:
[run 37609750802](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/37609750802)
finished with 13 successful jobs and one failed `windows-installer` job. The
failure was in frozen payload/isolated installer validation:
`Frozen bridge closed before protocol response`. It predates this redesign and
must not be hidden by citing the older successful 13-job matrix.

Current branch publication and its complete 14-job matrix: pending push/readback.
Native compilation/hosted fixtures are CI evidence for the tested SHA, not
physical acceptance of the owner's installation.
