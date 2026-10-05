# Real-machine validation runbook

This runbook is the entry point for an agent on a real Mac, Windows PC or Ubuntu
desktop. It requires only this repository and local tools. No Atlas, Knowledge,
personal memory, original chat or access to another agent is required.

Project: `codex-model-router`.
Repository: `https://github.com/Bogdan-Andrei-Faur/codex-model-router.git`.
Read the root [AGENTS.md](../AGENTS.md), then the current
[acceptance ledger](native-validation/STATUS.md). Record results with the
[report template](native-validation/REPORT-TEMPLATE.md).

## 1. Establish exactly what is being tested

Use a local logged-in graphical session. A hosted runner, remote shell without a
desktop, simulated OS, browser fixture or cross-compilation cannot establish
physical input, display placement or sleep/resume acceptance.

From the checkout, inspect:

```sh
git status --short --branch
git fetch origin
git log --oneline HEAD..origin/main
git log --oneline origin/main..HEAD
git rev-parse HEAD
git describe --tags --always
```

If clean and without local divergence, `git pull --ff-only` updates the checkout.
Otherwise preserve local changes and decide integration before proceeding. Never
use reset/clean to obtain a test environment. Use an existing authorized GitHub
login; do not paste credentials into reports or chats.

Record these **separately**, using safe labels instead of computer/user names:

| Identity | Required record |
| --- | --- |
| Source | Exact commit, dirty/clean state, product VERSION, policy version |
| Host | OS version/build, CPU architecture, Python version |
| Desktop/backend | Installed Desktop version and actual discovered official CLI version |
| Installed router | Source/ZIP/pkg/deb mode, installed product/build/router fingerprints, artifact SHA-256 when available |
| Active bridge | Build actually loaded, fresh heartbeat, completed handshake, Desktop connection |
| Displays | Display count, resolution/scaling per display, primary display, Linux session and actual monitor backend |

Inspect the installed monitor's version/build and connection in Settings. A
checkout commit is not proof that the installed monitor or open bridge uses it.
Data defaults are Mac `~/Library/Application Support/codex-model-router`, Ubuntu
`$XDG_DATA_HOME/codex-model-router` (or `~/.local/share/codex-model-router`), and Windows
`%LOCALAPPDATA%/codex-model-router` for the common layout. Legacy source/Windows
ZIP installations can keep data in their own directory. Confirm the actual root;
do not move it or copy another OS's configuration/credential blobs.

Diagnostics below are for **source mode** and can write a local connection report:

| Host | Local diagnostic |
| --- | --- |
| Mac | `python3 macos.py doctor`, then `python3 desktop.py doctor` |
| Windows | `python desktop.py doctor` |
| Ubuntu | `/usr/bin/python3 linux.py doctor` |

For an installed package use its Settings diagnostics rather than pointing source
commands at an assumed root. Inspect diagnostics locally; paths and raw reports
stay private. `desktop_connected` means the existing bridge is observed;
`restart_pending` means registration alone has not activated it. If activation
needs closing/reopening Desktop, let the owner choose when current work is done.
Record `BLOCKED` until that happens. Do not install/re-register merely to run QA.

## 2. Preconditions and portable regressions

- Native telemetry probes need **Python 3.11+** (`tomllib`); Python 3.14 is the
  recommended validation interpreter. Core CI also tests Python 3.9.
- Docker is needed only for experimental generated-code graders. Use local Docker
  Engine on Linux or Docker Desktop in **Linux containers** mode on Mac/Windows.
- Mac UI fixtures require Xcode Command Line Tools and a graphical session.
- Windows UI fixtures require .NET Framework 4.8 reference assemblies, native C#
  compiler and WebView2 Runtime Evergreen. `build.ps1 -BuildOnly` does not install
  shortcuts; it still writes build outputs. Do not replace running binaries.
- Ubuntu UI requires system PyGObject/Cairo, GTK3, WebKitGTK4.1 and `xprop`
  (`x11-utils`) for the window-manager probe. See [LINUX.md](LINUX.md) for packages.

Use a fresh terminal. Desktop can export `PERSONAL_CODEX_*`, `CODEX_CLI_PATH`,
`PYTHONPATH` and `PYTHONHOME` pointing to installed code; such inherited overrides
can make checkout tests exercise a different installation. The following portable
suite removes those overrides **only in its child process**, on any platform
(use `python3` instead of `python` on Mac/Linux):

