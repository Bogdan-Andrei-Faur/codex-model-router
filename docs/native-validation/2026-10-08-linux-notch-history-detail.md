# History detail cleanup — Ubuntu — 2026-10-08

## Identity and scope

- Development branch `feature/dynamic-notch-monitor`, dirty source based on
  `48760d78e35c7bd31263308f74cbc39b8a501611`; product `0.9.6`.
- Ubuntu 26.04.1 LTS, x86_64; Python 3.14.4, Node 20.20.0.
- Artifact `codex-model-router_0.9.6-1~notch41_all.deb`, SHA-256
  `24a0da7f2c0802a539e3c2671f3f6add344807afdbeb94c758abf966cfdcbc80`.
- Installed monitor build `49b9b69c36ea4ee7`; packaged/connected router
  `2fec36051e3ccedb`. Supersedes the installed artifact in the
  [performance receipt](2026-10-08-linux-notch-history-performance.md).
- Shared UI change only. Existing incremental transport/projection and journals
  are retained; no routing, bridge or telemetry collector change.

## Detail contract

The three canned model/effort/continuity explanation cards are removed. Selection
origin is compact metadata instead of a task category inferred from generic reason
text. Recorded elapsed decision/turn time, valid last-call input/output tokens and
connection retries are visible directly. Missing data is omitted; a recorded zero
is preserved and cumulative thread totals cannot substitute for a missing call.
List/detail dates consistently show the record's start when available.

Actual errors and inference mismatches are visible outside disclosures. Later retry
and explicit-model request signals are worded as observations, not proof of an
unsatisfactory outcome. Current manual/automatic task controls belong in Agents,
not a historical record. Ratings retain their native action payload and storage.

One optional, initially collapsed diagnostic section replaces redundant execution
and data sections. It retains confirmed/unconfirmed inference evidence, differing
accepted/published settings, recorded phase changes/failures, prior inferences,
telemetry samples, selector comparisons/failures and valid estimates. The inferred
historical pipeline, identical settings, successful applied-engine repetition and
empty/invalid estimate totals are omitted. Estimates remain explicitly distinct
from billed cost and subscription consumption. Raw records are not deleted.

## Results

| Mode | Status | Evidence |
| --- | --- | --- |
| Shared browser | PASS | History: useful/absent/zero metrics, errors, strict evidence labels, no duplicate settings, lazy disclosures, rating payload, read-only, search, pagination, retained DOM and responsive columns |
| Shared browser | PASS | Layout, lazy History with 37,000 synthetic records, glass/controls and preview groups |
| Synthetic visual review | PASS | Wide History screenshot with chosen model, measured duration, last-call tokens and collapsed ratings |
| Isolated GTK/WebKit | PASS | Exact extracted package onboarding, font, readiness, pointer ownership/recovery and single-instance fixture |
| Isolated GTK/WebKit | PASS | Exact package History: horizontal fit, measured tiles, zero, visible error, generic text removal, lazy confirmed evidence and DOM retention |
| Installed readback | PASS | One connected monitor, WebKit ready, matching UI files, settings preserved, no startup traceback, no bridge mismatch/unknown build, restartRequired=false |
| Physical owner interaction | NOT_RUN | Owner acceptance remains separate from synthetic/native fixtures |
| Native macOS/Windows | NOT_RUN | No execution on those platforms in this iteration |

Only the monitor was restarted after visible Ubuntu package authentication.
Desktop and the active bridge were not restarted. Previous `1~notch40` artifact and
settings are retained privately for recovery. No remote publication or private
logs/state in this receipt. The previously recorded intermittent quota Escape
failure remains open; its dedicated group was not rerun and no fix is claimed.
