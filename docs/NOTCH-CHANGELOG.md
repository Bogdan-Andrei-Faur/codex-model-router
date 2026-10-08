# Dynamic notch iteration archive — 2026-10-08

This archive preserves the successive development and installation notes. Claims
such as "latest installed" describe the iteration at the time it was recorded.
The current source/install/acceptance summary is in [HANDOFF.md](HANDOFF.md) and
[the acceptance ledger](native-validation/STATUS.md). Individual linked receipts
identify exact artifacts and limitations; earlier passes do not validate later
geometry or physical interaction.

## Dynamic notch redesign — development work, 2026-10-08

The working branch `feature/dynamic-notch-monitor` implements the approved
original colorful companions and top-centered notch in the shared UI and all
three native hosts. Start with [NOTCH-MONITOR.md](NOTCH-MONITOR.md) for design,
read-only live preview, test commands and acceptance gates. Routing and the
official engine are unchanged. A second visual iteration now fits overview height
to content, moves navigation below a horizontal crew, and separates agent selection
from the technical inspector. The current shared UI passes browser fixtures.
The `1~notch3` Ubuntu development package introduced the content-sized
overview and bundled Nunito font; isolated GTK/WebKit loading and shared browser
fixtures pass. See [the typography receipt](native-validation/2026-10-08-linux-notch-typography.md).
Ubuntu activation is now recorded in [the owner-host receipt](native-validation/2026-10-08-linux-notch-activation.md):
one installed monitor, correct top-center/keep-above state, preserved configuration
and matching connected router fingerprint. Desktop was not restarted. Installed
physical interaction/startup/sleep/scaling acceptance remains pending.
The installed successor `1~notch5` removes duplicate native hover tooltips and
fixes agent/quota panels staying open after pointer exit. Shared regressions and
the exact isolated GTK/WebKit package fixture pass; installed single-instance,
retained settings and connected data checks pass. See the
[hover correction receipt](native-validation/2026-10-08-linux-notch-hover.md).
Owner-observed physical hover/keyboard acceptance remains pending.
The `1~notch6` package replaced the single-agent compact view with a
responsive crew and a visual quota card. Shared/browser and isolated GTK/WebKit
fixtures pass, as do installed readback/connection/retained-setting checks. See
the [crew and quota receipt](native-validation/2026-10-08-linux-notch-crew.md).
Owner use subsequently reproduced stuck hover on `1~notch6`. Latest installed
`1~notch7` introduced actual GTK pointer-window ownership and repeated outside state
to recover lost delivery. The new regression fails on `1~notch6` and passes on
the exact `1~notch7` package; see the [pointer correction receipt](native-validation/2026-10-08-linux-notch-pointer.md).
Physical owner confirmation remains pending; do not equate earlier fixture passes
with acceptance of this intermittent XWayland interaction.
Latest installed `1~notch9` applies colored rounded model/effort tags throughout
the shared UI and restores hover after explicit DOM re-entry following Escape.
Shared UI groups, final GTK/WebKit fixture and installed readback pass; see the
[colored tags receipt](native-validation/2026-10-08-linux-notch-tags.md).
Installed follow-up `1~notch10` thickens shared tag borders to 2px while preserving
their dimensions. Scoped browser tests and installed readback pass, recorded in
the same tags receipt.
Latest installed `1~notch12` strengthens the entire tag's saturation/background/
border color. Scoped browser checks, visual screenshot review and installed
readback PASS, also recorded in the tags receipt.
Latest installed `1~notch13` restores 1px tag borders while retaining `1~notch12`
color intensity and dimensions. Scoped browser and installed readback PASS in
the same tags receipt.
Native Mac/Windows compilation and installed/physical redesign gates remain NOT_RUN. Historical receipts below describe earlier artifacts only.

Latest installed `1~notch14` simplifies compact agent context details and matches
the expanded meter's companion color and 6px track. Scoped browser/interaction,
exact GTK/WebKit package fixture and installed readback PASS; see the
[context receipt](native-validation/2026-10-08-linux-notch-context.md).
Latest installed `1~notch15` adds colored task-category icons, clearer blue quota
surfaces and removes the redundant quota footer. Scoped browser, exact GTK/WebKit
fixture and installed readback PASS; see the [category/quota receipt](native-validation/2026-10-08-linux-notch-category-quota.md).
Latest installed `1~notch16` removes the compact quota border/caption, retaining
the blue background and centered percentage. Scoped browser/readback PASS in
the same category/quota receipt.

