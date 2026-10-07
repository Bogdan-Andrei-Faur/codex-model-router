# Windows installation acceptance — 2026-10-07 — host-a

## Identity and scope

- Windows 11 x64, build 26300; one connected physical display, 1920 x 1200,
  with a 1536 x 960 logical desktop (125% scaling).
- Desktop package 26.930.7945.0; package identity is separate from bridge identity.
- Source baseline `50e63b07fbe65e182aebeb414e6daea1e1ca599e` plus uncommitted
  installer work. Final validated product 0.9.4, policy 8, build
  `d042188854998c95`, router build `1fa217653242b775`.
- Exact unsigned corrected pilot: `codex-model-router-0.9.4-windows-x64-setup.exe`;
  SHA-256 `9dbb3980442cad08a69d21758f372eaa2b8bdd3e5639a46250feacfc9594786d`.
- Owner's unchanged installation and initial guest failure use 0.9.3, build
  `3da07492a5af00ae`, router build `d323562bd219e24a`; artifact SHA-256
  `d3a99def267b8654b98d605f42c476cc2cbd897a3d8713a66193145f929b9072`.
- Previous setup used for upgrade/rollback: 0.9.1, build `f877fa26ee724479`;
  SHA-256 `afb8c9fb4bd05947b3c3454ee4d559279da76073c9a719670c2da62951780d89`.
- Owner authorized display/installation/clean-VM tests and reported a Desktop
  restart. No owner application was stopped, installation replaced, data imported,
  host rebooted or host suspended by these checks.
- Installed monitor manifest matches 0.9.3. Desktop still launches the old
  source bridge; installed data has no connection registration receipt.

## Results

| ID | Mode | Status | Evidence | Limit |
| --- | --- | --- | --- | --- |
| ENV-INSTALLED | Read-only owner installation | PASS | Active version/build/router build match the exact 0.9.3 setup | Distinct from loaded bridge |
| TEL-DESKTOP-INSTALLED | Read-only owner processes/registration | BLOCKED | Desktop still uses legacy source bridge; installed registration absent | Restart alone cannot transfer the connection |
| UI-SHARED | Chromium fixtures | PASS | All seven layout/interaction groups, including 100/125/150/200% scale, compact resize and Hidden/Compact restoration | Simulated DPI; no physical input or display switch |
| UI-NATIVE | 0.9.4 relocated frozen WebView2 fixture and guest | PASS | CSS/native region match at startup, resize and hide/show; assembly/runtime identities agree | Synthetic data and scripted interactions |
| INSTALL-FIXTURE | 0.9.4 isolated native setups | PASS | Install, upgrade 0.9.1 to 0.9.4, locked-file rejection, rollback, uninstall, reinstall, retained config/history | Fixture AppId; no owner registration |
| INSTALL-SHORTCUTS | Unique fixture Start-menu group | PASS | Three shortcuts; stable launcher target and status/recovery arguments; removal after uninstall | Real production registration tested separately |
| KEY-IMPORT | Synthetic native fixture | PASS | DPAPI CurrentUser secret imported and decryptable; source preserved | Same OS/user only |
| KEY-OWNER | Read-only native check | PASS | Imported existing encrypted key decrypts; plaintext neither printed nor retained | No provider/network request |
| CORE-SCOPED | Source tests | PASS | 33 tests: installation, build identity, Desktop, five compiled native disconnection regressions | Native tests redirect only their private source copy to a disposable registry key; owner's Environment untouched |
| INSTALL-CLEAN | Production setup in clean Windows evaluation VM | PASS 0.9.4 | All 24 assertions; real uninstall key/menu, standard-user install/uninstall, failure guards, upgrade/rollback, native WebView/capsule, retained data | Same clean VM repeated after restoring known synthetic fixture state; no developer Python/source/Desktop login |
| INSTALL-CONNECTED-RECOVERY | Production setup upgrade 0.9.3 to 0.9.4 in guest | PASS 0.9.4 | Eight recovery checks; connected uninstall succeeds and preserves prior value/type, config/history/DPAPI | Original 0.9.3 refusal preserved below; owner's installation not upgraded |
| UI-DISPLAY | Physical host | NOT_RUN | Only one connected display | Requires two physical monitors |
| UI-SCALE-PHYSICAL | Physical host | NOT_RUN | Owner initially sees no visual problem; automated fractional-DPI fixtures pass | Does not establish physical interactions at every scale |
| UI-INPUT / UI-SLEEP | Physical host | NOT_RUN | UI provider did not expose router windows; no owner sleep/reboot performed | Do not infer first-click, tray or resume from fixtures |

