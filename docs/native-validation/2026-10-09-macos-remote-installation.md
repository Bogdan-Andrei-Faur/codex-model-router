# macOS remote update installation — 2026-10-09

## Identity and scope

- Owner requested remote acquisition and installation. Clean main advanced by
  fast-forward from `a4af030` to `c82e1eab9f572bb36f7bb29859b52a03d84afe84`.
- Source-backed Mac installation, product `0.9.6`, policy `8`.
- Installed/source monitor `0e4670784e5b2672`, expected router `5aa7726ffeba863f`.
- Native AppKit/WebKit compilation and all bundled shared UI byte comparisons PASS.
- Previous bundles, launcher, config and UI preferences backed up privately outside Git.
  Configuration bytes and semantic UI preferences preserved exactly.
- Exactly one owned monitor relaunched. Desktop and owner agent tasks not restarted.
  No source commit/push, release/tag or standalone package migration performed.

## Safe installed readback

- One live ordinary connection; loaded router `80e86c3d7accf253`.
- `bridgeBuildMismatch=true`, `bridgeBuildUnknown=false`.
- Raw `restartRequired=false`, `desktopRestartPending=false`; these markers do
  not prove activation. Owner-controlled Desktop restart remains necessary.
- Remote changes include distinctive companion gestures/props and a synthetic
  26-entry GIF catalogue, plus Ubuntu-specific system clock/top-edge support.

## Verification and limits

- JS core: 33 tests PASS.
- Shared browser suite: all 14 groups PASS (Chromium), including camera, activity,
  editor, consumption/settings and layout regressions.
- `python3 tests/probe_mac_activity.py`: isolated native WebKit 18-pose styles,
  attention and reduced motion PASS; synthetic inputs, no owner data modified.
- No paid provider calls or CI success claims. No full Python rerun: this delivery
  changes shared UI/Linux host; prior source-layout tests remain revision-scoped.
- Natural Desktop state delivery, current gesture visual acceptance, physical
  display/input/sleep checks and the earlier glass bounds fixture remain open.

## Next step

Owner closes/reopens Desktop at a convenient time, then verify expected loaded
router and a healthy connection using safe metadata before accepting real-state
animations. Installation alone does not prove subsequent inference identity.
