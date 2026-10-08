# Notch integration and isolated Mac verification — 2026-10-08

## Identity and scope

This section records the initial local integration. The subsequently authorized
installation below supersedes its installed/loaded state and publication scope.

- Safe host alias: `mac-local`; macOS 27.0.1, arm64.
- Python 3.9.6; Node v24.11.1; optional Docker integration not run.
- Source: local `main` fast-forwarded from `48760d7` to
  `cef7feec460ee27bf8f28e418c2fc9a93df69f6e`, plus uncommitted corrections
  to `monitor-ui/monitor.js`, `tests/test_usage_layout.cjs` and
  `tests/probe_mac_glass.py`. Product 0.9.6; policy 8.
- Corrected source monitor identity: `840e7d1e86cceab6`;
  source router identity: `80e86c3d7accf253`.
- Installed source-mode monitor remains pre-notch 0.9.6,
  build `b0be069afb994cf0`, router `5bf81351ee03c1c7`.
  Fresh Desktop metadata still reports loaded 0.8.1, router `de67953b7ece48ce`.
  Equal product versions do not establish matching source/artifacts.
- Validation used an isolated detached worktree and synthetic browser/native
  fixtures. No owner configuration, data, installation or Desktop was replaced;
  no owner process was stopped, commit created or GitHub push performed.
- Remote `main` remains `48760d7`. Source integration is local, not publication.

## Results

| Check | Status | Evidence | Boundary |
| --- | --- | --- | --- |
| Python discovery | PASS | 518 discovered, 465 executed, 53 skipped | Optional Docker and other-platform checks skipped |
| JS core | PASS | 31/31 | Shared source logic |
| Shared Chromium groups | PASS | All ten groups, including preview, History and quota dismissal | Browser execution on Mac; not hosted Windows/Ubuntu CI |
| Routing corpus | PASS | 27/27 | Offline fixtures |
| JEV constraints | PASS | Six cases | Offline; no external inference |
| Native AppKit/WebKit lifecycle | PASS after correction | `probe_mac_glass.py`, exit 0 | Isolated preview; no visual owner acceptance |
| Native first-click fixture | PASS | `probe_mac_monitor.py`, exit 0, one-click delivered | Synthetic delivery; physical OS mouse not verified |
| Final main quota check | PASS | 320/390/432/600 px × 1/1.25/1.5/2 DPI | Same corrected files as isolated candidate |
| Installed notch / physical input / displays / sleep | NOT_RUN | Existing installation preserved | Rebuild and owner-host acceptance remain separate |

## Failures reproduced and corrections

The native lifecycle fixture originally exited 3 on this Mac. WebKit reported
`WKErrorDomain` code 5: assigning `window.monitorPointer=()=>{}` returned a
JavaScript function, which cannot cross that evaluation result boundary.
Returning `undefined` explicitly with `;void 0` preserves the fixture's pointer
isolation and all lifecycle assertions. The corrected real WebKit fixture passes.

A deterministic browser regression reproduced quota reopening after Escape:
replaying `mouseenter` on the compact surface and quota, with no pointer motion,
cleared the dismissal. Native hit-target changes could also clear it without new
coordinates. The shared UI now releases dismissal on actual pointer movement;
layout/enter replay alone retains it. Regression coverage checks both DOM and
native-coordinate replay, plus hover restoration on a new movement, across all
16 width/DPI combinations. It failed before the correction and passes afterward.

The previous quota CI failures may involve this race, but this receipt does not
prove their exact event sequence or close hosted Windows/Ubuntu CI. The preceding
Windows installer protocol failure is unchanged and predates the notch branch.
Keep the prior failed runs and the published acceptance ledger as historical
evidence until the correcting revision is published and its affected jobs rerun.

## Authorized installation follow-up

The owner then authorized publication and reinstallation. `macos.py setup`
rebuilt the source-mode bundles; only the owned monitor was stopped and relaunched.
Its previous bundle/launchers and configuration were retained in a private local
backup. Configuration remains byte-identical; histories and telemetry were retained.

Installed product 0.9.6 now has monitor build `840e7d1e86cceab6` and router
`80e86c3d7accf253`. Exactly one monitor is running and all ten shared UI/font
files match the source. The exact wrapper passes initialize/model-list preflight.

After the preflight exited, a distinct ordinary Desktop client had a live,
handshaken bridge with the same product/build/router identities. No old Desktop
bridge process was found alive. The read-only monitor payload reports one
connection, matching known bridge identity, `restartRequired=false` and
`desktopRestartPending=false`. This activation is independent of the probe client.
Desktop was not restarted by the agent; no additional restart is required for
that observed connection. No model inference attribution or physical UI approval
is inferred from these checks.

## Remaining boundaries

- Publication is owner-authorized; record the published runtime SHA and its CI
  result after push. Local installation/activation checks above do not prove CI.
- Observe native-plan/catalog projection during ordinary work. Handshake/build
  agreement is not inference attribution or independent result validation.
- Rerun hosted Windows/Ubuntu quota cases and the Windows installer fixture.
  Physical owner UI/display/sleep acceptance remains separate.

No prompts, titles, conversation identifiers, credentials, raw OTLP/logs or
private filesystem paths are included in this receipt.
