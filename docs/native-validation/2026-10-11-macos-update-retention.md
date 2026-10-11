# Mac update retention and local cleanup — 2026-10-11

Owner authorized automatic retention of one previous version and removal of
obsolete copies on this Mac. Scope: managed Mac updates and generated local
Router app bundles; no Desktop restart or active installation replacement.

## Implemented behavior

`update_cleanup.py` validates owned canonical directories, terminal operation
receipts, app identity/version/build and canonical package names/hashes before
constructing a removal plan. It requires a completed receipt matching the
installed version and one valid previous bundle. It retains the newest identified
previous version, small receipts/signatures and unrelated files.

The replacement lock serializes cleanup with a helper's commit/recovery. Pending
or malformed receipts, recovery LaunchAgents, live processes under a candidate,
failed process inspection, mismatched bundles or unsafe links defer cleanup.
Internal symlink targets are not traversed. Newer downloads and unknown bundles
are left alone. No data outside the bounded update artifacts is a deletion target.

MacApplier exposes maintenance to UpdateManager's single worker. The native
monitor retries it every60 seconds even with daily network checks off; disk work
does not run on the UI polling thread. This allows a newly launched monitor to
wait for its helper to finish before deleting the copied helper and temporary
extractions. It does not prune Windows/Ubuntu version directories.

## Verification

-49 focused Python update/trust/retention tests PASS in the prepared portable
  environment, no skips. Retention cases cover successive updates, idempotence,
  dry-run, pending/corrupt receipts, malformed versions, active processes,
  recovery registration, replacement lock, invalid package paths, changed bundle
  identity, missing backup, symlink targets, config preservation and background
  scheduling with automatic network checks disabled.
- Fresh isolated native Settings driver: success, cancel/retry, rollback after
  launch failure and interrupted-helper replay PASS. On success the **new frozen
  monitor itself** removed the terminal helper/extractions and preserved one
  previous app; the test did not invoke cleanup to manufacture that result.
- Native candidate build `78783ffcc0e0fd95`, router `59bba0400b3ad191`, package
  SHA-256 `510f3253b8f61eb75700e0eb06ee635a534d1441c4a453ec2b243d23a624e24e`.
  This is an unpublished local0.9.8 test build, not the public0.9.8 artifact. A
  subsequent defensive malformed-version exception guard has focused coverage;
  the native success/rollback behavior was unchanged by that guard.
- Local signed transport fixtures, not public GitHub transport or real login/
  power-loss acceptance. Synthetic apps/data; owner installation untouched by
  the native fixture. No CI or cross-platform native acceptance asserted.

## Applied on the owner Mac

The completed0.9.7 →0.9.8 transaction had no live helper or pending recovery.
The same reviewed cleanup routine removed six owned payload/cache entries: the
copied helper app, two extraction directories and three package copies. It kept
the real0.9.8 installation and exactly one hidden0.9.7 recovery bundle. Three
protected config/appearance/app metadata files were byte-identical immediately
before and after; no job app bundles remain.

After all fixtures exited, a bounded inventory of generated `release/` outputs
identified25 inactive Router application/runtime bundles, including the original
seven application copies and artifacts produced during this validation. Their
identities, canonical paths, ownership, inodes and absence from process command
lines were checked before removal.25 bundles were removed, representing937MiB
of logical file sizes; actual APFS space reclaimed was not measured. Published
installer files, signatures, manifests, source and build environments remain.

The installed/loaded application remains the public0.9.8 build
`e5bdb664cc13a783` / router `100ad6ea0e4db975`. **Periodic automatic cleanup
requires the next signed client release**; this turn applied cleanup once and
did not patch or replace the active bundle. The public0.9.8 release is immutable
for this work and was not overwritten with the test candidate.

## Later delivery

The next-release requirement above is resolved by public0.9.9. See the
[public delivery receipt](2026-10-11-macos-retention-release.md). The owner
installation remains0.9.8 until the owner applies it from Settings.
