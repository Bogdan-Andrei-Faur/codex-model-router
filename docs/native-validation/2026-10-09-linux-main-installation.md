# Native acceptance receipt — 2026-10-09 — Ubuntu — owner pilot

## Identity and scope

- Installation/readback completed before 06:06:38 UTC on 2026-10-09; exact start time was not retained in this safe receipt.
- Ubuntu 26.04.1 LTS, x86_64, local Wayland session. Display geometry and physical input were not evaluated.
- Source: clean `main`, `a4af0301e69562cbd2b412b81b1a4f8eb650a6b1`, matching fetched `origin/main` before this receipt.
- Product `0.9.6`, policy `8`; Debian package `0.9.6-2~main20261009.1`.
- Artifact: `codex-model-router_0.9.6-2~main20261009.1_all.deb`.
- SHA-256: `2e306cf5b89290670f8f6d3ee315cddf46c94448da29fd16127ef9979e97b0f3`.
- Installed/active monitor build: `2367c5161a84cbfa`; installed router build: `88a0be134bc26eb9`.
- Existing Desktop bridge remains loaded with monitor identity `d4c77d8725682366` and router identity `2fec36051e3ccedb`. It does not match the new installed router.
- Python 3.14.4, Node 20.20.0. Desktop/official CLI versions and Docker runtime were not rechecked for this installation.
- Owner authorized installation and completed visible Ubuntu authentication. Only the monitor restarted; Desktop and its bridge were left running.
- Supersedes the installed Ubuntu `1~notch43` artifact/readback in [the ratings/spacing receipt](2026-10-08-linux-notch-history-ratings.md). Historical physical and other-platform gates remain unchanged.

## Results

| ID | Mode | Status | Action | Observation / limitation |
| --- | --- | --- | --- | --- |
| ENV | Installed | PASS | Package version, process/readback and payload comparison | One monitor, WebKit ready, all 110 package application files match installation, source UI matches installed UI, no startup traceback |
| CORE | Source | PASS | Python suite and `npm test` in clean child environments | 544 Python tests, 37 platform/optional skips; 33 JavaScript tests, zero failures. Skips do not prove omitted native/Docker cases |
| UI-SHARED-FIXTURES | Source | PASS | `npm run test:layout` | All 14 browser groups pass, including camera, appearance, preferences and observed activity |
| UI-NATIVE-FIXTURE | Isolated native | PASS | Exact final package GTK/WebKit smoke using extracted launcher | Readiness, bundled font, onboarding cancel/new/import, hover ownership/exit recovery, shared UI payload and single instance pass; synthetic fixture only |
| INSTALL-LIFECYCLE | Installed | PASS | APT upgrade through visible PolicyKit authentication | One package upgraded, previous application/data/package backed up privately; seven protected settings files remain byte-identical after restart |
| TEL-DESKTOP-ACTIVE | Installed | NOT_RUN | Read-only bridge health check | Existing bridge PID retained, heartbeat fresh, one connection. New installed router has not been loaded by Desktop; no new authenticated telemetry or inference attribution acceptance claimed |
| UI-INPUT / UI-VIEWS / UI-DATA | Physical | NOT_RUN | Owner interaction and natural event delivery | Requires owner review of this exact artifact |
| UI-DISPLAY / UI-SCALE / UI-SLEEP / UI-START | Physical | NOT_RUN | Multiple displays, DPI, suspend/resume and ordinary startup | No disruptive checks performed |
| DKR / KEY-NATIVE | Native | NOT_RUN | Docker grader and native credential roundtrip | Outside this installation run |

## Evidence details

The installed monitor reports `bridgeBuildMismatch=true`, `bridgeBuildUnknown=false`
and `restartRequired=false`. The last field is not proof that the old loaded bridge
matches the new router: the explicit fingerprints above show it does not. Desktop
must be restarted by the owner when ongoing tasks permit to load the new bridge.

The Debian revision uses `2~main20261009.1` so it sorts above installed
`1~notch43`; product VERSION is unchanged. The earlier locally built
`1~main20261009.1` package was not installed. APT simulation required no added or
removed dependencies. No provider requests or credential changes were initiated.

## Conclusion and remaining work

Local source/browser checks, exact-package isolated GTK smoke, package upgrade,
monitor readiness and settings preservation pass for this artifact. Current CI
is not asserted; earlier remote runs belong to their recorded revisions.

The owner subsequently reported completion of the Desktop restart. Read-only
verification on 2026-10-09 confirms one fresh connection from a replacement bridge,
loaded router `88a0be134bc26eb9`, matching the installed router. Both
`bridgeBuildMismatch` and `bridgeBuildUnknown` are false; `restartRequired` is
false. This supersedes the earlier pending loaded-bridge state in this receipt.
Loaded-bridge activation now passes; authenticated telemetry delivery, inference
attribution and physical acceptance remain separate checks.

Next: record normal event/physical acceptance separately.
Private backups retain the previous artifact and settings for recovery. This
receipt contains no private state, raw logs, account/conversation identifiers or
credentials; it is local documentation and has not been published in this run.
