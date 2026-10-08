# Dynamic notch monitor

Design direction approved on 2026-10-08; visual implementation remains under review. This replaces the old floating
capsule/sidebar visual language in the **shared** `monitor-ui/` surface. It does
not change routing policy, model attribution, Desktop or the official Codex engine.
Version 0.9.6 remains the baseline: the development package is not a new release.

## Visual and data contract

- Opaque black body, square top corners, concave 20px shoulders and rounded
  32px bottom corners. Compact body adapts from 310px up to 390px and is 64px high;
  Home, Agents and History bodies are up to 750px; other expanded views remain up to 550px.
  Native bounds include the transparent shoulders and exclude their input areas.
- Bundled Nunito variable typeface for all three shared hosts, with rounded
  strokes and stronger titles. The font, OFL license and pinned-source/hash
  manifest live in `monitor-ui/fonts/`; runtime uses only local files.
- Three original rounded rectangular companions: Milo/coral, Lumi/mint,
  Nori/lilac. A deterministic hash of the thread identifier selects the visual
  alias. Model, effort, category and title changes cannot change that identity.
  Aliases may repeat: the actual task title identifies the conversation. These
  are illustrations of conversations, not extra processes or agents.
- Working breathes, compaction tilts/squashes with closed eyes, waiting/error
  demands attention, completed smiles, idle rests, disconnected fades. A text
  label remains available in reduced-motion mode and to screen readers.
- Compaction supersedes an old context percentage. Awaiting a measurement after
  compaction differs from both active compaction and an unknown measurement.
  Context shows **used** capacity; account quota shows **remaining** allowance.
  The compact quota is always weekly and never substitutes a 5-hour window.
  Unknown/expired/disconnected quota is an em dash, never a fabricated zero.
- Compact characters include live tasks and waiting/error tasks so attention
  is visible even without opening the island. They retain tiny context bars and
  accessible detailed labels;
  hover/focus expands details below the top row. The compact summary opens the
  island. Multiple tasks replace the single-task headline with a centered crew
  of up to six characters, reduced on narrow displays, and an overflow count.
  Each character opens its own details; no rotation hides other visible agents.
  The quota hover card highlights weekly remaining allowance, includes separate
  progress bars for each reported window and shows renewal times when supplied.
  Expired/unknown readings retain the existing explicit unavailable state.
  Expanded activity fits its
  contents: Home places the principal companion and its context/weekly quota
  in the left column, and the remaining agents in a bounded list on the right.
  The principal is not duplicated in that list; selecting another agent moves
  it into the principal view. Below 620px viewport width the columns stack.
  Selecting a crew member changes the hero; the detail icon in the principal
  card's top-right corner opens the task's routing workspace. Remaining-agent cards
  use a clearer neutral background, with a stronger hover/focus state.
  Waiting/error companions remain selectable but
  are not counted as live. Clicking the weekly quota reveals all account windows.
  Home metric tracks align to the row bottom even when labels wrap during
  opening. Overview height follows content; short viewports scroll while navigation stays
  available. History, consumption and settings use the resizable workspace.
  State refresh preserves crew selection, horizontal position and keyboard focus.
- Expanded navigation sits at the top, above scrollable
  content. It is a compact icon row: Home, Agents, History, Consumption
  and Settings. The active destination has a rounded neutral background; Settings
  is aligned at the right edge. Home restores the content-sized overview; Agents
  opens the selected task's routing workspace. The detail action and navigation share
  the same selection state. Accessible button names and keyboard focus remain;
  no native hover tooltips are introduced. The old task-count/collapse/hide
  header is removed. The page title and connection status remain accessible;
  read-only/synthetic preview disclosure remains visible below navigation.
- Agents includes all available non-archived conversations, including inactive
  ones. A separate monitor-only catalog supplies tasks never observed by the
  router, with unavailable settings/evidence left explicit. Desktop archive/delete
  notifications and the reconciled non-archived catalog remove them; unarchive
  restores them. Internal ephemeral tasks retain their existing visibility rules.
  Agents selection is independent of Home selection; Home keeps its existing
  live/attention filter. Older bridges fall back to their observed conversations
  until Desktop restarts with the new catalog projection.
