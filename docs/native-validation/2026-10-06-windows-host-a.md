# Native acceptance receipt — 2026-10-06 — Windows — host-a

## Identity and scope

- UTC reference points on 2026-10-06: verified pre-pull backup at 13:15:50;
  final identity/process check at 13:24:03. These are not full-turn timings.
- Host alias: host-a; local Windows session, isolated native and browser fixtures.
- OS: Windows 11 Pro 10.0.26300, x64. One display reports 1920×1200 physical
  pixels; prior logical bounds were 1536×960. No scaling/display changes made.
- Source: `50e63b07fbe65e182aebeb414e6daea1e1ca599e`, with preserved historical
  documentation changes and a local packaging-only reference-directory option.
- Product: 0.8.1, reference policy 8. Candidate policy9 was not activated.
- Source-mode installed monitor and rebuilt ZIP: build `dadea95e26f96444`,
  router `079489ab18a2d1df`.
- Artifact: `Codex-automatico-0.8.1-windows.zip`, SHA-256
  `a57d05ea1b6041e09ef3cc1e94cbec3d2985573220d8b1e23e8215ea4f913373`.
- Before the owner's restart, ordinary Desktop loaded 0.8.1, router
  `94bee8da688d9f24`. The new source differed despite the unchanged version.
  The post-restart check below records activation of the intended new bridge.
- Desktop: 26.930.7945.0; discovered official CLI: 0.160.1.
- Python: 3.14.3; Node: 24.13.1; PyInstaller: 6.22.3.
- Runtime: .NET Framework 4.8, installed release 533509; WebView2 Evergreen
  available. SDK 1.0.4258.31 verified using the repository lock.
- The host lacks installed Framework 4.8 *reference assemblies*. Microsoft
  referenceassemblies.net48 1.0.3 was extracted to ignored build storage and
  verified against NuGet catalog SHA-512; no system SDK/runtime installer ran.
- Desktop was not restarted. No production data migration, setup execution,
  integration re-registration, provider inference, Docker execution, sleep or
  physical display changes were performed. Existing source data/config retained.

## Results

| ID | Mode | Status | Command/action | Observation | Limitation |
| --- | --- | --- | --- | --- | --- |
| ENV | Source/installed | PASS | Inspect source, BUILD, doctor, live snapshot | Installed and loaded fingerprints measured separately | New bridge activation pending |
| CORE | Source fixtures | PASS | Clean-child `python -m unittest discover -s tests -p 'test_*.py' -q` | 482 tests, 55 skips, no failures | Platform/Docker skips; not a full Docker run |
| ROUTING | Source fixtures | PASS | `tests/evaluate_routing.py`; `tests/smoke_jev.py` | 27/27 corpus; six offline JEV policy cases | No classifier/provider requests |
| UI-SHARED-FIXTURES | Browser fixtures | PASS | `npm ci`, `npm test`, Chromium `npm run test:layout` | 26 JS tests; all seven UI groups pass | Browser input is not physical mouse acceptance |
| DKR-CONTROLS | Local Docker | BLOCKED | Inspect available CLI | Docker CLI unavailable | Install/prepare local Docker separately if grader acceptance is wanted |
| DKR-SUITE | Local Docker | BLOCKED | Not run | 55 suite skips include unavailable platform/grader paths | No unsandboxed grader fallback |
| DKR-CLEANUP | Local Docker | NOT_APPLICABLE | No Docker tests started | No owned Docker containers created | Does not certify an existing Docker environment |
| TEL-ROOT | Isolated native | PASS | `tests/smoke_telemetry.py --layout root --layout subcommand --layout desktop` | Config verified; requests 1; authorization/invalid counters zero | No model generation |
| TEL-SUBCOMMAND | Isolated native | PASS | Same command, subcommand result | Config verified; requests 1; authorization/invalid counters zero | No model generation |
| TEL-DESKTOP-LAYOUT | Isolated native | PASS | Same command, desktop result | Config verified; requests 1; authorization/invalid counters zero | Not ordinary Desktop activation |
| TEL-DESKTOP-ACTIVE | Ordinary installed bridge | PASS after owner restart | Safe live-status inspection at 13:33 UTC | One connected bridge; completed handshake; router `079489ab18a2d1df`; no build mismatch | Transport/activation only, not inference identity or correctness |
| UI-NATIVE-FIXTURE | Native source and extracted ZIP | PASS | `build.ps1 -BuildOnly -FrameworkReferencePath <verified refs>`; monitor `--self-test` | Exit 0: shared capsule/agents/pills, lazy history, private Python IPC, native bounds/mode ACK | Physical input/hover/DPI/DPAPI not certified |
| PACKAGE-WINDOWS | Extracted ZIP/native | PASS | `package_windows.py --framework-reference-path <verified refs>`; `tests/smoke_package_windows.py <zip>` | Doctor, frozen bridge/catalog, assets, default migration, preserved fixture upgrade and native monitor pass | ZIP, not graphical setup; did not register/open Desktop |
| UI-INPUT | Physical | NOT_RUN | Not performed | Native fixture only | Owner physical acceptance pending |
| UI-VIEWS | Physical | NOT_RUN | New source monitor launched after builds completed | Process remains alive; normal usage acceptance pending | No owner-approved tray/click checklist |
| UI-DATA | Ordinary installed | NOT_RUN | Not performed on new bridge | Existing bridge remains old | Wait for owner restart and natural observations |
| UI-DISPLAY | Physical | NOT_RUN | One display available | Multi-display hardware absent | Do not transfer fixture results to this gate |
| UI-SCALE | Physical | NOT_RUN | Scaling unchanged | No controlled fractional-DPI interaction | Owner-coordinated test pending |
| UI-SLEEP | Physical | NOT_RUN | No suspend/resume | Active owner work preserved | Owner-coordinated test pending |
| UI-START | Physical | NOT_RUN | Desktop not reopened/rebooted | Existing integration left in place | Owner chooses activation time |
| KEY-NATIVE | Isolated native store | NOT_RUN | No key written/read | Existing credentials preserved | Dedicated synthetic DPAPI roundtrip pending |