Latest installed `1~notch17` also removes the quota card border, keeping its blue
background. Installed readback PASS; scoped fixture passed on unchanged retry
after an intermittent Escape assertion, documented in the category/quota receipt.
Latest installed `1~notch18` makes only the compact percentage background
transparent and explicitly centers the number. Scoped browser/centering checks
and installed readback PASS in that receipt; quota card backgrounds are retained.
Latest installed `1~notch19` removes the quota card's trailing collapsed margin,
which created 9px of unnecessary hover overflow. Scoped browser regression and
installed readback PASS in the category/quota receipt; short viewports can still scroll.
Latest installed `1~notch20` replaces text tabs with five icon destinations and
a rounded selected state, with Settings aligned right. Home shows the summary;
Agents opens the selected inspector. Eight shared browser groups, exact native
package fixture and installed readback PASS; see the
[navigation receipt](native-validation/2026-10-08-linux-notch-navigation.md).
Latest installed `1~notch21` moves icon navigation below the header and above
scrollable content. Scoped layout/navigation fixtures and installed readback
PASS in that receipt.
Latest installed `1~notch22` removes the old header and automatically compacts
Expanded after pointer exit. Re-entry cancels closure, dragging defers it and
unsaved Settings input survives reopen. Shared browser groups, exact native
package fixture and installed readback PASS in the
[auto-compact receipt](native-validation/2026-10-08-linux-notch-autocompact.md).
Latest installed `1~notch23` makes Home wider and horizontal: principal agent
left, other agents right without duplication, with a narrow-screen fallback.
All three hosts allow an 800px viewport; secondary views keep their prior width.
Shared browser groups, exact Ubuntu package fixture and installed readback PASS
in the [horizontal Home receipt](native-validation/2026-10-08-linux-notch-horizontal-home.md).
An intermittent preview quota-exit timeout passed on unchanged retry; physical
hover acceptance remains open as recorded in that receipt.
Latest installed `1~notch24` moves principal details to a top-right icon, increases
other-card contrast, removes the footer and moves routing pause/version to
Settings. Shared controls/layout, exact native package and installed readback
are recorded in the [Home cleanup receipt](native-validation/2026-10-08-linux-notch-home-cleanup.md).
The intermittent quota Escape failure reproduced; a diagnostic rerun passed
without a runtime fix. Keep that acceptance caveat open.

