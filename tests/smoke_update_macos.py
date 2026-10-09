"""Exercise an authenticated update using disposable packaged Mac applications.

The old native host and the installation-owned frozen helper are real processes.
The fixture explicitly releases the old host after handoff: it does not claim a
native Settings-button click or login-agent recovery. No owner data, installation,
Desktop registration, credentials or real LaunchAgent is modified. Supply an
already signed manifest; this test never retrieves a signing key.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codex_model_router.update_install import (MacApplier, APP_NAME, app_info,
    extract_app, clean_environment)
from codex_model_router.update_trust import strict_json, decode, verify, load_keys
from codex_model_router.updates import architecture
from codex_model_router.storage.state_store import file_lock


def exercise(old_package, new_package, signed_manifest):
    if sys.platform != 'darwin':
        raise ValueError('This fixture requires a macOS GUI login session.')
    envelope = signed_manifest.read_bytes()
    payload = strict_json(decode(strict_json(envelope)['payload']))
    version = payload['version']
    package = dict(version=version, name=new_package.name, size=new_package.stat().st_size,
                   sha256=hashlib.sha256(new_package.read_bytes()).hexdigest())
    with tempfile.TemporaryDirectory(prefix='router-managed-update-') as folder:
        fixture = Path(folder).resolve()
        # Inspect the local old package to recover its version; no scripts run.
        expanded = fixture / 'old-expanded'
        subprocess.run(['/usr/sbin/pkgutil', '--expand-full', str(old_package), str(expanded)],
                       check=True, capture_output=True, timeout=120)
        apps = list(expanded.glob('**/Payload/Applications/' + APP_NAME))
        assert len(apps) == 1, 'Expected one old app'
        old_version = app_info(apps[0])['CFBundleShortVersionString']
        # Use the same tree and signature checks as the updater, then relocate it.
        checked = extract_app(old_package, fixture / 'checked-old', old_version)
        app = fixture / 'Applications' / APP_NAME
        app.parent.mkdir()
        checked.rename(app)
        resources = app / 'Contents/Resources'
        verify(envelope, load_keys(resources), package, 'macos', architecture())
        manifest = json.loads((resources / 'application.json').read_text())
        root = fixture / 'data'
        runtime = app / 'Contents' / manifest['runtime']
        env = clean_environment()
        env['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'
        subprocess.run([str(runtime), '--data-root', str(root), 'bootstrap'],
                       env=env, check=True, capture_output=True, timeout=30)
        config = root / 'config.local.json'
        value = json.loads(config.read_text())
        value.update(enabled=False, updates_auto_check=False, owner_preference='synthetic-update')
        config.write_text(json.dumps(value)); before = config.read_bytes()
        (root / 'state/monitor-ui-mac.json').write_text(json.dumps({'mode': 'Hidden'}))
        (root / 'state/history.jsonl').write_text('')
        (root / 'state/upgrade-sentinel').write_text('preserve')
        monitor = subprocess.Popen([str(app / 'Contents/MacOS/codex-monitor-mac'), str(root)],
                                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        job = None
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                assert monitor.poll() is None, 'Old fixture monitor exited'
                try:
                    with file_lock(root / 'state/monitor-mac.lock', timeout=.1):
                        pass
                except TimeoutError:
                    break
                time.sleep(.1)
            else:
                raise AssertionError('Old monitor did not acquire its lock')
            # Real extraction with cancellation keeps the running app intact.
            stop = threading.Event(); stop.set()
            assert not MacApplier(root, resources).prepare(new_package, package, envelope, stop)
            assert monitor.poll() is None and app_info(app)['CFBundleShortVersionString'] == old_version
            with patch('codex_model_router.update_install.recovery_agent',
                       lambda token: fixture / 'LaunchAgents' / (token + '.plist')):
                assert MacApplier(root, resources).prepare(new_package, package, envelope, threading.Event())
            job = next((root / 'state/updates/jobs').iterdir())
            assert monitor.poll() is None and (job / 'ready-to-close').exists()
            # Only this fixture's old process is signalled, after verified handoff.
            monitor.terminate(); monitor.wait(timeout=10)
            deadline = time.monotonic() + 70; result = {}
            while time.monotonic() < deadline:
                try:
                    result = json.loads((root / 'state/updates/result.json').read_text())
                except (ValueError, OSError):
                    pass
                if result.get('status') in ('completed', 'rolled_back', 'failed'):
                    break
                time.sleep(.2)
            assert result.get('status') == 'completed', result.get('status', 'no receipt')
            assert app_info(app)['CFBundleShortVersionString'] == version
            assert (job / 'ready').is_file(), 'New native monitor did not acknowledge readiness'
            assert config.read_bytes() == before and (root / 'state/upgrade-sentinel').read_text() == 'preserve'
            assert not (root / 'state/desktop-integration.json').exists()
            return dict(passed=True, oldVersion=old_version, newVersion=version,
                        oldBuild=manifest['build'], newBuild=app_info(app)['RouterBuildId'],
                        signedPackageVerified=True, installedFrozenHelper=True,
                        preflightCancellationPreservedOld=True, newNativeMonitorReady=True,
                        previousBundleRetained=len(list(app.parent.glob('.router-previous-*.app'))) == 1,
                        preferencesPreserved=True, ownerInstallationTouched=False,
                        desktopRestarted=False, settingsButtonNativeTested=False,
                        launchAgentLoginTested=False, systemInstallerTested=False)
        finally:
            if monitor.poll() is None:
                monitor.terminate(); monitor.wait(timeout=10)
            if job and (job / 'operation.json').exists():
                pid = json.loads((job / 'operation.json').read_text()).get('monitorPid')
                if pid:
                    try:
                        command = subprocess.check_output(['/bin/ps', '-ww', '-p', str(pid), '-o', 'command='], text=True)
                        if str(root) in command and str(app / 'Contents/MacOS/codex-monitor-mac') in command:
                            os.kill(pid, signal.SIGTERM)
                    except (ProcessLookupError, subprocess.CalledProcessError):
                        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old_package', type=Path)
    parser.add_argument('new_package', type=Path)
    parser.add_argument('signed_manifest', type=Path)
    args = parser.parse_args()
    print(json.dumps(exercise(args.old_package.resolve(strict=True), args.new_package.resolve(strict=True),
                              args.signed_manifest.resolve(strict=True))))