```sh
python -c "import os,subprocess,sys; env={k:v for k,v in os.environ.items() if not k.startswith('PERSONAL_CODEX_') and k not in ('CODEX_CLI_PATH','PYTHONPATH','PYTHONHOME','ROUTER_TEST_DOCKER_GRADERS')}; subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py'],env=env,check=True); subprocess.run([sys.executable,'tests/evaluate_routing.py'],env=env,check=True)"
```

The second command runs the routing corpus. Expected: all 27 current routing cases pass. Report
actual counts and skips, not an old expected total. These commands use fixtures
and request no Codex/JEV inference. Missing infrastructure is `BLOCKED`, not PASS.

For shared UI regressions, use the repository's Node/npm toolchain from
`package.json`/`package-lock.json`. These commands install checkout dependencies
and a test browser, then exercise synthetic data:

```sh
npm ci
npx playwright install chromium
npm test
```

For layout groups on Mac/Linux run `ROUTER_TEST_BROWSER=chromium npm run test:layout`.
On Windows PowerShell run `$env:ROUTER_TEST_BROWSER='chromium'; npm run test:layout`
in the disposable validation terminal. Record Node version, actual counts and
exit codes. Browser fixtures do not close any installed/physical UI row below.

## 3. DKR: actual Docker Desktop/Engine acceptance

This closes the Mac/Windows **local Docker** gap; Linux-hosted CI is only a
baseline. Record Docker client/server versions and engine OS/architecture:

```sh
docker version --format '{{.Client.Version}} {{.Server.Version}}'
docker info --format '{{.OSType}} {{.Architecture}} {{.CgroupVersion}}'
```

Expected: Linux engine, x86_64/aarch64, cgroup v2, local endpoint. Do not publish
context/socket paths, daemon configuration or full `docker info` output. Desktop
must share the user's temporary directory with its Linux VM. Remote TCP/SSH
contexts and ineffective resource controls are deliberately rejected.

Pull the exact image once, then check controls (Mac/Linux use `python3`):

```sh
python -c "import subprocess; from tests.grader_sandbox import IMAGE; print(IMAGE); subprocess.run(['docker','pull',IMAGE],check=True)"
python -m tests.grader_sandbox
```

Expected exit 0 and `read_blocked`, `write_blocked`, `network_blocked` all true.
Then enable the **entire** Docker integration suite:

```sh
# Mac/Linux
ROUTER_TEST_DOCKER_GRADERS=1 python3 -m unittest discover -s tests -p 'test_*.py'
```

```powershell
# Windows PowerShell; restore the previous test flag afterwards.
$routerPreviousDockerFlag = $env:ROUTER_TEST_DOCKER_GRADERS
try {
    $env:ROUTER_TEST_DOCKER_GRADERS = '1'
    python -m unittest discover -s tests -p 'test_*.py'
    if ($LASTEXITCODE -ne 0) { throw 'Docker grader suite failed' }
} finally {
    if ($null -eq $routerPreviousDockerFlag) { Remove-Item Env:ROUTER_TEST_DOCKER_GRADERS -ErrorAction SilentlyContinue }
    else { $env:ROUTER_TEST_DOCKER_GRADERS = $routerPreviousDockerFlag }
}
```

Run these probes from a terminal opened independently of Desktop, without the
overrides listed in section 2. If only an inherited Desktop terminal is available,
use the section 2 child-environment wrapper with the corresponding command and
set `env['ROUTER_TEST_DOCKER_GRADERS']='1'` inside it for the Docker suite.
Expected: no failures;
Docker-specific tests must execute, not skip. Other OS-specific tests may skip on
Mac/Windows. Record executed/skipped counts. The suite covers all eight evaluator
families, large heap/mmap/aggregate allocations, load-time defaults, socket denial,
read-only inputs, environment isolation, timeout cleanup and infrastructure errors.

Check `docker ps -aq --filter name=codex-grader-` before/after. PASS requires no
new leftover test containers. Never delete pre-existing or another process's
container. An orphan after SIGKILL/power loss is a recovery case, not permission
to remove every matching name. See [GRADER-SANDBOX.md](GRADER-SANDBOX.md) for the
256 MiB/no-swap/CPU/PID/seccomp invariants. Do not loosen limits to obtain PASS.

