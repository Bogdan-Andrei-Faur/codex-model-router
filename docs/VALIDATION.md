# Validation and integration notes

## Estado actual — 0.3.1, 25/09/2026

Chats laterales: [alcance, pruebas y activación](SIDE-CHATS.md). Suite local:
124 pruebas Python (121 superadas, tres omisiones de plataforma), incluidas ocho
regresiones nuevas. La sonda nativa sin inferencia no permite bifurcar una
conversación vacía; queda pendiente la validación real en Desktop tras reinicio.

## Base de la auditoría — 0.3.0, 24/09/2026

La referencia actual es [AUDIT-REMEDIATION.md](AUDIT-REMEDIATION.md): cubre G01–G20,
activación, contratos persistentes, límites de evidencia, claves por proveedor,
ZIP probado y comandos reproducibles. Las secciones antiguas de este documento
son evidencia histórica; sus cifras, reglas y límites no describen 0.3.0.
`Siempre` ya no recorta a 20.000 eventos. Las fases se extraen de acciones y no
se confirma inferencia por mera coincidencia de modelo. Falta validación nativa
Mac; esta entrega no reinicia Desktop ni publica cambios en GitHub.


## Pending-work follow-up correction — 0.2.4, 2026-09-24

- Reproduced in `Agatha Vision`: Jev selected Luna/low for a continuation after
  the agent had identified remaining points. The previous summary saw tests but
  did not classify the outstanding work, leaving no route floor.
- The response summary now recognizes pending points, remaining work, next steps
  and multi-service integrations. It derives a normal, complex or critical floor
  from safe labels. The local fallback and JEV candidates both enforce it, even
  when the last selected model was Luna.
- 93 tests pass with 3 platform skips, including direct and block message items,
  no persistence of response text, planned continuation and rejection of a
  Luna/low JEV proposal for pending complex work.

## Previous-response context — 0.2.3, 2026-09-24

- Completed assistant items are classified into ephemeral booleans: plan,
  implementation pending, tests, deployment and risk. Brief confirmations use
  that summary instead of relying on their few words alone.
- The summary is not written to history and response text is not sent to JEV.
- Handles direct text fields and text blocks. The 91-test suite covers planned
  `Adelante`, ordinary continuation, lightweight acknowledgement and privacy.

## JEV continuity and effort correction — 0.2.2, 2026-09-24

- Regression reproduced: a result confirmation inherited Astra/Max from the
  previous turn. JEV returned `continue`; the bridge forced the previous pair,
  and an ambiguous local classification also excluded Luna/Terra candidates.
- Continuity now describes the task; the selected pair is applied independently.
  Quality floors come from actual workload signals or instructions to resume
  known work, never from the visual identity/title or ambiguous fallback tier.
  Whole-message acknowledgements and bounded counter/status checks admit only
  Luna/Terra at low/medium; mixed messages and attachments do not get this cap.
  Max requires high risk plus exceptional scope, or failure after xhigh/max.
  A normal work continuation may retain capacity but does not inherit Max.
- `python -m unittest discover -s tests`: 89 tests, 86 passed and 3 POSIX skips.
  Includes changed effort during continuation, expensive malformed proposals,
  rate-limit fallback, attachments, complex work, explicit/manual selections,
  privacy-safe history and minimums independent of an inherited audit identity.
- `python tests/smoke_jev.py --live` used synthetic requests with configured
  Vercel JEV (`vmc/jev`), not Codex inference or user tasks. Observed choices:

  | Synthetic case, starting from Astra/Max unless stated | Selection | Strategy |
  | --- | --- | --- |
  | Result confirmation | Luna / low | reassess |
  | Read telemetry counters | Luna / low | reassess |
  | Proceed with agreed implementation | Astra / high | continue |
  | Unspecified question | Luna / low | reassess |
  | Exhaustive high-risk audit, no previous route | Astra / xhigh | reassess |
  | Failed attempt after Astra/xhigh | Astra / max | continue |

- The audit received one HTTP 429 during the initial sequence; one targeted
  repeat with `--live --case high_risk` succeeded. These are individual classifier
  observations, not measured output quality or a general accuracy benchmark.
  No prompts, raw responses or credentials were persisted in production history.
- Windows build and WPF self-test passed. Generated the local standalone ZIP
  `Codex-automatico-0.2.2-windows.zip`; checked its version and eight files, with
  no history or keys. This is a local package, not a signed/published installer.
- Already-running Desktop still uses its loaded policy until the user restarts
  it. Native macOS validation remains a MacBook task. Automatic phase switching
  remains disabled; permissions and active turns are untouched.

## Desktop telemetry correction — 0.2.1, 2026-09-24