- Agents is a dedicated task-control workspace: the selected companion and task
  identity and task picker in the left column, with the
  per-task automatic/manual control (effective for the next message) and live
  pipeline centered in the right column. The left column is 260px wide with a
  reserved scrollbar gutter and card clearance; narrow views retain the horizontal
  task picker with bottom clearance. The turn-selection heading and proposed, accepted
  and confirmed model cards have been removed. Agents fits its content height like Home; below 620px the columns
  stack. Other secondary views retain their resizable height. Disconnected data is explicitly
  marked as the last reading. Waiting/error/blocked changes show an attention
  notice; a phase is shown only when reported. Recorded evidence and phase changes
  are available from History in the top navigation. No hero, context/quota gauges,
  token totals or full history are repeated here. Live refresh retains selection,
  picker scroll and keyboard focus; preview controls are disabled. The routine next-message hint and evidence
  explanation paragraph are omitted from Agents; the paused-routing notice
  remains available.
- The expanded footer is removed. Routing pause/resume lives at the top of
  Settings, labeled “Pausar enrutamiento” / “Activar enrutamiento”. Installed
  version and bridge/restart indicators live in Settings' update card. Transient
  operation feedback remains visible below navigation and does not reserve space
  when empty. Preview controls remain read-only.
- Leaving the island returns Expanded to Compact after 320ms. Re-entering
  cancels the deadline, repeated native outside samples cannot postpone it,
  and resizing waits for pointer release. DOM and native pointer delivery share
  the same behavior. Escape and tray controls remain available. Unsaved Settings
  key input stays in memory through collapse/reopen; it is not persisted or sent.
- Compact agent details use the same 6px context track and companion color as
  the expanded overview. The routine working label and repeated token/context
  paragraph are omitted; the percentage/unknown/compacting state remains visible
  and exact context details remain in the progressbar's accessible label.
  Waiting/error/offline status remains visible. Hover height fits its content.
- The compact task category uses its mapped Lucide icon and a companion-colored
  label. The compact quota shows only a vertically centered percentage on a
  transparent background, including hover, without a border or repeated caption.
  Expanded quota cards retain borderless blue tinted surfaces;
  unavailable compact quota stays neutral. The redundant account-sharing footer
  is omitted from quota sections; accessible account context remains available.
- History, consumption, settings, manual/automatic task modes, evidence levels,
  incremental journals, exact zero/missing tokens and mode acknowledgements remain.
  “Modelo seleccionado” does not assert the actual model of an inference.
- Model/effort tags share rounded colored pills throughout hover details, hero,
  inspector, history and routing policy. Model families use blue (Luna), mint
  (Terra), gold (Sol) and lilac (Astra); effort retains its own shared palette.
  Borders are 1px, with padding preserving the pill's overall dimensions.
  Tinted backgrounds use 26% of the semantic color, borders use 60% opacity,
  and the whole pill uses 1.4× saturation for clearer color on the black surface.
  Missing values remain neutral and explicit. Text labels are always present;
  color is supplementary. Shared `badge()` and CSS define all three platforms.

## Native placement and interaction

AppKit, WPF/WebView2 and GTK/WebKitGTK request a horizontally centered window at
**the top of the selected display's work area**. This respects the macOS menu bar,
Ubuntu top panel and Windows taskbar. It does not cover or attach to physical
Mac camera hardware. The native window is up to 800 logical pixels wide; the
remaining area is transparent and passes clicks through.

The full-height native viewport allows downward expansion without moving the
anchor. The overview sizes automatically. In History, Consumption and Settings, the
resize handle is at the bottom: dragging down grows the panel;
ArrowDown grows it, ArrowUp shrinks it, Home/double-click resets automatic height.
Existing mode/topmost/height preferences remain compatible. No preference rewrite
or Desktop re-registration is required for this visual change.

The three hosts calculate the same concave shoulders and bottom curves for their
native input regions. macOS hides its former blur view because the new black
surface is deliberately opaque. X11/XWayland can honor position/topmost hints;
plain Wayland retains compositor restrictions. Multiple physical displays,
fractional scaling, first-click focus, startup and sleep require native receipts.

Compact agent/context/quota details use the integrated hover panel and accessible
labels, without duplicate native `title` tooltips. Leaving the island starts one
220ms close deadline; repeated outside samples cannot postpone it. Returning to
the panel cancels closure. AppKit and WPF project the pointer even with keyboard
focus; GTK samples the X11/XWayland pointer every 50ms. Bounds changes trigger a
fresh sample even when the pointer is stationary. Native Wayland falls back to
WebKit DOM enter/leave events because global pointer coordinates are unavailable.
GTK also verifies that the actual window under the pointer belongs to the monitor:
XWayland can retain stale coordinates after entering a native Wayland application.
An outside sample is repeated every 250ms to recover missed/late leave delivery;
only a real owned-window re-entry can cancel closure through native projection.
The isolated Linux package fixture tests closure without a DOM leave event;
physical use on each platform remains a separate acceptance gate.

