# Approved application brand — 2026-10-09

The owner approved `router-icon-v1.png` and requested using it as the application
brand. The exact approved pixels are retained as `assets/brand/router-source.png`;
PNG/ICO/ICNS exports and their hashes are documented in
[assets/README.md](../../../assets/README.md). Functional UI icons continue to use
the existing Lucide library.

Generated with the built-in `image_gen` tool, without input images. The concept
is a single routing input splitting into three rounded model destinations,
using mint, warm gold and lilac over graphite. No third-party logo was requested
or supplied. Current source/package/preview consumers use the new brand, including
Mac bundle icon metadata, Windows executable/setup/tray icons, Ubuntu launchers,
Settings and README. The active installation is not replaced by this source
change. No publication, installer activation or trademark clearance is asserted.

## Generation prompt

Use case: logo-brand. Create ONE polished original desktop application icon
proposal for a project called Codex Model Router, a personal multi-agent AI model
routing monitor. This is independent software: do not include or imitate any
OpenAI/ChatGPT/Codex/GitHub brand logo, knot, terminal logo, other existing product
trademark, wordmark, or text. Asset: a square 1024x1024 close-cropped app icon,
centered on a fully opaque deep graphite background, with generous rounded
squircle corners and the icon occupying most of the image, absolutely no
surrounding desktop mockup or extra canvas. Design: a distinctive minimal
geometric routing emblem: a single input point or small rounded capsule at the
bottom, a clean continuous softly rounded route rising to a junction and
branching to three equal rounded square destination nodes across the upper
half. Three model destinations are mint turquoise (#87D8C2), soft warm gold
(#E6C585), and soft lilac (#C4AFE9). The route is ivory with restrained mint
accents. Strong coherent silhouette that reads at 32px, large sturdy lines,
balanced generous negative space, a premium macOS-style material finish with a
very subtle soft top highlight and quiet depth on the rounded tiles, mostly
flat rather than glossy or bevel-heavy. Warm, approachable, compact and refined,
matching a minimalist dark glass UI with rounded agents. No mascot face,
letters, numbers, badges, tiny details, arrows, sparkles, neural brain, black
vignette, fake transparency checkerboard, watermark, text or decorative scenery.
Produce a single finished icon, not a presentation board. Original visual
concept, no trace of the previous third-party app icon.

## Artifact

SHA-256: `ffdf30dd279c1822abcafafa62ea2babb20f13d37b130f7fdf0baa7dbfb06783`.

Owner visual selection is complete. Native installation and physical appearance
on each OS remain separate acceptance gates. Producing a new current icon does
not remove the historical third-party artwork from Git history.

## Integration checks

- Master pixels/hash preserved; PNG256/1024, all seven ICO sizes and ICNS
  directory/size/hash checks pass with the standard-library `--check` command.
- 11 Python source-layout/preview tests pass, including the generated Ubuntu
  payload fixture. Ubuntu package tools are substituted on this Mac; no native
  Linux installation or GNOME appearance is asserted.
- Usage/layout and update-control browser groups pass with the new image routes.
- Real native Mac compilation succeeds in an isolated source snapshot; both
  generated app bundles reference and contain the exact new ICNS. macOS `sips`
  decodes each icon. The owner configuration remains byte-identical; no monitor
  is launched and the active installation is not replaced.
- Windows monitor/launcher cross-compilation with C#5/Framework4.8 references
  succeeds, including the multi-size ICO resource. This is compilation on Mac,
  not native Windows execution or visual acceptance.
- No current source/test/build/prototype consumer references the retired icon
  paths. Historical provenance records are retained. `git diff --check` passes.
- No commit, push, visibility change, release, active install or Desktop restart.
