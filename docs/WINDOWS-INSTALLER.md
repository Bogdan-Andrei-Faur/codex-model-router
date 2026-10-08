# Windows per-user installer — 0.9.6

The current shared monitor requests a top-centered dynamic notch, five icon
destinations, horizontal Home/Agents and incremental History. Installer layout,
per-user data and credential custody retain the contracts below. Source/native
compilation and owner-installed acceptance are separate; see
[NOTCH-MONITOR.md](NOTCH-MONITOR.md) and [STATUS.md](native-validation/STATUS.md).


This is a native x64 setup builder, not the legacy Windows ZIP. Production
installation/owner data migration is separate from isolated fixture acceptance.
No restart, source-installation replacement or live provider inference is needed
to build and test it. Do not publish unsigned artifacts as trusted automatic updates.

## Installed layout and lifecycle

```text
%LOCALAPPDATA%/Programs/Codex Model Router/
  bin/codex-router.exe                 stable native bridge and monitor entry
  active.json                         atomically selected version directory
  active.previous.json                previous validated selection
  versions/<semver>-<build>/
    Resources/application.json        windows-install-v1; owned executable paths
    Resources/ui/                     shared monitor UI
    Resources/assets/                 public product assets
    runtime/router-runtime.exe        frozen Python, no developer interpreter
    bin/codex-monitor.exe              WPF/WebView2 host

%LOCALAPPDATA%/codex-model-router/
  config.local.json
  state/                              history, prompts, DPAPI blobs, preferences
```

Installed launchers never select runtime executables from writable user settings.
Activation preflights the bundled runtime identity against the version manifest
and saves the previous pointer before selecting the new version. Version folders
remain available for manual recovery. `--rollback` selects the previous validated
runtime; the Start-menu recovery action asks before doing so. A damaged current
pointer can be recovered from the previous selection without removing user data.
Existing processes keep their loaded version; recovery does not kill Desktop.

Native executable informational versions match the frozen runtime's product and
router build stamps; the builder rejects a snapshot with a different identity.
Bridge launcher/layout changes also contribute to the router fingerprint.

Setup runs per user, checks .NET Framework 4.8, and checks the Evergreen WebView2
Runtime. If missing, interactive setup requests permission for the Microsoft
bootstrapper's network installation. Build and execution check Microsoft publisher
trust. Silent setup fails rather than downloading a missing prerequisite without
confirmation. The shared WebView2 Runtime is not removed when uninstalling our app.
Windows 10 build 19041 is the technical minimum; physical acceptance is currently
on Windows 11 x64. Other architectures require separate native builds/acceptance.

Setup refuses in-use components instead of terminating them or scheduling binary
replacement at reboot. Uninstall separately restores the prior user-level
`CODEX_CLI_PATH` only when the current value still belongs to this installation.
Native disconnection does not need the bundled Python runtime. Foreign connections
are preserved and block removal until resolved. Uninstall retains the data root.
Version 0.9.4 normalizes the owned wrapper path before comparing it with the
connection receipt. Version 0.9.3 could reject its own registered connection
because `bin/codex-router.exe` retained a forward slash in the expected path.
The clean VM reproduced this refusal; upgrade to 0.9.4 before connected uninstall.
Native regression tests compile against a disposable registry key, never the
owner's Environment key, and verify restoration and foreign-connection refusal.

## First run and source migration

The installed monitor presents Cancel, Start fresh and Import installation.
Version 0.9.2 keeps the welcome window open after success, showing an explicit
completion message and the separate Settings connection step. Open monitor starts
the monitor; Close leaves the imported data ready for the next launch. Successful
imports must not be repeated merely to see this confirmation.
Version 0.9.3 refreshes the native capsule clipping bounds after first layout,
viewport changes and hidden/show transitions. A capsule keeps its size when its
bottom-anchored position changes, so observing element size alone was insufficient.
The native self-test now checks the actual Windows region at capsule startup,
after viewport resizing and after hidden/show, before ever expanding the panel.
Version 0.9.1 accepts original Windows source configurations without a `platform`
field and adds `win32` only to the imported copy. Explicit foreign-platform
configurations remain rejected. Fixed, safe error codes now reach the welcome
dialog, distinguishing an open old monitor, an active Codex bridge, a wrong
folder and an occupied destination. No raw runtime output is shown.
Import uses `src/codex_model_router/platforms/installation_migration.py`: only known configuration/history/task
preferences and opaque credential blobs are copied, preserving source files.
Occupied destinations, active bridge snapshots, changing data, symlinks and
Windows reparse points/junctions are rejected. The existing WPF monitor's named
mutex is checked before copying, alongside bridge status and writer locks.
DPAPI blobs work for the same
Windows user; this is not cross-user or cross-platform credential migration.

