# Reviewable history-cleanup candidate — 2026-10-09

Status: **prepared locally; no remote history or visibility changed**. The owner
asked to see this result before authorizing a remote rewrite. The existing
checkout and all new uncommitted updater work are preserved.

## Exact candidate

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
No such action has been taken. Existing integrations, redirects, settings and
links must be inventoried before executing it. Do not delete either repository.

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