## 4. TEL: native authenticated telemetry on this host

Codex Desktop must already be installed and signed in through its normal login.
Run from the checkout with Python 3.11+, in the independent terminal described
in section 3 (or its clean child-environment wrapper):

```sh
python -m unittest tests.test_security_fixes.TelemetryTransportTests -v
python tests/smoke_telemetry.py --layout root --layout subcommand --layout desktop
```

Mac/Linux: substitute `python3`. There is **no `--live`** in this acceptance
step. It starts isolated backend sessions/ephemeral threads, disables tools/MCP
for those sessions, requests no model generation and leaves owner conversations
untouched. Native probes can use existing authentication locally; never export it.

For each layout require exit 0, `native_config_verified=true`,
`before_shutdown.requests > 0`, and zero `unauthorized_requests`, `unexpected_path`,
`rejected_connections` and all `invalid_*` counters, before and after shutdown.
Prompt logging must be disabled for the probe. The transport regression
asserts a synthetic bearer is only in child environment, absent from argv, and
rejects missing private environment. Successful native reception demonstrates
that this host's official backend accepts that transport. Do not dump process
arguments/environment to prove it: those can expose unrelated owner credentials.

This isolated probe does not prove an already-open Desktop has loaded the new
bridge. Separately check the installed monitor after owner-controlled activation:
one expected monitor, one bridge per connected Desktop, fresh handshake/heartbeat,
loaded build matching the intended artifact and authenticated counters advancing
during normal use. Do not assume multiple legitimate Desktop sessions are bugs.
A requested/accepted model setting does not identify the model of every response;
do not mark inferential attribution or billing proven by this check.

If catalog/authentication/config parsing rejects the probe (including its fixed
test model), record the phase and safe error code. Recheck current discovery and
catalog; do not silently enable tools, change account settings or remove auth.

## 5. UI: native fixtures and physical acceptance

Fixtures check source/native behavior. The manual checklist must then run against
the **actual installed** monitor, with installed/loaded identity recorded.

### Mac

```sh
python3 tests/probe_mac_monitor.py
```

Expected exit 0, `native_fixture_exit=0`, `one_click_delivered=true`.
`physical_os_mouse_delivery_verified=false` is expected: this fixture is not
physical acceptance. With another application focused, hover an agent, move into
its card, then click a monitor action once. Hover must keep external focus; one
click must activate the action, without needing a second click. Check Settings
input, click-through outside interactive regions, and responsive updates under
ordinary activity. See [MAC-MONITOR-INTERACTION.md](MAC-MONITOR-INTERACTION.md).

If the source native monitor must be rebuilt, `python3 macos.py setup` writes
config, launchers and bundle outputs. It is **not** a read-only prerequisite;
coordinate it with the owner and preserve existing artifacts/preferences. Do not
infer installed GUI acceptance from an isolated Swift compilation.

### Windows

Build only when outputs are safe to replace, using PowerShell:

```powershell
.\build.ps1 -BuildOnly
if ($LASTEXITCODE -ne 0) { throw 'Native build failed' }
$routerReview = Start-Process -FilePath '.\dist\codex-monitor-v24.exe' -ArgumentList '--self-test' -PassThru
if (-not $routerReview.WaitForExit(120000)) { $routerReview.Kill(); throw 'Owned self-test timed out' }
if ($routerReview.ExitCode -ne 0) { throw 'WebView2 self-test failed' }
Get-Content -LiteralPath '.\state\ui-review-checks.txt'
```

The timeout kills only the test process just started. Reference path defaults to
the .NET Framework 4.8 reference assemblies; pass `-FrameworkReferencePath` if the
installed location differs. Expected exit 0 and PASS in the synthetic receipt.
Self-test output stays in ignored `state/`. Then inspect first click/hover, tray,
transparent click-through, focus and Settings on the installed monitor. The
Windows ZIP is not a completed graphical setup installer.
See [WINDOWS-WPF-VALIDATION.md](WINDOWS-WPF-VALIDATION.md).

### Ubuntu

Run in a real GNOME/XWayland session with the system Python and `xprop` available:

```sh
env -u GDK_BACKEND /usr/bin/python3 tests/smoke_linux_window.py
env -u GDK_BACKEND /usr/bin/python3 tests/smoke_linux_window.py --saved-topmost off
```

