# Windows source-import correction — 2026-10-06 — host-a

## Identity and scope

- Windows x64 local host; source baseline `50e63b07fbe65e182aebeb414e6daea1e1ca599e` with uncommitted installer changes.
- Product 0.9.1; build `f877fa26ee724479`; router build `21919828f1c4baec`.
- Artifact: `codex-model-router-0.9.1-windows-x64-setup.exe` (unsigned local pilot).
- SHA-256: `afb8c9fb4bd05947b3c3454ee4d559279da76073c9a719670c2da62951780d89`.
- Owner's installed welcome dialog is still 0.9.0; existing source monitor/bridges were not stopped or replaced.
- No owner configuration, history or credentials were imported or modified.

## Results

| ID | Mode | Status | Evidence | Limit |
| --- | --- | --- | --- | --- |
| IMPORT-OWNER-090 | Physical owner report + read-only diagnosis | FAIL | Generic welcome error; original Windows configuration lacks platform marker | Old monitor and source bridges also remain open; source guard confirmed busy_source |
| IMPORT-LEGACY-CONFIG | Source fixture | PASS | 18 tests across application layout and Windows installation; normalize only imported Windows copy | No owner migration |
| IMPORT-FROZEN | Isolated installed payload | PASS | Frozen 0.9.1 imports markerless fixture, retains source bytes and accepts subsequent bootstrap | Synthetic data only |
| IMPORT-DIAGNOSTICS | Source and frozen fixtures | PASS | Safe reason codes for missing source/occupied destination; contract covers busy source/active bridge/foreign platform | Physical welcome-message interaction pending |
| NATIVE-PAYLOAD | Isolated native | PASS | Runtime/native assembly identities, JSONL IPC, WebView2 preview, preference preservation, DPAPI synthetic roundtrip, tampered candidate rejection | No live inference or registration |
| INSTALL-LIFECYCLE | Isolated setup | NOT_RUN | No setup lifecycle change in 0.9.1; previous 0.9.0 fixture receipt remains historical | New production setup not executed |
| OWNER-ACTIVATION | Physical | NOT_RUN | Owner must close tasks/Desktop and both monitor windows, install 0.9.1, then import source root | Do not restart or stop apps automatically |

## Conclusion

The original Windows source installer omitted `platform`; strict import validation
incorrectly rejected its own legacy format. 0.9.1 recognizes that format only for
Windows, normalizes the copied configuration and preserves the original. Explicit
foreign-platform settings remain rejected. The UI displays fixed diagnostics,
never raw subprocess output, and sizes itself to fit the message.

Remaining owner check: after closing the old monitor and Desktop, install 0.9.1,
import the source installation root, then connect Desktop separately in Settings.
Do not select Start fresh to work around an import failure. Data import alone is
not evidence that Desktop uses the new installed bridge.
