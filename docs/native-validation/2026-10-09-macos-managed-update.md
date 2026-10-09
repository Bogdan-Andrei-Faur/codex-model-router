# Mac authenticated update fixture — 2026-10-09

## Scope and identity

Local development on historical main `63d3f39`, before the owner-approved clean
public-repository migration. No active owner installation was replaced; Desktop
was not restarted, registered or disconnected. All runtime data was synthetic.
The owner approved creating a project signing key in this Mac's Keychain; only
public metadata and safe test results are recorded here.

Final isolated snapshots used the same implementation, with fixture-only VERSION
values0.9.6 and0.9.7. Old packaged monitor build `194f2b8074c4a33c`; new packaged
monitor build `1eb7bbc676d1b1b6`. These are fixture artifacts, not published product
releases. New `.pkg` SHA-256:
`810a3b5c9ff9798e96b302ee2a6f98ff9dccd97d3530d78a04268b2dba33eb3e`.

## Executed checks

| Check | Result and boundary |
| --- | --- |
| Python suite |557 tests,53 optional/platform skips; no failures |
| Shared JS core |33 tests pass |
| Browser/layout suite |All15 groups pass, including signed Update action, post-handoff cancellation suppression and rollback text |
| Native package build |Two arm64 packages built with pinned PyInstaller6.22.3, cryptography50.0.2 and native Swift; ad-hoc deep/strict codesign check passes |
| Signed old-to-new fixture |Project-key Ed25519 manifest verified, exact bytes rechecked by copied installation-owned frozen runtime, application replaced, new native WebKit/data acknowledgement received |
| Cancellation |Real package preflight with cancellation set preserves running old fixture app/version; browser/unit cancellation cases also pass |
| Preservation |Synthetic configuration and sentinel unchanged; previous app retained; independent data root untouched by replacement |
| Fault recovery |Unit-injected launch failure and interruptions between renames restore old app; terminal login registration cleanup tested |
| Package relocation |Extracted/relocated runtime and IPC pass with no development tools in PATH; native packaged monitor launches its child; bridge version forwarding passes |
| Owner processes/data |Not replaced or signalled; no Desktop registration, owner migration or provider inference |

`tests/smoke_update_macos.py` invokes real packaged native hosts and the frozen
installed helper. The fixture explicitly terminates its own old host **after**
ready-to-close, rather than automating a native Settings click. Its recovery plist
is redirected to the temporary fixture directory; no real login agent is created
by the test. Do not relabel this as complete end-user or power-loss acceptance.

Earlier preliminary fixture builds `bcc12e8b8af94693` → `2bf88eaca8dbddcd` also
passed; the final builds above include stricter handoff exclusion, schema checks,
downgrade rejection, frozen-child environment isolation and terminal-job cleanup.

## Still required

- Native Settings click through real release discovery/download and automatic old
  monitor exit, on a disposable installed target.
- Current-user Installer/Gatekeeper first installation and user-facing prompts.
- Real login/reboot recovery at interrupted commit points; do not suspend or
  restart the owner's computer merely to run this case.
- Guarded graphical import/connection transfer with real retained credential
  handles and complete data expectations; raw OTLP archives remain in the source.
- Windows/Ubuntu native apply adapters and their own lifecycle/recovery receipts.
  WPF only needs validation if using Windows.
- Exact public-installer dependency notices, release assembly and platform QA.

See [managed update contract](../MANAGED-UPDATES.md). Test/build evidence does not
activate this source in the owner's monitor or loaded Desktop bridge.
