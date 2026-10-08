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

First published implementation: `30ad758cf1d0c95ea4bed546ea3aa95ebf410971`,
remote branch identity verified, no uncommitted project files.
[Run 37799063084](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/37799063084)
finished with 11 successful jobs and three failures: the previous frozen Windows
installer failure, the Windows native monitor fixture, and macOS browser preview
startup. Python on all six OS/version combinations, both real Docker grader
architectures, both APT lifecycle variants and the Ubuntu monitor job passed.

Follow-up corrections before final publication:

- Windows permits the bundled Nunito file in its existing exact resource
  allowlist. The native fixture checks an actually loaded font face, Home's
  principal without inactive rows, the inactive Agents catalog and Escape ACK.
  The obsolete collapse-button/list assertions are replaced. Its synthetic
  DOM-driven sequence stops pointer polling, so the runner's unrelated mouse
  cannot close the fixture; physical hover still requires owner QA.
- The fixed loopback preview binds without `HTTPServer`'s reverse-DNS lookup,
  which introduces an unnecessary resolver-dependent startup delay. The new
  guard passes with DNS resolution forbidden; the existing browser adapter
  fixture passes locally. The follow-up macOS job passes all ten browser groups,
  including preview startup, without extending the 15-second timeout.
- The Mac lifecycle fixture now expects opaque/hidden legacy material, Home's
  principal and no inactive Home rows. Its historical script/capture names stay
  compatible, and synthetic lifecycle ignores physical pointer projection.
  It remains NOT_RUN on this Ubuntu host.

Follow-up source: `c5ff3d985648d07b168d7cb92bded45fcb536181`, pushed and
remote branch identity verified.
[Run 37799872117](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/37799872117)
attempt 1 finished with 11 successful jobs and three failures. The six Python
jobs, two Docker architectures, two APT lifecycles and macOS monitor passed.
Windows native compilation/self-test passed (including the bundled font), but
the Windows and Ubuntu monitor jobs then failed in the previously intermittent
quota Escape assertion. Their snapshots retained `quotaOpen=true` at different
width/DPI combinations. The frozen Windows installer failure also recurred.

Only the three failed jobs were requested once more on the same source to
distinguish intermittent behavior from the remaining installer failure. This
retry does not establish a quota root fix. Attempt 2 finished with the same
three failed jobs and 11 successful jobs in the combined latest matrix. Ubuntu
quota failed at 390px/1× DPI, Windows at 320px/2×; these differ from attempt 1's
600px cases. The installer again reported the same frozen protocol failure.

| Job family | Final result for `c5ff3d9` |
| --- | --- |
| Python — Windows/macOS/Ubuntu × 3.9/3.14 | PASS, all six jobs |
| Real Docker graders — Linux x86_64/ARM64 | PASS, both jobs |
| APT lifecycle — Ubuntu 24.04/26.04 | PASS, both jobs |
| macOS monitor | PASS: Swift compile, core and all ten browser groups, including preview |
| Windows monitor | FAIL in quota Escape browser assertion; native build/self-test/font PASS |
| Ubuntu monitor | FAIL in quota Escape browser assertion; native package step not reached in this run |
| Windows installer | FAIL: frozen bridge closed before protocol response, also present at baseline |

Final delivery documentation is an evidence-only follow-up to this tested source;
its commit skips duplicate CI and changes no runtime, assets or fixtures. Source,
documentation commit, installed artifact and loaded bridge remain separate.
Native compilation/hosted fixtures are CI evidence for the tested SHA, not
physical acceptance of the owner's installation.

## Remaining work

Reproduce and correct quota Escape behavior with the failing width/DPI cases;
retain native and browser event evidence without owner data. Diagnose the frozen
Windows installer protocol failure on an isolated native fixture before changing
its PASS gate. Then run the affected checks again on the correcting revision.
Neither issue was silently disabled or relabeled successful for publication.
Owner-host physical/macOS/Windows acceptance still follows the native runbook.
