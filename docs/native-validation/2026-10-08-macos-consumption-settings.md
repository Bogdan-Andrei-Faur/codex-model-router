# macOS Consumption and Settings alignment — 2026-10-08

## Identities and scope

- Source: dirty `main` on `38d3678e451ce14f525e6f4784c96f379097830a`;
  inherited camera/editor/wardrobe work preserved. No commit or push.
- Product `0.9.6`, policy `8`; installed monitor `ca01f55f5cdab9d4`;
  unchanged router `80e86c3d7accf253`.
- Installed build and every bundled shared UI file match source. Exactly one
  owned monitor runs. Configuration is byte-identical; prior artifacts are
  privately backed up under ignored `state/`.
- Only the owned monitor restarted. Desktop and agent tasks were not restarted.
  Read-only bridge metadata reports one connection, mismatch/unknown=false,
  restartRequired=false and desktopRestartPending=false.

## Delivered behavior

Consumption shows available quota, valid measured tokens, coverage and selected
model distribution first. Scope details and technical diagnostics are collapsed;
diagnostics offer Routing, Telemetry, Quality and Recorded usage as flat rows.
Missing/invalid samples are excluded and coverage remains explicit. Tokens are
not a quota or billed-cost estimate; selected models are not inference proof.
Telemetry status distinguishes historical counts from current receipt status.

Settings keeps routing pause visible and groups controls into Application,
Routing, Data/privacy and Connection. Version sits in the heading; updater and
task icon catalogue remain in Application. Existing privacy, telemetry, routing,
quality, credential custody, connection and installation actions are preserved.
Section state, disclosures and unsaved credential drafts survive refresh and
section changes. A reproduced read-only transition issue was fixed so controls
also reflect the new access state without discarding drafts.

Both views fit their content instead of inheriting a tall empty island. Shared
typography, rounded controls, subtle dividers and colored model pills remain.

## Verification and limitations

- `ROUTER_TEST_BROWSER=chromium npm run test:layout`: all thirteen browser
  groups PASS, including existing camera, editor, update, interaction and bridge
  checks adapted to grouped navigation.
- New `tests/test_monitor_preferences.cjs` PASS: invalid sample exclusion,
  measurement coverage, evidence limits, collapsed diagnostics, refresh state,
  credential draft isolation, unchanged action payloads, read-only controls and
  layouts at 320/390/620/800px.
- Synthetic Consumption/Settings screenshots visually inspected; no private
  records used. JavaScript syntax and whitespace checks PASS.
- Native Mac monitor compilation and installed readback PASS.
- `python3 tests/probe_mac_glass.py` currently FAILS at phase 0: the isolated
  WebKit document is ready and its DOM surface exists, but the first scheduled
  bounds report is absent (`reported=null`, native hit height=0). No JavaScript
  error is recorded. Repeating with the previous installed UI produces the same
  failure. Old observer targets and temporary fixture elevation did not resolve
  it; the cause remains unknown. Safe fixture geometry diagnostics were added.
  Earlier native PASS receipts remain historical evidence for their artifacts.

Remaining: recover isolated native bounds delivery, then record actual owner Mac
view/input acceptance. Shared browser proof and Mac compilation do not validate
Windows/Linux native execution. Rich activity animations remain separate work.
