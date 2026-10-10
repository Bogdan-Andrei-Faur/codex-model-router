# Windows and Ubuntu managed-update acceptance

Status: implementation available in source; **owner-host native acceptance pending on both
platforms**. This document is the handoff, not an installation receipt. The public
0.9.7 Release still contains only the previously validated Mac arm64 artifact.
Do not publish Windows/Linux assets as validated based on Mac unit tests.

## Preparation on each machine

1. Read `AGENTS.md`, `docs/HANDOFF.md` and `docs/MANAGED-UPDATES.md`. Record the
   exact source commit, OS/architecture, package hash, monitor and router builds.
   Use `REPORT-TEMPLATE.md`; include safe metadata only, never private state.
2. Use a disposable OS account/VM first. No owner app replacement, Desktop close,
   logout or crash injection while owner agents are working. Obtain a maintenance
   window before repeating approved cases against the actual installation.
3. Build two distinct increasing semantic versions from isolated checkouts. Both
   baselines must include `managedUpdateProtocol: 1` in `application.json` and
   the native shutdown/readiness hooks. Older packages cannot acquire those
   hooks retroactively: install this baseline once with the normal installer.
   A source checkout/legacy ZIP is deliberately ineligible for managed updates.
4. Produce the new version's exact target installer and signed update manifest.
   Test signatures must use a disposable key trusted only by fixture builds;
   never add a test key or alternate feed to production. The production signing
   key stays on the publisher's Mac; transfer only packages/hashes and signed
   public metadata through the owner. Never invent a new publisher on another PC.
5. First run the local fixture cases below. Then, after separate publication
   authorization, publish immutable validated assets plus the signed manifest
   and exercise the production anonymous GitHub check/download from Settings.
   A direct call to `PortableApplier.prepare` is not Settings-button acceptance.

## Windows

Build with `tools/packaging/build_windows_installer.py --help` (native Windows
x64, Python, Inno Setup, .NET Framework 4.8 references and authenticated Microsoft
WebView2 bootstrapper). Use the builder's isolated payload, not a legacy ZIP.
Run `python -m unittest discover -s tests -p "test_*.py"`, `npm test` and
`npm run test:layout`; then existing native package/WPF/WebView2 probes.
**WPF only needs validation when using Windows.** Cross-compilation is not WPF
acceptance.

The native monitor holds `state/monitor-windows.lock` for its full lifetime.
The old copied runtime lives outside the installation, runs the signed Inno
installer silently with no restart/no forced application closure, then reads its
version selection. The new monitor must acknowledge an actual WebView2 snapshot.
On failure, `active.json` returns to the recorded previous version and that
monitor is reopened. Versioned runtimes remain available; this is runtime
rollback, not a reversal of every Windows uninstall-registry/shortcut change.
The stable launcher must retain compatibility with previous version manifests.
Recovery registers an individual HKCU Run entry, removed on terminal completion.
The Run command uses the stable launcher and validates Microsoft's 260 UTF-16
code-unit limit before handoff. Oversized custom paths fail safely; validate
spaced/non-ASCII roots and the new launcher dispatch at actual login. See
[Microsoft Run/RunOnce limits](https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys).
No UAC elevation or machine-wide setting is used by this per-user installer.

Validate specifically:

- Paths with spaces/non-ASCII; per-user install, same data/DPAPI identity and
  WebView2 profile; only one monitor after automatic relaunch.
- The backend has exited and released binaries before Inno's locked-file check.
  Another process holding an install DLL refuses the update without termination.
- WebView2 missing/broken, disk full, denied write, installer nonzero/reboot-needed
  exit, interrupted activation and failed native readiness. Never reboot the PC.
- Kill only the disposable helper in `committing` / `confirming`; log out/in and
  verify HKCU recovery restores the prior runtime and removes its Run entry.
  A surviving installer or monitor must block recovery rather than be killed.
- Confirm the old runtime still starts through the **new** stable launcher after
  rollback, and Start-menu/uninstall entries remain usable. Keep the test failure
  open if the new launcher cannot run the old version.

## Ubuntu

Build on the actual target architecture:

