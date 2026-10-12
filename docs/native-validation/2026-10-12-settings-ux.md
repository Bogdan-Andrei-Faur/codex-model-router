# Shared Settings UX receipt — 2026-10-12

## Scope

- Source baseline: `90aadf8c468b1f00e151bcc00dcb877bf92f049a` plus local changes.
- Shared `monitor-ui` JavaScript/CSS; synthetic browser state only.
- Owner installed0.9.11, public release assets, preferences and consents unchanged.
- No installation, restart, provider inference, secret access or real uploads.

## Changes

- Four short navigation labels: Aplicación, Modelos, Privacidad, Conexión.
- Descriptive setting names and one-line hints instead of repeated activation
  commands; explicit Yes/No switches, colored states and rounded tinted cards.
- Local/remote data controls separated; additional permissions clearly marked,
  sensitive-content/destination/retention warnings visible and deletion confirmed.
- Technical explanations, comparison engines and current model policy collapsed;
  model/effort pills and original Lucide icons retained.
- Refresh preserves disclosure state, credential drafts and keyboard focus for
  switches/navigation/engine choices/disclosure summaries. Preview cannot save keys.

## Verification

| Gate | Result | Boundary |
| --- | --- | --- |
| JavaScript syntax and diff whitespace | PASS | `node --check`, `git diff --check` |
| Shared core | PASS |34 tests, `npm test` |
| Shared browser suite | PASS |All17 groups in `npm run test:layout`, including layout, update, Windows message-channel, privacy, appearance and rigidity |
| Settings interaction | PASS |Native action payloads, independent consent, deletion confirm/cancel, draft retention, preview/read-only guards, keyboard Space and live refresh |
| Responsive Settings | PASS |All four sections at320,390,620,800px; existing layout/DPI checks at1–2x |
| Visual inspection | PASS |Synthetic Application, Models, Privacy, Connection and narrow Jev screenshots reviewed with Playwright CLI; no owner data |
| Native hosts/owner installation | NOT_RUN |Shared browser checks do not establish new AppKit/WebKitGTK/WebView2 physical acceptance; installed0.9.11 untouched |
| Publication | NOT_RUN |Local implementation only; requires an authorized commit/release to reach installed users |

The initial glass probe expected the former pause icon/button and failed after
the intended switch replacement. Its assertion now checks the switch state and
track; the full suite passes. CLI file-URL access was blocked, so visual review
used a loopback-only static server. A stale browser cache was explicitly bypassed
before reviewing the changed UI; no production cache behavior was changed.

Screenshots are ignored local synthetic artifacts under
`output/playwright/settings-redesign/`. No raw logs, prompts, keys or personal
identifiers are included here. Next: owner visual review and, if approved,
publication in a new signed client release; cross-platform native acceptance
remains separate.
