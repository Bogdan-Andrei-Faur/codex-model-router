# Native acceptance receipt — 2026-10-09 — Ubuntu top edge

## Identity and scope

- Ubuntu 26.04.1 LTS, x86_64; local GNOME Wayland session, GTK using XWayland (`GdkX11Display`).
- Source: `fix/linux-notch-top-edge`, uncommitted changes over `a4af0301e69562cbd2b412b81b1a4f8eb650a6b1`; product `0.9.6`, policy `8`.
- Artifact: `codex-model-router_0.9.6-2~main20261009.2_all.deb`.
- SHA-256: `52c6a212dfb519efef05357d9d9aead7beb40e33ef5d5c676206b53e64bb5cc6`.
- Python 3.14.4. No Desktop/CLI update or provider requests were initiated.
- Primary display logical geometry: 1920×1080 at (1920,0), work area starts at Y=32 and ends at Y=1023. Secondary logical geometry: 1920×1200 at (0,0). Physical DPI transitions were not tested.
- User requested the macOS top-edge placement adaptation for Ubuntu. Existing installation, application data and seven protected settings files were backed up privately before activation.

## Results

| ID | Mode | Status | Action | Observation / limitation |
| --- | --- | --- | --- | --- |
| CORE | Source | PASS | `python3 -m unittest discover -s tests -p 'test_linux*.py'` with inherited router overrides removed | 20 tests, no skips/failures |
| UI-PLACEMENT | Native isolated preview on owner compositor | PASS | `tests/smoke_linux_window.py`, saved topmost on and off | All six transitions pass in both runs: startup, unpin, pin, hide, expanded reopen, compact. Actual EWMH role/ABOVE flag, coordinates, size, unchanged display/work area and preference preservation checked |
| UI-NATIVE-FIXTURE | Isolated native | PASS | Exact final package under Xvfb/private D-Bus, `tests/smoke_package_linux.py` | GTK onboarding, WebKit/shared payload/font, exact launcher, pointer ownership/exit recovery and single instance pass |
| UI-PHYSICAL | Physical | NOT_RUN | Owner review of panel overlap/input | Coordinate proof does not prove visibility above GNOME Shell chrome, first-click focus, display transitions or fractional scaling |
| ENV-INSTALLED | Installed | PASS | Visible Ubuntu authentication and monitor restart | `2~main20261009.2`, monitor `f96fe2f614fa076c`, router `88a0be134bc26eb9`, one connection, preserved settings; owner visual failure below supersedes geometry-only success |

## Evidence details

Normal GTK windows were constrained to Y=32 even after an explicit move to Y=0.
A dock role set before mapping allows Y=0. The implementation uses that role only
for pinned X11/XWayland windows and creates no strut. Width is centered on the full
display; the bottom still respects the work area. Unpinning restores normal window
semantics/work-area placement. Role changes remap the window: changing a mapped
dock directly into a normal window caused Mutter to move it to another display,
which the native regression now checks against.

The first source preview accidentally loaded an old generated `dist/linux-ui`.
Those runs were superseded: the fixture now copies the checkout's current shared
UI into its own temporary directory. Both saved-topmost variants were rerun and
passed with the current redesign. The package always contained the current UI.

Native Wayland still delegates placement to the compositor. No GNOME extension,
global shell setting, Desktop restart or other-platform layout change is involved.
Current CI, Docker, new bridge telemetry and inference attribution were not tested.

## Conclusion and remaining work

The first package installed successfully but failed owner visual acceptance:
GNOME's panel covered the upper parts of the companions. Correct coordinates and
the dock hint did not prove shell stacking. This failure led to the correction below.
Private backups allow recovery; this receipt contains no private logs, credentials
or conversation data.

## GNOME clock and stacking correction

Candidate `codex-model-router_0.9.6-2~main20261009.3_all.deb`, SHA-256
`7d1b9a15da0b992dfcf775f829521555245033a14be3ea2542fee4d8753eda92`.
GNOME uses an override-redirect accessory above its panel; a managed dock alone
remains insufficient. Native bounding/input shapes exclude a 220×32 logical-pixel
centered clock slot on this display. Shared UI places agents/navigation and quota
in the side wings, with a vertical fallback on narrow windows. Unpinning restores
managed window semantics. WebKit receives keyboard focus after a click, without
mapping stealing focus. No global shell setting or extension was installed.