Expected exit 0, real `GdkX11Display`, `error=null`, and all six steps passed:
startup, unpin, pin, hide, show-expanded, compact. These synthetic windows verify
the compositor's position and `_NET_WM_STATE_ABOVE`, with temporary preferences.
They do not cover physical multi-monitor or suspend/resume.

On pure Wayland without XWayland, record `BLOCKED` for absolute position/topmost:
the compositor controls those features. Check the monitor displays its limitation
notice. Do not disable Wayland or change the owner's session to force PASS.

### Physical checklist on the installed monitor

| ID | Action | PASS criteria |
| --- | --- | --- |
| UI-INPUT | Focus another app, hover, first click, click-through, Settings input | Hover preserves focus; one click works; outside transparent surface passes through; inputs accept text |
| UI-VIEWS | Compact/panel/hidden, tray/menu recovery, reopen | Correct view and bounds; no duplicate capsule; saved mode/topmost preserved |
| UI-DATA | Inspect context/compaction/quota during ordinary work | Context, compaction and missing-data states are distinct; quota number centered; no invented 0% for missing samples |
| UI-DISPLAY | Two physical displays with different scaling; change primary; move/disconnect/reconnect display | Monitor stays reachable in work area; no clipped buttons/overflows; physical clicks remain aligned |
| UI-SCALE | Record original scale; test supported fractional/DPI settings; restore | Correct hit regions/text/geometry after scale change and relaunch |
| UI-SLEEP | Owner suspends and resumes after safe work boundary | Monitor/bridge reconnect normally; heartbeat/telemetry resume; no stale active agents or duplicated monitor |
| UI-START | Owner closes/reopens or reboots through usual startup when convenient | Same expected instance and saved preferences; installed/loaded versions agree |

Run display/sleep checks only with owner agreement: they affect the whole desktop.
Restore the original display settings. A single-display machine cannot PASS the
multi-display row; record `NOT_RUN` with missing hardware. If no natural context
compaction occurs, keep that observation `NOT_RUN`; do not manufacture a costly
turn just to fill the row. A fixture-only result must say `fixture`, not `physical`.

Native credential storage remains a separate optional host acceptance row
`KEY-NATIVE`: Mac Keychain, Windows DPAPI, Ubuntu Secret Service. Use only an
isolated new test data root with a synthetic value, keep classifier mode Rules,
never use/replace an existing provider key, verify save/read/reopen, and remove
only the test entry afterward. Follow the native storage adapters in
`MonitorMac.swift`, `MonitorWindows.cs`, `linux_secret.py` and `decision_engines.py`;
record the store and booleans only. Unit mocks/presence indicators alone do not
prove native decryption. If that isolated test is not authorized/prepared, mark
`NOT_RUN`; it does not invalidate the unrelated Docker/telemetry results.

## 6. Report, handoff and closure

Create a new `docs/native-validation/YYYY-MM-DD-<platform>-<safe-label>.md` from
the template. A safe label is an arbitrary alias such as `host-a`, never the
actual machine/user name. One receipt covers one source/artifact/loaded-bridge
combination. Record every command, exit code, count/skip, observation, test mode
and limitation. Keep earlier reports unchanged; a later report can supersede
specific rows with links. Update only the relevant host cells in STATUS.md.

Allowed statuses: `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, `NOT_APPLICABLE`.
Explain every status other than PASS. Infrastructure/hardware absence is not
PASS; an intentional unsupported platform feature is not a successful test.
Keep source-only, isolated native, installed and physical results separate.

Reports contain only versions, hashes, counts, booleans, safe error codes and
sanitized descriptions. Keep raw doctor output, logs, process listings, state,
prompts, titles, response text, conversation IDs, account IDs, keys and original
install/home paths out of Git. Screenshots may only show synthetic fixtures or
an owner-reviewed/redacted surface; keep unredacted originals local.

After reviewing the receipt, commit/publish it through the owner's authorized
workflow. Do not message another machine's agent. The owner or that agent can
pull the repository and follow this runbook independently.

This plan does not authorize paid inference (`--live`), new sign-in credentials,
system installation, updates, reboot/sleep, paid signing, public releases or
activation of candidate policy9. Missing consent is recorded for the relevant
check; safe independent rows can continue. Installation/upgrade/uninstall QA has
its own [delivery plan](INSTALLATION-UPDATES.md) and is not closed by this runbook.
