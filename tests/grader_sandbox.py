"""Optional, fail-closed Docker execution for experimental graders only."""
import csv
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
# Official multi-architecture Python 3.14.7 slim-bookworm, fixed scoring runtime.
IMAGE = 'python@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56'
INTEGRATION = os.environ.get('ROUTER_TEST_DOCKER_GRADERS') == '1'


class SandboxUnavailable(RuntimeError):
    pass


def docker_command():
    executable = shutil.which('docker')
    if not executable:
        raise SandboxUnavailable('docker_grader_required: see docs/GRADER-SANDBOX.md')
    try:
        # Freeze the selected local endpoint. Never send candidate files to a
        # remote context, nor mount a Docker socket into the child container.
        endpoint = os.environ.get('DOCKER_HOST') if not os.environ.get('DOCKER_CONTEXT') else None
        if not endpoint:
            result = subprocess.run([executable, 'context', 'inspect', '--format', '{{.Endpoints.docker.Host}}'],
                                    capture_output=True, text=True, timeout=10, check=True)
            endpoint = result.stdout.strip()
        if not endpoint.startswith(('unix:///', 'npipe:////./pipe/')):
            raise SandboxUnavailable('local_docker_endpoint_required')
        command = [executable, '--host', endpoint]
        result = subprocess.run(command + ['info', '--format', '{{.OSType}}'],
                                capture_output=True, text=True, timeout=10, check=True)
        if result.stdout.strip() != 'linux':
            raise SandboxUnavailable('docker_linux_containers_required')
        subprocess.run(command + ['image', 'inspect', IMAGE],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=True)
        return command
    except (OSError, subprocess.SubprocessError):
        raise SandboxUnavailable('docker_grader_not_ready: see docs/GRADER-SANDBOX.md') from None


def run_sandbox(root, *args, timeout=4):
    """Run staged trusted worker; remove its whole container even on timeout."""
    command = docker_command()
    root = Path(root).resolve()
    translated = []
    for arg in args:
        path = Path(arg)
        if path.is_absolute():
            try:
                relative = path.relative_to(root)
            except ValueError:
                raise SandboxUnavailable('grader_argument_outside_root') from None
            translated.append('/grader/' + relative.as_posix())
        else:
            translated.append(str(arg))
    name = 'codex-grader-' + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix='codex-grader-stage-') as tmp:
        # The host parent remains private; the non-root container only sees
        # this readable child and never the original host workspace.
        stage = Path(tmp) / 'input'
        stage.mkdir(mode=0o755)
        stage.chmod(0o755)
        total = 0
        for source in root.iterdir():
            if source.is_symlink() or not source.is_file():
                raise SandboxUnavailable('grader_input_not_regular')
            if source.name == 'grader_limits.py':
                raise SandboxUnavailable('grader_input_reserved_name')
            size = source.stat().st_size
            total += size
            if total > 1024 * 1024:
                raise SandboxUnavailable('grader_input_too_large')
            target = stage / source.name
            target.write_bytes(source.read_bytes())
            target.chmod(0o444)
        guard = stage / 'grader_limits.py'
        guard.write_bytes((HERE / 'grader_limits.py').read_bytes())
        guard.chmod(0o444)
        mount = io.StringIO()
        csv.writer(mount, lineterminator='').writerow([
            'type=bind', 'source=' + str(stage), 'target=/grader', 'readonly'])
        create = command + [
            'create', '--name', name, '--pull=never', '--network=none',
            '--ipc=none',
            '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--user=65534:65534', '--memory=256m', '--memory-swap=256m',
            '--pids-limit=16', '--cpus=1', '--ulimit=cpu=2:2',
            '--ulimit=nofile=32:32', '--ulimit=fsize=0:0', '--log-driver=none',
            '--workdir=/grader', '--mount',
            mount.getvalue(),
            '--entrypoint=/usr/local/bin/python3', IMAGE,
            '-I', '-S', '-B', '/grader/grader_limits.py', '--container', *translated]
        try:
            try:
                created = subprocess.run(create, capture_output=True, timeout=15)
            except (OSError, subprocess.SubprocessError):
                raise SandboxUnavailable('docker_grader_create_failed') from None
            if created.returncode:
                raise SandboxUnavailable('docker_grader_create_failed')
            try:
                result = subprocess.run(command + ['start', '--attach', name],
                                        stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
            except OSError:
                raise SandboxUnavailable('docker_grader_start_failed') from None
            # A start timeout is the candidate wall-time limit; other setup
            # and inspection timeouts are infrastructure failures.
            try:
                inspected = subprocess.run(command + ['inspect', '--format', '{{json .State}}', name],
                                           capture_output=True, timeout=10, check=True)
                state = json.loads(inspected.stdout)
            except (OSError, subprocess.SubprocessError, ValueError):
                raise SandboxUnavailable('docker_grader_state_unavailable') from None
            # `docker start` uses exit 1 for both OCI/daemon errors and Python
            # failure. Only a completed container with a matching exit counts.
            if (not isinstance(state, dict) or state.get('Status') != 'exited'
                    or state.get('Error') or type(state.get('ExitCode')) is not int
                    or state['ExitCode'] != result.returncode):
                raise SandboxUnavailable('docker_grader_start_failed')
            return result
        finally:
            # Even a timed-out create can have reached the daemon. Always try
            # removal by our unique name, without touching other containers.
            try:
                removed = subprocess.run(command + ['rm', '--force', name],
                                         capture_output=True, timeout=10)
                if removed.returncode:
                    absent = subprocess.run(command + ['container', 'ls', '-aq', '--filter', 'name=^/' + name + '$'],
                                            capture_output=True, timeout=10, check=True)
                    if absent.stdout.strip():
                        raise SandboxUnavailable('docker_grader_cleanup_failed')
            except (OSError, subprocess.SubprocessError):
                raise SandboxUnavailable('docker_grader_cleanup_failed') from None


if __name__ == '__main__':
    from tests.coding_trials import sandbox_controls
    print(json.dumps(sandbox_controls(), sort_keys=True))
