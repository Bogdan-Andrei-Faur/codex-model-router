# macOS companion activity implementation — 2026-10-08

## Source, artifact and activation

- Dirty `main` on `38d3678e451ce14f525e6f4784c96f379097830a`, product `0.9.6`,
  policy `8`. Inherited camera/editor/preferences work preserved; no commit/push.
- Installed monitor `4891f87b980d518e`, expected router `281078dcf3e49517`.
  Source identities and all bundled shared UI assets match the installed bundle.
- One owned monitor was replaced/relaunched, with a private ignored backup.
  Configuration bytes are unchanged. Desktop and agent tasks were not restarted.
- Fresh readback: one monitor and one ordinary connection; loaded router remains
  `80e86c3d7accf253`, so bridgeBuildMismatch=true is expected. Unknown=false;
  restartRequired=false and desktopRestartPending=false are the raw marker values,
  **not proof that the new observer is loaded**. Settings shows “router anterior”.

## Delivered behavior

The [activity contract](../COMPANION-ACTIVITY.md) maps native item/turn lifecycle,
delta envelopes, wait flags, human-request resolution, retries and terminal errors
into shared labels/poses. Questions and approvals remain in Desktop. Nonblocking
input retains active work with a badge. Concurrent items and requests resolve
independently; stale turn/completed-item events cannot restore an old pose.
Snapshot/reconnect evidence is separate from current-turn activity.

Animations preserve independent wardrobe/color identity, use small shared gestures,
respect reduced motion and pause while hidden. Terminal gestures do not repeat
on every poll. Lucide lock/message icons were added from the existing pinned,
SHA-512-verified `lucide-static` 1.51.0 package; no generated UI icon artwork.

## Checks

- Full Python discovery: **538 tests PASS, 53 skipped** for optional/platform
  prerequisites. Fourteen reducer/bridge replay tests additionally pass after the
  final thread-start snapshot-status assertion. Skips do not close native gates.
- JS core: **33 PASS**. Shared browser suite: **14 groups PASS**. Camera and
  new activity groups rerun after final hand-pose styling and PASS.
- Routing corpus **27/27**, six offline JEV cases PASS; no paid provider call.
- New activity replay covers overlapping items, nonblocking/parallel input,
  numeric/string request IDs, wait flags, retries, interruption, completed-item
  deltas, previous turns, reconnection, review, plan completion, bounded overflow,
  safe metadata and unmodified request/response transport.
- New browser group verifies poses/labels, consistent wardrobe, attention,
  pipeline waits, reduced/hidden motion and no approval/answer actions.
- `python3 tests/probe_mac_activity.py`: real isolated AppKit/WebKit PASS for
  **18 pose styles**, attention badges and reduced motion. Inputs are synthetic;
  this does not prove real Desktop delivery or physical animation/input acceptance.
- Synthetic [pose board](../design/companion-activity-poses.png) inspected in
  Chromium using Playwright. No owner records or transcripts used.
- Native monitor compilation, installed readback and whitespace checks PASS.

## Remaining acceptance

Owner-controlled Desktop restart, then verify the expected loaded router and
naturally occurring activity envelopes with metadata-only inspection. Record
reasoning, response/approval waits and request cleanup independently; not every
model or workflow delivers every supported event. Do not treat schema/fixture
support as observed Desktop support.

Windows/Linux native animation acceptance and owner physical Mac interaction
remain separate. The previously recorded isolated glass bounds-callback failure
is unresolved; the new pose-style fixture does not close that unrelated gate.
