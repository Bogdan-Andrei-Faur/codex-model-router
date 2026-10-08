# History performance — Ubuntu — 2026-10-08

Artifact `codex-model-router_0.9.6-1~notch40_all.deb`, SHA-256
`e198814a3a2c458bc1a670fef443f2d86127988076e81680c0dfc1c8545e2afc`.
Development branch `feature/dynamic-notch-monitor`; baseline `0.9.6`.

The monitor transferred roughly 34,700 telemetry events to show 523 decisions,
then replayed them when live task data changed. The Python monitor now caches an
incremental decision projection and sends snapshots through the existing revision
channel. Journals and quality/action validation stay complete. Rotation and recovered
journals rebuild in original order. JS caches the base projection and applies live
overlays without mutating historical evidence. Search strings are reused; irrelevant
updates retain DOM nodes. Disclosure content is built only when opened.

Safe aggregate measurements (no raw state retained in this repository): initial
payload about 27.5MB → 2.53MB, around 91% smaller. Chromium first History render
110→13ms. Isolated real GTK/WebKit, same data, baseline installed UI versus exact
extracted successor: delivery/render 810→168ms, render alone 142→44ms. These
single-run measurements exclude disk collection and are not owner-perceived
latency certification. Initial local cold collection/projection was about 277ms;
normal primary appends process only new events. Full projection equality was
verified against the owner's complete journal in memory without exporting it.

PASS: 12 Python tests covering service actions, append/partial/rotation/deletion/
recovery and JS projection parity; 31 core tests including immutable live overlays;
History/lazy-history (37,000 synthetic decisions), glass/layout, Windows message
channel, interaction and preview groups. Exact GTK/WebKit package fixture passes
onboarding, fonts, loading, pointer ownership and single instance. Existing quota
Escape failure is still open from the previous receipt; its group was not repeated.
Native macOS/Windows execution and physical interaction are pending.

Installed readback PASS: `0.9.6-1~notch40`, one connected monitor, WebKit ready,
matching UI files, preserved settings and no startup traceback. Monitor build
`7e2076563b9d0fd7`; packaged/connected router `2fec36051e3ccedb`, no mismatch or
unknown build, restartRequired=false. Installed read-only payload confirms 524
compact decisions from 34,986 raw events, about 2.54MB at final readback.
Only the monitor was restarted; Desktop and the bridge were not restarted. No remote publication or private logs in this receipt.
