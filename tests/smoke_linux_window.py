"""Check real GTK placement/stacking in a logged-in Linux desktop session.

Run after linux.py setup with the system Python, without inheriting the shell's
backend: env -u GDK_BACKEND /usr/bin/python3 tests/smoke_linux_window.py
Uses an isolated preview and synthetic preferences; never reads user secrets.
Requires an X11/XWayland window manager and xprop (x11-utils).
"""
import argparse
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from monitor_linux import Gdk, GLib, Monitor
import gi
gi.require_version('GdkX11', '3.0')
from gi.repository import GdkX11


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saved-topmost', choices=('on', 'off'), default='on')
    args = parser.parse_args()
    display = Gdk.Display.get_default()
    if display is None or display.__gtype__.name != 'GdkX11Display':
        print('FAIL: this check requires the monitor to use X11/XWayland.')
        return 1

    with tempfile.TemporaryDirectory(prefix='router-window-smoke-') as directory:
        root = Path(directory)
        (root / 'state').mkdir()
        saved = args.saved_topmost == 'on'
        preferences = {'mode': 'Compact', 'topmost': saved, 'height_ratio': .65}
        prefs_path = root / 'state/monitor-ui-linux.json'
        prefs_path.write_text(json.dumps(preferences))
        app = Monitor(root, preview=True)
        payloads = []
        original_emit = app.emit

        def capture(function, payload):
            if function == 'receive':
                payloads.append(payload)
            original_emit(function, payload)

        app.emit = capture
        # These are the same actions used by the web UI, checked against the
        # compositor's acknowledged state, not just the requested preference.
        steps = [
            ('startup', None, saved, 'Compact'),
            ('unpin', {'action': 'topmost', 'value': False}, False, 'Compact'),
            ('pin', {'action': 'topmost', 'value': True}, True, 'Compact'),
            ('hide', {'action': 'mode', 'value': 'Hidden'}, True, 'Hidden'),
            ('show-expanded', {'action': 'mode', 'value': 'Expanded'}, True, 'Expanded'),
            ('compact', {'action': 'mode', 'value': 'Compact'}, True, 'Compact'),
        ]
        results = []
        index = 0
        deadline = time.monotonic() + 20
        failure = None
        observed = {}

        def poll():
            nonlocal index, deadline, failure, observed
            name, _, topmost, mode = steps[index]
            try:
                window = app.window
                matched = False
                if window and app.ready and payloads:
                    if mode == 'Hidden':
                        matched = not window.get_mapped()
                    elif window.get_mapped():
                        native = window.get_window()
                        area = display.get_monitor_at_window(native).get_workarea()
                        width = min(432, max(1, area.width - 20))
                        expected = (area.x + area.width - width - 10, area.y + 10)
                        # GTK's cached ABOVE flag can lag the actual WM state.
                        # Query only this synthetic window's EWMH property.
                        wm_state = subprocess.check_output(
                            ['xprop', '-id', str(GdkX11.X11Window.get_xid(native)), '_NET_WM_STATE'],
                            text=True, timeout=2)
                        above = '_NET_WM_STATE_ABOVE' in wm_state
                        observed = {'position': tuple(window.get_position()),
                                    'size': tuple(window.get_size()), 'above': above,
                                    'ui': payloads[-1]['ui']}
                        matched = (tuple(window.get_position()) == expected
                                   and tuple(window.get_size()) == (width, max(1, area.height - 20))
                                   and above == topmost
                                   and payloads[-1]['desktopCapabilities']['positioning'] is True
                                   and payloads[-1]['ui']['mode'] == mode
                                   and payloads[-1]['ui']['topmost'] == topmost)
                if matched:
                    results.append(name)
                    index += 1
                    if index == len(steps):
                        assert json.loads(prefs_path.read_text()) == preferences
                        app.quit()
                        return False
                    deadline = time.monotonic() + 10
                    app.action(steps[index][1])
                elif time.monotonic() > deadline:
                    raise AssertionError('Window did not reach expected state: ' + name + ' ' + json.dumps(observed))
            except Exception as error:
                failure = str(error)
                app.quit()
                return False
            return True

        GLib.timeout_add(100, poll)
        app.run([sys.argv[0]])
        print(json.dumps({'backend': display.__gtype__.name, 'saved_topmost': saved,
                          'passed': results, 'error': failure}))
        return 1 if failure or len(results) != len(steps) else 0


if __name__ == '__main__':
    raise SystemExit(main())
