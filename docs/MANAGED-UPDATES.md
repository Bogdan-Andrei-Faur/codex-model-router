# Authenticated managed updates — 2026-10-11

The owner personally accepted Windows/Ubuntu installation and waived a clean-Mac
prerequisite on2026-10-11. Installer publication is authorized, awaiting transfer
of the exact tested binaries from the other computers. See
[the owner decision](native-validation/2026-10-11-owner-installation-acceptance.md).
This closes installation acceptance; update/recovery coverage remains as below.

## What is implemented

Settings uses the canonical public GitHub latest-release endpoint. A newer release
must have the exact OS/architecture installer name plus
`codex-model-router-update.json`. An Ed25519 signature authenticates repository,
version, target, size, SHA-256 and expiry against public keys shipped with the
installed application. Downloaded keys and writable user preferences cannot add
publishers. A configured keyring rejects missing/invalid signatures; it does not
silently fall back to hash-only updates. Preview/read-only views cannot update.

| Host | Current operation | Remaining acceptance |
| --- | --- | --- |
| Packaged macOS, app writable by its user | Check → Update → real GitHub download/verify → installation-owned helper → replace → launch → WebKit/data acknowledgement PASS in isolated native Settings; owner Installer/import/connection also verified; restore previous app on launch failure tested locally | Downloaded-quarantine/clean-machine Gatekeeper, actual login/power-loss recovery, physical input and real provider credential use |
| Source-backed macOS | Signed download only; no managed replacement of a checkout | Migrate to packaged app when owner is ready |
| Packaged Windows with managed protocol 1 | Signed installer handoff, automatic native close/relaunch, version-selector rollback and login recovery implemented | Native Inno/WebView2/WPF, locked files, cancellation/recovery and real GitHub run pending |
| Packaged Ubuntu with managed protocol 1 | Signed per-user payload update, automatic GTK close/relaunch, atomic selection/rollback and login recovery implemented; apt baseline retained | Real signed-helper/new GTK readiness and rollback/replay pass in Ubuntu24.04 arm64 Docker; Settings actions, physical XDG/login/apt coexistence and real GitHub run pending |

