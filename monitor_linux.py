"""GTK/WebKit container for the same local-only monitor-ui used by macOS."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

# Set before GI imports: the Gdk override can open the display during import.
# Native Wayland cannot honor this utility window's placement/keep-above hints.
# Prefer X11 (XWayland in a Wayland session), with a native Wayland fallback.
# This affects only the monitor process and preserves explicit user overrides.
os.environ.setdefault('GDK_BACKEND', 'x11,wayland')

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('WebKit2', '4.1')
gi.require_foreign('cairo')
from gi.repository import Gdk, Gio, GLib, Gtk, WebKit2

from build_identity import identity, router_identity
from monitor_state import MonitorState, read_json
from state_store import atomic_json

ROOT = Path(__file__).resolve().parent


class Monitor(Gtk.Application):
    def __init__(self, root=ROOT, preview=False):
        app_id = 'local.codex.modelrouter.m' + hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:20]
        super().__init__(application_id=app_id, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.root = root
        self.preview = preview
        self.model = MonitorState(root, ROOT, preview)
        self.ui_path = root / 'state/monitor-ui-linux.json'
        saved = read_json(self.ui_path)
        self.mode = saved.get('mode', 'Compact')
        if self.mode not in ('Compact', 'Expanded', 'Hidden'):
            self.mode = 'Compact'
        self.topmost = saved.get('topmost', True) is True
        self.ratio = saved.get('height_ratio', .9)
        if type(self.ratio) not in (int, float) or not math.isfinite(self.ratio):
            self.ratio = .9
        self.ratio = min(1, max(.1, self.ratio))
        self.window = None
        self.ready = self.busy = self.action_busy = False
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='monitor')
        self.keys = dict.fromkeys(('jev-typesafe', 'jev-vercel'), False)
        self.last_payload = None
        self.history_requested = False
        self.history_revision = -1
        self.mode_request = None
        self.page = (ROOT / 'dist/linux-ui/index.html').resolve().as_uri()
        self.panel_height = 760
        self.connect('activate', self.activate_window)
        self.connect('shutdown', self.shutdown)

    def shutdown(self, *_):
        self.model.close()
        self.executor.shutdown(wait=False, cancel_futures=True)

    def activate_window(self, *_):
        if self.window:
            self.set_mode('Compact' if self.mode == 'Hidden' else self.mode)
            self.window.present()
            return
        self.hold()
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title('Codex automático · Monitor · v' + self.model.version)
        self.window.set_default_icon_from_file(str(ROOT / 'assets/codex-official.png'))
        self.window.set_decorated(False)
        self.window.set_app_paintable(True)
        self.window.set_keep_above(self.topmost)
        visual = self.window.get_screen().get_rgba_visual()
        if visual:
            self.window.set_visual(visual)
        self.window.connect('delete-event', self.on_delete)
        self.window.connect('map-event', self.on_map)
        manager = WebKit2.UserContentManager()
        manager.connect('script-message-received::monitor', self.message)
        manager.register_script_message_handler('monitor')
        context = WebKit2.WebContext.new_ephemeral()
        self.web = WebKit2.WebView(web_context=context, user_content_manager=manager)
        color = Gdk.RGBA(0, 0, 0, 0)
        self.web.set_background_color(color)
        settings = self.web.get_settings()
        settings.set_enable_developer_extras(False)
        settings.set_enable_html5_database(False)
        settings.set_enable_html5_local_storage(False)
        settings.set_allow_file_access_from_file_urls(False)
        settings.set_allow_universal_access_from_file_urls(False)
        self.web.connect('decide-policy', self.policy)
        self.web.connect('permission-request', lambda _web, request: (request.deny(), True)[1])
        self.web.connect('create', lambda *_: None)
        self.web.connect('context-menu', lambda *_: True)
        self.web.connect('web-process-terminated', self.reload_page)
        self.web.connect('load-failed', self.load_failed)
        self.window.add(self.web)
        self.make_tray()
        self.position()
        self.window.show_all()
        if self.mode == 'Hidden':
            self.window.hide()
        self.web.load_uri(self.page)
        GLib.timeout_add_seconds(2, self.refresh)
        Gdk.Display.get_default().connect('monitor-added', lambda *_: self.position())
        Gdk.Display.get_default().connect('monitor-removed', lambda *_: self.position())
        if not self.preview:
            self.executor.submit(self.load_keys)

    def load_keys(self):
        from linux_secret import request
        result = {provider: request(self.root, 'present', provider) == 'yes' for provider in self.keys}
        GLib.idle_add(self.keys_loaded, result)

    def keys_loaded(self, keys):
        self.keys = keys
        self.last_payload = None
        self.refresh()
        return False

    def policy(self, _web, decision, kind):
        if kind in (WebKit2.PolicyDecisionType.NAVIGATION_ACTION, WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION):
            if decision.get_navigation_action().get_request().get_uri() != self.page or kind == WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION:
                decision.ignore()
                return True
        return False

    def reload_page(self, *_):
        self.ready = False
        self.history_revision = -1
        self.web.load_uri(self.page)
        return True

    def load_failed(self, *_):
        print('Monitor: no se pudo cargar la interfaz local.', file=sys.stderr)
        return False

    def make_tray(self):
        menu = Gtk.Menu()
        for label, mode in [('Vista compacta', 'Compact'), ('Panel lateral', 'Expanded'), ('Ocultar monitor', 'Hidden')]:
            item = Gtk.MenuItem(label=label)
            item.connect('activate', lambda _, mode=mode: self.set_mode(mode))
            menu.append(item)
        pause = Gtk.MenuItem(label='Pausar / activar selección')
        pause.connect('activate', lambda _: self.action({'action': 'config', 'key': 'enabled', 'value': not read_json(self.root / 'config.local.json').get('enabled', False)}))
        menu.append(pause)
        pin = Gtk.MenuItem(label='Alternar Mantener delante')
        pin.connect('activate', lambda _: self.set_topmost(not self.topmost))
        menu.append(pin)
        quit_item = Gtk.MenuItem(label='Salir del monitor')
        quit_item.connect('activate', lambda _: self.quit())
        menu.append(quit_item)
        menu.show_all()
        self.tray = None
        try:
            gi.require_version('AyatanaAppIndicator3', '0.1')
            from gi.repository import AyatanaAppIndicator3 as Indicator
            self.tray = Indicator.Indicator.new(self.get_application_id(), str(ROOT / 'assets/codex-official.png'), Indicator.IndicatorCategory.APPLICATION_STATUS)
            self.tray.set_status(Indicator.IndicatorStatus.ACTIVE)
            self.tray.set_menu(menu)
        except (ValueError, ImportError):
            # The application launcher reactivates this same instance without a tray.
            pass

    def on_map(self, *_):
        # Window managers can ignore the initial, pre-map position. Repeat it
        # after mapping, including when a hidden monitor is shown again.
        GLib.idle_add(self.restore_window)
        return False

    def restore_window(self):
        if self.window.get_mapped():
            self.position()
            self.window.set_keep_above(self.topmost)
            self.refresh()
        return False

    def position(self):
        display = Gdk.Display.get_default()
        monitor = display.get_monitor_at_window(self.window.get_window()) if self.window.get_window() else display.get_primary_monitor()
        monitor = monitor or display.get_monitor(0)
        area = monitor.get_workarea()
        width, height = min(432, max(1, area.width - 20)), max(1, area.height - 20)
        self.panel_height = min(height, max(560, area.height * self.ratio))
        self.window.resize(width, height)
        # A positioning request on X11; the compositor chooses placement on Wayland.
        self.window.move(area.x + area.width - width - 10, area.y + 10)
        self.last_payload = None

    def on_delete(self, *_):
        self.set_mode('Hidden')
        return True

    def save_ui(self):
        if not self.preview:
            atomic_json(self.ui_path, {'mode': self.mode, 'topmost': self.topmost, 'height_ratio': self.ratio})

    def set_mode(self, mode):
        if mode not in ('Compact', 'Expanded', 'Hidden'):
            return
        self.mode = mode
        if mode == 'Hidden':
            self.window.hide()
        else:
            self.window.show_all()
        self.save_ui()
        if self.ready:
            self.emit('receiveUI', self.ui_snapshot())
        self.last_payload = None
        self.refresh()

    def set_topmost(self, value):
        if type(value) is not bool:
            return
        self.topmost = value
        self.window.set_keep_above(value)
        self.save_ui()
        self.last_payload = None
        self.refresh()

    def emit(self, function, value):
        script = 'window.' + function + '(' + json.dumps(value, ensure_ascii=True) + ')'
        self.web.evaluate_javascript(script, -1, None, self.page, None, None, None)

    def feedback(self, message):
        self.emit('monitorFeedback', message)

    def message(self, _manager, result):
        if self.web.get_uri() != self.page:
            return
        try:
            raw = result.get_js_value().to_json(0)
            if len(raw) > 20000:
                return
            data = json.loads(raw)
            if isinstance(data, dict):
                self.action(data)
        except (ValueError, TypeError, GLib.Error):
            self.feedback('No se pudo procesar la acción.')

    def action(self, data):
        action = data.get('action')
        if action == 'ready':
            self.ready = True
            self.history_revision = -1
            self.last_payload = None
            print('Monitor: interfaz compartida conectada.', flush=True)
            self.refresh()
        elif action == 'mode':
            self.mode_request = data.get('request') if type(data.get('request')) is int else None
            self.set_mode(data.get('value'))
        elif action == 'history' and type(data.get('value')) is bool:
            self.history_requested = data['value']
            self.last_payload = None
            self.refresh()
        elif action == 'topmost':
            self.set_topmost(data.get('value'))
        elif action in ('resizeEnd', 'resizeReset'):
            height = data.get('height')
            if action == 'resizeReset':
                self.ratio = .9
            elif type(height) in (int, float) and math.isfinite(height):
                self.ratio = min(1, max(.1, height / max(1, self.window.get_size()[1] + 20)))
            self.position()
            self.save_ui()
            self.refresh()
        elif action == 'bounds':
            self.input_region(data)
        elif action in ('config', 'quality', 'taskMode', 'secret', 'connection', 'update'):
            if self.preview or self.action_busy:
                self.feedback('Vista previa: cambios desactivados.' if self.preview else 'Espera a que termine la operación actual.')
                return
            self.action_busy = True
            self.executor.submit(self.perform_action, data)

    def input_region(self, data):
        values = [data.get(key) for key in ('x', 'y', 'width', 'height')]
        if not all(type(x) in (int, float) and math.isfinite(x) for x in values):
            return
        import cairo
        x, y, width, height = values
        if min(width, height) <= 0:
            return
        region = cairo.Region(cairo.RectangleInt(max(0, int(x)), max(0, int(y)), min(432, int(width + 1)), min(self.window.get_size()[1], int(height + 1))))
        self.window.input_shape_combine_region(region)

    def perform_action(self, data):
        message = 'Guardado.'
        try:
            action = data['action']
            if action == 'secret':
                from linux_secret import store_key
                provider = data.get('provider')
                if provider not in self.keys or not store_key(self.root, provider, data.get('value')):
                    raise ValueError('No se pudo guardar la clave. Desbloquea el llavero y vuelve a intentarlo.')
                GLib.idle_add(self.keys_loaded, dict(self.keys, **{provider: True}))
                message = 'Clave guardada en el llavero de Linux.'
            else:
                message = self.model.action(data)
        except ValueError as error:
            message = str(error) if type(error) is ValueError else 'No se pudo completar la operación.'
        except Exception:
            message = 'No se pudo completar la operación. Tus tareas siguen abiertas.'
        GLib.idle_add(self.action_finished, message)

    def action_finished(self, message):
        self.action_busy = False
        self.last_payload = None
        self.feedback(message)
        self.refresh()
        return False

    def refresh(self):
        if self.ready and not self.busy and not self.action_busy:
            self.busy = True
            self.executor.submit(self.collect)
        return True

    def collect(self):
        try:
            payload = self.model.payload(self.mode == 'Expanded' and self.history_requested, self.history_revision)
            GLib.idle_add(self.received, payload)
        except Exception:
            GLib.idle_add(self.received, None)

    def received(self, payload):
        self.busy = False
        if payload is None:
            self.feedback('No se pudo leer el estado. Se conserva la última vista.')
            return False
        if self.mode != 'Expanded' or not self.history_requested:
            payload.pop('history', None)
        payload['historyLoaded'] = self.history_revision >= 0 or 'history' in payload
        payload.update(keys=self.keys, ui=self.ui_snapshot(),
                       desktopCapabilities={'positioning': Gdk.Display.get_default().__gtype__.name == 'GdkX11Display', 'tray': self.tray is not None})
        comparison = {key: value for key, value in payload.items() if key != 'history'}
        encoded = json.dumps(comparison, sort_keys=True)
        if encoded != self.last_payload or 'history' in payload:
            self.emit('receive', payload)
            self.last_payload = encoded
            if 'history' in payload:
                self.history_revision = payload['journalRevision']
        return False

    def ui_snapshot(self):
        return {'mode': self.mode, 'topmost': self.topmost, 'panelHeight': self.panel_height,
                'reduced': not Gtk.Settings.get_default().get_property('gtk-enable-animations'),
                'lazyHistory': True, 'acknowledgesMode': True, 'modeRequest': self.mode_request}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', type=Path, default=ROOT)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    (args.root / 'state').mkdir(mode=0o700, parents=True, exist_ok=True)
    return Monitor(args.root, args.preview).run([sys.argv[0]])


if __name__ == '__main__':
    raise SystemExit(main())
