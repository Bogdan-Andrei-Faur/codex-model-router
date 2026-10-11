# Ubuntu native hover smoke timing — 2026-10-11

## Original failure and reproduction

Documentation-only main `489afb48be2b280554047dcbae1691e060e1309c`,
[run38170935448](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/38170935448),
attempt1 failed the first agent-peek closure assertion in native Ubuntu job
`114563211929`; the other seven hover assertions passed. The failed-job rerun
passed at unchanged source. That rerun established intermittency, not a repair.

The original failure was reproduced against that committed source in an
unprivileged Ubuntu24.04 arm64 container with GTK/WebKit2 (WebKit2.52), Xvfb
and a newly built DEB. A temporary synthetic-only trace observed a stale inside
pointer projection after opening the peek, then the first outside projection
about805ms after opening. The old assertion used a fixed500ms timer, before the
outside projection plus the application's220ms close timer could complete.

Further isolated traces showed queued native evaluations and JavaScript timers
arriving after busy startup frames. Comparing elapsed time in a polling
microtask can also fail before an already-due close timer gets dispatched.
No trace demonstrated a broken product close handler; no product delay or
native pointer behavior was changed.

## Repair and verification

`tests/fixtures/native_hover_probe.js` observes actual native projections,
first establishes outside delivery, then opens the agent detail, quota and
island without synthesizing DOM leave. Each stage requires a new outside
projection and the real automatic closure. All eight original assertions remain.
Scheduled deadlines distinguish missing delivery (5s) from missing closure
(1s after observing delivery); the native host retains its independent25s
wall-clock deadline. Repeated outside samples do not extend a stage deadline.
Diagnostics contain only synthetic stage names, booleans and relative timings.
The probe neither injects native exits nor retries a failed scenario.

Local verification:

- Four consecutive complete native DEB/GTK/WebKit smoke runs PASS, each using
  a fresh isolated Xvfb session and temporary data. These are repeated checks,
  not retry-until-success logic.
- The same probe in Chromium PASS with delayed outside delivery. Negative
  controls correctly reject a disabled close handler and missing outside
  delivery. This regression is included in `npm run test:layout`.
- All17 browser test groups PASS; the final deadline implementation also passed
  its targeted regression. Python syntax and diff checks PASS.

These checks establish fixture correctness and native package behavior under
Xvfb. They do not certify physical Ubuntu input, Wayland, owner acceptance or a
wall-clock UI latency guarantee. No installed app, release bytes, user data,
Desktop process or live telemetry service changed. Private traces remain outside
version control. GitHub CI for the repair must be checked at its published SHA;
the earlier successful rerun is not that evidence.
