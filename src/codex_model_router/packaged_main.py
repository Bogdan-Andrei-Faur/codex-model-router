"""Bundled runtime dispatch. No source checkout or development interpreter needed."""
import argparse
import json
import os
from pathlib import Path
from codex_model_router.paths import resource_root
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path)
    parser.add_argument('--resources', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('service', choices=('bootstrap', 'import-legacy', 'monitor-service', 'monitor', 'launch-native', 'desktop', 'bridge', 'identity', 'update-helper'))
    args, remaining = parser.parse_known_args()
    if args.resources is not None and not getattr(sys, 'frozen', False):
        resources = args.resources.resolve()
    elif getattr(sys, 'frozen', False):
        resources = next((parent/'Resources' for parent in Path(sys.executable).resolve().parents
                          if (parent/'Resources/application.json').is_file()),None)
        if resources is None:raise ValueError('No se encontraron los recursos de la aplicación.')
    else:
        resources = resource_root()
    os.environ['PERSONAL_CODEX_ROUTER_CODE_ROOT'] = str(resources)
    from codex_model_router.platforms.application_layout import data_root, bootstrap, manifest
    root = args.data_root.resolve() if args.data_root else data_root(resources)
    os.environ['PERSONAL_CODEX_ROUTER_ROOT'] = str(root)
    os.environ['PERSONAL_CODEX_ROUTER_CONFIG'] = str(root / 'config.local.json')
    os.environ['PERSONAL_CODEX_ROUTER_STATE'] = str(root / 'state')
    if args.service == 'update-helper':
        if len(remaining) != 1:
            raise ValueError('Solicitud de actualización no válida.')
        from codex_model_router.update_install import run_helper
        run_helper(root, resources, remaining[0])
        return 0
    if args.service == 'identity':
        from codex_model_router.build_identity import identity, router_identity
        version, build = identity(resources)
        print(json.dumps({'version': version, 'build': build, 'routerBuild': router_identity(resources), 'packaged': bool(getattr(sys, 'frozen', False) or manifest(resources))}))
        return 0
    if args.service == 'import-legacy':
        if sys.platform not in ('win32', 'darwin') or len(remaining) != 1:
            raise ValueError('Importación no compatible.')
        from codex_model_router.platforms.installation_migration import import_legacy, MigrationError
        try:
            result = import_legacy(remaining[0], root, platform=sys.platform, record_source=True)
        except MigrationError as error:
            print(json.dumps({'error': {'code': error.code}}))
            return 1
        print(json.dumps(result))
        return 0
    if args.service == 'monitor' and '--preview' not in remaining and not (root / 'config.local.json').exists():
        from codex_model_router.platforms.linux_onboarding import prepare
        if not prepare(resources, root):
            return 0
    created = False if args.service in ('monitor', 'monitor-service') and '--preview' in remaining else bootstrap(resources, root)
    if args.service == 'bootstrap':
        print(json.dumps({'ready': True, 'createdConfig': created}))
        return 0
    sys.argv = [sys.argv[0], *remaining]
    if args.service == 'monitor':
        import codex_model_router.monitor.monitor_linux as monitor_linux
        sys.argv += [str(root)]
        return monitor_linux.main()
    if args.service == 'launch-native':
        from codex_model_router.platforms.linux import launch_native
        return launch_native(remaining[1:] if remaining[:1] == ['--'] else remaining)
    if args.service == 'monitor-service':
        import codex_model_router.monitor.monitor_service as monitor_service
        sys.argv += ['--root', str(root), '--code-root', str(resources), '--platform', {'darwin': 'macos', 'win32': 'windows', 'linux': 'linux'}[sys.platform]]
        monitor_service.main()
        return 0
    if args.service == 'desktop':
        import codex_model_router.platforms.desktop as desktop
        return desktop.main()
    import codex_model_router.bridge.router as router
    return router.main()


if __name__ == '__main__':
    try:
        sys.exit(main() or 0)
    except (OSError, ValueError, KeyError):
        print('La instalación no pudo iniciarse. Se han conservado tus datos.', file=sys.stderr)
        sys.exit(1)