Latest installed `1~notch43` adds 12px between the diagnostic evidence separator
and the following metrics card. Shared History and exact-package WebKit spacing
checks PASS; installed readback PASS, one connected monitor and preserved settings.
Only the monitor was restarted. See the [spacing follow-up](native-validation/2026-10-08-linux-notch-history-ratings.md#spacing-follow-up).

Previously installed `1~notch42` styles History ratings with coral/mint/lilac options,
solid selected fills and dark checks, aspect icons and accessible clear actions.
History list width adapts to keep the controls readable in narrow two-column views.
Shared History/layout, visual 390–800px and exact GTK/WebKit checks PASS.
Installed readback PASS: one connected monitor, matching UI/bridge builds and
preserved settings. Only the monitor was restarted. See the
[ratings receipt](native-validation/2026-10-08-linux-notch-history-ratings.md).

Previously installed `1~notch41` replaces generic History detail explanations with
recorded duration, last-call usage, retries and visible incidents. Current task
controls remain in Agents; one optional lazy diagnostic section retains strict
inference attribution, meaningful setting/phase changes and estimates. Shared
History/layout/lazy/glass/preview checks and the exact GTK/WebKit package fixture
PASS. Installed readback PASS: one connected monitor, preserved settings,
matching UI/bridge builds; Desktop was not restarted. See the
[detail cleanup receipt](native-validation/2026-10-08-linux-notch-history-detail.md).

Previously installed `1~notch40` optimizes History transport, incremental projection and
rendering. Full journals remain intact; the UI receives cached decision snapshots,
reuses live overlays/search text and builds disclosures only when opened.
Parity, append/reset/recovery, shared UI and exact GTK package fixtures PASS.
Isolated WebKit delivery/render improves 810→168ms on the same aggregate workload.
Installed readback PASS: one connected monitor, matching UI/bridge builds,
preserved settings and compact history payload confirmed. See the
[performance receipt](native-validation/2026-10-08-linux-notch-history-performance.md).

Previously installed `1~notch38` redesigns History as a wide record/detail workspace with
shared cards, status icons, colored tags and persistent disclosures. Removes
Home's old-history hint. Scoped shared/browser and exact native package checks
PASS; known quota Escape regression remains open. Installed readback PASS:
one connected monitor, preserved settings and matching UI/bridge build.
See the [History receipt](native-validation/2026-10-08-linux-notch-history.md).

Previously installed `1~notch37` fixes the empty Home metric space retained by WebKit after
opening. Native WebKit regression fails on installed `1~notch35` with 42px of
excess space and passes on source and the exact extracted successor. Shared
alignment/preview fixtures PASS. Includes the pending `1~notch36` centered
pipeline and picker spacing. Ubuntu readback PASS: one connected monitor,
matching UI files and preserved settings. Desktop was not restarted.
See the [Home spacing receipt](native-validation/2026-10-08-linux-notch-home-spacing.md).

Previously installed `1~notch35` removes the entire Agents turn-selection section and its
proposed/accepted/confirmed cards; routing controls and live pipeline remain.
Shared controls, opening metric alignment and preview browser fixtures PASS.
Installed readback PASS: one connected monitor, matching UI files and preserved
settings. Includes the `1~notch34` opening-alignment fix; Desktop was not restarted. See the [Agents simplification receipt](native-validation/2026-10-08-linux-notch-agents-simplified.md).

Previously verified `1~notch33` refines the pipeline's drop connections to
12px and makes the active node solid green without animation, matching completed
nodes. Visual/computed-style checks and installed readback PASS in the
[live pipeline receipt](native-validation/2026-10-08-linux-notch-live-pipeline.md).
Existing live bridge/Desktop restart and physical acceptance remain pending.

Previously installed `1~notch32` restyles the pipeline as smaller solid drops:
black checks/numbers, curved thicker connections, 30px nodes and a 360px track.
Scoped browser, exact GTK/WebKit and installed readback PASS in the
[live pipeline receipt](native-validation/2026-10-08-linux-notch-live-pipeline.md).
The existing live bridge mismatch/Desktop restart and physical acceptance
remain pending.

Previously installed `1~notch31` adds the horizontal live pipeline and hides the
confirmed card until confirmed model evidence exists. Native `turn/plan/updated`
events project content-free steps; absent plans use observed lifecycle states.
78 Python/30 core tests, scoped browsers, exact package and installed readback
PASS; see the [live pipeline receipt](native-validation/2026-10-08-linux-notch-live-pipeline.md).
Owner Desktop restart is still required to load the new listener; actual task
plan delivery and Mac/Windows physical acceptance remain pending.

Previously installed `1~notch30` removes the two routine Agents explanations
and includes inactive, non-archived conversations through an independent
monitor catalog. Home/compact filters stay unchanged. Scoped Python/browser
checks and `1~notch29` native fixture PASS; installed successor readback PASS.
Only the monitor restarted. The live bridge still has the old router fingerprint:
owner Desktop restart is required for the complete catalog. See the
[Agents catalog receipt](native-validation/2026-10-08-linux-notch-agents-catalog.md).

Previously installed `1~notch28` makes Agents horizontal and content-sized:
selected character/task picker left, routing controls/evidence right. Narrow
screens stack the columns. Scoped browser checks, exact native package fixture
and installed readback PASS; see the [horizontal Agents receipt](native-validation/2026-10-08-linux-notch-agents-horizontal.md).
Mac/Windows native and physical acceptance, and the existing intermittent quota
Escape issue, remain open.

Previously installed follow-up `1~notch27` removes the redundant bottom History action
from Agents; top navigation retains access. Scoped lazy-history test and
installed resource/connection/settings readback PASS, recorded in the
[Agents workspace receipt](native-validation/2026-10-08-linux-notch-agents-workspace.md).

Previously installed `1~notch26` replaces the Agents inspector with a dedicated
routing workspace: selected companion at the top, task picker, per-task mode,
proposal/acceptance/confirmed evidence cards and contextual attention/phase.
Home metrics and full history are not duplicated. Scoped browser checks, final
native fixture and installed readback PASS; see the
[Agents workspace receipt](native-validation/2026-10-08-linux-notch-agents-workspace.md).
The existing intermittent quota Escape regression remains open. Mac/Windows
native and physical owner acceptance remain independent pending gates.
