# Per-agent companion editor and observed activity — proposal, 2026-10-08

Status: the per-agent editor, richer activity projection and animations are now
implemented; the installed Mac monitor awaits owner-controlled bridge activation
for the new observer. See the [current activity contract](COMPANION-ACTIVITY.md).
The original research and candidate table below retain their historical scope. The owner
requested independent agent customization using the supplied rounded rectangle
character as the reference, plus animations driven by actual Desktop signals.
Coucou is the owner's inspiration; no Coucou assets or implementation were used.
Existing uncommitted camera/navigation work must be preserved.

## Editor contract and remaining options

Entry: Agents → selected agent → Personalize character. Use one inline editor
with the upper-left portrait as its only live preview. Do not add a main
navigation destination. Saved identity belongs to the stable agent/thread ID,
not its title, model, current task category or current ordering. A model change
must not change the character. Keep model/effort tags visually independent.

- Fixed rounded rectangular body, with a bounded corner-radius adjustment.
- Curated body/accessory palette: coral, mint, lilac, sky, honey, rose, sage,
  slate and cream; no free-form color picker. Optional compact alias field
  without renaming the actual chat. Existing stored colors are preserved until edited.
- Implemented: eye style plus five compatible slots: clothing, head, glasses,
  neck and detail. The [wardrobe catalogue](COMPANION-WARDROBE.md) documents
  all25 pieces and the shared artwork. Six thumbnail categories keep it compact.
- Appearance remains stable across every pose. Expressions and limbs animate;
  accessories follow attachment points. Tiny capsule rendering may simplify
  detail but must preserve identity. Product action/status icons remain Lucide.
- Implemented: live draft preview, Save, Cancel and restore default (saved explicitly).
  Copying appearance to another agent remains a future option.
- State audition is explicitly simulated and never changes a real agent's state.
  Respect reduced motion; use short attention gestures, no sound by default.

Implemented storage: version 1 `state/agent-appearances.json`, with an `agents` map
keyed by stable local thread ID;
allowlisted IDs/colors/ranges, no arbitrary SVG/HTML or executable imports.
Default remains the current deterministic companion if no override exists.
Persistence uses the shared monitor state/service with an atomic write and file lock.
All three hosts forward the same appearance action and correlated acknowledgement.
A failed or busy save retains the draft. Preview/read-only modes reject mutation;
malformed stored data cannot be silently overwritten by a save.
Cross-device synchronization and alias inheritance for subagents are not assumed.
The conversation prototype retains only local proposal choices, not app settings.

## Evidence and current gaps

Inspected local `codex-cli 0.162.0-alpha.2`. Generated its own protocol schema via
`app-server generate-json-schema --experimental` in ignored scratch state.
No turn/inference was started and no private transcript was read. Schema
presence proves availability in this binary, not actual delivery by every model,
Desktop workflow, connection or experimental capability. Native acceptance of
each new projection is still required.