## Read-only local preview

From the repository root:

```bash
python3 tools/preview_monitor.py --live
```

Open the temporary URL printed by the command. It reads the installed per-user
root resolved by `application_layout.user_data_root()`; it does not read a source
checkout's state. Data polls every two seconds. History is requested only for
History/Consumption, with incremental revisions. Window modes and resizing are
local to the browser preview and never saved to the installed preferences.

The server binds only to `127.0.0.1`, uses a random URL token, validates host,
origin and fetch site, serves an explicit file allowlist, and supports only GET.
Startup uses the fixed loopback address directly, without reverse-DNS lookup.
It has no mutation/credential endpoint. `MonitorState(read_only=True)` separately
blocks configuration, task modes, ratings, connection actions and updates, and
skips automatic update checks. The native monitor keeps its existing direct/
private-pipe transport and CSP with `connect-src 'none'`; this development server
is not part of the packaged runtime. Stop it with Ctrl+C when review is finished.
Do not share the URL or save screenshots of private telemetry to Git.

For synthetic review, generate an isolated fixture and use its printed path:

```bash
python3 tests/preview_monitor.py
python3 tools/preview_monitor.py --fixture-root /tmp/codex-router-preview-EXAMPLE
```

The UI explicitly distinguishes simulated data from live read-only data. A browser
preview proves shared UI/data behavior, not native installation or physical input.

## Verification and remaining acceptance

```bash
npm test
ROUTER_TEST_BROWSER=chromium npm run test:layout
env -u PERSONAL_CODEX_ROUTER_ROOT -u PERSONAL_CODEX_ROUTER_CODE_ROOT \
  -u PERSONAL_CODEX_ROUTER_CONFIG python3 -m unittest discover -s tests -q
python3 build_linux_package.py --output dist/notch-review --revision 1~review1
env -u PERSONAL_CODEX_ROUTER_ROOT -u PERSONAL_CODEX_ROUTER_CODE_ROOT \
  -u PERSONAL_CODEX_ROUTER_CONFIG xvfb-run -a dbus-run-session -- \
  /usr/bin/python3 tests/smoke_package_linux.py \
  dist/notch-review/codex-model-router_0.9.6-1~review1_all.deb
```

The environment reset is essential: an installed Desktop can export installed
resource paths. Tests must use fixture code/data rather than the owner's active
installation. Choose a fresh output directory/revision if the artifact exists.

Current local delivery verification passes 518 Python tests (37 optional/native
skips), 31 JS core tests and all 10 browser groups. Routing corpus 27/27 and six
offline JEV cases pass. Latest installed Ubuntu pilot is `0.9.6-1~notch43`, recorded
in the [ratings/spacing receipt](native-validation/2026-10-08-linux-notch-history-ratings.md).
The exact extracted `1~notch43` package passes the isolated GTK/WebKit
spacing/detail fixture and full onboarding/pointer/single-instance smoke.
The [delivery receipt](native-validation/2026-10-08-documentation-delivery.md)
separates source checks, prior CI and the current published SHA's remote result.

The quota Escape group passed the current local run; the earlier intermittent
failure has no demonstrated root fix and remains open. Installed physical
interaction/startup/sleep/scaling acceptance remains pending. macOS/Windows native
execution is NOT_RUN on this Ubuntu host. CI compilation/self-tests, when available,
do not close owner-host input or installation gates. Run the existing probes and
physical checks from [NATIVE-VALIDATION.md](NATIVE-VALIDATION.md), including top
centering, shoulder/corner click-through, downward resize, hover, keyboard and
preference restoration. Record exact source/artifact/loaded identities. Previous
capsule/sidebar receipts do not accept the new geometry.

## Live pipeline

Agents replaces the raw `execution` phase row with a horizontal connected-node
pipeline. Nodes are solid 30px colored drops with black checks/numbers, connected by
curved 12px necks. The track is capped at 360px. Completed nodes/links are green,
the active node uses the same green without motion, pending nodes are gray; text and accessible step state supplement color. The active step retains its
number and “En curso” label. Offline, waiting, interrupted and failed states
retain their explicit status labels.

