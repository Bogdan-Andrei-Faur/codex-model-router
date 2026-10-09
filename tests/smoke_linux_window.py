"""Check real GTK placement/stacking in a logged-in Linux desktop session.

Run with the system Python, without inheriting the shell's
backend: env -u GDK_BACKEND /usr/bin/python3 tests/smoke_linux_window.py
Uses an isolated preview and synthetic preferences; never reads user secrets.
Requires an X11/XWayland window manager and xprop (x11-utils).
"""
import argparse
import ctypes
import json
from pathlib import Path
import sys
import subprocess
import shutil
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from codex_model_router.monitor.monitor_linux import Gdk, GLib, Monitor
import gi
gi.require_version('GdkX11', '3.0')
from gi.repository import GdkX11


def clock_hole(native, width, height):
    """Read the X server's actual bounding/input shapes without moving input."""
    class Rectangle(ctypes.Structure):
        _fields_ = [('x', ctypes.c_short), ('y', ctypes.c_short),
                    ('width', ctypes.c_ushort), ('height', ctypes.c_ushort)]
    x11 = ctypes.CDLL('libX11.so.6')
    extension = ctypes.CDLL('libXext.so.6')
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    x11.XFree.argtypes = [ctypes.c_void_p]
    extension.XShapeGetRectangles.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int,
                                             ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
    extension.XShapeGetRectangles.restype = ctypes.POINTER(Rectangle)
    connection = x11.XOpenDisplay(None)
    if not connection:
        return False
    try:
        center = native.get_width() // 2
        for kind in (0, 2):  # ShapeBounding and ShapeInput
            count, ordering = ctypes.c_int(), ctypes.c_int()
            rectangles = extension.XShapeGetRectangles(connection, GdkX11.X11Window.get_xid(native),
                                                      kind, ctypes.byref(count), ctypes.byref(ordering))
            try:
                def contains(x, y):
                    return any(r.x <= x < r.x + r.width and r.y <= y < r.y + r.height
                               for r in rectangles[:count.value])
                if (contains(center, height // 2)
                        or not contains(center - width // 2 - 40, height // 2)
                        or not contains(center - width // 2 + 1, 3)
                        or not contains(center, 0)
                        or not contains(center, height + 8)):
                    return False
            finally:
                x11.XFree(rectangles)
        return True
    finally:
        x11.XCloseDisplay(connection)


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
        # Never display an obsolete dist/linux-ui left by an earlier setup.
        # This fixture exercises the current checkout's UI in private storage.
        ui = root / 'ui'
        shutil.copytree(ROOT / 'monitor-ui', ui)
        shutil.copyfile(ROOT / 'assets/brand/router-1024.png', ui / 'codex.png')
        app.page = (ui / 'index.html').resolve().as_uri()
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
        initial_monitor = display.get_primary_monitor() or display.get_monitor(0)
        initial_area = initial_monitor.get_workarea()
        initial_workarea = (initial_area.x, initial_area.y, initial_area.width, initial_area.height)
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
                        monitor = display.get_monitor_at_window(native)
                        area = monitor.get_workarea()
                        bounds = monitor.get_geometry() if topmost else area
                        width = min(800, max(1, bounds.width - 20))
                        expected = (bounds.x + (bounds.width - width) // 2, bounds.y)
                        expected_height = max(1, area.y + area.height - bounds.y - 20)
                        # GTK's cached ABOVE flag can lag the actual WM state.
                        # Query only this synthetic window's EWMH property.
                        wm_state = subprocess.check_output(
                            ['xprop', '-id', str(GdkX11.X11Window.get_xid(native)), '_NET_WM_STATE'],
                            text=True, timeout=2)
                        above = '_NET_WM_STATE_ABOVE' in wm_state
                        wm_type = subprocess.check_output(
                            ['xprop', '-id', str(GdkX11.X11Window.get_xid(native)), '_NET_WM_WINDOW_TYPE'],
                            text=True, timeout=2)
                        dock = '_NET_WM_WINDOW_TYPE_DOCK' in wm_type
                        info = subprocess.check_output(
                            ['xwininfo', '-id', str(GdkX11.X11Window.get_xid(native))],
                            text=True, timeout=2)
                        overlay = 'Override Redirect State: yes' in info
                        clock_clear = (not app.clock_height
                                       or clock_hole(native, app.clock_width, app.clock_height))
                        workarea = (area.x, area.y, area.width, area.height)
                        observed = {'position': tuple(window.get_position()),
                                    'size': tuple(window.get_size()), 'above': above, 'dock': dock, 'overlay': overlay,
                                    'clockClear': clock_clear,
                                    'expected': expected, 'expectedHeight': expected_height,
                                    'ui': payloads[-1]['ui']}
                        matched = (tuple(window.get_position()) == expected
                                   and tuple(window.get_size()) == (width, expected_height)
                                   and (above or overlay) == topmost
                                   and dock == topmost
                                   and overlay == app.edge_overlay
                                   and clock_clear
                                   and monitor == initial_monitor
                                   and workarea == initial_workarea
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
