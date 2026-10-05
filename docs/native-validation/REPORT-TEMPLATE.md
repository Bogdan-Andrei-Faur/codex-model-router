# Native acceptance receipt — <UTC date> — <platform> — <safe host alias>

Copy to `YYYY-MM-DD-<platform>-<safe-label>.md`. This template is not evidence.
Use PASS/FAIL/BLOCKED/NOT_RUN/NOT_APPLICABLE; preserve failures and explain skips.

## Identity and scope

- UTC start/end:
- Safe host alias (no hostname/user name):
- OS version/build, CPU architecture:
- Session: physical/local / remote / fixture; Linux desktop and actual GDK backend:
- Displays: count, resolution/scaling, primary; omit hardware serial numbers:
- Source commit and dirty/clean state:
- Product VERSION and policy version:
- Installed mode: source / ZIP / pkg / deb; installed version/build/router hash:
- Artifact filename and SHA-256 (or unavailable reason):
- Active monitor and loaded bridge build; identity match result:
- Desktop and official CLI versions:
- Python and Node versions; Docker client/server/engine OS/arch/cgroup version (when tested):
- Owner-coordinated activation or disruptive checks, if any:
- Previous receipt superseded, by individual row:

## Results

| ID | Mode (source / isolated native / installed / physical) | Status | Command or exact action | Exit/count/observation | Limitation or safe error code |
| --- | --- | --- | --- | --- | --- |
| ENV | | NOT_RUN | | | |
| CORE | | NOT_RUN | | | |
| UI-SHARED-FIXTURES | | NOT_RUN | | | |
| DKR-CONTROLS | | NOT_RUN | | | |
| DKR-SUITE | | NOT_RUN | | | |
| DKR-CLEANUP | | NOT_RUN | | | |
| TEL-ROOT | | NOT_RUN | | | |
| TEL-SUBCOMMAND | | NOT_RUN | | | |
| TEL-DESKTOP-LAYOUT | | NOT_RUN | | | |
| TEL-DESKTOP-ACTIVE | | NOT_RUN | | | |
| UI-NATIVE-FIXTURE | | NOT_RUN | | | |
| UI-INPUT | | NOT_RUN | | | |
| UI-VIEWS | | NOT_RUN | | | |
| UI-DATA | | NOT_RUN | | | |
| UI-DISPLAY | | NOT_RUN | | | |
| UI-SCALE | | NOT_RUN | | | |
| UI-SLEEP | | NOT_RUN | | | |
| UI-START | | NOT_RUN | | | |
| KEY-NATIVE | | NOT_RUN | | | |

## Evidence details

- Docker controls: read/write/network blocked booleans; image digest; suite
  executed/skipped/failed counts; new leftover containers count (no container IDs).
- Native telemetry per layout: config verified, before-shutdown requests,
  unauthorized requests and errors; live=false. Do not include raw OTLP.
- Physical UI: observations for each display/scale and after resume; distinguish
  simulated clicks from owner-observed physical clicks. State settings restored.
- Native storage: store used, synthetic roundtrip/cleanup booleans only.
- Safe screenshot/receipt links, if any (synthetic or reviewed/redacted only).

## Conclusion and remaining work

- Gates closed on this exact host/artifact/loaded revision:
- Gates still open, with reason and concrete next check:
- Reproduction steps for each failure, with sanitized errors:
- Recovery/original settings restored:
- Private data review completed before Git publication:

Do not include credentials, prompts, titles, response text, conversation/account
IDs, raw logs/doctor output, home/install paths, personal machine names or private
screenshots. Do not claim global three-platform acceptance from this receipt.
