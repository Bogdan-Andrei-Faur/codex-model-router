# Validation and integration notes

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