```sh
python3 tools/packaging/build_linux_package.py --output release/linux-candidate --release-name
python3 -m unittest discover -s tests -p 'test_*.py'
npm test
npm run test:layout
xvfb-run -a dbus-run-session -- python3 tests/smoke_package_linux.py release/linux-candidate/<package>.deb
```

For repeatable isolated helper coverage (no sudo, no system installation):

```sh
xvfb-run -a dbus-run-session -- python3 tests/probe_linux_managed_update.py
```

Run as an unprivileged fixture user with the build/runtime dependencies. It builds
signed synthetic0.0.1/0.0.2 packages with an ephemeral private key kept in memory,
checks successful new GTK/WebKit readiness, injected startup rollback and killed
helper replay, data retention and recovery-registration cleanup. On Docker use
`--init` so Xvfb's startup signal works; mount only an explicit source snapshot,
never owner state/home or the Docker socket. It passed Ubuntu24.04 arm64 on Mac;
this is **not** Settings-button, GUI-login or physical desktop acceptance.

The `.deb` remains `Architecture: all` (Python/system GTK), while the release
filename identifies the architecture that was actually validated. Do not label
other architectures as validated by copying/renaming that file.

Install the baseline `.deb` through the normal graphical package installer once
so apt resolves its dependencies. Managed updates extract **only** the signed
application payload into the user's private update directory; they run no Debian
maintainer scripts and do not write `/usr`, use sudo or change dpkg's database.
An atomic per-user selector chooses the new runtime. The system package remains
the bootstrap/dependency baseline; `dpkg-query` reports that baseline, while
Settings reports the running application. A newer/equal baseline installed via
apt takes precedence over the selected user runtime. Existing system dependencies
are checked before handoff; future dependency changes require a baseline package
upgrade and a new managed protocol, rather than privileged ad-hoc commands.

Validate specifically:

- A real GTK/WebKit session on supported Ubuntu; X11 and Wayland/XWayland.
  New UI acknowledgement must happen only after a successful WebKit snapshot.
- Launch from the desktop file, system launcher and ordinary Desktop bridge after
  success/rollback. Each must select the expected runtime without a source repo.
- Preserve XDG data root, keyring namespace/Secret Service access, config,
  characters, history and metrics. Use non-ASCII/spaced paths and a custom
  absolute `XDG_DATA_HOME` / `XDG_CONFIG_HOME`.
- Verify `/usr/lib/codex-model-router` and dpkg version are unchanged by a managed
  update. Another local user must retain their own runtime selection.
- Verify missing GTK/WebKit/crypto dependency, disk full, invalid tar link/path,
  non-writable state directory and readiness failure leave/recover the old app.
- Interrupt only the disposable helper at commit; verify GUI-login autostart
  recovery, native lock contention and removal of its `.desktop` recovery entry.
- Install a newer system `.deb` through apt; confirm it supersedes an older user
  runtime. Removing the baseline removes the system launcher; private data and
  retained runtimes are not automatically deleted. Do not uninstall mid-update.

## Shared acceptance matrix — record each independently

| Case | Required evidence |
| --- | --- |
| Settings Check → Update | Exact target/version, anonymous GitHub response, signature/digest match, progress, automatic old-monitor exit, new native UI ready, completed receipt |
| Cancel download/preparation | No pointer/install change, current monitor survives, no later apply/recovery from cancelled job |
| Wrong/expired signature or changed package | Rejected before installer/payload execution or monitor close |
| Desktop bridge active | Update refused; no Desktop/agent termination or signal; retry succeeds after owner-controlled closure |
| Launch/readiness failure | Prior selection restored and old native monitor starts; receipt rolled_back, not completed |
| Interrupted transaction | Recovery at login or explicit fixture replay, no overwrite while another installer/monitor survives |
| Data retention | Synthetic markers/hashes unchanged, credential handle still usable; never export secret values |
| Repeated launch/update | Exactly one monitor; terminal helper replay idempotent; no stale startup entry |
| Public-release run | Real downloaded bytes, actual Settings action and native acknowledgement; local fixtures alone cannot close this gate |

On failure retain the private job for diagnosis, report only phase/error/version
and safe hashes, and leave the specific gate pending. Never copy operation files,
private paths, keys, raw logs or conversation identifiers into the repository.
