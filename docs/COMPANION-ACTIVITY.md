# Observed companion activity

Implementation: `src/codex_model_router/bridge/companion_activity.py` observes the existing native bridge;
`monitor-ui/core.js` projects labels and `monitor.js`/`monitor.css` render poses.
The [App Server reference](https://learn.chatgpt.com/docs/app-server) and installed
CLI schema supply the event vocabulary. Actual Desktop delivery is a separate gate.

## Visual contract — rigid character revision

The owner requires the same rounded rectangular body in every pose: no squashing,
stretching, skew or animated scale on the body, limbs, face or props. Rigid translation
and rotation are allowed. Blinks swap open eyes and closed eyelid strokes through
opacity; they do not flatten eye shapes. Original mint/lilac body scale overrides
are removed. Depth comes from static highlights and subtle mood gradients.

Artwork stays 2D. `scenes.js` owns original illustrated props; semantic symbols are
original Lucide1.51.0 vectors. Neutral paper/device/tool palettes are independent
of character color. Permission is amber, response blue, retry yellow, error coral
and completion pale mint, each on a dark contrasting badge clear of the body.

| GIF | State / evidence | Visual action |
| --- | --- | --- |
| 01 | Preparing / local submission | Arrange a folder and pencil in a desk tray |
| 02 | Working / active without specific activity | Work at a laptop; no inference of thinking |
| 03 | Thinking / reasoning envelope | Upward gaze and a white thought cloud |
| 04 | Planning / plan item or step | Follow rows on a paper checklist with a finger |
| 05 | Writing / agentMessage | Hands type above a detailed keyboard |
| 06 | Executing / commandExecution | Type on a laptop with terminal lines/cursor |
| 07 | Editing / fileChange | Write in a notebook with a wood pencil |
| 08 | Searching / webSearch | Back-facing character at a laptop with moving search highlight |
| 09 | Tool / MCP or dynamic tool | Silver Lucide wrench and amber screwdriver |
| 10 | Collaborating / collab tool | Exchange notes on a shared board with a small illustrative partner |
| 11 | Inspecting / imageView | Move a silver magnifier with a contrasting blue lens |
| 12 | Generating / imageGeneration | Brush a picture on a small easel |
| 13 | Reviewing / review mode | Read along a paper and point to the checked line |
| 14 | Compacting / contextCompaction | Sort separate sheets into a stack; body never compresses |
| 15 | Approval / explicit approval wait | Amber lock badge; permission stays in Desktop |
| 16 | Question / explicit user input wait | Blue question symbol; response stays in Desktop |
| 17 | Retrying / willRetry | Yellow circular arrow rotates within its own badge |
| 18 | Error / terminal failure | Concerned face, red warning and subtle forehead tint |
| 19 | Interrupted / interrupted turn | Settled pose, closed eyes and cool forehead tint |
| 20 | Done / completed turn | Modest smile, happy eyes, attached resting hands and separate check |
| 21–22 | Entry / exit | Rigid fade/translation over900ms; no width/scale compression |
| 23 | Idle / no active work | Upright, mild smile and occasional blink |
| 24 | Unknown / insufficient evidence | Neutral gaze and subdued dashes; no user-question badge |
| 25 | Offline / lost connection | Resting with closed eyes and drifting sleep marks |
| 26 | Waiting / legacy generic wait | Folded arms and occasional foot tap |

Idle is the default resting pose; unknown means evidence is insufficient; offline
means the connection is absent. The sleepy drawing does not assert the process is
literally asleep. The small collaboration partner is illustration, not another
observed agent. A question and an approval always need their existing explicit
metadata. No new backend event classification or retention is introduced.

A fixed square-proportion scene viewport reserves room for props above/beside the
body. Capsule buttons remain38×40px inside the48px bar; the artwork is uniformly
fitted within them. Exit avatars leave layout flow, clamp to the safe crew width
and fade for900ms so shrinking the island cannot push them over the camera.

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
  in front of clothes and held objects. Reduced motion retains those static visual differences.
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
entry/exit transition and animated fallback at portrait and capsule sizes.
Regenerate all previews or an individual activity with
`node tools/render_companion_gifs.cjs [activity-key]`; timings come from production
CSS and the catalogue records source hashes, including scenes.js and icons.js.
The renderer also rebuilds the contact sheet using render_companion_board.py. Synthetic previews do not change
the active monitor or establish native event delivery.
The Mac receipt records its own pending bridge activation; it is not a statement
about other hosts. Ubuntu has a matching installed/loaded bridge and observed
current-scope native activity. See its [gesture receipt](native-validation/2026-10-09-linux-companion-gestures.md)
for the current UI artifact and acceptance boundaries. No event retention or
classification changed: short events can remain brief, and unspecified activity
continues to use the generic Working pose. Do not interrupt active tasks merely
to validate animation.
