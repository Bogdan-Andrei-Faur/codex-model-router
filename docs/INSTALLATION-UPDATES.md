# Graphical installation and updates

2026-10-09 distribution decision: the owner selected the canonical repository
itself for eventual public installers, accepted GitHub platform forks and chose
personal/noncommercial source-available licensing. The clean canonical source
repository is now public; the original is retained as a private archive. See
[the publication receipt](HISTORY-CLEANUP.md). This supersedes the historical
artifact-only channel proposal below; see [DISTRIBUTION-PLAN.md](DISTRIBUTION-PLAN.md) for the exact update flow,
publication prerequisites and current implementation gaps.

Owner-approved direction (2026-10-04): one shared product, distributed as a macOS
`.pkg`, Windows `-setup.exe` and Ubuntu `.deb`. The installed application must work
without a checkout, development Python, compilation or terminal commands. Settings
must check for releases, download a compatible prebuilt installer and eventually
apply it with managed monitor relaunch. Installation and updates preserve account
credentials, settings, task modes and private telemetry.

## Current implementation boundary

`src/codex_model_router/updates.py` provides shared asynchronous stable-release discovery and download
staging. Settings exposes installed/latest version, explicit checks, opt-in daily
checks, progress and cancellation. All three native hosts forward the same actions
through the shared monitor model. Preview cannot start updates.

Discovery queries only the canonical repository's public GitHub latest-release
endpoint, without account tokens or application data. A missing/private/inaccessible
release, network error or rate limit is an unknown state, never proof of being up to
date. Daily checks are opt-in and rate bounded per running monitor. Legacy keyless
installations provide hash-only downloads. New builds additionally require an
Ed25519 release manifest authenticated by bundled public keys. Eligible packaged
Mac builds can apply through the installed helper; Windows, Ubuntu and source-backed
Mac still disable apply. See [MANAGED-UPDATES.md](MANAGED-UPDATES.md) for custody,
recovery and acceptance limits.

Asset naming contract (version excludes the optional `v` tag prefix):

| Platform | Release asset |
| --- | --- |
| macOS | `codex-model-router-{version}-macos-{arch}.pkg` |
| Windows | `codex-model-router-{version}-windows-{arch}-setup.exe` |
| Ubuntu | `codex-model-router-{version}-linux-{arch}.deb` |

`arch` is `arm64`, `x64` or `x86`; the publisher must only produce supported targets.
No architecture fallback is permitted. Drafts, prereleases, downgrades, duplicate
matching assets, foreign repository links, missing SHA-256 digests and invalid
sizes are rejected. TLS redirects stay on an explicit GitHub transport allowlist.
Metadata is bounded at 1 MiB and installers at 512 MiB. A private temporary download
is promoted only after exact byte-count and SHA-256 checks; cancellation discards
partial files and late responses. The safe receipt contains no credentials or URL.
Staging currently uses the existing data root's `state/updates` directory.

## Portable macOS package implemented — 2026-10-04

`src/codex_model_router/platforms/application_layout.py` separates immutable resources from per-user data while
preserving legacy checkout mode. Packaged Mac defaults to
`~/Library/Application Support/codex-model-router`; Windows/Linux user-data paths
are defined and tested. Ubuntu packaging is described below; Windows setup is
implemented in the 0.9.0 local pilot below. Existing configuration is never replaced by bootstrap. Packaged identity
comes from the embedded build stamp, not a VERSION file in the data directory.

`tools/packaging/package_macos.py` builds a fresh local `.pkg` with an AppKit/WebKit host, native
`native/macos/BridgeMac.swift` launcher and console-capable nested runtime bundle produced by
pinned PyInstaller6.22.3. The nested bundle keeps macOS code/framework/resource
layout and private JSONL stdin/stdout intact. Only source code and selected public
assets enter packaging; repository state, local config, prompts and keys do not.
Build outputs and isolated dependency environments are preserved separately.
Ad-hoc signatures allow local code-integrity verification, **not publisher trust**.

The artifact was extracted with `pkgutil`, relocated and deep/strict verified.
Its embedded runtime and monitor IPC worked with an empty executable search path,
with no source-checkout access or developer Python. The exact packaged native
monitor reached WebKit readiness and started its bundled child in a synthetic
preview. Version forwarding used the original Desktop Codex CLI with standard OS
utilities available. No provider inference, integration registration or system
installer execution was performed. Repeated bootstrap preserved fixture settings.
This is artifact/runtime acceptance, not clean-machine Installer/Gatekeeper QA.

`src/codex_model_router/platforms/installation_migration.py` imports known product data into a new, independent
root: configuration, history/prompts, task modes/workloads, monitor preferences
and opaque credential metadata/blobs. Original data files remain unchanged;
coordination lock files may be created. Active bridge snapshots, occupied targets,
symlinks, cross-platform config and changing files are rejected. Keychain/Secret
Service namespace is retained without retrieving/decrypting keys. Build trees,
unknown state, caches, status snapshots and Desktop registration are not copied.
On macOS import is now connected to the first-run native dialog. Ubuntu now integrates it in its
first-run GUI, with a separately requested connection transfer. The existing live
source-based installation has not been migrated by the package validation.