- Reproduced on Desktop 26.917.9434.0 / backend 0.155.0-alpha.16.4:
  root OTel overrides appear in native `config/read` until an override is added
  after `app-server`. Desktop supplies a bundled-MCP override there; the native
  CLI then discards the entire root override list, including OTel. Two completed
  production turns and an open loopback listener had produced zero requests.
- Append OTel in the subcommand list. Carry over existing root overrides only
  when there was no subcommand override list, preserving native effective config.
  No persisted Codex settings, permissions, prompt logging or application files
  are changed. The earlier analytics-flag hypothesis did not fix this defect.
- `python tests/smoke_telemetry.py` passed all three argument layouts against the
  installed backend. It verifies the effective endpoint, prompt redaction and
  unrelated tool restrictions through `config/read`, and receives real native
  telemetry without any model request.
- `python tests/smoke_telemetry.py --layout desktop --live` passed with one small
  ephemeral Luna/Low response. The production receiver parsed completed-response
  events before process shutdown. It stores only the existing safe allowlist.
- These are isolated native checks. The already-running Desktop retains 0.2.0
  until a user-controlled restart; that follow-up remains a separate validation.
  Native macOS compilation/runtime validation still requires the MacBook.
- Statistics invalidation includes telemetry counters in both renderers, so a
  received batch refreshes without waiting for a task/history change. WPF checks
  this with an unchanged empty history and a changing receiver count. All 80
  Python tests (77 passed, 3 POSIX skips), 9 JS tests and the native monitor
  self-test pass. The zero-event state and v0.2.1 footer were visually inspected.

## Windows phase UI correction — 2026-09-24

- Added the missing WPF phase pipeline, history provenance and evidence counters.
  The web assets previously changed are used by macOS, not the Windows monitor.
- Native v21 builds alongside the running v20. Native review checks exercise
  Activity, History and Statistics with phase fixtures and unknown inference.
  Rendered `review-phase-activity.png` and `review-phase-history.png` were inspected.
- Python regression covers delayed picker notifications after turn start and
  completion: neither changes lifecycle state nor claims an observed inference.
  Started/completed pipeline state is persisted for history replay.
- Added opt-in loopback inference telemetry. Unit tests submit an OTel payload
  containing private prompt/resource fields and verify that only model, effort
  and completed-event kind reach the router. A matching single active task is
  confirmed; ambiguous concurrent tasks remain unattributed. Automatic model
  switching remains disabled.
- After replacement, v21 remained running and its `--render` path consumed the
  current status snapshots: the actual featured task rendered as active with
  the pipeline visible. This is an in-process native render, not a desktop screenshot.
- Publishing the stable launcher was blocked because it is in use by Desktop.
  It was preserved. Only the owned v20 monitor process was stopped; v21 was
  launched, and the stopped legacy monitor path received the same v21 binary
  (matching SHA-256), so the still-running old launcher remains compatible.
  No backend or Desktop process was stopped. A later build when Desktop is
  closed can replace the stable launcher normally.

## macOS visual fidelity follow-up — 2026-09-22

The owner identified visual omissions after functional acceptance. Compared
`MonitorWpf.cs`, `MonitorAnalytics.cs` and `MonitorAgents.cs` against all four
Mac pages, capsule and avatar detail. Functional acceptance alone had not
established complete visual parity.

| Area | Restored on macOS |
| --- | --- |
| Explanation cards | Original 3-point left rail: lilac `#C7BBFF` for model, green `#93D2AD` for effort; matching headings, `Panel2` background, 13-point medium-weight ink text, original padding and 16-point corners. Other explanation cards use a neutral rail. |
| Expand/collapse | Matching SVG chevrons mirrored horizontally, with identical dimensions, stroke and rounded caps. The compact action retains its original icon. |
| Badges and header | 12-point badge text, original padding, model/effort tooltips and 40/36/36-point header control columns. |
| History | Compact title/date with badges on the right, 16-point detail title, original detail height, rating heading and separate clear action; telemetry grouped in explanation cards. |
| Statistics | Effort-specific bar colors, neutral engine colors, original vertical density and rated-decision count. |
| Avatars | Transparent-to-model-color orbit gradient, original 8-point effort dot with 1-point outline, 34-point overflow control and 420 ms width/fade/slide transitions. |
| Avatar detail | Colored category above title, original spacing and bottom divider, height measured from its contents. |
| Settings and shell | Original policy-row sizing and text size, original shell shadow opacity; existing palette, rounded controls, scrollbars and anchored shell preserved. |

