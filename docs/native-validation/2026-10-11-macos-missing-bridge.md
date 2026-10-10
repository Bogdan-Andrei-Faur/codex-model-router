# Mac connection repair — 2026-10-11

The owner reported the generic connection failure even with Desktop closed.
Read-only checks found the managed connection receipt and login-agent definition
still correct, and the session override pointing to the expected managed bridge,
but `Contents/MacOS/codex-router` was absent from the installed app.
Discovery/backend version checking still worked; registration was consequently
reported false. Closing Desktop could not repair a missing executable.

The installed app was compared with the exact published Mac0.9.7 package:
SHA-256 `8e5b7489f306465721bd27a4467dab018d876b4234b2ad1e8f3656552eff56b2`.
The extracted app passed deep/strict code-signature verification. All existing
installed files matched; the bridge was the only missing payload file. Restored
only that absent86608-byte executable with exclusive creation and its original
permissions. No application replacement, rebuild, integration change, Desktop
restart, owner process termination or private-data modification was performed.

After restoration:

- Entire installed app deep/strict signature verification PASS.
- Exact installed bridge `--version` PASS.
- Isolated native bridge initialize/model-list handshake PASS; no task/turn made.
- Managed doctor: discovery ready, registered true, compatibility version checked,
  ordinary Desktop connection `restart_pending`, zero current Desktop sessions.
- Installed identity remains monitor992cea11bb136ed0/router0c8570cfccd9a1a8.

The cause of removal is **unknown**. No evidence attributes it to an updater,
Desktop, user action or security software. A subsequent read-only recheck on 11/10 confirms the ordinary managed connection:
`desktop_connected`, one Desktop/bridge session, completed Codex Desktop handshake,
product0.9.7, monitor992cea11bb136ed0 and router0c8570cfccd9a1a8. No restart
was performed by this follow-up. This is connection proof, not model inference proof.

Source-only follow-up maps an unavailable packaged bridge to a safe specific error
and changes generic feedback so it does not claim tasks are currently open.
22 desktop tests and7 monitor-service tests PASS under the clean portable Python.
These feedback changes are not installed/published; existing Windows/Ubuntu work
and other local changes are preserved. The incident is an operational repair,
not a new release or completion of outstanding platform acceptance gates.