The owner confirms no Apple Developer account. No Developer ID signing identity
was found locally. The canonical source repository is confirmed private: its
anonymous GitHub release query cannot currently supply public update downloads.
A public artifact-only distribution channel can keep the code private; it remains
a proposal, not a created repository or published release. Publisher trust,
notarization or an explicitly chosen alternative distribution experience remain
owner decisions. No signing account, certificate, persistent signing key, hosting
purchase or public release was created.

## Ubuntu native package implemented — 2026-10-05

`tools/packaging/build_linux_package.py` creates a `.deb` with the shared Python engine, monitor
assets and `linux-deb-v1` manifest. Runtime dependencies are installed by APT;
there is no development interpreter, virtualenv, checkout or pip requirement.
The application lives in `/usr/lib/codex-model-router`, with independent XDG user
data. Unlike the macOS runtime freeze, Ubuntu uses distribution-maintained Python
and GTK/WebKit libraries. No official Codex engine is shipped or modified.

The GTK first-run dialog supports cancel, new configuration and offline import.
Import keeps original files and credential namespaces; activation through Settings
verifies and transfers an owned Desktop shortcut separately. User launchers fall
back to the original Desktop command when APT removes the package. No maintainer
scripts read/write user homes, stop applications or register Desktop automatically.

The real package is tested through APT in disposable Ubuntu 24.04 and 26.04 x86_64
containers, using unprivileged runtime/IPC and synthetic configuration/history.
Install, upgrade, remove, purge and reinstall retain user data. Extracted package
tests run GTK onboarding and the shared WebKit preview under Xvfb on Ubuntu 26.04.
CI includes these lifecycle cases plus Ubuntu native UI readiness. These checks
do not certify a full GNOME session, ARM, publisher identity or live migration of
the owner's installation. Local artifacts use Debian version/revision names;
mapping tested targets to public update assets remains part of release delivery.

## Remaining delivery stages (historical baseline below)

Windows 0.9.6 has a per-user Inno setup builder with a frozen runtime,
side-by-side version folders, independent user data, native first-run import,
guarded legacy connection adoption, prerequisite/publisher checks for Microsoft's
WebView2 bootstrapper and native disconnect/rollback. See [WINDOWS-INSTALLER.md](WINDOWS-INSTALLER.md)
for build and acceptance evidence. Version 0.9.4 passes the production lifecycle
in a clean Windows VM, including native connected uninstall. Version 0.9.5 fixes
stale reused PIDs blocking connection migration and passes frozen/native/setup
fixtures. Version 0.9.6 additionally passes interactive native protocol and UI
progress fixtures. The unsigned setup is now installed on the owner host, with
verified registration. After the owner's restart, the installed 0.9.6 Desktop
handshake, matching identity and authenticated telemetry also pass. Physical
input/display/sleep and latest clean-VM acceptance remain separate gates. See the [connection repair receipt](native-validation/2026-10-07-windows-connection-repair-host-a.md).
The legacy ZIP builder remains available for backwards compatibility. This does
not change the shared update boundary: no trusted automatic installer execution.

1. Separate immutable application resources/runtime from per-user writable data.
   Remove installed launchers' dependence on the source checkout and developer
   interpreter. Bundle the runtime and shared monitor assets. Migrate existing
   data without deleting it, including credential handles and integration settings.
2. Produce native installers in isolated platform builds. macOS needs a signed,
   notarized app/package; Windows needs signed setup and WebView2/runtime handling;
   Ubuntu needs dependency integration and a trusted package distribution path.
   Pin build inputs, publish checksums and verify the actual installed version.
3. Add a trusted apply helper owned by the installation, not downloaded code.
   Verify publisher identity before execution, recheck staged bytes, acquire an
   update lock, preserve data, wait for safe lifecycle boundaries, run the platform
   installer and relaunch the monitor. Report privilege prompts and installation
   failures honestly; keep the previous installation recoverable.
4. Update the routing bridge separately from the monitor lifecycle. Existing
   Desktop sessions must remain operational. If backend changes require a new
   Desktop process, report pending activation and ask the owner to choose its
   restart time. Never restart Desktop or abandon active agent work silently.
5. Validate fresh install, upgrade, cancellation, failure/recovery, uninstall/data
   retention and relaunch on real macOS, Ubuntu and Windows machines. Cross-builds
   and browser fixtures do not establish native installation acceptance.

The historical discovery/staging slice did not imply self-update acceptance.
The current [managed-update contract](MANAGED-UPDATES.md) supersedes its
Mac apply and signing boundaries, without claiming all-platform acceptance. Windows/Ubuntu
native validation requires access to those systems.
