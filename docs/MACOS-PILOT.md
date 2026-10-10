# Mac 0.9.7 pilot

The owner chose a Mac-first pilot; Windows/Ubuntu follow independently. The local
candidate targets **Apple Silicon (arm64)**. Intel Mac, Windows and Ubuntu are not
validated by this artifact. [Version 0.9.7 is published](https://github.com/Bogdan-Andrei-Faur/codex-model-router/releases/tag/v0.9.7)
from source `8d6fb670010311239c657ee676c8b6d8183be193`, with the exact owner-installed
package and a project-signed update manifest.

The owner waived a clean-Mac validation prerequisite on2026-10-11. It does not
block this delivery; no clean-machine PASS or notarization is implied. See
[the owner decision](native-validation/2026-10-11-owner-installation-acceptance.md).

## Current local installation

The owner-authorized 2026-10-10 build `992cea11bb136ed0` is now installed through
macOS Installer in user Applications. First-run import (199 files) and explicit
connection transfer are complete. After the owner's normal restart, Desktop uses
the installed managed bridge with matching fingerprints, completed handshake and
advancing authenticated telemetry. No restart/mismatch flags remain. Post-import
source history/prompts are reconciled without added duplicates; originals and
private backups remain intact. Do not re-import. See [the receipt](native-validation/2026-10-10-macos-pilot-installation.md).
The earlier package described below remains preserved as historical evidence.

## Candidate freshness

The previously prepared 0.9.7 package predates the 2026-10-10 companion laptop,
neutral appearance-preview and compact-context-bar corrections. It remains intact
and must not be described as containing those changes. Build/sign a new candidate
with its own hashes and repeat artifact checks before coordinated owner installation.
That rebuild and coordinated installation are complete in the 2026-10-10 receipt
above; its exact package contains the fixes. The earlier artifact stays historical.

## What to expect

The installer contains the native monitor, bridge, portable Python runtime and
dependency notices. End users do not need Git, Python, Xcode or terminal commands.
Updates in the packaged app use Settings → Check → Update, with project-signature
verification, automatic monitor exit/relaunch and retention of the previous app.
Automatic checking does not authorize unattended installation or a Desktop restart.

The project signature authenticates updates inside the app; it is **not** Apple
Developer ID/notarization. On first installation macOS may require an explicit
exception for this particular package/app. Follow [Apple's current instructions](https://support.apple.com/es-es/102445)
in System Settings → Privacy & Security after trying to open it. Do not disable
Gatekeeper globally. Stop and record an unexpected damaged/malware warning rather
than treating it as the ordinary unidentified-developer prompt.

## Coordinated owner installation

1. Finish active agent work before migration. Close Codex/ChatGPT and the old
   monitor before importing its data. Installing this pilot is not permission
   for an agent to terminate those applications or lose current work.
2. Open `codex-model-router-0.9.7-macos-arm64.pkg` in Installer. The package selects
   the current-user domain and installs `~/Applications/Codex Model Router.app`.
   Record the actual Installer/Gatekeeper result; extraction alone is not this test.
3. Open the new app from Finder. Choose **Importar instalación…** and select the
   prior installation folder containing `config.local.json`. The original stays
   intact. If the destination already contains data, coordinate a separate migration
   plan; do not delete it or choose Start fresh to work around the guard.
4. Check retained settings, characters, history and credential availability. No
   provider call is needed just to inspect configuration. Raw OTLP archives remain
   in the source folder; the importer does not claim to migrate every cache/file.
5. In Settings → Connection, prepare the normal Desktop startup connection, then
   reopen Desktop when ready. Record the installed artifact separately from the
   bridge that the fresh Desktop process actually loads.
6. Record the outcome with `docs/native-validation/REPORT-TEMPLATE.md`. Keep the
   previous source installation and data until native acceptance is complete.

**Comprobar ahora** now reads the public 0.9.7 Release. An older eligible packaged
Mac can use Update; a 0.9.7 installation is already at that published version.
The real anonymous GitHub download and native Settings update passed on an isolated
synthetic 0.9.6 installation. See [the exact receipt](native-validation/2026-10-10-macos-github-update.md).
Other architectures have no installer asset in this release. Prereleases remain
excluded from the stable latest-release endpoint.

## Pilot acceptance and publication

Publication is complete: current-user Installer/import, artifact notices and
signature checks, fixed published source, and real GitHub discovery/download/update
on a disposable older installation. Retain precise local package hashes when rebuilding, as signing and package
timestamps can change bytes without changing the monitor build fingerprint.

Actual login/reboot recovery and real provider credential use remain distinct
from the verified owner connection/namespace retention and isolated Settings/
cancel/rollback/helper-crash cases. Windows and
Ubuntu still need native managed-apply adapters. WPF only needs validation when
using Windows.

See [portable native evidence](native-validation/2026-10-09-macos-portable-settings.md),
[managed updates](MANAGED-UPDATES.md) and [handoff](HANDOFF.md).