## Evidence details and recovery

- Native transport reports show all three layouts received requests before and
  after shutdown with zero unauthorized, rejected, unexpected-path and invalid
  counters. No live inference was requested and prompt capture was disabled in
  those isolated sessions.
- Native WebView2 history screenshot was reviewed using synthetic fixture data.
  All private logs/reports/screenshots remain in ignored local state/storage.
- Initial browser fixtures lacked the newly pinned Chromium build; installing
  that test browser resolved the prerequisite and all groups then passed.
- The native executable cannot be rebuilt while an owned self-test uses it.
  The overlapping preparation attempt was discarded; the final package was
  built after that test exited and the extracted artifact passed independently.
- The source monitor was not already running. The rebuilt monitor was launched
  only after package compilation completed; existing Desktop/bridge kept running.
- Saved routing remains JEV, with phase routing, inference telemetry and private
  prompt capture enabled. No routing preferences or provider keys changed.
- Original unrelated documentation additions were backed up, verified and
  re-applied after the fast-forward. No general reset/clean or private-state
  replacement was used.
- Authenticated canonical GitHub Releases listing on this date returned no
  releases. Source/docs also explicitly identify Windows setup as pending.
  This artifact is local, unsigned and unpublished; not a `-setup.exe`.

## Conclusion and remaining work

The source/native WebView2 monitor, authenticated telemetry transport and
portable ZIP are prepared and validated on this Windows host. The owner then
restarted Desktop; the 13:33:05 UTC check confirms product 0.8.1 and router
`079489ab18a2d1df`, matching installed code, with one connection, completed
handshake, no restart flag or build mismatch, and 76 telemetry requests with
zero unauthorized/invalid requests. This closes the ordinary bridge activation
gate without extending physical UI or inference attribution acceptance. Physical
input/hover/tray, DPI/multi-display, sleep/resume, DPAPI and graphical setup
acceptance remain open. This receipt does not imply acceptance on Mac/Ubuntu.

This report contains only safe versions, hashes, counts and sanitized outcomes.
No private prompts, titles, conversation/account identifiers, keys or original
installation/home paths are included. Publication has not been requested.
