"""Exercise the extracted Windows artifact without registering or opening Desktop."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from smoke_native import Client
from platform_support import creation_flags


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    if sys.platform != 'win32':
        raise SystemExit('Windows artifact smoke requires Windows')
    output = Path(tempfile.mkdtemp(prefix='router-package-smoke-')).resolve()
    with zipfile.ZipFile(args.archive) as archive:
        names = archive.namelist()
        assert not any(name.endswith(('config.local.json', '.secret', 'history.jsonl')) or '/state/' in name for name in names)
        for name in names:
            (output / name).resolve().relative_to(output)
        archive.extractall(output)
    root = output / 'Codex-automatico'
    for name in ('assets/codex.ico', 'assets/codex-official.png', 'assets/codex-ui-1024.png', 'BUILD.json', 'VERSION', 'docs/AUDIT-REMEDIATION.md'):
        assert (root / name).is_file(), name
    env = dict(os.environ)
    for name in ('PERSONAL_CODEX_ROUTER_ROOT', 'PERSONAL_CODEX_ROUTER_CONFIG', 'PERSONAL_CODEX_ROUTER_STATE'):
        env.pop(name, None)
    result = subprocess.run([str(root / 'dist/codex-router.exe'), '--doctor-json'], env=env,
                            capture_output=True, timeout=40, creationflags=creation_flags())
    assert result.returncode == 0, 'Packaged doctor failed'
    doctor = json.loads(result.stdout)
    assert (root / 'config.local.json').exists(), 'First-run bootstrap failed'
    # Simulate an in-place update: mutable preferences and the journal survive.
    config_path = root / 'config.local.json'
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    assert all(config.get(key) is True for key in ('inference_telemetry', 'prompt_logging', 'phase_routing'))
    assert config.get('history_days') == 0
    legacy = {key: value for key, value in config.items()
              if key not in ('inference_telemetry', 'prompt_logging', 'phase_routing', 'history_days')}
    config_path.write_text(json.dumps(legacy), encoding='utf-8')
    migrated = subprocess.run([str(root / 'dist/codex-router.exe'), '--doctor-json'], env=env,
                              capture_output=True, timeout=40, creationflags=creation_flags())
    assert migrated.returncode == 0, 'Existing-config default migration failed'
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    assert all(config.get(key) is True for key in ('inference_telemetry', 'prompt_logging', 'phase_routing'))
    assert config.get('history_days') == 0
    config['enabled'] = False
    config_path.write_text(json.dumps(config), encoding='utf-8')
    (root / 'state').mkdir(exist_ok=True)
    sentinel = root / 'state/upgrade-sentinel.txt'; sentinel.write_text('keep')
    with zipfile.ZipFile(args.archive) as archive:
        archive.extractall(output)
    assert json.loads(config_path.read_text())['enabled'] is False
    assert sentinel.read_text() == 'keep'
    loaded = json.loads((root / 'BUILD.json').read_text())
    with patch.dict(os.environ, dict(env, PERSONAL_CODEX_ROUTER_ROOT=str(root), PERSONAL_CODEX_ROUTER_CONFIG=str(config_path)), clear=True):
        client = Client([str(root / 'bin/codex-router-core.exe'), 'app-server'])
        try:
            client.call('initialize', {'clientInfo': {'name': 'artifact_probe', 'version': loaded['product_version']}})
            client.send({'method': 'initialized', 'params': {}})
            models = client.call('model/list', {})
            assert models['data'], 'Frozen bridge did not forward native catalog'
            snapshots = list(client.state.glob('status-*.json'))
            assert len(snapshots) == 1, 'Expected one isolated frozen bridge snapshot'
            snapshot = json.loads(snapshots[0].read_text(encoding='utf-8'))
            assert snapshot['build_id'] == loaded['build_id']
            assert snapshot['product_version'] == loaded['product_version']
        finally:
            client.close(); client.temp.cleanup()
    monitor = subprocess.run([str(root / 'dist/codex-monitor-v24.exe'), '--self-test'], env=env, timeout=40,
                             capture_output=True, creationflags=creation_flags())
    assert monitor.returncode == 0, 'Packaged monitor self-test failed'
    report = {'artifact': args.archive.name, 'version': loaded['product_version'], 'build_id': loaded['build_id'],
              'doctor': True, 'frozen_bridge': True, 'assets': True, 'preserved_upgrade': True, 'monitor': True,
              'registered_desktop': False, 'live_inference': False, 'output': str(output)}
    (output / 'artifact-checks.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__': main()