- PASS: all 14 browser groups, including 1×/2× camera and clock-wing geometry
  across Compact/Home/Agents/History/Consumption/Settings and the narrow fallback.
- PASS: current-redesign owner-compositor preview, both initial pin settings,
  all six transitions. X server bounding/input shape readback confirms the clock
  center is excluded and both surrounding and lower surface remain included.
- PASS: isolated Xvfb probe using actual XTest click/key events; WebKit input
  receives typed `a`. Native visual/input holes also checked in that probe.
- PASS: exact final extracted package GTK/WebKit smoke.
- PASS: visible-auth installation/readback of `2~main20261009.3`, monitor
  `1ad50dd7d6ffdeb1`, installed/loaded router `88a0be134bc26eb9`. One monitor and
  connection, WebKit ready, current source UI matches, seven protected settings
  unchanged, no traceback/mismatch/unknown/restart flags. Only the monitor restarted.
- PASS: installed main surface at logical origin (2480,0), override-redirect
  enabled, actual X server bounding/input shapes leave the clock hole clear.
- Pending: owner visual/input acceptance of this correction. The previous clipped
  installed state is retained above as a failure, not an accepted design.

## Rounded clock fit

The owner accepted the general arrangement and requested a tighter rounded hole
around the gray clock pill. The rectangular 220×32 opening becomes a 128×28 pill
with a 2-pixel vertical inset on this 32-pixel panel. The same rounded scanline
region controls both visibility and click-through; the shared side wings shrink
with it. This targets the owner's default centered date/time format and theme.

Artifact `codex-model-router_0.9.6-2~main20261009.4_all.deb`, SHA-256
`9aad5920fe48b72228ef4a2a0393b5c543f9a382e634654edd8ce19519d2d03f`.
Both saved-topmost native runs pass all six transitions with the current UI.
X server shape checks additionally verify that the top margin and upper corners
are filled while the clock center remains excluded. Shared camera/clock browser
checks at 1×/2× and the exact extracted-package GTK/WebKit smoke pass. Broader
checks above remain evidence for `.3`; they were not all repeated for this shape
change. Activation/readback and owner visual fit are recorded separately.

Installed readback PASS: `.4`, monitor `586862aea84883c2`, unchanged installed/loaded
router `88a0be134bc26eb9`, one monitor/connection, WebKit ready, matching UI, seven
protected settings files preserved and no mismatch/restart/traceback flags. Actual
mapped overlay remains at (2480,0); native rounded visual/input-hole checks pass.
Only the monitor restarted after visible authentication. Owner visual fit pending.

## Final clock margin refinement

Owner feedback confirmed the rounded shape was nearly right, with a small remaining
border. Candidate `.5` reduces the opening to 122×26 logical pixels on this panel:
3 fewer pixels per side and 1 fewer pixel above/below than `.4`. Native current-UI
startup/unpin/pin/hide/expanded/compact and rounded visual/input shape checks pass,
as do the camera/clock browser fixture and exact extracted-package GTK/WebKit smoke.
Artifact `codex-model-router_0.9.6-2~main20261009.5_all.deb`, SHA-256
`8bb03619a092c118beb6dbbbc7afbdd28b41381e8c607a662b71e61fd5e25d75`.

Installed readback PASS: `.5`, monitor `484dca514488a5d7`, installed/loaded router
`88a0be134bc26eb9`, one monitor/connection, current UI matches, seven protected
settings preserved, WebKit ready and no traceback/mismatch/restart flags. Only
the monitor restarted after visible authentication. On 2026-10-09 the owner accepted
the final visual fit and authorized publication to remote `main`. This closes the
clock/top-edge visual fit for this owner session; broader physical keyboard/input,
display/scaling/sleep and telemetry/inference gates remain separate. The candidate
branch and uncommitted states above identify the observations before publication;
use the published Git revision for delivery identity.