Import never transfers Desktop registration by itself. The subsequent Settings
connection action validates the exact legacy bridge/receipt, probes the new
bridge, rechecks the environment and source provenance, then adopts only an owned
legacy connection. It retains the environment preceding the source installation
for future disconnect. Failed probes are retryable without a partial adopted
registration. The source folder remains available as backup.

Version 0.9.5 fixes false active-session blocks from old snapshots whose PIDs
Windows has reused. Native process creation time must prove that the current
process started after the snapshot; stale age alone never dismisses a live bridge.
Unknown process identity stays blocked. Connection errors now use fixed public
codes and actionable monitor messages without exposing private runtime output.
See the [frozen regression and lifecycle receipt](native-validation/2026-10-07-windows-connection-pid-reuse-host-a.md).

Version 0.9.6 flushes each native stdin chunk: initialize/model-list must reply
while input remains open. JSON diagnostics remain parseable through Windows ANSI
pipes. Settings shows immediate progress, disables duplicate connection actions,
and retains a restart notice until the installed bridge is observed. Verified
connection adoption only prepares the next launch and can run while Desktop is
open; it does not copy data or stop that source bridge. The offline import guard
above still applies. See the [owner repair receipt](native-validation/2026-10-07-windows-connection-repair-host-a.md).

Finish current tasks and close the old Desktop/monitor before importing. Do not
switch the owner's installation merely to perform acceptance. After connecting,
the owner chooses when to restart Desktop. Check installed/loaded build identity
and a fresh handshake afterward; source revision alone is not activation evidence.

## Build without changing the active installation

Use Windows x64, Python 3.14.3, .NET Framework 4.8 reference assemblies and network
access to official tool repositories. Reference assemblies are build inputs only;
users of the resulting setup do not need development tools or the source checkout.

```powershell
python -m venv state/windows-installer-venv
state/windows-installer-venv/Scripts/python.exe -m pip install -r tools/packaging/requirements-windows.txt
python tools/prepare_windows_installer.py
$tools = Get-Content state/installer-build-tools/tools-receipt.json -Raw | ConvertFrom-Json
$python = 'state/windows-installer-venv/Scripts/python.exe'
& $python tools/packaging/build_windows_installer.py --python $python --compiler $tools.compiler --webview2-bootstrapper $tools.webview2Bootstrapper
```

If framework references are not at the standard location, supply
`--framework-reference-path <existing-v4.8-directory>`. The builder snapshots
source/public assets into a new release workspace and compiles there. The live
checkout's `dist/`, source configuration and Desktop registration are untouched.
It verifies pinned Inno Setup 6.7.3 inputs, PyInstaller 6.22.3 and the Microsoft
bootstrapper signature. `tools/prepare_windows_installer.py` verifies the official
Inno setup SHA-256/publisher and uses CURRENTUSER/PORTABLE mode; it does not install
global compiler shortcuts, file associations or a WebView2 runtime. Retain the
tool receipt and actual dependency versions. Review upstream tool licensing before
commercial distribution; compiler tooling is not shipped in the product.

Output: `codex-model-router-<version>-windows-x64-setup.exe`, checksum,
`build-result.json`, isolated payload and build log. Outputs contain no owner
configuration, state, prompts, keys, Desktop executable or Codex engine. The
artifact is an unsigned local pilot. Inno's publisher signing hook is reserved
for a future explicitly configured signing pipeline; no certificate is provisioned.

## Validation

```powershell
python tests/smoke_windows_installer.py <build-result.json>
python tests/smoke_windows_installer.py <build-result.json> --compiler <ISCC.exe> --webview2-bootstrapper <MicrosoftEdgeWebview2Setup.exe> --previous-receipt <previous-build-result.json>
python tests/smoke_windows_installer.py <build-result.json> --compiler <ISCC.exe> --webview2-bootstrapper <MicrosoftEdgeWebview2Setup.exe> --previous-receipt <previous-build-result.json> --shortcuts
```

The first command relocates the payload and tests frozen identity/runtime/IPC
with empty PATH, preservation of fixture preferences, synthetic offline import
and DPAPI roundtrip, native WebView2 preview and the official CLI's `--version`.
It rejects a manipulated candidate without changing the active pointer.
It does not register Desktop or run inference.

