# Owner installation acceptance and release decision — 2026-10-11

The owner explicitly confirms that installation on Windows and Ubuntu has already
been tested personally and instructs that those installation gates be closed.
Record both as **ACCEPTED_BY_OWNER**. Do not require repeating installation merely
to obtain an agent-generated receipt. The owner's statement is the acceptance
source; no additional installer version, architecture, hash or test result was
provided. Existing artifact-specific technical receipts remain valid history.

The owner also rejects a clean-Mac test as excessive for this delivery. Record
that prerequisite as **WAIVED_BY_OWNER**, not PASS. It does not block installer
publication. Existing Mac Installer/import/connection and isolated managed-update
results remain the technical evidence; this waiver does not assert notarization
or certification on additional hardware.

## Authorized publication and missing files

The owner authorizes uploading the installers to GitHub Releases. The exact tested
Windows and Ubuntu files are on other computers, as confirmed by the owner. They
are absent from this Mac's release/download folders and GitHub's current release;
current Actions artifacts contain WebView2 validation, not release installers.
Publication awaits transfer of those actual files, rather than another acceptance
request. Do not rebuild or rename a different binary and claim it was owner-tested.

Transfer the Windows setup `.exe` and Ubuntu `.deb` to the publisher Mac through
the owner. Include the build receipt/source revision if available; do not transfer
private state, logs, configuration, credentials or signing keys. On receipt:

1. Inspect actual embedded/package version, target architecture and SHA-256.
2. Preserve each binary's identity. A filename change cannot change its embedded
   version or make an untested architecture supported.
3. Choose the matching release/version. The existing public0.9.7 Mac package and
   tag remain immutable. Do not add an older/different-version binary to a signed
   latest-release manifest as0.9.7, or claim a common source revision without proof.
4. Sign final matching assets with the existing publisher key on this Mac; update
   checksums, per-asset provenance and release notes. Inspect installers for private
   payloads and include their required notices before publishing.
5. Upload under the owner's authorization and verify anonymous download bytes and
   signature. Record the public URLs and hashes in the repository handoff.

## Scope that remains separate

The installation statement does not specify Settings update, cancellation,
failure recovery, GUI-login replay, uninstall, display/sleep or credentials tests.
Their existing recorded results remain unchanged; do not describe them as newly
executed or owner-confirmed. They are follow-up coverage, not a demand to repeat
already accepted installation or the waived clean-Mac prerequisite.
