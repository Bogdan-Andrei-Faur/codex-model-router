# Mac pilot installation — 2026-10-10

## Scope

Owner requested installation and confirmed other agents finished. Source main
`c0667cf1cec97f1655b5ef67b50efbd396a7cd52` plus preserved local packaging and
companion changes. No commit, push, Release or Desktop restart occurred.

## Artifact and actual Installer result

Fresh arm64 0.9.7 package: monitor `992cea11bb136ed0`, router `0c8570cfccd9a1a8`.
SHA-256 `8e5b7489f306465721bd27a4467dab018d876b4234b2ad1e8f3656552eff56b2`.
Build source snapshot SHA-256
`ec6d1e8246b21bbfe774e9a791014bdc891080400b236df055227e8f83d5ba29`.
Ignored delivery: `release/macos-pilot-20261010/delivery/`; original pilot and
previous inactive application preserved separately. Manifest signed by the
owner-approved Keychain publisher. This is not Apple Developer ID/notarization.

Exact package passes extraction/relocation, empty-PATH runtime/IPC, native monitor
startup, official backend version forwarding, 98 notice hashes and six Mach-O
non-system-dependency checks. The graphical macOS Installer selected current-user
home installation and displayed successful completion. No password/security
exception was needed on this local host. This does not prove downloaded-package
quarantine/Gatekeeper or clean-machine acceptance.

Installed `~/Applications/Codex Model Router.app` has matching version/build,
valid ad-hoc signature and exact current monitor.js/css/characters.js/scenes.js.
Its native first-run welcome is visible with Import, Start fresh and Cancel.

## Initial post-install state (superseded by activation below)

The old source-backed monitor was closed normally by SIGTERM for this authorized
update. Codex/ChatGPT and its bridge were not stopped. Original config and
appearance file bytes match their pre-install hashes. No managed data/config was
created and no source data moved, deleted or imported.

Owner must close Codex/ChatGPT before guarded import; select the original checkout
folder through Import installation. Do not choose Start fresh. Import preserves
source data and credential namespace; actual retained history/credentials and
connection transfer still require verification. Mac connection ownership must be
transferred from the original installation explicitly before claiming installed
bridge activation; importing alone does not transfer it. Preserve both installations
until that is complete. This chat still uses its existing bridge.

Not proven: managed live monitor readiness after import, installed bridge handshake,
natural companion acceptance, real GitHub download, reboot recovery, Intel Mac,
Windows or Ubuntu acceptance.

## Owner import and connection transfer follow-up

Owner reports offline import completed after closing/reopening Desktop. Verified
199 imported files, exact semantic config equality, exact appearance bytes and
preserved Mac UI settings at import. Imported history (74,479 lines) and prompts
(772 lines) are intact prefixes of the original files; the current source bridge
has appended subsequent records. Keep the original installation until those
post-import records can be reconciled after its bridge exits. Credential namespace
matches the original source; key material was not read or moved. This verifies
references, not a real provider request or full credential-use acceptance.

The imported application is running: exactly one installed native monitor and its
bundled runtime child. Owner-authorized connection transfer used the original
registered interpreter to disconnect source ownership and the installed frozen
runtime to register its own bridge. Before mutation, exact launchctl/registration
ownership was checked and rollback metadata copied privately. Installed bridge
preflight initialize/model-list PASS; source registration removed, installed
registration and per-user launch agent match the exact installed wrapper/runtime.
Config and character choices remain unchanged. No Desktop process was stopped.

State before the second owner restart: managed snapshot reports zero connections and restart pending;
one fresh source bridge remains active with product0.9.7/build992cea11bb136ed0/
router0c8570cfccd9a1a8. Matching fingerprints do not establish that Desktop uses
the installed data/runtime. Owner must quit/reopen Desktop normally once more.
Then verify fresh managed handshake/heartbeat and reconcile post-import source
history without removing originals. Do not re-import into the occupied destination.
Actual new-root telemetry, provider credential use, natural animations and public
GitHub update remain unproven.

## Managed activation after owner restart

The owner restarted Desktop normally and reported completion. The installed
runtime's monitor IPC snapshot now reports product 0.9.7, one ordinary Desktop
connection, completed native handshake and matching loaded router
`0c8570cfccd9a1a8` / monitor `992cea11bb136ed0`. Build mismatch, unknown build,
restart required and Desktop restart pending are all false. No fresh source
bridge remains. The native installed monitor continues running; the agent did
not restart Desktop or replace another installation during this follow-up.

Authenticated ordinary-Desktop telemetry advanced from 15 to 80 requests, 70 to 439
scanned records and 3 to 59 completion records during observation. Unauthorized,
invalid request/payload/size, rejected connection and identity-conflict counters
are zero in that connection. Separate non-Desktop protocol probes are excluded
from this live-Desktop claim. Attribution is 54 probable, 0 confirmed and 5
unattributed completions at the later snapshot. Receipt and accepted settings
alone do not prove that a specific inference used a requested model or phase.

## Post-import journal reconciliation

After the source bridge stopped, compared the complete JSONL journals privately.
The imported common prefixes contain 74,479 history and 772 prompt records. Restored
the missing 60 history and one private prompt record into the managed destination.
At the locked merge instant, history grew 74,658→74,718 records and prompts 777→778;
live appends continue afterwards. Both tails had valid records, complete newlines
and monotonic numeric timestamps. The common prefix was preserved byte-for-byte;
the tails were merged by timestamp without adding duplicates. All pre-existing
managed records and all source records are retained. Original files are unchanged.

Used the same history/prompts cross-process locks as production writers, private
pre-merge backups, fsync and atomic replacement. The monitor journal detects inode
replacement and rebuilds its projection; the installed IPC subsequently returned
1,043 projected decisions with history loaded. Configuration remains semantically
equal and appearance bytes match the source. No prompts, record contents, private
identifiers, credentials or journal hashes are included in this public receipt.
Original data, previous app and both pilot artifacts remain preserved.

Remaining: owner visual/natural-animation acceptance, real GitHub Release
discovery/download/update, downloaded-quarantine/clean-machine Gatekeeper,
actual login/reboot recovery, real external-provider credential use, Intel Mac
and Windows/Ubuntu managed apply. No new commit, push or Release was performed.
Atlas tools were unavailable for continuity retrieval/reconciliation; this
repository receipt records the verified result without claiming an Atlas update.
