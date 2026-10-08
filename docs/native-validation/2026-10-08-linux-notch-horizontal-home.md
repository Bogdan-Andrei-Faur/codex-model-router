# Horizontal Home — Ubuntu — 2026-10-08

Source base `48760d78e35c7bd31263308f74cbc39b8a501611`, dirty branch
`feature/dynamic-notch-monitor`; product baseline `0.9.6`.
Artifact `codex-model-router_0.9.6-1~notch23_all.deb`, SHA-256
`a1adbde1196b5b3d9ff4d10bdfa1aa79f9e3044498926999f76e77f9d855a263`.

Home now places the principal agent and its metrics on the left, with the other
agents in a bounded list on the right. Selecting another agent moves it into the
principal view without duplicating it in the list; keyboard focus follows it.
Home's visible body grows to 750px (790px including shoulders), while secondary
views retain their previous 550px body. All three native hosts allow an 800px
viewport, constrained by the selected display's work area. Below 620px viewport
width, columns stack. Inspector navigation and automatic compact mode remain.
The principal character's detail action now uses the same navigation state as
the explicit detail button.

| Check | Status | Evidence and boundary |
| --- | --- | --- |
| Eight shared browser groups | PASS | Layout, usage, interaction, lazy history, glass, Windows channel, updates and preview adapter. |
| Horizontal selection | PASS | Preview fixture asserts left/right columns, no duplicate principal and keyboard focus following selection into the principal view. |
| Visual / large crew | PASS | Synthetic 790×369px Home screenshot inspected. Fifteen-agent checks at 320/640/800px retain all 14 other agents in a scrollable list without horizontal page overflow; wide Home height is 392px. |
| Exact Ubuntu package fixture | PASS | GTK/WebKit/font, launcher/single-instance, hover exit recovery and expanded automatic compact mode. |
| Installed activation | PASS | Visible authentication completed; only monitor restarted. One instance, WebKit ready, shared resources match source, settings unchanged, one connection and no mismatch/unknown/restart flags or traceback. Monitor `a882d14649d796fd`, router `7b899c9ef41eedde`. |
| Native Mac/Windows / physical owner acceptance | NOT_RUN | Native source viewport adapted; no compilation or physical acceptance claimed. |

Fixtures were updated for the principal no longer having a duplicate task card.
One preview run timed out waiting for quota hover closure; the unchanged retry
passed. This intermittent result remains open physical-hover evidence, not proof
that every owner interaction is fixed. No new hover behavior change in this
iteration. No routing/official engine changes or remote publication; previous
package/settings retained privately. No owner state or raw logs in this receipt.
