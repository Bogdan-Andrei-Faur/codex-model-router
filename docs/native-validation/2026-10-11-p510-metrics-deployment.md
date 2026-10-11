# P510 central metrics deployment — 2026-10-11

## Scope and result

Owner completed Sentinel project registration and explicitly authorized deployment
after review. Registered target is P510, service `api`, internal8080, readiness
`/health/ready`, public `https://router.andreifaur.dev`. Owner left polling enabled
at300s. Sentinel controller `05cccb553b282588a09fe38881a23f841fed8288`.

Backend source `e41f739b2dfcf97d3d6de219644c2257b5cc4c66` deployed successfully
through Sentinel's normal remote operation. Durable worker receipt confirms success
and transfer cleanup. API and PostgreSQL are running/healthy; only API is published
on a Sentinel-assigned LAN port. Public HTTPS returns expected readiness JSON;
Sentinel shows2/2 healthy services,1/1 route enabled and no active exclusive operation.
Atlas and Cashflow remain healthy and unchanged.

## Initial failures and correction

Earlier attempts at `fdac173` and `cea6eb0` failed API startup; DB remained healthy,
remote operation cleanup was confirmed, public route stayed disabled. Importing
the telemetry protocol raised `ModuleNotFoundError`. Initial suspicion of an
incomplete Docker context was incorrect: root inspection confirmed the files were
present, but nested directories had mode0700 and root ownership after private
archive extraction. A root-only build check falsely passed.

Final Dockerfile copies package/app/schema with ownership10001:10001 and runs the
import/protocol smoke as the actual runtime user, after `USER`. Unnecessary ignore
changes were reverted. Native P510 Compose build using a clean tracked-source
archive extracted under umask0077 passes; non-root/read-only/no-network import
also passes. Private source permissions and container privilege protections stay
intact. No database volume was removed or reset.

## Public verification

Eight synthetic checks PASS over verified HTTPS, without exposing credentials:

1. Expected public readiness JSON, not generic Caddy HTTP200.
2. Owner panel rejects unauthenticated access and accepts the existing owner secret.
3. Enrollment alone cannot upload without consent.
4. Metrics upload and repeat of the same event receive idempotent acknowledgements.
5. Prompts/raw OTLP are rejected without their additional permissions.
6. Synthetic diagnostic upload and owner-authenticated retrieval roundtrip.
7. Opt-out rejects further upload.
8. Synthetic deletion acknowledges and diagnostic retrieval returns404.

The real repository client transport also passed enrollment/consent/metrics retry/
deletion against the public service. Cloudflare rejected urllib's generic Python
User-Agent with403/error1010; truthful `Codex-Model-Router/central-telemetry-v1`
identification succeeds and is now set by client source. TLS verification and
redirect rejection remain intact. Twelve focused client tests PASS.

Only synthetic content was sent. Final aggregate DB inspection:2 installations,
0 events,0 event bytes,2 deletion tombstones. Installation/tombstone rows intentionally
remain; no claim of full installation metadata erasure. No real owner prompts,
raw OTLP or local history were uploaded.

## Remaining boundaries

Owner Desktop app/configuration and published0.9.7 release were not replaced.
The new sharing client still needs delivery and native Settings acceptance on
each platform before claiming real installation collection. Sharing remains
default-off. Sentinel remote backup/restore is unsupported and was explicitly
accepted by owner for deployment; this receipt is not a restore/protection test.
Residual local-container upstream warning is a Sentinel UI issue; actual remote
route assignment and public ingress were verified. No credentials, request bodies,
raw private logs or conversation identifiers are included in this receipt.