Verified JavaScript syntax, all seven existing monitor-core test groups, native
build and actual AppKit/WebKit screenshots in an isolated eight-task preview:
capsule/overflow, avatar detail, activity, history cards/list, statistics,
settings policy rows and clicking the corrected collapse button. The original
Windows runtime was not available for a fresh screenshot comparison; font
rasterization and the native menu remain platform-specific. No routing code
or provider choices changed in this follow-up.

## macOS visual/functional port and real launch correction — 2026-09-22

- The owner's actual Desktop launch used `-c value app-server` and the first Mac
  detector silently passed through to the native engine. It now consumes known
  global options before finding the subcommand, without matching a user prompt
  containing `app-server`. Alternative transports remain untouched.
- Native smoke now uses the actual global-option arrangement and requires a
  fresh `bridge_started` snapshot for its own bridge PID. Handshake/catalog/account
  success alone is no longer enough. This strengthened smoke passed, as did
  the read-only background inventory test with global `-c` arguments.
- Replaced the basic AppKit text panel with a borderless native AppKit/WebKit
  monitor using local bundle assets only. Surface dimensions, 26-point corners,
  model/effort palettes, 44-point avatars, category glyphs, 5+N overflow and
  420 ms transitions derive from the current Windows implementation. Native
  window envelope is fixed; transparent unused space passes clicks through.
- Implemented capsule peek, stable surviving-agent order, all four views,
  persisted/removable ratings, recovered-history merge, applied-engine metrics,
  comparisons and provider settings. Task/telemetry strings use DOM text nodes.
  UI preferences persist separately from routing configuration. Metadata I/O is
  off the main queue and unchanged data is not resent to the web surface.
- Added Keychain storage for explicitly entered classifier keys and a scoped,
  timeout-bounded Python reader. No real credentials were entered, migrated or
  read for validation. Keychain lookup tests use mocks; first-use OS authorization
  and real external classifier calls remain untested.
- `python3 -m unittest discover -s tests -q`: 57 passing tests.
  `node --test tests/test_monitor_core.cjs`: 7 passing groups covering history
  replay, clearing ratings without changing chronology, pending settings/live
  usage, applied versus comparison engines, stable agents, category identities
  and badge contrast.
- Native compilation targeting macOS 12+ on Apple Silicon passed. Inspected
  actual native capsule/panel screenshots with eight isolated synthetic agents.
  Verified five avatars plus `+3`, opened an agent's attached detail, opened the
  panel via `+3`, and checked the shared anchor, palette, activity rows and
  scrolling overflow visually. The fixture is explicitly labelled as simulated.
- After unlocking the Mac, verified Activity → History navigation, adequate
  rating write and removal with journal readback, and rating/statistics survival
  across a native monitor restart. Retention and topmost preferences also
  survived restart. Verified pause/resume, conditional provider controls,
  restored fixture settings, and Escape returning to the compact capsule.
  All mutations used an isolated synthetic preview; no real provider was called.
  Returned the installed monitor to the real workspace afterward.
- Reduced-motion CSS is implemented but the OS preference was not changed
  during validation. Code tests and these interactions do not prove compositor
  smoothness on every display. Do not claim pixel-for-pixel Windows equality:
  macOS uses its system font, menu bar and system menu.
- Final real integration passed after a full launch through Codex automático.
  The observed process chain was ChatGPT PID 62125 → router PID 62549 → native
  engine PID 62559, with the actual global `-c value app-server` arguments.
  This user turn produced `bridge_started`, `routed`, `native_settings` and
  `turn_accepted` events for the same decision, followed by usage telemetry.
  The native monitor simultaneously showed the real task as Sol / Medio,
  working and accepted by Codex. This validates activation for the installed
  Apple Silicon Desktop build without making an artificial test inference.

The following section describes the earlier baseline, not the final monitor.

## macOS port — 2026-09-22

- Built the native AppKit monitor on Apple Silicon with Swift, targeting macOS
  12+. The installer found `/Applications/ChatGPT.app/Contents/Resources/codex`.
  Intel hardware and older macOS releases were not exercised.
- All 55 Python unit tests pass with the system Python 3.9.6. New regressions
  cover POSIX executable discovery, paths/arguments with spaces and quotes,
  stdio transport selection, atomic configuration updates, refusing to relaunch
  an open Desktop, unchanged protocol bytes and backend cleanup on SIGTERM.
- The SIGTERM regression initially exposed Python aborting during interpreter
  shutdown while a daemon held buffered stdin. POSIX input now uses interruptible
  descriptor reads, and the worker is joined during shutdown. The test passes.
- `python3 tests/smoke_native.py` passed native version, initialize handshake,
  model catalog, ChatGPT account-type check and clean shutdown. The installed
  catalog includes the four configured routes and their configured effort levels.
