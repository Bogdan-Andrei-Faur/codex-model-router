"""Bundled runtime dispatch. No source checkout or development interpreter needed."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path)
    parser.add_argument('--resources', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('service', choices=('bootstrap', 'monitor-service', 'monitor', 'launch-native', 'desktop', 'bridge', 'identity'))
    args, remaining = parser.parse_known_args()
    if args.resources is not None and not getattr(sys, 'frozen', False):
        resources = args.resources.resolve()
    elif getattr(sys, 'frozen', False):
        resources = next((parent/'Resources' for parent in Path(sys.executable).resolve().parents
                          if parent.name=='Contents' and (parent/'Resources/application.json').is_file()),None)
        if resources is None:raise ValueError('No se encontraron los recursos de la aplicación.')
    else:
        resources = Path(__file__).resolve().parent
    os.environ['PERSONAL_CODEX_ROUTER_CODE_ROOT'] = str(resources)
    from application_layout import data_root, bootstrap, manifest
    root = args.data_root.resolve() if args.data_root else data_root(resources)
    os.environ['PERSONAL_CODEX_ROUTER_ROOT'] = str(root)
    os.environ['PERSONAL_CODEX_ROUTER_CONFIG'] = str(root / 'config.local.json')
    os.environ['PERSONAL_CODEX_ROUTER_STATE'] = str(root / 'state')
    if args.service == 'identity':
        from build_identity import identity, router_identity
        version, build = identity(resources)
        print(json.dumps({'version': version, 'build': build, 'routerBuild': router_identity(resources), 'packaged': bool(getattr(sys, 'frozen', False) or manifest(resources))}))
        return 0
    if args.service == 'monitor' and '--preview' not in remaining and not (root / 'config.local.json').exists():
        from linux_onboarding import prepare
        if not prepare(resources, root):
            return 0
    created = False if args.service in ('monitor', 'monitor-service') and '--preview' in remaining else bootstrap(resources, root)
    if args.service == 'bootstrap':
        print(json.dumps({'ready': True, 'createdConfig': created}))
        return 0
    sys.argv = [sys.argv[0], *remaining]
    if args.service == 'monitor':
        import monitor_linux
        sys.argv += [str(root)]
        return monitor_linux.main()
    if args.service == 'launch-native':
        from linux import launch_native
        return launch_native(remaining[1:] if remaining[:1] == ['--'] else remaining)
    if args.service == 'monitor-service':
        import monitor_service
        sys.argv += ['--root', str(root), '--code-root', str(resources), '--platform', {'darwin': 'macos', 'win32': 'windows', 'linux': 'linux'}[sys.platform]]
        monitor_service.main()
        return 0
    if args.service == 'desktop':
        import desktop
        return desktop.main()
    import router
    return router.main()


if __name__ == '__main__':
    try:
        sys.exit(main() or 0)
    except (OSError, ValueError, KeyError):
        print('La instalación no pudo iniciarse. Se han conservado tus datos.', file=sys.stderr)
        sys.exit(1)
