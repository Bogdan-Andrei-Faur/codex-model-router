import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tests import grader_sandbox as sandbox


class DockerAdapterTests(unittest.TestCase):
    def test_missing_docker_and_remote_context_fail_before_execution(self):
        with patch.object(sandbox.shutil, 'which', return_value=None):
            with self.assertRaises(sandbox.SandboxUnavailable):
                sandbox.docker_command()
        with patch.object(sandbox.shutil, 'which', return_value='docker'), \
                patch.dict(os.environ, {'DOCKER_HOST': 'tcp://remote:2375', 'DOCKER_CONTEXT': ''}), \
                patch.object(sandbox.subprocess, 'run') as run:
            with self.assertRaisesRegex(sandbox.SandboxUnavailable, 'local_docker_endpoint_required'):
                sandbox.docker_command()
            run.assert_not_called()

    def test_context_and_missing_image_fail_closed(self):
        with patch.object(sandbox.shutil, 'which', return_value='docker'), \
                patch.dict(os.environ, {'DOCKER_CONTEXT': 'desktop-linux'}), \
                patch.object(sandbox.subprocess, 'run') as run:
            for endpoint in ('unix:///tmp/desktop.sock', 'npipe:////./pipe/dockerDesktopLinuxEngine'):
                run.side_effect = [subprocess.CompletedProcess([], 0, endpoint),
                                   subprocess.CompletedProcess([], 0, 'linux'),
                                   subprocess.CalledProcessError(1, [])]
                with self.assertRaisesRegex(sandbox.SandboxUnavailable, 'docker_grader_not_ready'):
                    sandbox.docker_command()

    def test_cleanup_after_failed_create_timeout_and_interrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'worker.py').write_text('pass')
            for error in (subprocess.TimeoutExpired('docker', 1), KeyboardInterrupt()):
                for phase in ('create', 'start'):
                    calls = []
                    def run(cmd, **kwargs):
                        calls.append(cmd)
                        if phase in cmd:
                            raise error
                        return subprocess.CompletedProcess(cmd, 0, b'', b'')
                    with patch.object(sandbox, 'docker_command', return_value=['docker']), \
                            patch.object(sandbox.subprocess, 'run', side_effect=run):
                        expected = sandbox.SandboxUnavailable if phase == 'create' and isinstance(error, subprocess.TimeoutExpired) else type(error)
                        with self.assertRaises(expected):
                            sandbox.run_sandbox(root, str(root / 'worker.py'))
                    self.assertEqual(calls[-1][1:3], ['rm', '--force'])
                    self.assertEqual(calls[-1][-1], calls[0][calls[0].index('--name') + 1])

    def test_failed_cleanup_is_infrastructure_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'worker.py').write_text('pass')
            responses = [subprocess.CompletedProcess([], 0, b''),
                         subprocess.CompletedProcess([], 0, b'{}'),
                         subprocess.CompletedProcess([], 0, b'{"Status":"exited","ExitCode":0,"Error":""}'),
                         subprocess.CompletedProcess([], 1, b''),
                         subprocess.CompletedProcess([], 0, b'container-still-present')]
            with patch.object(sandbox, 'docker_command', return_value=['docker']), \
                    patch.object(sandbox.subprocess, 'run', side_effect=responses):
                with self.assertRaisesRegex(sandbox.SandboxUnavailable, 'docker_grader_cleanup_failed'):
                    sandbox.run_sandbox(root, str(root / 'worker.py'))

    def test_daemon_failure_is_not_scored_as_bad_candidate(self):
        from tests import coding_trials
        for state in ({'Status': 'created', 'ExitCode': 128, 'Error': 'OCI failure'},
                      {'Status': 'exited', 'ExitCode': 0, 'Error': ''}):
            responses = [subprocess.CompletedProcess([], 0, b''),
                         subprocess.CompletedProcess([], 1, b'', b'daemon failure'),
                         subprocess.CompletedProcess([], 0, json.dumps(state).encode()),
                         subprocess.CompletedProcess([], 0, b'')]
            with patch.object(sandbox, 'docker_command', return_value=['docker']), \
                    patch.object(sandbox.subprocess, 'run', side_effect=responses):
                with self.assertRaisesRegex(sandbox.SandboxUnavailable, 'docker_grader_start_failed'):
                    coding_trials.grade_source('confidence-repair', 'def confidence(response):return 0.5')

    def test_external_arguments_and_symlink_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(sandbox, 'docker_command', return_value=['docker']), \
                patch.object(sandbox.subprocess, 'run') as run:
            root = Path(tmp); (root / 'worker.py').write_text('pass')
            with self.assertRaisesRegex(sandbox.SandboxUnavailable, 'grader_argument_outside_root'):
                sandbox.run_sandbox(root, str(root.parent / 'external.py'))
            if os.name != 'nt':
                (root / 'alias').symlink_to(root / 'worker.py')
                with self.assertRaisesRegex(sandbox.SandboxUnavailable, 'grader_input_not_regular'):
                    sandbox.run_sandbox(root, str(root / 'worker.py'))
            run.assert_not_called()

    @unittest.skipIf(os.name == 'nt', 'Container guard imports Linux resource module')
    def test_missing_effective_controls_stop_before_candidate_loading(self):
        from tests import grader_limits as limits
        with patch.object(limits.sys, 'argv', ['guard', '--container', '/grader/worker.py']), \
                patch.object(limits, 'container_controls', return_value=False), \
                patch.object(limits.runpy, 'run_path') as run:
            self.assertEqual(limits.main(), 79)
            run.assert_not_called()
        with patch.object(limits.os, 'getuid', return_value=65534), \
                patch.object(limits.Path, 'read_text', side_effect=[
                    'CapEff:\t0\nNoNewPrivs:\t1\nSeccomp:\t2', 'max']):
            self.assertFalse(limits.container_controls())