- `python3 tests/smoke_inventory.py` passed background pagination, task-title
  synchronization, retained conversation and isolation of private replies.
  Neither native check requested inference or changed conversations.
- Inspected the actual monitor window through the native accessibility tree and
  a window screenshot: labels and controls are legible. Clicked pause, verified
  the paused settings, resumed, and verified History/Statistics empty states.
  Configuration was restored to enabled local rules. AppKit bitmap exports do
  not accurately capture all composited control materials on this macOS release;
  the actual window screenshot was used for visual acceptance.
- Generated local launcher and monitor bundles in ignored `dist/`. The existing
  Desktop was left running. Loading the bridge through the launcher and observing
  a real accepted user turn remain pending until the owner closes current work.
- This is a functional Mac baseline, not WPF feature parity: animated capsule,
  review ratings, recovered Windows history and advanced provider settings are
  not implemented in the Mac monitor. DPAPI secrets are not migrated.

See [macOS setup and limitations](MACOS.md). Historical Windows evidence follows;
the Windows UI build was not rerun on this Mac.

Date: 2026-09-21. Personal project; no Grimaldi implementation or Moontech task.

## Integration evidence

- Desktop package observed: `OpenAI.Codex_26.915.4065.0_x64__2p2nqsd0c76g0`.
- Desktop's original engine: `codex-cli 0.155.0-alpha.9.2`.
- npm CLI is a different installation/version (`0.155.1`) and is not the backend.
- Read-only inspection of the installed app's `app.asar` found
  `CODEX_CLI_PATH` in `main-LM8MUIFp.js` and `src-C3YaUE83.js`. The latter's
  `HQ`, `CQ`, `wQ` and `_Q` functions resolve and launch an override using stdio.
  No installed app files were patched or redistributed.
- The original engine was probed using its actual JSONL transport. `initialize`,
  `model/list`, `account/read`, `thread/start` and `thread/settings/update` worked.
  Account type was `chatgpt`; no auth token or API key was read by this project.
- Native `thread/settings/updated` reports configured model and reasoning.
  The bridge requests this update after the original `turn/start` ACK, preserving
  the turn's already-applied mode and permissions. The request's own ACK is hidden;
  native notifications pass through. No model is called for settings updates.
- The desktop deliberately drops `CODEX_WINDOWS_SANDBOX_PACKAGE_FAMILY` for an
  override. The bridge restores the originally observed package family solely
  for its unchanged, original installed engine. No sandbox policy, permissions,
  approval policy, tool definition or user instruction is rewritten.
- Windows launch uses a small .NET Framework WinExe shim and Python 3.14 stdlib.
  A Windows Job object terminates bridge descendants if the shim is killed.

## Scope of transformation

For eligible new `turn/start` requests, only `model`, `effort`, and the corresponding
two `collaborationMode.settings` fields are rewritten. Input arrays, attachments,
unknown future fields, workspace, instructions, permissions and identifiers are
preserved. A native settings-update request publishes configuration to the app;
it does not guarantee the composer picker visually follows that configuration.

Unknown models/providers, missing catalogs, malformed policy files and unsupported
input are passed through. Active-turn steering, server requests, tool results,
interrupts and unrelated RPC methods are passed through. No retries, prompt
blocking/replay, transcript edits, new persistent tasks or platform-API proxy exist.

The router uses an in-memory provider/model catalog and tier per loaded thread.
Reopened conversations infer the previous tier from the resumed model. Short
continuations keep the tier; an explicitly new task can be reassessed.

## Reproducible checks

Run from the project root in PowerShell:

```powershell
.\build.ps1
& C:\Python314\python.exe -m unittest discover -s tests -v
& C:\Python314\python.exe tests\smoke_native.py
```

The default smoke reads the version, model catalog and account type without asking
a model to generate a response. The optional test below makes three small model
turns against the existing subscription and therefore consumes quota:

```powershell
& C:\Python314\python.exe tests\smoke_native.py --live
```

The live test uses a separate ephemeral session, a read-only sandbox and one
harmless dynamic echo tool. MCP servers are disabled in that test session. It
checks an answer, remembered context, a tool request/result, native model settings
and clean bridge shutdown. Test outputs are in ignored `state/` files; no real
conversation text is stored by the router.

Policy/protocol tests cover ES/EN task examples, critical production examples,
follow-ups, escalation, explicit model selection, attachment/permission integrity,
unknown providers/models, disabled/broken configuration, immediate pause, active
and pending turns, server request-id direction, display synchronization and log
privacy. These tests validate policy behavior, not model-quality optimality.

## Remaining acceptance checks

