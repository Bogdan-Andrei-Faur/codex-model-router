# Rigid companion animations and GIF catalogue — macOS — 2026-10-09

## Scope and installed identity

- Owner requested revision of all26previews, rigid rounded rectangular body and
  components, meaningful actions, distinct prop/signal colors and compact containment.
- Local main on `c82e1ea`; inherited Consumption width,48pt capsule and receipts
  preserved. No commit/push, release or provider call.
- Source-backed Mac product0.9.6 monitor `e20402820c674648`, expected router
  `5aa7726ffeba863f`. All installed shared assets including scenes.js and build
  stamp match source. Config bytes preserved; UI preferences match after settling.
- Private ignored backup retained. Only owned monitor relaunched; Desktop untouched.
  Safe readback: one monitor/connection; mismatch=false, unknown=false.

## Artwork and previews

- Body/parts use rigid translation/rotation only. Removed static mint/lilac
  deformation and all animation scale/skew. Eyes blink by alternating opacity
  between open eyes and fixed eyelid paths; body silhouette remains78×65units.
- Original props live in scenes.js; bundled Lucide1.51.0 supplies lock, question,
  retry, warning, check and wrench symbols.39original icons verified against the
  pinned package integrity. Device/paper/tool colors are independent of body color.
-26GIFs, HTML/Markdown gallery, manifest and contact sheet regenerated from
  production UI. All26have multiple encoded frames; fallback loops now animate.
  Loop4s; terminal/entry/exit previews2.4s with a900ms one-shot entrance/exit.
- GIF metadata/source hashes/frame counts/dimensions/durations PASS; combined GIF
  size1,611,348bytes. Contact sheet and selected frames inspected; physical owner
  visual acceptance is separate. Rendering uses isolated Pillow11.3.0 on Python3.9.
- Capsule scene fits its38×40px target in the48px bar. Slower exit uses an absolute
  clamped ghost, preserving body shape and keeping controls outside the camera.

## Verification

-33JS core tests PASS; all15browser groups PASS across the run and focused reruns.
- New rigidity/containment check covers576pose/color/time samples; preserved
 78×65body geometry, unit transforms and scene bounds.
- Native isolated AppKit/WebKit18-state animation/reduced-motion fixture PASS.
-3Python read-only preview-adapter tests PASS. Preview serves the new scenes.js.
- Existing appearance/draft/acknowledgement, attention/action boundaries, capsule
  interaction and camera/flat/narrow/clock exclusion checks PASS.
- An initial native fixture assertion expected the old HTML approval badge;
  updated it to inspect the actual SVG status symbol. First preview adapter run
  exposed a missing scenes.js allowlist entry; fixed and rerun PASS.
- First camera run exposed longer leaving avatars pushing the crew across the
  cutout; fixed with rigid out-of-flow fading and rerun PASS. Failures were not
  hidden by lowering geometry checks.

## Acceptance boundary

This closes implementation, regenerated synthetic catalogue and local installation.
Owner review of the26visuals remains open. Natural Desktop event coverage,
physical display/input checks, other-host native acceptance and the previously
recorded unrelated glass bounds fixture remain separate. Artwork does not change
backend classification, permission handling or inference identity evidence.
