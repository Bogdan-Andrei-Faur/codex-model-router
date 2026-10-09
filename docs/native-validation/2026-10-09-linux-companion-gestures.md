# Native acceptance receipt — 2026-10-09 — Linux — owner Ubuntu host

## Identity and scope

- Readback recorded: 2026-10-09 06:54 UTC. Python 3.14.4, Node v20.20.0.
- Session: local Ubuntu 26.04.1 x86_64, GNOME/Wayland; monitor uses XWayland.
- Source at installation readback: `fix/companion-activity-gestures`, uncommitted changes on
  `dc317cbe804f491c67a4048df0b47023d0487ff5`. Product `0.9.6`, policy 8.
- Installed artifact: `codex-model-router_0.9.6-2~main20261009.6_all.deb`.
- SHA-256: `b27d599b7963f72938074afc50b74059a685715f2cc1b9cf66e3f20c64a8e626`.
- Installed/active monitor: `752a92efa0d22e29`; installed/loaded router:
  `88a0be134bc26eb9`. One connection; mismatch/unknown/restart flags false.
- Installation used visible Ubuntu privilege authentication and restarted only
  the monitor. Desktop and its bridge remained running. Private rollback backup
  retained; no configuration change, release/tag or new remote publication at
  that observation time. The owner subsequently authorized source/GIF publication;
  see HANDOFF and Git history for its delivery revision.
- Supersedes the installed artifact row of
  [the top-edge receipt](2026-10-09-linux-top-edge.md). That receipt's owner
  acceptance applies to the clock fit, not these new animations.

## Results

| ID | Mode | Status | Action | Observation | Boundary |
| --- | --- | --- | --- | --- | --- |
| CORE-JS | source | PASS | `npm test` | 33 tests | No backend/routing change |
| UI-SHARED-FIXTURES | source | PASS | `npm run test:layout` | All 14 browser groups | Synthetic inputs |
| UI-ACTIVITY | source | PASS | `test_monitor_activity.cjs` | Distinct specific movements/props, stable wardrobe, compact prop/body retention, 38px width, attention, terminal aging, reduced/hidden motion | An old compaction animation-name expectation was updated; the complete rerun passes |
| UI-VISUAL | browser fixture | PASS | Production artwork at 100px and 38px | [Synthetic pose board](../design/companion-activity-poses.png) inspected | Static comparison, not physical owner acceptance |
| UI-NATIVE-FIXTURE | isolated GTK/WebKit | PASS | Exact `.deb`, `GDK_BACKEND=x11 xvfb-run -a dbus-run-session -- /usr/bin/python3 tests/smoke_package_linux.py` | 18 distinct pose styles/props and reduced motion; onboarding, launcher, single instance, bundled font and hover fixtures pass | Xvfb; no owner Desktop events or physical input |
| UI-INSTALLED | installed | PASS | Readback after monitor-only restart | One ready monitor, source UI equals installed UI, no startup traceback | No Desktop restart |
| UI-DATA | installed | PASS | Before/after hashes | Seven protected settings files byte-identical | Private backups/logs excluded from Git |
| ACTIVITY-DELIVERY | installed, read-only | PASS | Current monitor payload | Four native activity rows; three current-turn scoped rows: two Working, one Tool; one matching connection | Point-in-time observation; does not prove every event kind or duration |
| GIF-CATALOGUE | subsequent source fixture | PASS | Production CSS/JS capture and Pillow encode | All26 GIFs validated:22 animated/four static, dimensions480×296, frame counts/durations and source hashes; gallery number/name/accent search and responsive layout; selective regeneration preserves unrelated GIFs | Synthetic artwork; no native activation or physical acceptance |
| UI-INPUT/DISPLAY/SCALE/SLEEP | physical | NOT_RUN | No disruptive checks | Earlier accepted clock fit code unchanged | Owner visual acceptance of new gestures remains open |
| CI / other platforms | remote/native | NOT_RUN | No remote run, Mac/Windows activation or installation | Shared source only | Linux receipt does not close their gates |

## Evidence and remaining work

The former animation reused the same work sway for writing, execution, editing,
tools and image generation; thinking/planning also shared movement. Hands were
mostly behind the face/clothes. Specific activities now have distinct silhouettes,
gestures and props; hands are foregrounded. Monotonic body/hand/prop phases avoid
restarting each poll. Reduced motion retains static pose/prop differences.

The native observer, event priorities, turn scope, routing and activity retention
are unchanged. An unspecified native activity remains Working; no specific action
is invented to add visual variety. Brief events may remain brief.

Owner acceptance is pending: compare the installed capsule and expanded portrait
while actual work changes. Source checks, synthetic visual inspection, native
WebKit styles and real current-scope event presence are separate evidence.
No raw logs, private screenshots, prompts, titles, identifiers or keys are included.
