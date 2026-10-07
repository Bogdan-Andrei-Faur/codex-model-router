# Windows import completion — 2026-10-06 — host-a

## Identity and scope

- Windows x64 local host; source baseline `50e63b07fbe65e182aebeb414e6daea1e1ca599e` with uncommitted installer work.
- Owner-installed artifact: 0.9.1, build `f877fa26ee724479`.
- Read-only owner receipt: config exists; 78 known files imported; source preserved.
- Installed-data connection receipt is absent. Import does not establish Desktop connection.
- New candidate: `codex-model-router-0.9.2-windows-x64-setup.exe`, unsigned local pilot.
- Candidate build `f87632d8b3088565`; router build `32f97f11cc1ff861`.
- SHA-256: `67bf260fbd3ced8a8c3c63352c059ab74e04428e6bf6e27afcc724b82ff1c321`.
- No owner files modified, apps stopped, installed version replaced or Desktop restarted.

## Results

| ID | Mode | Status | Evidence | Limit |
| --- | --- | --- | --- | --- |
| IMPORT-OWNER-091 | Physical owner operation/read-only receipt | PASS | Import persisted configuration and 78 known files; original source retained | No raw data or identifiers included |
| IMPORT-CONFIRMATION-091 | Physical owner report/source inspection | FAIL | Successful operation closed welcome immediately without confirmation | Data import itself succeeded |
| IMPORT-CONFIRMATION-092 | Source/native build | PASS | Success keeps welcome open with completion text and Open monitor/Close actions | Physical input/visual acceptance pending |
| NATIVE-PAYLOAD-092 | Isolated native/frozen fixtures | PASS | Runtime/native identity, WebView2 preview, IPC, import normalization, safe diagnostics, DPAPI roundtrip and source preservation | Synthetic data; no production setup execution |
| IMPORT-CONNECTION | Installed owner data | NOT_RUN | No desktop-integration receipt at imported root | Owner must connect via Settings and choose restart timing |

## Conclusion

0.9.2 adds explicit success feedback for import and fresh configuration. Closing
the completion window preserves imported data and defers the monitor to a later
launch. Open monitor starts it immediately. The original welcome choices disappear
after success, preventing accidental duplicate import attempts.

The owner's existing import is complete; do not rerun it to test confirmation.
Installed 0.9.1 can continue with Settings connection without installing this UI
revision immediately. Owner activation and physical first-run UI remain separate.
