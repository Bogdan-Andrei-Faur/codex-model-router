# Mac 0.9.7 pilot

The owner chose a Mac-first pilot; Windows/Ubuntu follow independently. The local
candidate targets **Apple Silicon (arm64)**. Intel Mac, Windows and Ubuntu are not
validated by this artifact. Version 0.9.7 is prepared locally, not published as a
GitHub Release. The source changes have not yet been committed or pushed.

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

No installer Release exists yet, so **Comprobar ahora** currently reports that
no public release is available. This is expected, not proof the installed app is
up to date. A pilot marked prerelease on GitHub would also be excluded from the
stable latest-release endpoint. Do not mark an unvalidated artifact stable just
to make that check pass.

## Pilot acceptance and publication

Before stable publication: current-user Installer/first-run acceptance, exact
artifact notices/signature review, source revision fixed and published with owner
authorization, then real GitHub discovery/download on a disposable older installed
target. Retain precise local package hashes when rebuilding, as signing and package
timestamps can change bytes without changing the monitor build fingerprint.

Actual login/reboot recovery and real provider credential use remain distinct
from the verified owner connection/namespace retention and isolated Settings/
cancel/rollback/helper-crash cases. Windows and
Ubuntu still need native managed-apply adapters. WPF only needs validation when
using Windows.

See [portable native evidence](native-validation/2026-10-09-macos-portable-settings.md),
[managed updates](MANAGED-UPDATES.md) and [handoff](HANDOFF.md).
