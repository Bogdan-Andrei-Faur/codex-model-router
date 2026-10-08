"""Source-checkout entrypoint; installed applications use their bundled runtime."""
from pathlib import Path
import runpy
import sys

SERVICES = {
    'bridge': 'codex_model_router.bridge.router',
    'desktop': 'codex_model_router.platforms.desktop',
    'macos': 'codex_model_router.platforms.macos',
    'linux': 'codex_model_router.platforms.linux',
    'monitor-service': 'codex_model_router.monitor.monitor_service',
    'monitor-linux': 'codex_model_router.monitor.monitor_linux',
    'runtime': 'codex_model_router.packaged_main',
    'build-identity': 'codex_model_router.build_identity',
    'evidence': 'codex_model_router.telemetry.evidence',
    'policy': 'codex_model_router.evaluation.policy_control',
    'recover-history': 'codex_model_router.storage.recover_history',
}


def run(service):
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
    runpy.run_module(SERVICES[service], run_name='__main__')


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in SERVICES:
        print('Usage: python run.py {' + ','.join(SERVICES) + '} [arguments]', file=sys.stderr)
        raise SystemExit(2)
    run(sys.argv.pop(1))
