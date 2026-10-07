# Windows installer acceptance — 2026-10-06 — host-a

## Identity and scope

- Session: Windows 11 x64 owner host; isolated synthetic package/setup fixtures.
- Source: `50e63b07fbe65e182aebeb414e6daea1e1ca599e` plus uncommitted installer work.
- Product: 0.9.0; policy reference 8. Candidate policy 9 is not activated.
- Final product build: `32c9543555c53846`; router build: `75113c8c6e5890b5`.
- Artifact: `codex-model-router-0.9.0-windows-x64-setup.exe` (unsigned local pilot).
- SHA-256: `75984b67b2e67742207328b72135257705b4e9fbd2463f93d3ca11685da17da0`.
- Toolchain: Python 3.14.3, PyInstaller 6.22.3, Inno Setup 6.7.3 verified against
  pinned input hashes and official installer publisher. Existing Framework 4.8
  references were supplied explicitly; WebView2 SDK 1.0.4258.31.
- No production setup execution, source-to-installed connection transfer, owner
  key read, paid inference, Desktop restart or interruption was performed.
- Earlier ordinary source/ZIP 0.8.1 activation remains historical evidence in
  [the preparation receipt](2026-10-06-windows-host-a.md), not 0.9.0 acceptance.

## Results

| ID | Mode | Status | Evidence | Limitation |
| --- | --- | --- | --- | --- |
| CORE | Source fixtures | PASS | 490 Python tests, 55 skips, no failures | Platform/optional Docker skips remain visible; not deployment acceptance |
| ROUTING | Offline fixtures | PASS | 27/27 corpus and six JEV cases | No live inference/provider calibration |
| UI-SHARED | Browser fixtures | PASS | 26 JS tests and seven Chromium layout/interaction groups | Physical OS input is not proven |
| PACKAGE-IDENTITY | Relocated frozen payload | PASS | Empty PATH; frozen runtime/bridge identity; native informational version checks | No source/developer interpreter required |
| PACKAGE-IPC | Relocated frozen payload | PASS | Private JSONL monitor service, isolated snapshot and retained preferences | Fixture data only |
| PACKAGE-MIGRATION | Synthetic Windows import | PASS | Config/history/blob bytes preserved; original retained; registration not copied | Owner migration not performed |
| KEY-NATIVE | Synthetic DPAPI | PASS | CurrentUser fixture encrypted/imported/decrypted successfully | No real account key was retrieved |
| IMPORT-CONNECTION | Mocked ownership tests | PASS | Transfer retains original environment; retry after failed probe; concurrent/foreign change refused; active monitor mutex refused | Owner registry transfer remains NOT_RUN |
| UI-NATIVE | Relocated native preview | PASS | WebView2 capsule/history/IPC self-test and isolated receipt | No normal first-run/physical mouse/tray acceptance |
| SETUP-LIFECYCLE | Real setup, isolated fixture build | PASS | Install, upgrade, file-lock rejection, rollback, uninstall retaining data and reinstall | Fixture AppId/no uninstall registry entry/no shortcuts; production setup not executed |
| SETUP-FAILURE | Isolated fixture | PASS | Locked component prevents upgrade; manipulated version does not replace active pointer | Disk-full/copy cancellation/clean-machine dependency failures NOT_RUN |
| ENV-OWNER | Production installed/loaded identity | NOT_RUN | Owner installation was not switched | Coordinate activation after current tasks finish |
| UI-OWNER | Physical/normal installation | NOT_RUN | No owner first-run, Start menu, registry/uninstall, display/DPI/sleep checks | Separate owner/VM acceptance required |
| PUBLISHER | Release trust | NOT_RUN | No product signing identity/certificate supplied | Local setup remains unsigned; no public release |
| UPDATE-APPLY | Shared updater | NOT_APPLICABLE | `canInstall=false` preserved | Trusted automatic apply is a separate delivery |

## Failures found and corrected

- Tool preparation initially waited at Inno's install-mode dialog. Explicit
  CURRENTUSER/PORTABLE preparation avoided elevation/global registration.
- Windows PowerShell inherited incompatible PowerShell 7 module paths from the
  build environment. Isolated build commands now clear that inherited module path.
- The older activation helper accepted a candidate whose version directory did
  not match its frozen identity. Candidate identity is now checked before promotion.
- Short/long Windows path aliases caused a fixture uninstall to classify its own
  helper as busy. Native ownership checks now normalize paths, and distinguish
  the running uninstaller from product processes. Silent errors are suppressible.
- Inno's finalizer retained redirected output/log handles after its stub exited.
  GUI fixture commands use no stdout protocol and wait for their owned log release.
- Native assembly stamps initially described a partial source snapshot, while
  frozen runtime stamps described the complete source. All fingerprint inputs
  are now copied; the builder refuses divergence and smoke checks both native PEs.

These failures were retained as test feedback, not converted into successful
owner-installation results. Raw fixture logs and generated artifacts stay ignored.

## Conclusion and remaining gates

The local installer/runtime path is ready for coordinated owner/VM acceptance.
Do not infer cross-platform/native-owner acceptance from these fixtures. Before
switching the owner: finish tasks, close the old Desktop/monitor, install the
pilot, import the source folder, connect explicitly and let the owner restart.
Then measure installed/loaded identity, handshake, telemetry and ordinary UI use.
Clean Windows prerequisites, interactive cancellation/permission/disk failures,
physical first-run/tray/input, normal installation registration and publisher trust
remain open. No personal state, keys, prompts, conversation IDs or raw logs appear
in this receipt. Existing data and active source installation were preserved.