`turn/plan/updated` from the native app-server protocol supplies pending,
inProgress and completed step states for the current thread/turn. The bridge
validates the complete update, rejects wrong/ended turns, resets across turns,
and emits a new monitor snapshot immediately. Free-text steps/explanations are
not persisted: existing symbolic action categories provide labels, otherwise
`Paso N`. Labels are coarse categories; completion is reported by the agent's
native plan, not an independent verification of its work. Empty plans reset to
the lifecycle view. Ending a turn never marks unfinished plan steps completed.

When no matching native plan exists, the component shows Selection, Acceptance,
Execution and Completion from observed routing/lifecycle fields. It does not
advance the old inferred semantic plan. Native plan updates require Desktop to
load the new bridge; shared monitor updates alone cannot activate the listener.
Model attribution remains available in History; Agents no longer repeats its cards.
No official engine patch or automatic model-switch policy change is involved.

### Home opening metric regression

The context/quota row uses flex layout with equal-width children aligned at the
bottom. WebKit retained a stale CSS grid row height from the narrow opening
animation, leaving 42px of blank space until a data refresh. Do not restore grid
without checking the real WebKit regression (Chromium alone did not catch this).

```bash
xvfb-run -a /usr/bin/python3 tests/smoke_webkit_metric_layout.py
```

An optional UI-directory argument exercises an extracted package. Synthetic
known/unknown/compacting cases sample opening/reopening frames and check both
natural row height and aligned track bottoms; no owner data or monitor is used.
The probe forces GTK's X11 backend so Xvfb, rather than an inherited Wayland
session, owns its window and animation frames.

### History workspace

History uses the shared wide island and typography, with search, bounded record
cards and pagination left, and the selected record right. Both columns reserve
scrollbar space. The detail shows selection origin, status and chosen-model tags,
then recorded elapsed decision/turn time, available last-call input/output tokens
and connection retries. Absent/invalid measurements stay absent; zero usage remains
zero, and cumulative thread totals never fill last-call gaps. Incidents and later
retry/explicit-model request signals appear directly, without interpreting them as
proof of result quality. Generic engine reason/continuity prose and the inferred
historical pipeline are omitted. Current task controls belong in Agents.

Ratings retain their native payloads in a collapsed disclosure. Each aspect has
an icon and three equal-width choices: coral for insufficient, mint for adequate,
and lilac for excessive. Selected choices use a solid fill, dark check/text and
`aria-pressed`; the aspect header has an accessible clear action. The record
column shrinks proportionally below its 260px maximum so narrow two-column views
keep the full rating labels and checks legible. Keyboard and read-only behavior
are retained. One optional
diagnostic disclosure groups confirmed/unconfirmed inference evidence, changed
accepted/published settings, recorded phase changes/failures, telemetry samples,
selector comparisons/failures and valid Standard-equivalent estimates. Identical
settings and successful applied-engine repetition are suppressed. Estimates are
explicitly not billed cost or subscription consumption; observed metrics are not
turn totals. Inference is labeled confirmed only with confirmed attribution.
Disclosure state, selection, scroll and search focus survive updates. Read-only
changes rerender controls immediately. Below 620px columns stack with bounded
record-list scrolling.
History retains the secondary-view height control and lazy journal projection.
Home no longer displays the redundant old-history hint.

Validate with `node tests/test_monitor_history.cjs` (included in `test:layout`).

### History performance and projection contract

`MonitorState` keeps the complete journals for actions and analysis, and folds
normal primary-journal appends into `HistoryProjection`. Rotation, truncation,
delete/recovery changes rebuild in the original primary-then-recovered order.
Revision payloads use the existing `history` channel with one
`monitor_decision_snapshot` envelope per decision. The JS core accepts both these
snapshots and legacy raw events; all three hosts retain their revision protocol.
Tests compare incremental snapshots with the legacy JS result at batch boundaries.
Projection fields, evidence levels, last-call versus cumulative usage and quality
writes must retain their semantics. Do not silently drop historical decisions.

The web UI projects each delivered journal revision once and applies detached live
overlays. Context/quota changes do not rebuild History; search text is cached by
record. Closed disclosure bodies are created on first opening and stay subject to
read-only controls. Test with `tests/test_monitor_history_projection.py`, the core,
History and lazy-history browser groups. The transport change is monitor-only.
