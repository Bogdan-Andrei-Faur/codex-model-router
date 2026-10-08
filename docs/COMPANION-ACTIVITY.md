# Observed companion activity

Implementation: `src/codex_model_router/bridge/companion_activity.py` observes the existing native bridge;
`monitor-ui/core.js` projects labels and `monitor.js`/`monitor.css` render poses.
The [App Server reference](https://learn.chatgpt.com/docs/app-server) and installed
CLI schema supply the event vocabulary. Actual Desktop delivery is a separate gate.

| Observed metadata | Presentation |
| --- | --- |
| Local turn submission | Preparing |
| Active thread/turn, unspecified activity | Working; never inferred thinking |
| `reasoning` lifecycle/delta envelope | Thinking, upward gaze and gentle tilt |
| `agentMessage` lifecycle/delta envelope | Writing, small hand taps |
| Active `plan` item/plan step | Planning |
| `commandExecution`, `fileChange` | Executing, editing; shared work pose |
| `webSearch` | Searching, looking side to side |
| `mcpToolCall`, `dynamicToolCall` | Using a tool |
| `collabAgentToolCall` or `collabToolCall` | Collaborating, brief wave |
| `imageView`, `imageGeneration` | Looking closely, creating |
| Review mode entry/exit items | Reviewing |
| `contextCompaction` lifecycle | Compacting, compress/settle pose |
| Approval request or `waitingOnApproval` | Raised hand and Lucide lock badge |
| User-input request/elicitation or `waitingOnUserInput` | Raised hand and Lucide message badge; neutral “waiting for your response” |
| Current-turn error with `willRetry=true` | Retrying; distinct from terminal failure |
| Failure/interruption/completion | Concerned expression / stop / one short happy bounce |
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
- Infinite poses keep phase across polling; terminal gestures do not replay on
  every poll. Reduced-motion preferences disable animations; hidden pages and
  a hidden document pause them. A blocking wait pauses the live pipeline.

The monitor never answers questions, approves permissions, retries commands,
starts inference or changes routing through an animation. Native requests and
responses pass through unchanged. Astra boundaries and approval authority remain.

## Verification and activation

See the [Mac receipt](native-validation/2026-10-08-macos-companion-activity.md).
The synthetic [pose board](design/companion-activity-poses.png) uses production
artwork/styles; it does not assert real Desktop event delivery.
The local monitor is installed, but Desktop must load the new bridge on its next
owner-controlled restart. Do not interrupt active agent tasks to validate it.
