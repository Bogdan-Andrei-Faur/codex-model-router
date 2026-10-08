# Source organization validation — 2026-10-08

## Scope and identities

- Local uncommitted changes on `main` above published `5b050fc200f6c0d0b04770130185ca1aa8a3519c`.
- Tracked root files reduced from 71 to 17; root Python files from 45 to seven
  dispatchers. Forty-one shared Python modules moved into seven responsibility
  groups and package-wide helpers. Four builders, dependency pins and the Inno
  recipe moved to `tools/packaging/`; fourteen native files moved to `native/`.
- Product remains `0.9.6`, policy `8`. New source product fingerprint
  `37359ff46664c768`, router fingerprint `5aa7726ffeba863f`.
- Existing installation and running Desktop/monitor were not replaced/restarted.
  Previous installed monitor `4891f87b980d518e`, its expected router
  `281078dcf3e49517` and last observed loaded router `80e86c3d7accf253` belong to
  the earlier artifact, not this source candidate. No fresh owner connection or
  new natural activity-event acceptance is asserted here.

## Changes

Qualified Python imports replace root implementation imports. Root resource/data
resolution stays independent of cwd and package nesting. Six original source
launchers and `build.ps1` remain small compatibility dispatchers; tools and test
entrypoints add `src` explicitly. Native source compilation paths, CI commands,
current guides, generated fingerprints and build snapshots follow the new layout.

Mac/Windows snapshot source paths preserve `src/native/tools` structure. Frozen
analysis uses a static entrypoint. Ubuntu resources contain `src`, with an isolated
module launcher; the system-interpreter Secret Service adapter also loads its
qualified module explicitly. User data, credentials and capture settings retain
their existing locations.

Cross-compilation discovered an inherited C#7 pattern declaration in the published
Windows appearance acknowledgement. It was replaced with an equivalent C#5 type
check/cast so the existing Framework compiler contract remains valid.

## Verification

| Check | Result and limit |
| --- | --- |
| Python full discovery, system Python 3.9, clean child environment | **544 tests OK; 53 skipped** for optional/platform prerequisites |
| Source-layout regressions | Six tests: root boundary, fresh legacy launchers from another cwd, snapshot identity/exclusions, relocated isolated resources and actual generated Ubuntu runtime execution |
| JS core and shared browser matrix | **33 JS tests**, all **14 browser groups PASS** |
| Local routing / offline JEV | **27/27**, six cases PASS; no provider inference |
| Mac package build | Real unsigned/ad-hoc local `.pkg`, pinned PyInstaller 6.22.3; not installed or published |
| Exact Mac package extraction/relocation | PASS with no development PATH: frozen identity/bootstrap/IPC, preserved synthetic preferences, native monitor ready and backend version forwarding |
| Windows source cross-compilation | Actual WPF/launcher sources PASS on Mac against supplied Framework 4.8 references, C#5 and WebView2 1.0.4258.31; no native Windows execution |
| Ubuntu payload | Real builder stages source; actual generated shell/Python runtime executes identity outside checkout. Missing Debian/desktop-validation tools substituted in this test; no real `.deb` lifecycle or GTK acceptance claimed |
| Imports, whitespace and documentation links | No unqualified shared imports; whitespace and current local links PASS |

Mac package SHA-256:
`ab45e60255e63e05a000df4cf2110673dbc54ac9d5213291af9677e5eba88636`.
Build outputs and detailed logs remain ignored and local; no private configuration,
raw telemetry, prompts, keys, conversations or owner screenshots enter this receipt.

## Remaining separate gates

Windows native installer/runtime and Ubuntu real package lifecycle/GTK checks need
those hosts. Current CI is not awaited or assumed to pass. Existing glass bounds
fixture and physical input/display gates remain open. The new organization does
not close them or validate already-running older artifacts.

Before later activation, select and rebuild the intended source/package artifact,
coordinate any replacement/restart with the owner, then independently verify
source, installed and loaded identities. Do not compare these new source hashes
against an older installed stamp and declare it current. No commit/push, release,
system installer or Desktop registration was performed for this reorganization.