## Clean Windows environment

Hyper-V was already enabled. Its VM management service was started with owner
authorization; no existing VMs were present. Windows Sandbox was briefly enabled
with `-NoRestart`, then restored to its original Disabled state without reboot.
The management service was restored to its original Stopped state after QA.

The clean guest uses official Windows Enterprise evaluation media verified
against Microsoft's published SHA-256, a synthetic local QA account and public
installer inputs only. Its generated account secret and raw logs remain in
ignored state. No owner credentials, prompts, history, Desktop login or live
inference are used. The 0.9.4 full guest repeat completed successfully at
`2026-10-07T08:11:53Z`; all 24 assertions pass. Stock Windows already included
WebView2, so missing-runtime download/interactive prerequisite consent was not
exercised. Developer Python and source checkout are absent.

The guest was initially clean. Following the 0.9.3 failure, the real 0.9.4 setup
recovered that installation and all eight recovery checks passed. Only known
synthetic fixture data/environment were then reset for the full 0.9.1 to 0.9.4
production lifecycle repeat in the same VM. This is not a second independent OS
installation. The full repeat ran in the synthetic user's interactive session.

The successful VM is stopped with automatic startup disabled. Two failed QA VM
configurations were retired and their two large temporary disks removed; private
diagnostics remain ignored. No owner application was stopped or replaced.

Preparation exposed QA infrastructure issues before the production setup ran:
the initial Hyper-V automatic checkpoint left a differencing disk, and a writable
base mount caused a parent identifier mismatch (`0xC03A000E`). The failed chain
was retained; no identifiers were forced. A separate clean image/VM is used for
the next attempt, with automatic checkpoints disabled before boot.

Host RAM reservation prevented a 4 GiB startup (`0x8007000E`); the QA VM uses
3 GiB startup, 2–4 GiB dynamic memory and 2 CPUs without closing owner apps.
This is an installer check, not Windows hardware-minimum or performance acceptance.
The retry also exposed a QA helper resetting an existing virtual TPM protector
(`0xC000A002`); retry now preserves it. The disposable VM configuration was
re-created with its owned disks only. No host TPM/firmware security was changed.
WinPE boot setup now selects the marked basic Windows volume, which also selects
its disk, avoiding localized DiskPart table parsing and assumed disk numbers.

Official references: [evaluation media](https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise),
[DiskPart focus](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/diskpart),
[virtual TPM troubleshooting](https://learn.microsoft.com/en-us/troubleshoot/windows-server/virtualization/virtual-shielded-host-guardian-service).
Verified evaluation ISO SHA-256:
`bc3f24086ebadc94489066b5ad78089e2cf5c3491e90e790bb81a2b199c10e38`.

## Product failure found and corrected

The initial 0.9.3 guest run passed install, upgrade, rollback, standard-user,
permission/disk-space and native UI checks. Foreign connection refusal also
passed. The following owned connected uninstall failed with exit 1; the native
preflight passed, and the uninstall log identified connection removal as the
failing step. This reproduced after waiting, ruling out finalizer timing.

`Path.Combine(ApplicationRoot, "bin/codex-router.exe")` kept a forward slash,
while the real connection receipt used Windows backslashes. Native comparison
therefore rejected its own wrapper. Version 0.9.4 uses normalized owned paths
and continues preserving foreign connections. Five compiled native tests verify
Windows and forward-slash aliases, literal ExpandString restoration, absent
previous values and both foreign current/receipt refusals. Guest recovery and
the complete 0.9.4 lifecycle repeat pass; this does not retroactively mark 0.9.3
connected uninstall as passing.

## Fixture correction

An initial shortcut check failed because the fixture passed `/GROUP` while the
installer hides the group-selection page. Inno then uses `DefaultGroupName`.
The fixture now changes that value only in its private script, giving each test
a unique group. The test-created links from the failed attempt were verified
to point exclusively at its temporary fixture and moved into ignored quarantine.
The product installer was not changed by this fixture correction.

## Remaining work

At an owner-selected break, close Desktop/legacy components, upgrade the owner's
0.9.3 installation with the validated 0.9.4 setup and use the installed monitor's
Settings connection action, then reopen Desktop. Recheck actual loaded
bridge identity and native telemetry. Existing imported data is valid; do not
repeat import into the occupied data directory.

Physical input, two-display behavior, sleep/resume, interactive cancellation and
missing-prerequisite installation remain separate acceptance gates. This receipt
does not establish macOS/Ubuntu acceptance, signing, public
distribution, automatic update execution or live inference on a clean guest.
