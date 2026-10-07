# Windows capsule startup correction — 2026-10-06 — host-a

## Identity and scope

- Windows x64 local host; source baseline `50e63b07fbe65e182aebeb414e6daea1e1ca599e` with uncommitted installer work.
- Candidate product 0.9.3; build `3da07492a5af00ae`; router build `d323562bd219e24a`.
- Artifact: `codex-model-router-0.9.3-windows-x64-setup.exe`, unsigned local pilot.
- SHA-256: `d3a99def267b8654b98d605f42c476cc2cbd897a3d8713a66193145f929b9072`.
- Owner reported an invisible startup capsule that became visible after expanding the panel.
- Agent checks did not stop apps, modify owner data, register Desktop or install the candidate.
- Owner subsequently installed 0.9.3 and confirmed the capsule fix worked. Read-only active manifest matches the candidate version/build/router build above.

## Results

| ID | Mode | Status | Evidence | Limit |
| --- | --- | --- | --- | --- |
| CAPSULE-OLD | Browser regression reproduction | FAIL | Compact viewport height changed while surface size stayed constant; last native bounds remained stale | Original resize observer only watched element size |
| CAPSULE-BOUNDS | Browser fixtures | PASS | Native bounds match compact surface after viewport resize and Hidden/Compact transition | Does not prove native region visibility alone |
| CAPSULE-NATIVE | Isolated installed WebView2 fixture | PASS | Startup, viewport resize, restored position and hidden/show checked before expanding; CSS/native bounds match; GetWindowRgn/PtInRegion verify visible capsule center | Owner's physical startup/input/DPI acceptance pending |
| UI-SHARED | Browser fixtures | PASS | 26 core tests and seven layout/interaction groups | No cross-host physical acceptance |
| NATIVE-PAYLOAD | Relocated frozen/native fixtures | PASS | Runtime/assembly identities, IPC, preview, imports, safe diagnostics, DPAPI synthetic roundtrip, invalid candidate rejection | No production setup or live inference |
| OWNER-UPDATE | Physical owner action + read-only manifest | PASS | Installed active manifest matches exact 0.9.3 candidate | No claim about loaded Desktop bridge |
| CAPSULE-OWNER-START | Physical owner report | PASS | Owner confirmed the startup capsule fix worked after updating | Scope is reported capsule visibility; separate DPI, sleep/resume and general UI acceptance remain open |

## Root cause and correction

The bottom-anchored compact surface moves when the native viewport settles at
startup or changes size. Its own width/height can remain constant, so its size
observer does not emit a new native clipping rectangle. Expanding changes surface
size, refreshing that rectangle and making the UI visible again.

The shared surface now reports bounds on viewport resize and mode acknowledgement,
in addition to surface-size changes. Native positioning explicitly requests fresh
bounds. Reporting happens on the next animation frame to measure completed layout.
No forced Expanded/Compact workaround or stored-preference reset is used.

Owner confirmation closes the reported startup visibility defect on this installed
artifact. Existing imported configuration/history remain valid. This does not close
other physical display/input/sleep checks or establish loaded Desktop bridge identity.
