# Colored model/effort tags — 2026-10-08 — Ubuntu

Source base `48760d78e35c7bd31263308f74cbc39b8a501611`, dirty working tree on
`feature/dynamic-notch-monitor`, baseline `0.9.6`.
Artifact `codex-model-router_0.9.6-1~notch9_all.deb`; SHA-256
`52a765b60c91710ba2e54b3c495660f70fc68d1be9cb0d130266129c9ccb7479`.

The owner requested colored model/effort tags matching the new UI. Shared CSS
now consumes the existing semantic palette for text, tinted background and border,
with rounded pills and stronger type. All existing `badge()` call sites inherit
the treatment: hero, agent hover/inspector, history list/detail and settings policy.
Unknown values retain neutral labels. No routing or official engine changes.

Validation also found that a dismissed peek could reject DOM re-entry before
pointer movement cleared the Escape latch. Compact parent entry now clears that
latch before avatar entry. The preview hover regression passes after this change.
The native fixture now waits for both font readiness and first bounds delivery;
font loading alone could race its geometry assertion. Intermediate `1~notch8`
was not installed.

| Check | Status | Evidence and boundary |
| --- | --- | --- |
| Shared UI groups | PASS | Layout, usage, glass, history, message/update fixtures pass in Chromium. Updated pill rounding expectation. Final preview and interaction groups pass after re-entry correction. |
| Visual review | PASS | Synthetic expanded screenshot reviewed: colored model/effort pills use bundled Nunito and match companion palette/rounded UI. |
| Exact Linux package | PASS | Final artifact loads shared UI/bundled font, passes pointer ownership/missed-exit and agent/quota closure fixtures, and packaged launcher/single-instance checks. |
| Installed activation | PASS | Owner completed visible PolicyKit authentication; installed `1~notch9`, restarted only monitor, WebKit ready and shared CSS/JS match source. Configuration/UI/credential namespace byte-identical; connected bridge with mismatch/unknown/restart flags false. Build `119502178c109300`, matching router fingerprint `7b899c9ef41eedde`; no runtime traceback. |
| Native Mac/Windows | NOT_RUN | Shared UI implemented; native installed acceptance is independent. |

Earlier receipts remain historical evidence for their artifacts. No private
logs/state or conversation identifiers are included. Remote publication/CI has
not been performed for this branch.

## Border follow-up

The owner requested slightly thicker tag borders. Shared CSS changes 1px to 2px
and reduces padding by 1px per side to preserve overall dimensions. Scoped glass
and usage/layout fixtures pass (320–600px, 1–2 DPI); no new behavioral code.
Artifact `codex-model-router_0.9.6-1~notch10_all.deb`, SHA-256
`4cc903160ee3802de88ff7374efc5579598ecabfabac216afe037f9ccebed7c2`.
Installed via visible PolicyKit authentication after another APT operation released
its lock; no lock/process was removed. Restarted only the monitor. Readback PASS:
WebKit ready, CSS matches source, configuration/UI/credential namespace unchanged,
connected with no mismatch/unknown/restart flags. Monitor build `cded4311b89e0d52`,
router fingerprint `7b899c9ef41eedde`. The `1~notch9` native fixture above remains
evidence for that artifact only; no full native fixture rerun for this CSS adjustment.

## Whole-tag color follow-up

Owner clarified that the whole tag should be more colorful, including text.
Shared CSS increases background tint from 14% to 26%, border opacity from 22% to
60%, and applies 1.4× saturation to the complete pill. Dimensions and 2px borders
remain unchanged. Scoped shared glass/interaction fixture PASS; synthetic tag
screenshot reviewed. Artifact `codex-model-router_0.9.6-1~notch12_all.deb`, SHA-256
`24af3941d77ccd37279e70f65ff7746f6881e4c6fefd89357aebf08921972795`.
Installed readback PASS after visible PolicyKit authentication and monitor-only
restart: WebKit ready, CSS/source match, settings unchanged, connected with no
mismatch/unknown/restart flags; build `64db12f9f653214b`, router fingerprint
`7b899c9ef41eedde`. Intermediate `1~notch11` was not installed. No full native
fixture rerun for this CSS-only adjustment; physical visual acceptance pending.

## Thin-border follow-up

Owner requested returning to 1px borders while retaining the current colors.
Shared CSS restores 1px borders/3px 10px padding, preserving overall dimensions,
26% background tint, 60% border opacity and 1.4× saturation. Scoped glass/shared
interaction fixture PASS. Artifact `codex-model-router_0.9.6-1~notch13_all.deb`,
SHA-256 `7fe50b11a900158742233357a9144a4aac1c125fae1cd64a057d2699355f643e`.
Installed readback PASS after visible PolicyKit authentication and monitor-only
restart: WebKit ready, CSS/source match, settings unchanged, connected with no
mismatch/unknown/restart flags; build `e283b3e3789450a0`, router fingerprint
`7b899c9ef41eedde`. No full native fixture rerun for this CSS adjustment.