@unittest.skipUnless(sandbox.INTEGRATION, 'Requires Docker grader integration')
class DockerIsolationTests(unittest.TestCase):
    def test_environment_and_mount_isolation_with_spaces_and_commas(self):
        original_temp = tempfile.TemporaryDirectory
        with original_temp(prefix='grader space,comma-') as tmp:
            root = Path(tmp) / 'source'; root.mkdir()
            worker = root / 'worker.py'
            worker.write_text('import os,json\nfrom pathlib import Path\n'
                              "assert 'GRADER_SYNTHETIC_SECRET' not in os.environ\n"
                              "assert os.getuid()==65534\n"
                              "for path in ('/grader/worker.py','/grader/new','/tmp/new','/dev/shm/new'):\n"
                              " try:open(path,'w')\n except OSError:pass\n else:raise AssertionError(path)\n"
                              "print(json.dumps({'bounded':True}))\n")
            with patch.dict(os.environ, {'GRADER_SYNTHETIC_SECRET': 'synthetic-value'}), \
                    patch.object(sandbox.tempfile, 'TemporaryDirectory',
                                 side_effect=lambda **kw: original_temp(dir=tmp, **kw)):
                result = sandbox.run_sandbox(root, str(worker))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {'bounded': True})

    def test_real_timeout_removes_container(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); worker = root / 'worker.py'
            worker.write_text('import time\ntime.sleep(30)\n')
            real_run = subprocess.run
            names = []
            def observe(cmd, **kwargs):
                if 'create' in cmd:
                    names.append(cmd[cmd.index('--name') + 1])
                return real_run(cmd, **kwargs)
            with patch.object(sandbox.subprocess, 'run', side_effect=observe):
                with self.assertRaises(subprocess.TimeoutExpired):
                    sandbox.run_sandbox(root, str(worker), timeout=1)
            self.assertEqual(len(names), 1)
            result = real_run(sandbox.docker_command() + ['container', 'ls', '-aq', '--filter', 'name=^/' + names[0] + '$'],
                              capture_output=True, check=True)
            self.assertEqual(result.stdout.strip(), b'')