1. **Passed 2026-09-21 08:26 UTC:** Desktop launched through the automatic shortcut.
   Observed process chain: Desktop -> codex-router.exe (23248) -> Python (16308)
   -> original Codex engine (22228). A real message in the existing user task
   produced a routed event followed by a native settings confirmation. It kept
   Astra/high because the short message continued a resumed Astra conversation.
2. **Routing passed in v1:** the user's explicit topic change to translating
   "hola" produced Luna/medium and native confirmation in the existing task.
   **Picker not confirmed:** the user's screenshot still shows Astra/Muy alto.
3. Check a real attachment and the Desktop's permission controls.
4. Pause routing; verify the selected model is honored. Resume routing.
5. Compare quality and actual subscription usage over representative real tasks.

The integration has passed the live Desktop connection and cheaper-route checks;
the native picker and checks 3–5 remain outside the demonstrated acceptance.
No claim is made about attachment/permission UI. Automatic routing of
remote hosts, engine-internal scheduled runs, subagents, non-OpenAI providers and
new model names is outside this version's scope. Future Desktop updates can change
the observed executable override or protocol; the normal app launcher remains
the recovery path. Core and desktop paths are pinned locally and are not committed.

## V2 upgrade evidence

- `dist/codex-router-v2.exe` and `dist/codex-monitor-v2.exe` compiled successfully.
  The running v1 executable and Desktop process were not stopped or replaced.
  Desktop shortcuts now target v2; a complete close and automatic reopening of
  Codex is required to load the new Python code into the Desktop connection.
- 22 policy/protocol tests passed. New checks cover UI/UX and general audits,
  independent effort selection, all six explicit levels, non-directive Ultra
  mentions, Luna/Ultra fallback, accepted versus rejected settings, later
  configuration changes, paused-turn observation and subagent metadata privacy.
- A separate native live smoke through the exact v2 executable passed on
  2026-09-21: real Luna answer, preserved conversation number, one dynamic tool
  request/result, native model-setting notification and clean process shutdown.
  It used an ephemeral session, not an existing user task. No agent was delegated.
- The installed native model catalog confirms low/medium/high/xhigh/max for Luna,
  with ultra additionally available on Terra, Sol and Astra. The ignored
  `state/catalog.json` stores a timestamped catalog snapshot for the panel.
- The monitor reads only local router snapshots. It refreshes every two seconds,
  checks Python process liveness plus a heartbeat for v2, handles legacy v1,
  distinguishes pending/accepted/requested evidence and retains the accepted
  turn's model independently of configuration for subsequent turns.
- Local metadata now includes task names, parent identifiers, status and optional
  token counters. No prompt, tool arguments, model output or credentials are copied.
  Titles themselves may be sensitive; all runtime files remain ignored by Git.
- Visual checks used the monitor's own WinForms `DrawToBitmap` rendering, without
  reading the desktop. Full activity, policy, reasoning and compact views were
  inspected. Notification-area and always-on-top controls are implemented.

Remaining V2 acceptance: load it through the Desktop shortcut after ongoing work
ends, observe real task names/states during a user turn, exercise the user's tray
and topmost workflow, and compare routing quality on representative real work.
The live native smoke proves integration below the Desktop UI; it does not prove
that the running Desktop has already reloaded v2. No claim of measured quota
savings or comparative model quality is made.

## V3 monitor evidence

- The diagnostic WinForms window was replaced by one frameless WPF surface with
  three exclusive states: hidden, compact and expanded. Compact is anchored to
  the bottom-right working area; expanded is aligned to the right edge. Both use
  the same icon, surface, task hierarchy and state reader.
- The system-tray icon remains available in every state. Its menu selects compact,
  expanded or hidden, pauses/resumes routing, controls topmost behavior and exits
  the monitor. A left click cycles hidden → compact → expanded → compact.
- The compact surface opens the expanded panel. The panel's chevron returns to
  compact and its close button hides the surface. The selected state and topmost
  preference are saved in ignored local runtime state.
- `--render` generated and visually inspected `state/wpf-compact.png` and
  `state/wpf-expanded.png`. The build uses local .NET Framework references and
  adds no installed runtime, package or browser engine.
- Snapshot process validation rejects reused Windows PIDs by comparing process
  start time with the state-file timestamp. This avoids counting an unrelated
  process against old routing telemetry.

## V4 UI/UX review — 2026-09-21

- The local accepted-turn snapshot identifies this review as `gpt-6-astra` with
  `xhigh` effort. This is native turn-acceptance evidence, not internal inference telemetry.
- Both surfaces share a bottom-right working-area anchor and the same width.
  The shadow is rendered behind the opaque content, not over the text tree.
  Segoe UI, display text metrics, grayscale smoothing and larger body/metadata
  sizes replace the previous thin, partially transparent presentation.