The optional lifecycle compiles **fixture-only** setup programs with synthetic
data roots, no uninstall registry entry and `/NOICONS`. It exercises real setup
execution in temporary directories: install, locked-file failure, upgrade,
rollback across two builds, uninstall/data retention and reinstall. The actual
production setup is not executed by this test. The CI `windows-installer` job
uses ephemeral fixture versions 9.9.0/9.9.1 and restores the checkout VERSION.
`--shortcuts` adds creation, target/arguments and removal checks in a unique
fixture Start-menu group. Its private script changes `DefaultGroupName`, because
Inno ignores `/GROUP` when the group-selection page is hidden. Never direct this
fixture at the owner's normal Start-menu group.

For an owned clean Hyper-V guest, use the three QA scripts below from one
elevated PowerShell session. Preparation requires an official
Microsoft evaluation ISO verified against Microsoft's SHA-256 and a new owned
workspace. Stage only public installers (`latest.exe`, `previous.exe`), the
Microsoft-signed WebView2 bootstrapper, `tests/windows_clean_guest.ps1`, and
`expected.json` with each installer version/build/SHA-256. The guest script
accepts only a disposable QA account and checks the real production AppId,
Start menu, uninstall registration, prerequisites, upgrade/rollback, failure
preservation, DPAPI and uninstall/reinstall retention. It uses synthetic data;
no owner state, Desktop login or live inference is copied into the VM.
Raw logs and the generated guest password stay in ignored local state.

```powershell
# Hyper-V must already be available; do not reboot the owner's host for QA.
$qaWorkspace = '<new-owned-workspace>'
$qaIso = '<official-Windows-evaluation.iso>'
$qaIsoHash = '<SHA-256-published-by-Microsoft>'
New-Item -ItemType Directory -Path $qaWorkspace
tools/prepare_windows_qa_vm.ps1 -Workspace $qaWorkspace -Iso $qaIso -IsoSha256 $qaIsoHash -InputRoot '<public-input-directory>' -DeferBootSetup
tools/boot_windows_qa_with_winpe.ps1 -Workspace $qaWorkspace -Iso $qaIso -IsoSha256 $qaIsoHash
tools/collect_windows_qa_vm.ps1 -Workspace $qaWorkspace
```

The recommended path applies Windows offline, then runs BCDBoot inside a
disposable WinPE guest. It does not repair the host's live BCD or change firmware
security settings. The guest has 2 CPUs, 2–4 GiB dynamic RAM, a 64 GiB dynamic
disk, local synthetic accounts and no automatic startup. Automatic checkpoints
are disabled before boot: reading a base disk after a checkpoint would miss
guest writes. Never mount a base disk writable while it has differencing children.
Default startup memory is 4 GiB; `-StartupMemoryGiB 3` allows testing with less
initial host RAM without closing the owner's applications. Record that constraint;
it does not validate Windows hardware minimums or performance.
WinPE finds the QA Windows volume by its marker and selects that disk's EFI
partition; it does not assume a disk number. Completed boot output is read only.

The collector uses PowerShell Direct and the generated synthetic credential;
it copies sanitized assertions only and shuts down a successful guest. The
credential file and VM/ISO disks remain private, ignored test resources. Remove
only explicitly owned QA VMs/disks when no longer needed. The helpers use cached
process handles and bounded parent-process waits to support Windows PowerShell
5.1; waiting for DISM's entire child tree can block image servicing.
VMMS must be running for Hyper-V commands. If it was started only for QA and
restored to Stopped afterward, an authorized later QA run must start it again;
the retained VM does not start automatically.

The guest additionally tests a real non-administrator installation/uninstall,
permission and disk-space failures in guest-owned locations, production registry
and shortcut removal, foreign-connection refusal and restoration of the prior
environment value/type. Missing WebView2 is conditional: if already supplied by
Windows, that download branch remains untested. These automated checks do not
establish interactive installer cancellation or physical keyboard/hover behavior.

Physical first-run keyboard/hover/input, normal Start menu/uninstall registration,
clean-machine prerequisites, cancellation during copy, disk-full/permission failure,
source-to-installed activation and natural Desktop use require separate owner/VM
acceptance. Record failures and skips in `docs/native-validation/`; do not commit
raw fixture logs, private configuration or credentials.

## Remaining distribution work

The canonical source repo is private. Anonymous discovery cannot supply public
installer downloads yet. No release, public artifact repo, publisher certificate
or trusted update executor is created by this work. `canInstall=false` remains;
Settings can stage downloads only. Signing, accessible distribution and automatic
installation remain a separate delivery.
