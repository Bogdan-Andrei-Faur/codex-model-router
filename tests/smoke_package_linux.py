"""Extract a real .deb and exercise GTK onboarding + shared WebKit in isolation.

Run under xvfb-run -a dbus-run-session -- python3 this.py package.deb.
No host Desktop activation, credential reads, user configuration or inference.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import selectors
import shlex
import signal


def adopt_worker_descendants():
    # WebKit helpers can start their own sessions. Become their nearest
    # subreaper so killing the worker group cannot orphan a cache writer.
    import ctypes
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'Unable to own smoke-test descendants')


def stop_worker_tree(child):
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait()
    children = Path('/proc/self/task') / str(os.getpid()) / 'children'
    deadline = time.monotonic() + 5
    while True:
        owned = [int(pid) for pid in children.read_text().split()]
        if not owned:
            return
        for pid in owned:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass
        if time.monotonic() >= deadline:
            raise RuntimeError('Smoke-test descendants did not exit before cache cleanup')
        time.sleep(0.01)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--worker-root', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_root is not None:
        exercise(args.package, args.worker_root)
        return
    # GTK/WebKit and Mesa retain background processes after Gtk.Application.quit.
    # Let the UI process exit, then reap its private process tree before removing
    # its cache. Never suppress cleanup errors or touch the user's monitor group.
    adopt_worker_descendants()
    with tempfile.TemporaryDirectory(prefix='router-native-package-') as folder:
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                                  str(args.package.resolve()), '--worker-root', folder],
                                 start_new_session=True)
        try:
            code = child.wait(timeout=120)
        finally:
            stop_worker_tree(child)
        if code:
            raise SystemExit(code)


def exercise(package, base):
    application = base / 'extracted/usr/lib/codex-model-router'
    subprocess.run(['dpkg-deb', '-x', str(package.resolve()), str(base / 'extracted')], check=True)
    resources = application / 'Resources'
    for key in tuple(os.environ):
        if key.startswith('PERSONAL_CODEX_') or key in ('CODEX_CLI_PATH', 'PYTHONPATH', 'PYTHONHOME'):
            os.environ.pop(key, None)
    os.environ.update(PERSONAL_CODEX_ROUTER_CODE_ROOT=str(resources),
        PERSONAL_CODEX_ROUTER_ROOT=str(base / 'data'), HOME=str(base / 'home'),
        XDG_DATA_HOME=str(base / 'xdg'), XDG_CONFIG_HOME=str(base / 'config'),
        XDG_CACHE_HOME=str(base / 'cache'), GDK_BACKEND='x11')
    sys.path.insert(0, str(resources))
    from monitor_linux import Gtk, GLib, Monitor
    from linux_onboarding import prepare
    from state_store import atomic_json
    source = base / 'old checkout'
    atomic_json(source / 'config.local.json', {'platform': 'linux', 'enabled': False, 'owner_preference': 'synthetic'})
    (source / 'state').mkdir()
    (source / 'state/history.jsonl').write_text('{"synthetic":true}\n')
    atomic_json(source / 'state/status-old.json', {'pid': os.getpid(),
                'events': [{'event': 'bridge_stopped'}]})

    def onboarding(choice, destination):
        deadline = time.monotonic() + 12
        failure = []
        def respond():
            windows = [window for window in Gtk.Window.list_toplevels() if window.get_visible()]
            if time.monotonic() > deadline or any(isinstance(w, Gtk.MessageDialog) for w in windows):
                failure.append('Onboarding failed or timed out')
                for window in windows:
                    if isinstance(window, Gtk.Dialog): window.response(Gtk.ResponseType.CANCEL)
                return False
            chooser = next((w for w in windows if isinstance(w, Gtk.FileChooserDialog)), None)
            if chooser:
                if chooser.get_filename() == str(source):
                    chooser.response(Gtk.ResponseType.OK)
                else:
                    chooser.set_filename(str(source))
            elif windows:
                windows[0].response(choice)
            return True
        timer = GLib.timeout_add(100, respond)
        try:
            result = prepare(resources, destination)
        finally:
            if not failure: GLib.source_remove(timer)
        assert not failure, failure
        return result

    cancelled = base / 'cancelled'
    assert onboarding(Gtk.ResponseType.CANCEL, cancelled) is False and not cancelled.exists()
    fresh = base / 'fresh'
    assert onboarding(1, fresh) and (fresh / 'config.local.json').exists()
    migrated = base / 'migrated'
    assert onboarding(2, migrated)
    assert (migrated / 'config.local.json').read_bytes() == (source / 'config.local.json').read_bytes()
    assert (migrated / 'state/history.jsonl').read_bytes() == (source / 'state/history.jsonl').read_bytes()
    assert not (migrated / 'state/desktop-integration.json').exists()
    # A genuine active bridge must still refuse import, with a specific GTK
    # message rather than suggesting that a valid configuration is missing.
    atomic_json(source / 'state/status-active.json', {'pid': os.getpid()})
    blocked = base / 'blocked'
    message_seen = []
    deadline = time.monotonic() + 12
    failure = []
    def blocked_import():
        windows = [w for w in Gtk.Window.list_toplevels() if w.get_visible()]
        message = next((w for w in windows if isinstance(w, Gtk.MessageDialog)), None)
        if time.monotonic() > deadline:
            failure.append('Blocked import did not show a specific error')
            for window in windows:
                if isinstance(window, Gtk.Dialog): window.response(Gtk.ResponseType.CANCEL)
            return False
        if message:
            message_seen.append(message.get_property('secondary-text'))
            message.response(Gtk.ResponseType.OK)
        else:
            chooser = next((w for w in windows if isinstance(w, Gtk.FileChooserDialog)), None)
            if chooser:
                if chooser.get_filename() == str(source): chooser.response(Gtk.ResponseType.OK)
                else: chooser.set_filename(str(source))
            elif windows:
                windows[0].response(Gtk.ResponseType.CANCEL if message_seen else 2)
        return True
    timer = GLib.timeout_add(100, blocked_import)
    try:
        assert prepare(resources, blocked) is False
    finally:
        if not failure: GLib.source_remove(timer)
    assert not failure and message_seen and 'Codex' in message_seen[0] and 'config.local.json' not in message_seen[0]
    assert not blocked.exists()
    app = Monitor(migrated, preview=True)
    received = []
    original = app.emit
    def capture(function, payload):
        if function == 'receive': received.append(payload)
        original(function, payload)
    app.emit = capture
    deadline = time.monotonic() + 25
    error = []
    def check():
        if app.ready and received:
            app.quit(); return False
        if time.monotonic() > deadline:
            error.append('Packaged WebKit never became ready'); app.quit(); return False
        return True
    GLib.timeout_add(100, check)
    app.run(['router-package-smoke'])
    assert not error and received and app.ready, error
    assert (migrated / 'config.local.json').read_bytes() == (source / 'config.local.json').read_bytes()
    # Exercise the actual executable/dispatcher as well as the GTK object.
    child_env = dict(os.environ, PERSONAL_CODEX_ROUTER_ROOT=str(base / 'launcher-preview'))
    child = subprocess.Popen([str(application / 'bin/codex-monitor-linux'), '--preview'],
                             env=child_env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            assert selector.select(25), 'Packaged launcher did not report WebKit readiness'
            assert child.stdout.readline().strip() == b'Monitor: interfaz compartida conectada.'
        assert child.poll() is None
        assert not (base / 'launcher-preview/config.local.json').exists()
        # Reproduce Desktop starting a cached legacy monitor command while
        # the installed monitor is already open. It must activate that same
        # GTK application and exit rather than displaying another capsule.
        from linux_legacy_handoff import redirect_launchers
        (source / 'dist').mkdir()
        old_router = '#!/bin/sh\nexport PERSONAL_CODEX_ROUTER_CONFIG=' + shlex.quote(str(source / 'config.local.json')) + '\nexport PYTHONUTF8=1\nexec /usr/bin/python3 ' + shlex.quote(str(source / 'router.py')) + ' "$@"\n'
        old_monitor = '#!/bin/sh\nexec /usr/bin/python3 ' + shlex.quote(str(source / 'monitor_linux.py')) + ' "$@"\n'
        old_desktop = '#!/bin/sh\nexec /usr/bin/python3 ' + shlex.quote(str(source / 'linux.py')) + ' launch-native -- "$@"\n'
        for name, text in [('codex-router', old_router), ('codex-monitor-linux', old_monitor), ('codex-desktop', old_desktop)]:
            path = source / 'dist' / name; path.write_text(text); path.chmod(0o755)
        redirect_launchers(base / 'launcher-preview', source, application / 'bin/codex-router',
                          application / 'bin/codex-monitor-linux', Path('/bin/true'))
        repeated = subprocess.run([str(source / 'dist/codex-monitor-linux'), '--preview'],
                                  env=child_env, capture_output=True, timeout=15)
        assert repeated.returncode == 0 and not repeated.stdout, 'Cached command opened a second monitor'
        assert child.poll() is None
        # The cached Desktop launcher itself used to spawn the old monitor
        # before exec. Use a synthetic original Desktop, keeping argv intact.
        argv=['original desktop','$(exit 99)']
        desktop_env=dict(child_env, PERSONAL_CODEX_ROUTER_ROOT='/old/data')
        repeated_desktop=subprocess.run([str(source / 'dist/codex-desktop'),'/bin/echo',*argv],
                                        env=desktop_env,capture_output=True,timeout=15)
        assert repeated_desktop.returncode == 0 and repeated_desktop.stdout.strip()==b'original desktop $(exit 99)'
        assert child.poll() is None
    finally:
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired: child.kill(); child.wait()
        child.stdout.close()
    print(json.dumps({'pass': True, 'extracted_package': True, 'gtk_onboarding_cancel_new_import': True,
                      'webkit_ready': True, 'shared_ui_payload': True, 'preview_only': True,
                      'exact_packaged_launcher_ready': True,
                      'stopped_pid_reuse_import': True, 'active_bridge_specific_error': True,
                      'cached_monitor_single_instance': True}))

if __name__ == '__main__':
    main()