- Model and reasoning badges have distinct, restrained palettes, explicit labels,
  and a common 100-DIP column in activity rows. All six reasoning levels remain
  readable. Known model/effort badge combinations exceed 4.5:1 text contrast.
- A styled WPF context menu replaces the unstyled WinForms tray menu. View
  selection has a visible check mark. Topmost has an explicit Activado/Desactivado
  label, an accessible state and a tested click handler that toggles the window.
- Activity no longer silently stops at seven secondary tasks. A dark scrollbar
  exposes the full observed list. Unchanged lists are retained between refreshes.
- Pending turns show requested settings and pending evidence instead of the
  previous turn's accepted settings. Hide/reveal cancels stale size animations.
  Display/work-area changes reposition the surface.

Validation commands:

```
.\build.ps1 -BuildOnly
.\dist\codex-monitor-v4.exe --self-test
<configured-python> tests\smoke_native.py
```

Seven local UI regression groups passed: bounds/anchor across five work areas,
badge fit/alignment/contrast, overflow scrolling, pending-turn evidence,
interrupted view transitions, tray/topmost actions and indicators, empty state.
The check runner writes `state/ui-review-checks.txt` and generates synthetic
preview images only; it does not alter routing configuration or saved UI state.
The native smoke passed version, handshake, catalog and ChatGPT account checks,
then exited cleanly. No model inference or quota-consuming smoke was needed.

The monitor's own renders were visually inspected for the panel, capsule,
both topmost menu states, scroll overflow and empty state. Exports at 100%,
125%, 150% and 200% exercise raster export sizes; they do not substitute for
testing physical monitors with different DPI settings. Tray placement/focus and
perceived sharpness on the user's display remain user-experience acceptance items.

