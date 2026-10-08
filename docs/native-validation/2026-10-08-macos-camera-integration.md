# Native receipt — 2026-10-08 — macOS camera integration

## Identity and scope

- Owner Mac, macOS 27.0.1 arm64; one physical display, 1728 × 1117 points.
  Native API reports a camera exclusion of 185 × 32 points. No serials retained.
- Source: local uncommitted changes on `38d3678`; product 0.9.6, policy 8.
- Source-mode installed monitor: `6d5ce16a097573ca`; packaged router identity
  unchanged at `80e86c3d7accf253`. No release/tag/publication in this iteration.
- Owner requested top-edge/camera integration. Only the monitor was rebuilt and
  relaunched; Desktop and agent connections were not restarted.
- Configuration remained byte-identical. Prior artifacts/config have a private
  ignored rollback copy under `state/`; no private data is included here.

## Results

| Check | Result | Evidence and boundary |
| --- | --- | --- |
| Native geometry | PASS | Full display edge; fixture cases cover notched/flat displays, negative origin and hidden menu bar |
| Installed window | PASS | Compositor metadata: x464, y0, width800, height1012, level25; confirms actual top placement, not visual acceptance |
| Installed identity | PASS | Exactly one monitor; bundle identity and every shared UI file match source |
| Bridge continuity | PASS | One connection; version0.9.6; mismatch/unknown/restartRequired/desktopRestartPending all false |
| Browser UI | PASS | `ROUTER_TEST_BROWSER=chromium npm run test:layout`: all eleven groups, including camera controls outside exclusion, 1x/2x, flat-display reset and narrow fallback |
| Native first click | PASS | `python3 tests/probe_mac_monitor.py`: geometry assertions plus one native down/up delivered once to non-key WebKit |
| Native camera lifecycle | PASS | `python3 tests/probe_mac_glass.py`: top edge/statusBar level, real WebKit compact controls outside actual camera exclusion, expanded Home and hide |
| Physical acceptance | NOT_RUN | Owner camera/menu appearance, auto-hidden menu/full-screen behavior and real external-display change remain to observe |
| Publication | NOT_RUN | Changes remain local; no commit, push or CI result for this patch |

The shared browser checks retain the normal Windows/Linux defaults. Native
Windows/Linux execution was not repeated for this Mac host change. Existing
Windows installer failure is outside this iteration and remains open.

## Implementation and next observation

`MonitorMac.swift` uses full-screen coordinates, camera-safe metadata, a
noninteractive physical cutout and menu-bar window ordering. Compact agents
occupy the left wing; quota/expand occupy the right wing. Expanded navigation uses the camera side wings when space permits,
with a vertical safe inset as the narrow-window fallback. Screens without a cutout use the ordinary compact
layout attached to their top edge. Geometry updates on display changes.

Ask the owner to observe the new physical camera integration during ordinary
use. If an external display is available, confirm its top-edge placement and
the removal of the camera gap after switching/disconnecting the active display.
No Desktop restart is needed for this UI-only change. Fixtures do not establish
physical pointer, menu overlap or multi-display acceptance.

### Owner width refinement

The owner found the first camera layout too wide. The final compact layout
uses433 points for zero/one/two agents on this camera, then509 for three,
585 for four and631 for four plus an overflow count. It contracts when agents
leave and caps at the initial iteration's ordinary width, rather than reserving
headline space. Agent names remain in hover details. Companions are clipped to
their wing while the width animates. Camera browser tests now cover growth,
contraction and stable width with40 synthetic agents at1x/2x. Focused quota and
native WebKit fixtures also passed during the refinement. Only the monitor
restarted again; configuration remains byte-identical. The earlier eleven-group
run preceded this sizing refinement; the camera group passed on the final patch.

### Expanded upper navigation refinement

The owner asked to use the blank upper band of the open island. Home/Agents
now occupy the left camera wing; History/Consumption/Settings occupy the right.
The full-width camera-height spacer is removed only when both navigation groups
fit. This raises the content by40 points on the observed Mac. Narrow widths
retain the safe inset; flat displays retain the original navigation flow.
Overflow clips navigation groups during width animations, keeping the physical
camera area free. The compact adaptive width behavior is preserved.

All eleven browser groups passed again on this patch. The camera group visits
all five destinations, verifies button exclusion at1x/2x, exercises the narrow
fallback and checks camera hit targets during a constrained width. The isolated
AppKit/WebKit fixture additionally verifies navigation in the upper band.
The monitor alone was rebuilt/relaunched; source/bundle/UI match, exactly one
monitor runs, configuration is byte-identical, and the unchanged router remains
connected with no mismatch/unknown/restart flags. Physical owner appearance is
still separate from those fixture checks. The patch remains uncommitted.
