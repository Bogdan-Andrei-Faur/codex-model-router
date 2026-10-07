# Windows owner restart check — 2026-10-07 — host-a

## Identity and scope

- Read-only owner-host check after the owner reported installing/restarting.
- Final snapshot: `2026-10-07T09:24:50Z`; Windows x64.
- Source baseline `50e63b07fbe65e182aebeb414e6daea1e1ca599e` plus preserved
  uncommitted installer work; product 0.9.4, policy 8.
- Installed active manifest: 0.9.4, build `d042188854998c95`, router build
  `1fa217653242b775`. The running native monitor image belongs to that installed
  version directory. The previous setup acceptance receipt identifies the exact
  artifact; no installer was executed by this check.
- Desktop package observed: 26.1002.6548.0. Registered wrapper and actual bridge
  processes still use the source checkout. Its live Python bridge reports 0.9.4
  and the same build/router fingerprints as the installed artifact.
- No registration, configuration, owner data, credentials or processes changed;
  no additional inference, restart, sleep or display change requested.

## Results

| ID | Mode | Status | Evidence | Limit |
| --- | --- | --- | --- | --- |
| ENV-INSTALLED | Read-only physical host | PASS | Active manifest and running monitor image belong to installed 0.9.4 | Does not identify Desktop's bridge by itself |
| TEL-DESKTOP-SOURCE | Read-only live source state | PASS | Fresh heartbeat, completed Desktop handshake; telemetry requests advance 41 to 66; final accepted decisions 4 | Uses the legacy source data root and development Python |
| TEL-TRANSPORT-SOURCE | Read-only live source counters | PASS | Telemetry enabled; all reported invalid, unauthorized, unexpected-path and capacity-rejection counters zero | Reception does not prove per-response inference attribution or billing |
| TEL-DESKTOP-INSTALLED | Read-only registration/process/state check | BLOCKED | User environment still selects source wrapper; installed integration receipt absent; no fresh bridge status in installed data root | Installation/restart has not transferred registration |
| IMPORT-PROVENANCE | Read-only installed metadata | PASS | Schema-1 migration marker references the existing source installation | No re-import performed; connection adoption still needs the normal action |
| UI-INPUT / UI-DISPLAY / UI-SCALE / UI-SLEEP | Physical host | NOT_RUN | No physical interactions or disruptive checks performed | Prior fixtures remain separate |

## Conclusion and remaining work

The new version's code is running through the legacy source bridge. The installed
monitor and source bridge still read different data roots. This is an incomplete
connection migration, not evidence that 0.9.4 routing or telemetry is stopped.

At an owner-selected break, close Desktop completely, keep/open the installed
monitor, and select Settings **Conectar al inicio habitual**. The connection
transfer checks that the imported source bridge has stopped; wait for successful
registration before reopening Desktop. Then verify installed bridge/runtime,
fresh handshake and authenticated counters in the installed data root. Existing
imported data remains valid; do not reinstall or re-import for this check.

This receipt supersedes only the owner installed-version and current source
bridge observations in the earlier Windows installation acceptance report.
Clean-VM lifecycle acceptance and outstanding physical/prerequisite/cancellation
gates remain unchanged. Raw state, process paths and private identifiers are
excluded from this report.
