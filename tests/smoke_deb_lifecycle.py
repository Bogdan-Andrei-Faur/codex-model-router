"""Destructive ONLY inside a disposable Docker container: install/upgrade/purge.

Usage: python3 smoke_deb_lifecycle.py old.deb newer.deb
Mount only the two packages. Never execute this on a workstation.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    if not Path('/.dockerenv').is_file() or os.getuid() != 0:
        raise SystemExit('This lifecycle test requires a disposable root Docker container.')
    old, new = map(lambda value: Path(value).resolve(strict=True), sys.argv[1:])
    home = Path(tempfile.mkdtemp(prefix='router-test-home-'))
    os.chown(home, 65534, 65534)
    data = home / '.local/share/codex-model-router'
    runtime = '/usr/lib/codex-model-router/bin/router-runtime'
    resources = Path('/usr/lib/codex-model-router/Resources')
    env = {'HOME': str(home), 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
           'PYTHONPATH': '/nonexistent/developer/environment', 'PYTHONHOME': '/nonexistent',
           'PERSONAL_CODEX_ROUTER_ROOT': str(data)}

    def unprivileged():
        os.setgroups([]); os.setgid(65534); os.setuid(65534)

    def run(command, **kwargs):
        return subprocess.run(command, check=True, capture_output=True, text=True,
            timeout=40, env=env, cwd=home, preexec_fn=unprivileged, **kwargs).stdout

    def apt(*arguments):
        subprocess.run(['apt-get', '-y', '--no-install-recommends', *arguments],
                       check=True, env=dict(os.environ, DEBIAN_FRONTEND='noninteractive'), timeout=600)

    def inline(code):
        return run(['/usr/bin/python3', '-I', '-c', 'import sys; sys.path.insert(0,' + repr(str(resources / "src")) + '); ' + code])

    apt('install', str(old))
    installed = subprocess.check_output(['dpkg-query', '-W', '-f=${Version}', 'codex-model-router'], text=True)
    identity = json.loads(run([runtime, 'identity']))
    assert identity['packaged'] and not data.exists()
    forbidden = {'config.local.json', 'history.jsonl', 'prompts.jsonl', '.git', 'desktop-integration.json'}
    assert not any(path.name in forbidden or path.suffix == '.secret' for path in resources.rglob('*'))
    inline('import gi; gi.require_version("Gtk","3.0"); gi.require_version("WebKit2","4.1"); '
           'gi.require_version("Secret","1"); gi.require_foreign("cairo"); from gi.repository import Gtk,WebKit2,Secret')
    # Migrate synthetic offline data using the exact installed code, never keys.
    inline('from pathlib import Path; import json; from codex_model_router.storage.state_store import atomic_json; '
           'from codex_model_router.platforms.linux_onboarding import import_installation; '
           'source=Path.home()/"old checkout"; '
           'atomic_json(source/"config.local.json", {"platform":"linux","enabled":False,"installation_mode":"auto","updates_auto_check":False,"owner_preference":"keep"}); '
           '(source/"state").mkdir(); (source/"state/history.jsonl").write_text("{\\"fixture\\":true}\\n"); '
           'import_installation(source,Path(' + repr(str(data)) + '))')
    assert not json.loads(run([runtime, 'bootstrap']))['createdConfig']
    config = data / 'config.local.json'; history = data / 'state/history.jsonl'
    before = (config.read_bytes(), history.read_bytes())
    reply = json.loads(run([runtime, 'monitor-service'], input='{"requestId":1,"action":"snapshot","history":false,"revision":-1}\n'))
    assert reply['ok'] and reply['payload']['connections'] == 0
    assert reply['payload']['productVersion'] == identity['version']
    # Synthetic original executable: verifies argv forwarding without inference.
    fixture_app = Path('/opt/ChatGPT'); (fixture_app / 'resources').mkdir(parents=True, exist_ok=True)
    for name, content in [('ChatGPT', '#!/bin/sh\nexit 0\n'),
                          ('resources/codex', '#!/bin/sh\nprintf "codex-cli fixture\\n"\n')]:
        path = fixture_app / name; path.write_text(content); path.chmod(0o755)
    assert run(['/usr/lib/codex-model-router/bin/codex-router', '--version']).startswith('codex-cli fixture')
    inline('from codex_model_router.platforms.linux_desktop import fallback_launcher; from pathlib import Path; '
           'fallback_launcher(Path(' + repr(str(data)) + '),Path("/usr/lib/codex-model-router/bin/codex-desktop"))')
    apt('install', str(new))
    upgraded = subprocess.check_output(['dpkg-query', '-W', '-f=${Version}', 'codex-model-router'], text=True)
    subprocess.run(['dpkg', '--compare-versions', upgraded, 'gt', installed], check=True)
    assert not json.loads(run([runtime, 'bootstrap']))['createdConfig']
    assert (config.read_bytes(), history.read_bytes()) == before
    apt('remove', 'codex-model-router')
    assert not Path(runtime).exists()
    assert (config.read_bytes(), history.read_bytes()) == before
    shim = str(data / 'state/launchers/codex-desktop')
    assert run([shim, '/bin/echo', 'original desktop works']).strip() == 'original desktop works'
    # With no system conffiles, remove fully forgets this local-only package.
    # Reinstall before independently exercising purge of an installed package.
    apt('install', str(new))
    assert not json.loads(run([runtime, 'bootstrap']))['createdConfig']
    apt('purge', 'codex-model-router')
    assert (config.read_bytes(), history.read_bytes()) == before
    apt('install', str(new))
    assert not json.loads(run([runtime, 'bootstrap']))['createdConfig']
    assert (config.read_bytes(), history.read_bytes()) == before
    assert not (data / 'state/desktop-integration.json').exists()
    print(json.dumps({'pass': True, 'installed': installed, 'upgraded': upgraded,
        'unprivileged_runtime': True, 'migration': True, 'ipc': True, 'system_dependencies': True,
        'synthetic_backend_forwarding': True, 'remove_purge_reinstall_preserve_data': True,
        'removed_package_launcher_fallback': True, 'official_engine_modified': False,
        'sha256': hashlib.sha256(new.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
