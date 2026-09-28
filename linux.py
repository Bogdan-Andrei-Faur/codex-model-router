"""Ubuntu setup/launcher. Shared router and macOS web UI; no system app patches."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from desktop_runtime import discover_linux, DiscoveryError
from linux_desktop import atomic_text, applications, entry_quote, app_running, desktop_source, registration
from state_store import atomic_json

ROOT = Path(__file__).resolve().parent


def dependencies():
    found = {}
    try:
        import gi
        try:
            gi.require_foreign('cairo')
            found['Cairo'] = True
        except ImportError:
            found['Cairo'] = False
        for name, version in [('Gtk', '3.0'), ('WebKit2', '4.1'), ('Secret', '1'), ('AyatanaAppIndicator3', '0.1')]:
            try:
                gi.require_version(name, version)
                found[name] = True
            except ValueError:
                found[name] = False
    except ImportError:
        found = dict.fromkeys(('Gtk', 'WebKit2', 'Secret', 'Cairo', 'AyatanaAppIndicator3'), False)
    return found


def setup(app=None, entry=None):
    found = discover_linux(app)
    required = dependencies()
    if not all(required[name] for name in ('Gtk', 'WebKit2', 'Secret', 'Cairo')):
        raise DiscoveryError('Faltan dependencias. Instala python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 gir1.2-secret-1.')
    path = ROOT / 'config.local.json'
    if path.exists():
        config = json.loads(path.read_text(encoding='utf-8'))
        if config.get('platform') != 'linux':
            raise DiscoveryError('Hay una configuración de otro sistema; consérvala con otro nombre antes de preparar Ubuntu.')
    else:
        config = json.loads((ROOT / 'config.example.json').read_text())
        config['comparison_engines'] = []
        config['platform'] = 'linux'
    for key, default in [('phase_routing', True), ('inference_telemetry', True), ('prompt_logging', True), ('history_days', 0)]:
        config.setdefault(key, default)
    config.update(installation_mode='auto', python=sys.executable, codex=str(found.backend), desktop=str(found.desktop))
    if entry:
        config['desktop_entry'] = entry
    config.setdefault('desktop_entry', 'chatgpt.desktop')
    if app:
        config['desktop_app'] = str(Path(app).expanduser().resolve())
    (ROOT / 'state').mkdir(mode=0o700, exist_ok=True)
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    # Every launch reads the same UI sources as macOS; no Linux fork of the UI.
    ui = dist / 'linux-ui'
    shutil.copytree(ROOT / 'monitor-ui', ui, dirs_exist_ok=True)
    shutil.copyfile(ROOT / 'assets/codex-ui-1024.png', ui / 'codex.png')
    commands = {'codex-router': [sys.executable, ROOT / 'router.py'],
                'codex-monitor-linux': [sys.executable, ROOT / 'monitor_linux.py'],
                'codex-desktop': [sys.executable, ROOT / 'linux.py', 'launch-native', '--']}
    for name, command in commands.items():
        env = 'export PERSONAL_CODEX_ROUTER_CONFIG=' + shlex.quote(str(path)) + '\nexport PYTHONUTF8=1\n' if name == 'codex-router' else ''
        atomic_text(dist / name, '#!/bin/sh\n' + env + 'exec ' + ' '.join(shlex.quote(str(x)) for x in command) + ' "$@"\n', 0o755)
    atomic_json(path, config)
    for identifier, name, command in [('codex-router-monitor.desktop', 'Monitor de Codex', [dist / 'codex-monitor-linux']),
                                      ('codex-router.desktop', 'Codex automático', [sys.executable, ROOT / 'linux.py', 'open'])]:
        target = applications() / identifier
        content = '[Desktop Entry]\nType=Application\nName=' + name + '\nExec=' + ' '.join(entry_quote(x) for x in command) + '\nIcon=' + str(ROOT / 'assets/codex-official.png') + '\nTerminal=false\nCategories=Utility;Development;\nX-Codex-Router-Root=' + str(ROOT) + '\n'
        if target.exists() and ('X-Codex-Router-Root=' + str(ROOT) + '\n') not in target.read_text():
            raise DiscoveryError('Existe un acceso del monitor de otra instalación; no se ha sustituido.')
        atomic_text(target, content, 0o644)
    return {'prepared': True, 'backend': str(found.backend), 'dependencies': required}


def open_monitor():
    subprocess.Popen([sys.executable, str(ROOT / 'monitor_linux.py')], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def launch_native(command):
    if not command:
        raise DiscoveryError('Falta el comando del acceso original.')
    config = ROOT / 'config.local.json'
    env = dict(os.environ)
    wrapper = ROOT / 'dist/codex-router'
    if wrapper.is_file() and config.is_file():
        env.update(CODEX_CLI_PATH=str(wrapper), PERSONAL_CODEX_ROUTER_CONFIG=str(config))
        open_monitor()
    # Preserve the user's launcher and every desktop field-code argument.
    os.execvpe(command[0], command, env)


def open_app():
    config = json.loads((ROOT / 'config.local.json').read_text())
    found = discover_linux(config.get('desktop_app'))
    if app_running(found):
        raise DiscoveryError('Desktop sigue abierto. Termina tus tareas y ciérralo antes de activar la conexión.')
    record = registration(ROOT)
    if record and record.get('previous'):
        import base64
        source = base64.b64decode(record['previous']).decode('utf-8')
    else:
        source_path, _ = desktop_source(config)
        source = source_path.read_text()
    section = None
    command = None
    for line in source.splitlines():
        if line.startswith('['):
            section = line
        if section == '[Desktop Entry]' and line.startswith('Exec='):
            command = [arg for arg in shlex.split(line[5:]) if arg not in ('%U', '%u', '%F', '%f', '%i', '%c', '%k')]
            break
    if not command:
        command = [str(found.desktop)]
    # If original was a system entry, avoid feeding our wrapper back into itself.
    if command[0] == str(ROOT / 'dist/codex-desktop'):
        command = command[1:]
    launch_native(command)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'doctor', 'install', 'uninstall', 'open', 'monitor', 'pause', 'resume', 'launch-native'))
    parser.add_argument('--app')
    parser.add_argument('--desktop-entry')
    parser.add_argument('command', nargs='*')
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise DiscoveryError('Este lanzador requiere Linux.')
    if args.action == 'setup':
        result = setup(args.app, args.desktop_entry)
    elif args.action in ('doctor', 'install', 'uninstall'):
        import desktop
        result = getattr(desktop, args.action)()
        if args.action == 'doctor':
            result.update(dependencies=dependencies(), session=os.environ.get('XDG_SESSION_TYPE', 'unknown'))
    elif args.action == 'open':
        result = open_app()
    elif args.action == 'launch-native':
        result = launch_native(args.command)
    elif args.action == 'monitor':
        open_monitor()
        result = {'opened': True}
    else:
        from monitor_state import MonitorState
        MonitorState(ROOT).configure('enabled', args.action == 'resume')
        result = {'enabled': args.action == 'resume'}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({'error': str(error) if isinstance(error, DiscoveryError) else 'No se pudo completar la operación. Ejecuta linux.py doctor.'}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
