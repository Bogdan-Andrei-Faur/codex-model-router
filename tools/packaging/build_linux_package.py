"""Build a repository-independent .deb with Ubuntu-managed runtime dependencies.

No maintainer scripts, home-directory writes, runtime downloads or Codex binaries.
Build with python3 build_linux_package.py; install with apt install ./file.deb.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from tools.packaging.legal import copy_legal_notices

ROOT = Path(__file__).resolve().parents[2]
DEPENDENCIES = ('python3 (>= 3.9), python3-gi, python3-gi-cairo, '
                'gir1.2-gtk-3.0, gir1.2-webkit2-4.1, gir1.2-secret-1, '
                'gir1.2-ayatanaappindicator3-0.1')


def write(path, text, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    path.chmod(0o755 if executable else 0o644)


def build(output, revision='1'):
    version = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version) or not re.fullmatch(r'[0-9][a-zA-Z0-9.+~]*', revision):
        raise ValueError('Invalid Debian version or revision')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / ('codex-model-router_' + version + '-' + revision + '_all.deb')
    if artifact.exists():
        raise ValueError('Output already exists; choose a new output directory or revision')
    with tempfile.TemporaryDirectory(prefix='router-deb-') as directory:
        stage = Path(directory)
        application = stage / 'usr/lib/codex-model-router'
        resources = application / 'Resources'
        resources.mkdir(parents=True)
        copy_legal_notices(ROOT, resources)
        # Explicit source patterns: never include local config, state or Git data.
        shutil.copytree(ROOT / "src", resources / "src",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ('VERSION', 'config.example.json'):
            shutil.copyfile(ROOT / name, resources / name)
        shutil.copytree(ROOT / 'monitor-ui', resources / 'ui')
        shutil.copytree(ROOT / 'assets', resources / 'assets')
        shutil.copyfile(ROOT / 'assets/brand/router-1024.png', resources / 'ui/codex.png')
        write(resources / 'application.json', json.dumps({'schema': 1, 'layout': 'linux-deb-v1',
            'runtime': 'bin/router-runtime', 'bridge': 'bin/codex-router', 'launcher': 'bin/codex-desktop',
            'monitor': 'bin/codex-monitor-linux'}) + '\n')
        write(application / 'bin/router-runtime', '#!/bin/sh\nset -eu\n'
            'base=$(dirname "$(dirname "$(readlink -f "$0")")")\n'
            'exec /usr/bin/python3 -I -B -c \'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); '
            'runpy.run_module("codex_model_router.packaged_main",run_name="__main__")\' "$base/Resources/src" "$@"\n', True)
        for name, service in [('codex-router', 'bridge'), ('codex-desktop', 'launch-native'), ('codex-monitor-linux', 'monitor')]:
            write(application / 'bin' / name, '#!/bin/sh\nset -eu\n'
                'base=$(dirname "$(readlink -f "$0")")\n'
                'exec "$base/router-runtime" ' + service + ' "$@"\n', True)
        binary = stage / 'usr/bin/codex-model-router'
        binary.parent.mkdir(parents=True)
        binary.symlink_to('../lib/codex-model-router/bin/codex-monitor-linux')
        write(stage / 'usr/share/applications/codex-model-router.desktop',
            '[Desktop Entry]\nType=Application\nName=Codex Model Router\n'
            'Comment=Monitor and model routing for Codex\nExec=codex-model-router\n'
            'Icon=codex-model-router\nTerminal=false\nCategories=Development;\n')
        icon = stage / 'usr/share/icons/hicolor/1024x1024/apps/codex-model-router.png'
        icon.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / 'assets/brand/router-1024.png', icon)
        copy_legal_notices(ROOT, stage / 'usr/share/doc/codex-model-router')
        write(stage / 'DEBIAN/control',
            'Package: codex-model-router\nVersion: ' + version + '-' + revision + '\n'
            'Section: utils\nPriority: optional\nArchitecture: all\n'
            'Maintainer: Bogdan Andrei Faur <Bogdan-Andrei-Faur@users.noreply.github.com>\n'
            'Depends: ' + DEPENDENCIES + '\n'
            'Homepage: https://github.com/Bogdan-Andrei-Faur/codex-model-router\n'
            'Description: Codex routing and desktop monitor\n'
            ' Shared routing engine and GTK/WebKit monitor with private per-user data.\n')
        # Source permissions/umask must not make a root-owned package unreadable.
        for path in stage.rglob('*'):
            if path.is_symlink():
                continue
            path.chmod(0o755 if path.is_dir() or path.parent == application / 'bin' else 0o644)
        subprocess.run(['desktop-file-validate', str(stage / 'usr/share/applications/codex-model-router.desktop')], check=True)
        subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(stage), str(artifact)], check=True)
    receipt = {'artifact': artifact.name, 'version': version + '-' + revision, 'architecture': 'all',
               'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(), 'runtime': 'Ubuntu system Python and GTK/WebKit',
               'dependencies': DEPENDENCIES}
    write(artifact.with_suffix('.json'), json.dumps(receipt, indent=2) + '\n')
    return artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'release/linux')
    parser.add_argument('--revision', default='1')
    args = parser.parse_args()
    print(build(args.output, args.revision))


if __name__ == '__main__':
    main()