Text-rendering reference: [Microsoft WPF rendering guidance](https://learn.microsoft.com/en-us/dotnet/api/system.windows.media.renderoptions.cleartypehint?view=netframework-4.8.1).

Activation: only the previous v3 monitor was stopped after verifying its full
executable path. The v4 monitor started successfully and remained responsive;
one monitor process was present afterward. The existing Compact/topmost=true
preferences were preserved, desktop shortcuts were verified against v4, and
the final live-state panel render was inspected. Codex and its running tasks
were not restarted.

## V5 interaction polish — 2026-09-21

- Featured model and reasoning badges now have an explicit 24-DIP height, so
  glyph metrics cannot produce visibly mismatched pills.
- Compact/expanded geometry uses a 420 ms cubic ease-in-out transition. The
  Windows reduced-motion preference still disables this animation.
- Active rows use a filled status core plus a restrained expanding/fading halo.
  The same activity pulse appears beside the active count in both monitor modes.
  Idle rows remain static and hollow; reduced-motion keeps the active core but
  suppresses its pulse.
- Activity indicators now own a 24-DIP column, leaving approximately 12 DIPs
  between the visible core and the task text. Singular header grammar is
  `1 tarea activa`; plural counts retain `tareas activas`.
- UI review checks confirm equal featured-badge height, active versus idle
  animation state, indicator spacing, transition duration and all previous v4
  layout, contrast, scrolling, evidence and tray behaviors. Native read-only
  handshake/catalog/account smoke also passed and exited cleanly.

## V6 decision history and analytics — 2026-09-21

- An append-only local `state/history.jsonl` records privacy-safe decision
  lifecycle events. Each decision has a random correlation id and separate model
  and reasoning explanations. Accepted, completed, rejected, interrupted and
  backend-error events retain status, duration and available token counters.
- No prompt, response, attachment, tool argument, command, path, authentication
  value or error message is persisted. Errors retain only a bounded type/code.
  A sentinel test proves user content is absent from the history file.
- Explicit model changes and follow-ups such as `sigue fallando` produce structured
  override/retry signals. Completion alone is not treated as proof of quality.
- Retention defaults to 90 days and can be changed locally to 30, 90, 180 days or
  unlimited. Compaction retains at most the latest 20,000 events when the file
  exceeds 5 MB. Runtime history and configuration remain Git-ignored.
- The expanded monitor provides exclusive Activity, History, Statistics and
  Settings tabs. Activity rows open their matching history details. History keeps
  reasons available after completion; Statistics summarizes model/effort mix,
  non-Astra choices, errors, retries, durations and observed tokens; Settings
  controls routing, topmost state and retention.
- 25 routing/protocol tests pass. Native monitor review renders and validates all
  four tabs in addition to the previous geometry, contrast, scrolling, pending,
  animation and tray checks.

The history begins when Codex loads the v7 router on its next full launch. The v7
monitor can display current live rows immediately, including legacy rows with an
explicit note when their separate reasoning explanation was not previously stored.

## V8: anchored animation and honest live statistics — 2026-09-21

- Confirmed the live legacy bridge had 14 task snapshots but 22 accepted sends,
  no decision IDs and no history.jsonl. The previous "Decisiones observadas"
  label incorrectly counted tasks. The monitor now separates session sends,
  persisted decisions and partial task snapshots, with explicit coverage and
  two-second polling time. Legacy bridges require a full Codex relaunch to load
  the new recorder; no live agent or Codex process was restarted.
- Analytics invalidation includes token changes and session counters. Usage is
  persisted while work continues, not only on completion; new decisions clear
  stale tokens. Tokens are labeled as the last observed call, not turn totals.
- History hover has the same rounded padding as Activity. The capsule chevron
  is a vector centered on the same vertical axis as the active count.
- The native transparent window stays at a fixed envelope. Its bottom-aligned
  visual surface animates upward/downward; no native position/size animation.
- 26 Python tests pass. Native review samples render frames in both directions
  and verifies lower-edge/native-window drift below 1.1 DIP; it also checks
  repeated decisions on one task, live usage without timestamp changes, legacy
  coverage, history hover, arrow alignment and the existing navigation checks.
- Native layout/frame tests and rendered previews do not measure desktop
  compositor latency under every GPU/load combination.

## V9: persistence across sessions and legacy recovery — 2026-09-21

- Verified the running v8 bridge after the user's full relaunch: new decisions,
  acknowledgements and usage were already written to history.jsonl. Resumed
  threads without new turns falsely triggered the legacy/relaunch warning.
- History and statistics now derive from persisted decision IDs only. Resumed
  tasks stay in Activity; accepted counts and model/effort breakdowns accumulate
  across sessions. Live rows enrich existing historical decisions without
  creating synthetic records. Removed the misleading restart/partial warning.
- Recovered exactly 22 accepted sends from the previously verified user bridge
  snapshot into history.recovered.jsonl. Native live history is untouched;
  deterministic IDs make reruns idempotent (second run added zero). Missing
  effort explanations, tokens and exact outcomes are not invented.
- At validation, the rendered live monitor showed 24 decisions/accepted sends:
  22 recovered and two native decisions after restart. The data paths resolve
  from the installed router, not the chat's project or working directory.
- 29 Python tests pass. Native review verifies persistence with no connected
  task rows, accepted counts after reloading, recovery merge without duplication,
  and no false restart warning for resumed tasks; all existing UI checks pass.
- Only the monitor is replaced. The running recorder already supports persistence,
  so this fix requires no further Codex restart. Personal journals stay Git-ignored.

## V11: native agent-first capsule — 2026-09-21

- Added MonitorAgents.cs: circular task-category glyphs, existing model palette,
  rotating arcs, stable active ordering and at most five visible avatars plus
  an overflow action. No classifier/API call or routing change is involved.
- Replaced the compact logo/featured-model block with active avatars and count.
  Attached hover/focus/click details show the observed title, model, effort and
  state without entering the expanded panel. A 220 ms leave delay permits
  moving into the detail; Escape closes it.
- Compact visual width is 326 DIP; the transparent native envelope stays fixed.
  Width, height and peek motion retain a shared bottom-right anchor. Motion
  honors Windows animation settings; hidden/expanded modes stop orbit clocks.
- Native UI review verifies stable ordering across refreshed rows, task glyphs,
  active orbit, hover details and edge stability, moving toward the detail,
  reactivation during exit, model/effort refresh, 5+N overflow, idle cleanup and
  stopping hidden animations. Existing persistence/navigation checks pass.
- Rendered capsule, attached detail, overflow and idle fixtures were inspected.
  Native compositor performance under every GPU/load and DPI combination is
  not established by these local layout tests.
- Only the monitor is replaced; currently running Codex tasks are unaffected.

## V12: outer circular orbit and rounded components — 2026-09-21

- Fixed the orbit's rotation center: the former partial path bounding box was
  not concentric with the avatar. A fixed 44-DIP layer rotates explicitly around
  (22,22), with a radius-20 arc outside the radius-16 face and a faint full track.
- Restored the vertical separator before the capsule expand action. Rounded
  model/effort tags, buttons/tabs, Activity/History cards, explanation cards and
  the tray menu; preserved tag heights and existing information.
- Native review samples points on the rendered arc over twelve rotation angles
  to verify constant radius relative to the face and positive external clearance.
  Existing anchor, hover, reactivation, overflow and persistence checks pass.
- Inspected rendered capsule, attached detail, History and tray-menu previews.

## V13: shared avatars and reasoning indicators — 2026-09-21

- Activity rows and the highlighted task use the capsule's avatar component,
  task glyphs and model palette. Active orbits share a time-based phase across
  refreshed rows; idle agents retain their identity without a rotating sweep.
- Restored the Codex logo on the left, centered agents and right-hand expand
  action with separator. Compact visual width is now 366 DIP. The logo uses
  the original 1024-square listing image at 40 DIP with high-quality scaling;
  source provenance is documented in assets/README.md.
- The lower-right dot uses the existing reasoning tag palette independently
  of activity; unknown reasoning is neutral. Native review checks all six levels
  and unknown, including effort-only changes without a model/status change.
- Existing native review covers fixed anchors, overflow, Activity navigation,
  hover, animation lifecycle, persistent statistics and history.

## V14: durable agent identity classification — 2026-09-21

- The router classifies an agent at message submission using title, message,
  attachment presence and the routing explanation. It records only the category
  and confidence, never the message, attachment content, tool data or output.
- Categories cover interfaces, corrections, tests, audits, architecture, text,
  research, configuration, automation and a neutral fallback. A specific title
  outweighs a short follow-up; ambiguous continuations retain the prior category.
- Safe identity metadata reloads from the local decision journal after a restart.
  Child agents inherit their coordinator's category until they receive their own
  routed instruction. Native review checks every stored category reaches a
  distinct catalog identity; Python tests verify privacy and restart behavior.

## Activity catalog reconciliation — 2026-09-22

- Activity and capsule snapshots reconcile observed threads with a complete,
  paginated, non-archived `thread/list` catalog every approximately 15 seconds.
  The catalog uses state metadata only; previews and transcript content are not
  retained. Renames, archive/delete notifications, and unarchive are handled.
- A partial page, timeout, malformed response, or API error never replaces the
  last successful catalog. Late responses cannot undo lifecycle notifications.
  Newly observed tasks and working ephemeral agents survive an in-flight scan.
- Filtering changes monitor snapshots only. Routing context and persistent
  decision journals remain intact. It does not populate Activity with all old
  stored conversations or promise visibility of unobserved tasks/other hosts.
- `python -m unittest discover -s tests -v`: 49 passing tests, including seven
  reconciliation regressions for pagination/failure, lifecycle changes, privacy,
  ephemeral agents, and unchanged history.
- `python tests/smoke_inventory.py`: passed against the installed app-server;
  automatic polling, title synchronization, existing-task retention, and private
  reply isolation were checked without inference or conversation mutations.
- `python tests/smoke_native.py`: native handshake, model catalog, ChatGPT
  account and clean shutdown passed. No UI binaries changed; the Python bridge
  update loads on the next full launch through Codex automático. The currently
  running desktop connection was not restarted as part of validation.

### Desktop lifecycle and ephemeral-thread correction

- A real Desktop run exposed two different records beside a new persisted task:
  an ephemeral title helper that completed and an ephemeral root with no turn.
  Neither represented a user conversation. The persisted root retained its real
  title and routing decision.
- Catalog reconciliation now becomes ready after the successful `initialize`
  response. It still accepts the later `initialized` notification, but no longer
  depends on observing it. This matches the authoritative server handshake and
  fixes live snapshots that remained permanently unsynchronized.
- Ephemeral roots without a parent are excluded from monitor snapshots and their
  `turn/start` bytes are preserved unchanged. They create no routing decision and
  keep Codex's native model/effort. Ephemeral collaboration agents remain visible
  only while working and once linked to a parent task.
- `python -m unittest discover -s tests -v`: 50 passing tests. The added protocol
  regression proves an internal ephemeral root is neither rerouted nor persisted
  as a decision. Inventory regressions cover hidden roots and visible active children.
- `python tests/smoke_inventory.py`: passed against the installed app-server with
  the `initialized` acknowledgement deliberately unobserved. Background catalog
  synchronization still completed and private responses remained isolated.
- `python tests/smoke_native.py`: native handshake, model catalog, ChatGPT account
  and clean shutdown passed. No inference request was made by either smoke test.

## References and provenance

This implementation is original. No upstream router source code was copied.

- [Official App Server documentation](https://learn.chatgpt.com/docs/app-server)
- [Official hook contract](https://learn.chatgpt.com/docs/hooks): submit hooks can
  block/add context but have no documented model-override output.
- [Codex Adaptive Model Router](https://github.com/hadongil19822-blip/codex-adaptive-model-router):
  reference for local classification and native subscription goals. Its inspected
  implementation blocks/resumes via CLI; its Windows pipe-selector approach and
  language patterns were unsuitable for this installation.
- [Codex Smart Router](https://github.com/giovannimirarchi420/codex-smart-router):
  reference for routing before `turn/start` and handling collaboration-mode model
  overrides. This project does not use its classifier or separate TUI.
