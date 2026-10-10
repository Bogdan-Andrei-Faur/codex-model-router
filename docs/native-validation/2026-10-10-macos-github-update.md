# Native acceptance receipt — 2026-10-10 — macOS — public Release update

## Identity and scope

- Owner authorized publishing and testing a real GitHub Release update.
- macOS 27.0.1, arm64; isolated hidden native AppKit/WebKit fixture on the owner host.
- Source/tag: `8d6fb670010311239c657ee676c8b6d8183be193`, `v0.9.7`, published to main.
- Release: https://github.com/Bogdan-Andrei-Faur/codex-model-router/releases/tag/v0.9.7
- Exact package: `codex-model-router-0.9.7-macos-arm64.pkg`, 18,159,922 bytes.
- SHA-256: `8e5b7489f306465721bd27a4467dab018d876b4234b2ad1e8f3656552eff56b2`.
- Monitor `992cea11bb136ed0`; router `0c8570cfccd9a1a8`.
- Source snapshot: `ec6d1e8246b21bbfe774e9a791014bdc891080400b236df055227e8f83d5ba29`.
- Build source snapshot matches the committed release source; the exact previously
  installed/tested package is reused, without relabeling a different artifact.
- CPython 3.14.8 portable runtime, 98 verified notice files; Node 24.11.1 for UI checks.
- No Desktop restart, live connection transfer or owner installation replacement.

## Results

| ID | Mode | Status | Action and result | Boundary |
| --- | --- | --- | --- | --- |
| CORE | Source | PASS | 560 Python tests, 53 platform/optional skips; 33 JS tests; 15 browser groups including 14,976 rigidity samples | Skips are not native/Docker proof |
| RELEASE | GitHub | PASS | Public latest stable 0.9.7 targets exact source; four uploaded/downloaded assets match local bytes; project signature verifies against bundled key | Mac arm64 only; no new CI success asserted |
| UPDATE-GITHUB | Isolated native | PASS | Hidden Settings DOM clicks Check then Update; ordinary anonymous production latest-release fetcher/download transport; signed public package SHA matches expected bytes | Synthetic old 0.9.6 install; hidden automated clicks, not physical input |
| UPDATE-APPLY | Isolated native | PASS | Installed old helper re-verifies package, old monitor exits normally, 0.9.7 replaces and relaunches, native readiness acknowledgement and terminal completed receipt | No mock readiness or local transport in this case |
| UPDATE-DATA | Isolated native | PASS | Exact fixture config bytes retained, previous app preserved, no Desktop registration created, no pending fixture recovery plist | No real provider credential use |
| OWNER-PRESERVED | Installed owner | PASS | Seven captured installed/configuration/registration files unchanged; same single native monitor PID after test | Owner's live 0.9.7 was not upgraded again |
| UPDATE-CANCEL/ROLLBACK | Local transport, earlier receipt | PASS | Cancellation/retry, rollback and interrupted-helper replay recorded in portable Settings receipt | Not rerun or claimed against GitHub in this success-only test |
| GATEKEEPER / UI-INPUT / LOGIN | Physical | NOT_RUN | No clean-machine quarantine, physical mouse or actual login/reboot check | Requires separate coordinated native acceptance |
| WINDOWS / UBUNTU / INTEL | Other hosts | NOT_RUN | No corresponding installer in this Release | Mac evidence does not validate another target |

## Reproduction and evidence

`tests/probe_mac_settings_update.py --github-release --python <prepared-build-python>
--package <exact-published.pkg> --output <new-fixture-directory>` builds the
synthetic old version. Only its hidden DOM driver and fixture-owned recovery
registration are injected; `UpdateManager` fetcher/opener and HTTPS redirects use
the production implementation. The new package is unchanged. The local package
argument is solely the expected-byte comparison, never the download source.

This execution built that driver first with `build_driver(..., github_release=True)`
and then ran `exercise(..., scenario='success', github_release=True)` after public
promotion. The same functions back the CLI. Recorded buttons: Comprobar ahora,
Actualizar a 0.9.7. The old host exited 0; operation and result both completed;
the new native host wrote its readiness acknowledgement. Owned fixture processes
were stopped after verification; owner processes were not signaled.

Public assets are the canonical installer, `codex-model-router-update.json`,
`SHA256SUMS` and `build-provenance.json`. The release tag remains fixed at the
source commit above; this later documentation does not retag/rebuild its bytes.
The Ed25519 signer used the already approved Mac Keychain item without exporting
private key material. It is not Apple Developer ID/notarization.

An initial test run inherited installed-app environment paths and produced four
fixture registration errors. Rerunning with those environment variables removed
passed 560 tests under portable Python 3.14.8 (53 skips); clean system Python 3.9 also
passed 560 (58 skips, including missing optional crypto). No failing run was labeled
successful and no production code change was needed for this environment issue.

## Remaining work

Real login/power-loss recovery, clean-machine/downloaded-quarantine Gatekeeper,
physical UI acceptance and Windows/Ubuntu managed-apply adapters remain open.
WPF only needs validation when using Windows. Future stable manifests must be
renewed before expiry; package bytes remain immutable. The current signature has
the standard 30-day validity. No raw logs, owner paths, prompts, private IDs or
credentials are published. Atlas tools were unavailable; no Atlas mutation is
claimed. Repository continuity and this receipt are published with the result.
