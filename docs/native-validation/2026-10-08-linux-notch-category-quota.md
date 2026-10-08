# Task category and quota color — 2026-10-08 — Ubuntu

Source base `48760d78e35c7bd31263308f74cbc39b8a501611`, dirty branch
`feature/dynamic-notch-monitor`; product baseline `0.9.6`.
Artifact `codex-model-router_0.9.6-1~notch15_all.deb`; SHA-256
`b017fd91a91f3e94139ea12a4093131f87df2f31969ef6e66239dbcd57e07b5e`.

The owner requested more color and the corresponding task icon, removal of the
account-sharing footer and clearer blue quota backgrounds. Shared UI uses the
existing category/icon mapping in a companion-colored label; strengthens compact
quota and quota-card backgrounds/borders; omits the redundant footer from quota
sections. Unavailable quota remains neutral, and accessibility retains context.

| Check | Status | Evidence and boundary |
| --- | --- | --- |
| Shared glass and usage/layout | PASS | Category catalog, hover, quota expiry, narrow/fractional scale, context/compaction and responsive control fixtures. |
| Visual review | PASS | Synthetic compact category and quota screenshots inspected; research icon matches mapping and visible account-sharing footer is absent. |
| Exact native package fixture | PASS | Shared UI/font loaded, pointer ownership/missed-exit recovery and agent/quota closure pass; packaged launcher/single-instance verified. |
| Installed activation | PASS | Visible PolicyKit authentication completed; installed `1~notch15` and restarted only monitor. WebKit ready, shared CSS/JS match source, settings unchanged; connected without mismatch/unknown/restart flags. Build `198551547e5b8a41`, matching router fingerprint `7b899c9ef41eedde`, no runtime traceback. Previous package/state retained privately. |
| Native Mac/Windows / physical acceptance | NOT_RUN | Shared code is included; independent native acceptance remains pending. |

No routing/official engine changes. Prior receipts remain artifact-specific.
No private state/logs or conversation identifiers retained; no remote publication.

## Compact quota correction

Owner clarified that the compact quota should have background color only, with
no visible border or “cuota” caption. Shared CSS removes the compact button border
and its renderer retains only the centered percentage; accessible quota labels
remain. Scoped usage/layout fixtures PASS at 320–600px and 1–2 DPI. Artifact
`codex-model-router_0.9.6-1~notch16_all.deb`, SHA-256
`8515e9b6629d6c4a58ed23bcf169abd49176b57224e4fc9308c4fce84f85ee71`.
Installed readback PASS after visible PolicyKit authentication and monitor-only
restart: shared CSS/JS match source, WebKit ready, settings unchanged and healthy
connection without mismatch/unknown/restart flags. Monitor `91973fb814365cd6`,
matching router fingerprint `7b899c9ef41eedde`. Earlier native fixture remains
evidence for `1~notch15`; no full native fixture rerun for this visual correction.

## Quota card border removal

Owner also requested removing the quota-window card border. Shared CSS removes
only that border and retains the blue tinted background. Artifact
`codex-model-router_0.9.6-1~notch17_all.deb`, SHA-256
`debc484f43b62d6f0f2e20ba8ff725d7b07c365ca94e62ed6142e754e085322f`.
The first scoped usage fixture run failed its Escape dismissal assertion; the
unchanged retry passed. This intermittent fixture result is not evidence that
physical Escape behavior is fixed. No behavior code changed for this adjustment.
Installed readback PASS after visible authentication and monitor-only restart:
CSS/source match, WebKit ready, settings unchanged, connected without mismatch/
unknown/restart flags; monitor `23c3fecb2b017b32`, router `7b899c9ef41eedde`.

## Transparent compact percentage

Owner requested removing the background only from the compact percentage and
ensuring vertical centering. Shared CSS uses a 44px grid centered in both axes,
single-line number text and transparent normal/hover/unavailable backgrounds.
Expanded quota card background remains unchanged. Scoped usage/layout fixture
PASS; direct browser measurements confirm centered zero/79/full/unknown values
and transparent hover. Artifact `codex-model-router_0.9.6-1~notch18_all.deb`,
SHA-256 `48b19f8bbc308d73d4061d296ab1b68d76de2ccaaf047c463f8b98764638f65a`.
Installed readback PASS after visible authentication and monitor-only restart:
CSS/source match, WebKit ready, settings unchanged, connected without mismatch/
unknown/restart flags; monitor `f6efeeb67b50b426`, router `7b899c9ef41eedde`.
Native package fixture not rerun for this CSS adjustment.

## Quota hover overflow correction

The final quota window's collapsed 9px bottom margin was excluded from the
content height used to size the hover surface. It produced a scrollbar despite
sufficient viewport space. Remove only that trailing margin; spacing between
windows and the existing 20px bottom padding remain intact.

Scoped usage/layout regression PASS across 320–600px and 1–2 DPI. Synthetic
one/two-window checks show equal scroll/client heights at 850px viewport height;
at 240px, scrolling remains available to reach all content. Artifact
`codex-model-router_0.9.6-1~notch19_all.deb`, SHA-256
`8cf0347e9161cd6c982c4211da7b7ae480d198e0d08a444518beebc0dcd176e6`.
Installed readback PASS after visible authentication and monitor-only restart:
one monitor, shared CSS/JS match source, WebKit ready, settings unchanged and
connected without mismatch/unknown/restart flags or runtime traceback.
Monitor `795fbfce2218a700`, router `7b899c9ef41eedde`. Native package fixture
not rerun for this CSS correction; physical owner acceptance remains pending.
