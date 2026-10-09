# macOS compact capsule height — 2026-10-09

- Owner requested less overlap with application windows. Shared compact height
  reduced from64 to48 CSS pixels (AppKit points), with a40px avatar/crew row and
  quota target,4px vertical padding and24px compact lower corners.
- Camera side wings remain clear; narrow camera fallback retains the safe top
  inset plus48px content. Expanded screens retain their existing height behavior.
- Local main based on `c82e1ea`; inherited Consumption width and documentation
  changes preserved. Installed/source product0.9.6 monitor `d90a78874b17fb92`,
  router `5aa7726ffeba863f`; CSS and build stamp match.
- Private backup retained outside Git; configuration bytes and semantic UI
  preferences unchanged. Only owned monitor relaunched, Desktop untouched.
- Safe readback: one monitor, one connection; mismatch=false, unknown=false.
- Browser camera group PASS for camera exclusion, flat/narrow layouts, Ubuntu
  clock cutout and1x/2x scaling. Usage/layout and interaction groups PASS,
  covering compact controls, hover/peek, quota dismissal and opening.
- Native compilation PASS. Browser fixtures do not establish physical owner
  acceptance; no claim about new natural activity or inference evidence.
- No commit/push or CI claim. Previous receipts remain historical.
