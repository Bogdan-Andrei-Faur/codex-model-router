# Authenticated managed updates — local implementation, 2026-10-09

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
| Packaged macOS, app writable by its user | Check → Update → download/verify → installation-owned helper → replace → launch → WebKit/data acknowledgement; restore previous app on launch failure | Native Settings click, fresh Installer/Gatekeeper, owner import/connection transfer, login/power-loss recovery and real credentials |
| Source-backed macOS | Signed download only; no managed replacement of a checkout | Migrate to packaged app when owner is ready |
| Packaged Windows | Shared signed discovery/download; apply disabled | Implement/test native transaction adapter and native relaunch/recovery |
| Packaged Ubuntu | Shared signed discovery/download; apply disabled | Implement/test package-manager authorization/transaction adapter and native relaunch/recovery |

No release installer has been published by this implementation. Fixture versions
0.9.6 → 0.9.7 are synthetic package builds, not a product release or owner upgrade.
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

Use an isolated build environment with `tools/packaging/requirements-build.txt`.
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
connection transfer remain explicitly unperformed.

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