The [official App Server reference](https://learn.chatgpt.com/docs/app-server)
documents item lifecycles, runtime flags, streaming events and server requests.
Local schema is authoritative for version differences: this binary calls the
collaboration item `collabAgentToolCall`, while the fetched reference describes
`collabToolCall`. Do not hardcode only one spelling across supported versions.

Current `monitor-ui/core.js` selects three deterministic color/name variants
in `companion()` and eight coarse states in `companionState()` (including unknown).
The editor now applies per-agent appearance overrides on every shared surface.
`router.py` consumes turn lifecycle,
native plan updates, command lifecycle and errors, and passes compaction into
`usage_state.py`. Its `thread/status/changed` branch retains `status.type` but
discards `activeFlags`; there is no dedicated pending-request projection for
approvals/questions. Command tracking currently supports cancellation, not a
complete visual activity feed. Generic active state does not prove reasoning.

## Candidate signals and animations

The schema-backed rows below are candidates to add; existing coarse mapping is
identified separately. Metadata alone suffices; do not collect reasoning text,
prompts, command arguments, file paths, tool output or question content for this.

| Presentation | Signal | Current monitor | Proposed gesture |
| --- | --- | --- | --- |
| Preparing | Local pending turn until accepted/started | Folded into working | Lean forward briefly |
| Working, activity unspecified | Active thread/turn with no more specific evidence | Working | Gentle breathing |
| Thinking | `reasoning` item or its summary/text event envelope | No specific projection | Look upward, small head tilt |
| Writing | `agentMessage` lifecycle/deltas | Completed message context only | Small typing motion |
| Planning | `plan` item or current `turn/plan/updated` | Pipeline only | Count steps with hand |
| Executing command | `commandExecution` lifecycle | Cancellation tracking only | Tap hands rhythmically |
| Editing files | `fileChange` lifecycle | No specific projection | Short drawing gesture |
| Searching web | `webSearch` lifecycle | No specific projection | Look left/right |
| Using connector/tool | `mcpToolCall` / `dynamicToolCall` lifecycle | No general projection | Work gesture with activity label |
| Collaborating | Local `collabAgentToolCall` lifecycle | Partial child routing metadata | Wave toward smaller companion |
| Looking at image | `imageView` lifecycle | No specific projection | Lean closer |
| Generating image | `imageGeneration` item in local schema | No specific projection | Drawing gesture; capability-dependent |
| Reviewing | `enteredReviewMode` / `exitedReviewMode` | No specific projection | Narrow eyes, nod |
| Compacting | `contextCompaction` lifecycle; legacy notification fallback | Explicit tracking exists | Compress then settle |
| Needs permission | `waitingOnApproval`; command/file/permissions request envelopes | Flags discarded | Raised hand + lock indicator |
| Has a question | `waitingOnUserInput`; `item/tool/requestUserInput` | Flags discarded | Raised hand + question indicator |
| Connector needs input | `mcpServer/elicitation/request` | No specific projection | Same attention pose with connector label |
| Retrying | Matching current-turn `error` with `willRetry=true` | Journal incident, no visual state | Recover balance, brief retry indicator |
| Failed | Terminal failed/error for current turn | Error | Brief flinch, concerned expression |
| Interrupted | Turn interrupted | Falls into unknown presentation | Stop movement, neutral expression |
| Turn finished | `turn/completed` with completed status | Done | One brief happy bounce, then rest |
| Resting | Idle/catalog-only with no live activity | Idle | Relaxed eyelids |
| Disconnected / stale | Lost bridge freshness/connection | Coarse offline | Muted colors, no claim agent stopped |
| Unknown | Missing, unsupported or conflicting evidence | Unknown | Neutral pose, explicit label |

These are activity distinctions, not 24 mutually exclusive permanent animations.
Use a small shared set of expressive poses plus activity labels and Lucide badges.
Do not infer testing from an arbitrary shell command, thinking from elapsed time,
success from an assistant sentence, or a question from punctuation in message text.
`notLoaded` is not a crashed agent. Completed turn is not validated task success.

## State projection contract

Keep connection, turn lifecycle, current activity and pending human requests as
separate fields. An asynchronous question can coexist with continuing work: show
the attention badge while retaining the activity pose unless a blocking wait is
explicitly observed. Permission controls remain in Desktop; the monitor must
never auto-approve or synthesize responses. Custom asynchronous question tools
need an explicit host signal/mapping; a tool name alone does not establish that
a prompt remains pending. A generic input request used by an app approval should
show neutral attention unless trusted metadata distinguishes its purpose.

Track sets keyed by thread/turn/item/request and session epoch, not a single last
event. Ignore late events from older turns. Resolve requests using the matching
client response or `serverRequest/resolved`; cancellation/turn completion clears
only the corresponding scope. Keep concurrent items until each completes.
On reconnect use explicit status snapshots; absent evidence becomes unknown,
not an invented continuation. Never allow a stale overlay to hide a fresh turn.

Priority for the primary pose: terminal failure/interruption for the current
turn, explicit blocking human wait, confirmed compaction, observed active item,
generic active, brief completed pose, idle. Connectivity overlays confidence;
nonblocking questions are badges. Coalesce rapid changes; keep low-frequency
poses stable and stop animations while hidden/reduced-motion. Preserve original
protocol messages, permissions, approval transport and cancellation behavior.

## Proposed implementation sequence

1. Completed locally: owner-selected Agents entry, shared per-agent appearance
   storage, draft/cancel and consistent capsule/expanded rendering. Mac installed;
   physical owner acceptance and Windows/Linux native editor validation remain open.
2. Add a metadata-only event reducer plus projector for reasoning/writing/tools,
   questions/approvals, cancellation and reconnect. Preserve parallel requests.
3. Bind a small animation set; add activity variants only when distinguishable
   in a roughly 40-point capsule. Keep alert symbols independent from body color.
4. Fixture replay: concurrent items, out-of-order completion, pending async input,
   automatic request resolution, retry versus failure, stale callbacks, reconnect,
   reduced motion and multiple independent appearance records.
5. Native acceptance per platform and real Desktop event presence. Existing
   protocol schemas and browser fixtures cannot close those gates.

The initial research delivered a simulated editor. The subsequent owner-approved
implementation installs customization from Agents → Personalizar. It adds no new
live activity projection or animation states. No Desktop restart, paid API call,
commit or push was performed.

## Proposal validation

The interactive conversation prototype was opened in Chromium using Playwright.
Checked independent agent appearance, returning to a draft, accessory changes,
state audition and local proposal saving, plus 320/736-point layout overflow.
A rendered screenshot was inspected and the console reported no warnings/errors.
Those initial checks validate the simulated editor only. The production editor
now additionally passes five persistence tests, twelve browser groups and a real
isolated AppKit/WebKit → Python service → disk → acknowledgement fixture.
See the [editor receipt](native-validation/2026-10-08-macos-agent-editor.md).
Event reduction and shared poses are now implemented and fixture-verified.
Real Desktop delivery remains pending after owner-controlled bridge activation;
see the [activity receipt](native-validation/2026-10-08-macos-companion-activity.md).