The [public 0.9.7 Release](https://github.com/Bogdan-Andrei-Faur/codex-model-router/releases/tag/v0.9.7)
contains the arm64 Mac installer, signed manifest, checksums and public build
provenance. The real Settings update test uses an isolated synthetic 0.9.6 old
installation and downloads the exact published 0.9.7 package anonymously. Earlier
local transport fixtures remain separate evidence. See [the receipt](native-validation/2026-10-10-macos-github-update.md).
Opt-in daily checking exists; installation still requires the explicit Update
button. Desktop and active agents are never terminated by the updater.

## Authentication and key custody

The owner approved a project signing key in this Mac's Keychain. The public key ID
is `f6e9b7030520f8335f4669f86c03a20dd826dd08100309917636c67963a114ff`, stored in
`assets/update-trust.json`. The private key is a device-only, unlocked-Keychain
item under service `local.codex-model-router.release-signing.v1`, account
`ed25519-publisher`. The native utility emits public bytes or signatures, never
private key bytes. No private key, key backup or secret is in Git or CI.

This is project-level authenticity, **not** Apple Developer ID/notarization or
Windows Authenticode. First installation still needs honest platform acceptance
instructions; [Apple's distribution guidance](https://developer.apple.com/developer-id/)
remains a separate gate. No Apple Developer account was provisioned.

The signed envelope is capped at64KiB, rejects duplicate JSON keys, and uses the
fixed `codex-model-router/release-manifest/v1` domain. Manifests expire after30 days
by default (maximum180); renew the signed manifest for an unchanged stable release
before expiry. An expired latest manifest blocks downloads, rather than implying
up-to-date status. Keep the published assets immutable while renewing metadata.

Before losing/replacing this Mac, arrange deliberate key rotation: ship a new
public key in an update signed by a still-trusted key. No private-key export or
recovery backup exists currently. Losing the sole key without rotation requires
a separately authenticated manual reinstall. Do not silently generate a new key
and assume existing installations will trust it.

## Developer-only release preparation

Use the pinned portable Mac interpreter and prepared dependency notices described
in [the handoff build recipe](HANDOFF.md#reconstruir-el-paquete-mac-experimental).
Mac packaging rejects an unprepared interpreter (including Xcode Python). Its
CPython archive and full licensing metadata are SHA-256 pinned for each target.
`prepare_runtime_notices.py` reads the exact installed crypto wheel SBOMs, verifies
source archives, collects crate/OpenSSL notices and the compiler-matched Rust
standard-library notices. The generated inventory is a conservative superset,
not an assertion every build/all-target dependency is shipped. Packaging copies
only listed, reverified texts offline; no source archives enter the installer.
The end-user needs neither this build environment nor a source checkout.
Compile `native/macos/ReleaseSigner.swift` with Swift/CryptoKit/Security; `public`
reads its public key and `create` creates only if absent. Do not run `create` on
another host as a substitute for the approved publisher.

`tools/packaging/release_manifest.py sign --keychain-helper <compiled-helper>
--version <version> --asset macos/arm64 <canonical.pkg> --output
<codex-model-router-update.json>` produces offline signed metadata. Repeat
`--asset` for each **actually validated** Windows/Ubuntu/other architecture target.
The optional encrypted-PEM signer is available for separately approved custody;
its password is interactive and its private file must stay outside the checkout.
Neither utility uploads files or creates/releases a GitHub release.

Build all installers from one immutable source revision, review dependencies and
notices for the exact artifacts, sign the final unchanged bytes, assemble a draft
release, and verify every public URL/digest/signature before stable promotion.
Do not label an unvalidated architecture supported merely by renaming its file.
Never upload local job archives, runtime data, private backups or fixture state.

## Mac transaction and migration

The `.pkg` selects the current user's domain (`~/Applications`) and includes a
bundled runtime. The managed update does not execute package scripts: it extracts
one authenticated, script-free app, checks its identity, version, tree and ad-hoc
code integrity, then rechecks its bytes with the copied **old installed runtime**.
It refuses downgrades, active Desktop bridge snapshots and unwritable installs.
A download/verification failure leaves the running app unchanged. Cancel is
available before handoff; after commit begins the updater finishes or recovers.

Before closing the monitor, the helper prepares a replacement beside the owned
application and reports ready-to-close. A per-parent lock serializes replacements;
the monitor lock gates the two renames. The old app remains as
`.router-previous-<job>.app`. A successful new native WebKit/data acknowledgement
completes the transaction. Startup failure restores and launches the previous
app. Safe result metadata appears in Settings. Recovery jobs retry interrupted
commits at the next GUI login through a user LaunchAgent; terminal jobs remove
their registration. Actual logout/power-loss execution still needs native QA.

User configuration, credential handles, history and metrics are outside the app
and are not modified by replacement. Previous app/job artifacts are retained;
automatic backup pruning and user-facing manual rollback selection are not yet
implemented. Do not delete them while an operation or recovery is pending.

First launch offers Import / Start fresh / Cancel before creating data. Import
preserves the source and refuses occupied targets, active bridges/monitors,
symlinks, changing files and foreign-platform configurations. It includes known
configuration, characters, history/prompts, task/workload records, preferences
and opaque credential namespaces. It does not decrypt secrets or transfer the
Desktop connection automatically. Unknown state/caches and raw OTLP archives are
left in the original source folder; do not claim a complete raw-archive migration.
The native dialog calls the guarded import on first run; owner migration and
connection transfer passed on 2026-10-10, with originals preserved. See
[the installation receipt](native-validation/2026-10-10-macos-pilot-installation.md).

## Reproducible verification

`tests/test_update_trust.py` covers signature tampering, wrong publisher/target,
expiry, malformed metadata, signed manager flow and handoff exclusion.
`tests/test_update_install.py` covers replacement, rollback, interrupted renames,
byte/link validation, environment isolation and terminal recovery cleanup.
`tests/test_monitor_updates.cjs` checks Settings actions and recovery messaging.

On a logged-in Mac, `tests/smoke_update_macos.py <old.pkg> <new.pkg>
<signed-manifest.json>` uses isolated data/apps, the actual frozen helper and native
hosts, checks preflight cancellation and preserves owner installations. It signals
only its own old fixture monitor after handoff, so it does not establish a native
Settings-button click or login recovery. `tests/smoke_package_macos.py <pkg>`
checks relocation, empty-PATH runtime/IPC and packaged WebKit readiness separately.

See the [native receipt](native-validation/2026-10-09-macos-managed-update.md).
Windows and Ubuntu must run their own native cases. WPF only needs validation
when using Windows; Mac evidence is not WPF acceptance.

The follow-up `tests/probe_mac_settings_update.py --python <build-python>
--package <new.pkg> --signature <signed-manifest> --output <new-fixture-dir>` builds
a test-only old snapshot. Its native WebKit driver uses real Settings controls
while the window remains hidden; transport is replaced with signed local fixture
files only in that snapshot. It covers cancel/retry, automatic host exit, native
readiness, forced-readiness rollback, and actual helper interruption after the
first rename followed by replay. No test hook or alternate update URL is added to
the production application. See [the portable Settings receipt](native-validation/2026-10-09-macos-portable-settings.md).

For an owner-authorized public release, use the same probe with `--github-release`
and omit `--signature`. It builds an isolated synthetic old version and retains
the production anonymous latest-release fetcher and download transport. Its
hidden native Settings driver clicks Check and Update once, verifies the downloaded
package against the supplied release artifact, and requires automatic exit,
replacement, native readiness and preserved fixture configuration. It runs only
the success case; the local cancellation/recovery cases remain separate evidence.
The supplied package is an expected-byte comparison, never a download substitute.
Recovery registration is redirected into the fixture. The owner's installation,
Desktop processes and data are not replaced or stopped.

## Windows/Ubuntu transaction contract (source implementation)

`update_portable.py` copies the old installed runtime before handoff, rechecks the
signed bytes in the helper, refuses active bridge snapshots, waits for the native
monitor's lifecycle lease and preserves the old selection. Both native hosts
close only themselves when the shared updater requests it. Completion requires a
successful new UI snapshot acknowledgement, not merely installer exit status.
Recovery uses HKCU Run on Windows and XDG autostart on Ubuntu; retained runtimes
and jobs are not pruned automatically. Native execution remains unverified here.

Windows runs the authenticated per-user Inno installer with explicit
[no-restart/no-application-close switches](https://jrsoftware.org/ishelp/topic_setupcmdline.htm).
Rollback restores the previous version selection; stable launcher compatibility
and uninstall-registry behavior are native gates. Ubuntu installs a signed
user-scoped runtime while keeping the system .deb as its dependency/bootstrap
baseline. It does not claim to update dpkg's installed version. Changes to system
dependencies require a new baseline package/protocol.

The existing public packages do not gain new host hooks retroactively. A native
protocol-1 baseline must be installed once before testing Settings updates. No
Windows/Ubuntu Release assets have been published for this implementation. Follow
[the complete per-machine runbook](native-validation/WINDOWS-UBUNTU-UPDATES.md).
