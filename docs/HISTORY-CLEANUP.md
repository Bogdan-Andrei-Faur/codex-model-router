# Clean public source publication — 2026-10-09

Status: **executed after owner review and approval**. The canonical repository
is public with clean history; the original remains private and archived. No remote
history was force-rewritten, no repository was deleted and no installer was released.

## Initial review candidate (before updater source commit)

A fresh mirror of the canonical remote at main
`63d3f39985dc426d0e0339f99d549917324ce5dd` was backed up as a verified full Git
bundle, then filtered with git-filter-repo 2.47.0. Only these paths were removed
from all reachable history in that isolated mirror:

- `assets/codex-official.png`
- `assets/codex-ui-1024.png`
- `assets/codex.ico`

| Check | Result |
| --- | --- |
| Main candidate | `4f8b040909a0f2c2c392b42be64e8b036d185b68` |
| Current main file tree before/after | Identical Git tree; no current source files lost |
| Removed paths in candidate reachable history | Absent |
| Candidate Git object integrity | `git fsck --full` passes |
| Rewritten references | 2 branches, 10 version tags, 1 GitHub pull-request reference |
| Backup | Full original bundle, verified; SHA-256 `43ab12831e3401a47807e96471ca3a51bb5acfa89d4867a8783ee33419198394` |
| Active checkout / remote | Neither rewritten |

Private local evidence is under the ignored directory named by
`state/distribution-review/history-candidate-path.txt`. Its `report.json` contains
the complete old/new reference map and `original.bundle` holds the backup. Do not
publish the backup: it intentionally retains the retired artwork.

This candidate predates the uncommitted authenticated updater. After any further
source publication, regenerate the candidate and review exact remote reference
leases before proposing a rewrite. Never force-push the stale candidate.

## GitHub limitation requiring an owner decision

The mirror contains `refs/pull/1/head`. GitHub manages pull-request references as
read-only: rewriting branches and tags does **not** remove that copy or cached
commit views. GitHub's [documented removal procedure](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
also states that Support does not remove non-sensitive data. Do not promise a
complete purge of these historical brand images through a normal force-push.

Recommended publication alternative: keep the existing repository private as a
renamed archive, then create a fresh repository at the canonical name/URL with
only the reviewed clean branches/tags. This preserves the original backup,
Actions records and PR privately. It does require separate owner authorization
for the rename, creation, source publication and eventual visibility change.
The owner subsequently selected this alternative. The execution receipt below
records the result. Do not delete either repository.

Alternatively, the owner may retain this same repository and defer public
visibility until a satisfactory resolution of the PR/cached-history exposure is
available. A local clean mirror alone does not establish public-exposure clearance.

## Other exposure evidence

The bounded preliminary scan covered 1,421 historical blobs, 58 accessible Actions
log archives and 21 accessible artifacts. The 20 images inside those artifacts
have now been visually reviewed: all depict synthetic Windows self-test views;
no owner content was observed. Private scans/contact sheets remain ignored.
This is an observation of the reviewed snapshot, not a privacy or secret
certification. Refresh the review for any new commits, runs or assets before
changing visibility.

## Other-machine handoff after an approved rewrite

Preserve each machine's current checkout, uncommitted files and local commits.
Use a fresh clone to validate the new remote history before migrating local work.
Do not merge the old history back, and do not use reset/clean to discard owner
changes. Installed applications and their private data are independent and must
not be replaced merely to synchronize source history.

## Executed publication and local synchronization

- Public canonical repository:
  [codex-model-router](https://github.com/Bogdan-Andrei-Faur/codex-model-router).
- Original repository preserved PRIVATE and archived:
  [codex-model-router-private-archive-20261009](https://github.com/Bogdan-Andrei-Faur/codex-model-router-private-archive-20261009).
  Its original main, PR and Actions records remain intact. No releases, webhooks,
  deployment keys, Actions secrets/variables or environments needed transfer.
- Updated source was committed as `b3cbac3c190018ed5fb2c7b7382737e7c8d80d93` in the pre-public local history.
  A fresh backed-up mirror produced clean public main `5dac586bf6d74cea6a58da7e89798cbf1218ad06`.
  Its file tree is exactly equal to that source commit, with the three old image
  paths absent from every published branch/tag history. Object checks pass.
- Published exactly2 branches and10 tags, with atomic normal push. No PR refs,
  private backups, runtime state or installers were uploaded. New repository
  Actions were temporarily disabled during historical ref import and reenabled
  afterwards; no result of the new CI is asserted.
- Latest verified private pre-filter bundle SHA-256:
  `c62084a997f045f7f3633b02b96f8886a6ee29deb118abdc77af55bdab4b4e2e`.
  Local evidence lives in the ignored path referenced by `state/public-source-path.txt`.
- Local `main` tracks the new `origin/main`. The old main is preserved as
  `codex/pre-public-20261009`, all previous local branch/tag refs are retained
  under `refs/archive/pre-public-20261009/`, and a full local bundle was verified.
  Local version tags now match the clean public tags. The `private-archive`
  remote points to the preserved original. No reset/clean or owner-data deletion
  was used. Never push archival refs or use `git push --mirror` from this checkout.
- Historical CI links now point to the private archive and require owner access.
  Historical receipt commit IDs describe their original evidence; they are not
  the rewritten public commit IDs. Documentation-only publication receipts may
  follow the clean main commit named above.

The repository is public; the application is **not** yet a published installer
release. Signing/managed-update and native acceptance limits remain in
[MANAGED-UPDATES.md](MANAGED-UPDATES.md).
