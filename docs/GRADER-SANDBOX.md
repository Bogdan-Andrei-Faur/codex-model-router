# Optional experimental evaluator sandbox

Only experiments that execute generated Python code require Docker. The monitor,
router, normal Codex integration and portable unit tests do not require it.
Linux, macOS and Windows use the same pinned Linux Python 3.14.7 runtime and
unchanged scoring workers. There is no native or unsandboxed fallback.

## Setup and verification

Use a local Docker Engine on Linux, or Docker Desktop with **Linux containers**
on Windows/macOS. The engine needs cgroup v2 with memory, swap, CPU and PID limits,
and seccomp. Supported container architectures are x86_64 and aarch64. Remote
SSH/TCP Docker contexts are deliberately rejected. The daemon must be able to
bind-mount the user's temporary directory (Desktop file sharing must allow it).

From the repository, pull the exact image once:

```sh
python -c "import subprocess; from tests.grader_sandbox import IMAGE; subprocess.run(['docker', 'pull', IMAGE], check=True)"
python -m tests.grader_sandbox
```

The second command must print three `true` controls: outside read, write and
network blocked. Missing Docker, missing image or ineffective isolation aborts
evaluation before candidate loading; grading never pulls an image automatically.
No Codex/JEV requests are made by these setup and regression commands.

Run all evaluator regressions on Linux/macOS:

```sh
ROUTER_TEST_DOCKER_GRADERS=1 python -m unittest discover -s tests
```

In PowerShell:

```powershell
$env:ROUTER_TEST_DOCKER_GRADERS = '1'
python -m unittest discover -s tests
```

The explicit test flag enables integration tests; it does not change the
evaluation backend or allow a fallback. Without it, the ordinary suite skips
Docker integration tests. With it, unavailable Docker is a failure, not a skip.

## Boundary and lifecycle

The shared runner mounts only copied grader inputs, read-only, from a private
temporary parent. It exposes no home, repository, credentials or daemon socket.
The child is UID 65534 with no capabilities, no privilege escalation, read-only
root, no IPC namespace and no network. A supplementary seccomp filter denies
socket/socketpair creation (including loopback and Unix sockets), preserving
Docker's default filter. Unsupported syscall architectures fail closed.

Docker enforces 256 MiB memory, zero swap, 16 PIDs, one CPU, two CPU seconds,
zero regular-file growth and 32 file descriptors. The trusted entrypoint checks
the **actual cgroup files**, UID/capabilities/seccomp state and network denial,
then verifies a hard 256 MiB address-space quota before loading candidate code.
This rejects rootless configurations that silently ignore resource options.
The host enforces each evaluation's wall timeout and removes the entire named
container in `finally`, including failed create/start and timed-out workers.
Docker logging is disabled; only existing filtered grading receipts persist.

The container engine is a trusted local dependency; this is defense in depth,
not a guarantee against a container-kernel exploit. An interrupted host process
that cannot execute cleanup (for example SIGKILL or power loss) can leave a named
`codex-grader-*` container. Ordinary exceptions and timeouts perform cleanup;
cleanup failures are explicit infrastructure errors.

## Why this replaces native Seatbelt grading

GitHub's macOS ARM Python processes reserve hundreds of GiB of virtual address
space before candidate execution. Native `RLIMIT_AS` rejects 256 MiB and 2 GiB;
raising that ceiling to hundreds of GiB would defeat the intended protection.
The approved Docker backend applies the same Linux kernel controls on all hosts.

CI runs real Docker grading on Linux x86_64 and ARM64, plus portable Python and
native monitor checks on Windows/macOS/Linux. GitHub's macOS ARM runners cannot
run nested virtualization, so they do not run Docker Desktop integration. Actual
Docker Desktop setup/file-sharing on the user's Mac/Windows remains a separate
host smoke test; Linux CI is not evidence that it has been performed.
