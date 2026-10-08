# Mac per-agent character editor — 2026-10-08

## Scope and artifact

Local uncommitted work on `main` at `38d3678`; product `0.9.6`.
Initial editor monitor `ad91e913cfd118a4`; current refined editor monitor
`aaab03edac60a8d5`, router `80e86c3d7accf253`.
Inherited camera/navigation work was preserved. No commit, push or new CI claim.

Agents → Personalizar opens an inline editor for the selected character. It
supports alias, body/accessory colors, bounded roundness, oval/round eyes,
cap/antenna, glasses and scarf. The upper-left portrait is the only live preview. Save waits
for a correlated native acknowledgement; failure retains the draft. Cancel
discards changes; restoring the default requires Save. Shared appearances are
keyed by stable local agent ID, independent of chat title and model.

`state/agent-appearances.json` is private runtime state, never committed.
Writes use the shared Python service, validation, locking and atomic replacement.
All three hosts forward the same action and acknowledgement. Routing config,
history and mode actions remain separate. Preview/read-only cannot save.

## Verified

- 31 JS core tests; all twelve Chromium layout groups, including draft polling,
  independent identities, model/title changes, failed/retried saves, stale
  acknowledgement, cancel/reset, and 320/390/600/800-point editor layout.
- Five Python persistence tests: restart, independent agents, malformed values,
  corrupt/newer storage, preview/read-only guards and concurrent writers.
- Nine existing monitor Python tests; Python compilation and diff whitespace.
- Existing isolated real AppKit/WebKit glass/camera lifecycle fixture.
- New `python3 tests/probe_mac_appearance.py`: real WebKit → AppKit → private
  Python IPC → isolated disk → correlated UI acknowledgement, exit 0. Synthetic
  agent only; no owner appearance data or Desktop/provider activity.
- Browser screenshot inspected with synthetic data. No page exception; a
  favicon-only 404 belongs to the temporary static preview server.
- Mac setup compiled successfully. Installed build ID and all bundled shared UI
  files match source. Exactly one owned monitor runs; only this monitor restarted.
  Configuration stayed byte-identical. Previous artifact/config privately backed
  up in ignored local state. Desktop and active agents were not restarted.
- Read-only ordinary bridge metadata: one connection; mismatch/unknown,
  restartRequired and desktopRestartPending all false. No inference claim.

## Remaining boundaries

Owner visual/input acceptance is separate from automated fixture proof.
Windows WebView2 action forwarding is implemented but native compilation and
execution were not run on this Mac (dotnet unavailable). Linux forwarding passes
Python compilation; GTK native editor execution remains untested here.
Physical camera/menu, external displays and sleep acceptance remain open as
recorded in the camera receipt.

The richer metadata-only activity reducer and new thinking/writing/question/tool
animations remain proposed in `docs/COMPANION-EDITOR-PROPOSAL.md`. This editor uses
the existing coarse animation states; it does not infer new Desktop activity.

## Owner layout refinement

Personalizar is right-aligned beside the state. The alias input is capped at
220px. Free-form native color inputs are replaced by nine named, solid-fill
swatches for body and accessories: coral, mint, lilac, sky, honey, rose, sage,
slate and cream. Legacy saved colors are not rewritten automatically. The lower
capsule preview was removed; the selected upper-left character previews drafts.

On this refinement the editor browser regression passed (320/390/600/800px),
including palette selection/live portrait/save payload, no unrestricted picker,
compact alias, failed save/retry, stale acknowledgement, cancel and restore.
The rendered 800px synthetic screenshot was inspected. The isolated native Mac
save/ack fixture passed again. Earlier full-suite results above belong to the
initial editor; this cosmetic iteration reran the affected checks only.
Mac rebuilt and only the monitor restarted: installed ID and UI files match,
one monitor/connection, config byte-identical, router unchanged and all four
mismatch/restart flags false. No Desktop restart, commit or push.

## Wardrobe catalogue extension

Current installed monitor `a0a5ea7bcfe28228` supersedes the initial/refined editor
artifacts above. Router remains `80e86c3d7accf253`. Six compact categories expose
25 pieces using the same authored vector art in thumbnails, portrait and capsule.
The owner-requested explanatory chat/model paragraph is removed. See the
[wardrobe contract and gallery](../COMPANION-WARDROBE.md).

Canonical clothing/glasses/head/neck/detail enums preserve legacy boolean
accessories by normalization on read; old owner files are not rewritten during
installation. Unknown styles reject saves.32 JS tests, six persistence tests,
nine monitor Python tests, the native glass fixture and native wardrobe
save/ack fixture PASS. All twelve browser groups passed across the initial run
and targeted reruns: the initial loopback preview group failed because its
asset allowlist lacked `characters.js`; adding the new asset fixed that failure.
Windows' asset route was updated too. Final editor checks include each catalogue
choice, independent identities, draft/failure/reset and320/390/600/800px layouts.
The full catalogue and six combinations at large/capsule size were visually
inspected using synthetic data only.

Mac setup PASS; source build and every installed UI asset match. Exactly one
monitor/ordinary connection, unchanged configuration, mismatch/unknown and both
restart flags false. Only the owned monitor restarted; Desktop/agent work stayed
active. Physical owner acceptance and Windows/Linux native execution remain open.
No new rich activity reducer, provider request, commit or push.
