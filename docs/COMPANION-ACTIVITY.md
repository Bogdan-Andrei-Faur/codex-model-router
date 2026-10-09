# Observed companion activity

Implementation: `src/codex_model_router/bridge/companion_activity.py` observes the existing native bridge;
`monitor-ui/core.js` projects labels and `monitor.js`/`monitor.css` render poses.
The [App Server reference](https://learn.chatgpt.com/docs/app-server) and installed
CLI schema supply the event vocabulary. Actual Desktop delivery is a separate gate.

| Observed metadata | Presentation |
| --- | --- |
| Local turn submission | Preparing |
| Active thread/turn, unspecified activity | Working; never inferred thinking |
| `reasoning` lifecycle/delta envelope | Thinking, hand at the chin, upward gaze and thought bubbles |
| `agentMessage` lifecycle/delta envelope | Writing at a keyboard, alternating hands and downward gaze |
| Active `plan` item/plan step | Planning with a clipboard and focused pose |
| `commandExecution`, `fileChange` | Executing at a terminal with stepping feet; editing with a moving pencil |
| `webSearch` | Searching through binoculars, sweeping from side to side |
| `mcpToolCall`, `dynamicToolCall` | Using a moving wrench |
| `collabAgentToolCall` or `collabToolCall` | Collaborating, broad raised-hand wave |
| `imageView`, `imageGeneration` | Inspecting with a magnifying glass; creating with a brush and sparkle |
| Review mode entry/exit items | Reviewing a checklist with a deliberate nod |
| `contextCompaction` lifecycle | Compacting, stacked sheets and pronounced compression |
| Approval request or `waitingOnApproval` | Raised hand and Lucide lock badge |
| User-input request/elicitation or `waitingOnUserInput` | Two-hand shrug and Lucide message badge; neutral “waiting for your response” |
| Current-turn error with `willRetry=true` | Retrying with a curved arrow and recovery movement; distinct from terminal failure |
| Failure/interruption/completion | Concerned expression and exclamation / pause bars / raised arms, check and one happy bounce |
| Idle / absent evidence / lost connection | Resting / unknown / muted last reading |

## Projection invariants

- Store allowlisted enums, bounded identifiers and timestamps only. No reasoning,
  questions, answers, command arguments, file paths or output enter this observer.
  It does not add activity journal records or change existing capture settings.
- Track concurrent items and typed request IDs separately. Item completion clears
  only that item; matching client replies or `serverRequest/resolved` clear only
  that request. Numeric and string request IDs are distinct.
- A request explicitly marked `isBlocking=false` adds attention while work keeps
  its pose. Native wait flags are authoritative blocking evidence; a reply does
  not clear a still-observed flag until a new status snapshot clears it.
- A generic tool input can represent an app approval. Its content is never
  inspected to classify purpose, so input uses a neutral response label. A custom
  asynchronous tool name alone is not a signal that a question remains pending.
- Reject mismatched turn events, completed-item replay/deltas and observed older
  turn starts. Current completion/interruption clears items, requests and flags.
  Thread-status flags have no turn ID in the protocol and apply in transport order.
- Each bridge instance is a new epoch. Read/resume snapshots clear old item/request
  identities; only explicit in-progress snapshot items recover a specific pose.
  A thread-only snapshot cannot borrow a stale row's turn identity.
- Memory is bounded (1,024 threads, 256 item/completion identities per turn,
  64 pending requests and 128 retired turn identities per thread). Item overflow
  produces unknown activity, rather than inventing work. These are display state
  bounds; native RPC transport is never filtered by this observer.
- The same character, clothes and colors render in every pose. Attention badges
  supplement accessible text. No sounds or color changes signal model selection.
  Terminal completion says “Turno terminado”, not independently verified success.
- Specific activities use different silhouettes, props and movement, including in
  the 38px capsule. Props change only with the pose or appearance; hands render
  in front of clothes. Reduced motion retains those static visual differences.
- Body, hand and prop animations use a common monotonic phase across polling;
  terminal gestures do not replay on every poll. Reduced-motion preferences disable animations; hidden pages and
  a hidden document pause them. A blocking wait pauses the live pipeline.

The monitor never answers questions, approves permissions, retries commands,
starts inference or changes routing through an animation. Native requests and
responses pass through unchanged. Astra boundaries and approval authority remain.

## Verification and activation

See the [Mac receipt](native-validation/2026-10-08-macos-companion-activity.md).
The synthetic [pose board](design/companion-activity-poses.png) uses production
artwork/styles; it does not assert real Desktop event delivery.
The [numbered GIF catalogue](design/companion-animations/README.md) and
[visual gallery](design/companion-animations/index.html) capture each activity,
entry/exit transition and static fallback at portrait and capsule sizes.
Regenerate all previews or an individual activity with
`node tools/render_companion_gifs.cjs [activity-key]`; timings come from production
CSS and the catalogue records source hashes. Synthetic previews do not change
the active monitor or establish native event delivery.
The Mac receipt records its own pending bridge activation; it is not a statement
about other hosts. Ubuntu has a matching installed/loaded bridge and observed
current-scope native activity. See its [gesture receipt](native-validation/2026-10-09-linux-companion-gestures.md)
for the current UI artifact and acceptance boundaries. No event retention or
classification changed: short events can remain brief, and unspecified activity
continues to use the generic Working pose. Do not interrupt active tasks merely
to validate animation.
