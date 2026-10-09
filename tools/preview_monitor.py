"""Serve the shared monitor locally without writing telemetry or installation state.

Use --live for the installed user data, or --fixture-root for synthetic fixtures.
The private URL is temporary; only loopback GET requests with its token work.
"""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
from socketserver import TCPServer
import sys
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from codex_model_router.platforms.application_layout import user_data_root
from codex_model_router.monitor.monitor_state import MonitorState


class PreviewServer(HTTPServer):
    def server_bind(self):
        # This fixed loopback service needs no reverse DNS. HTTPServer's FQDN
        # lookup can stall startup on hosts without a responsive resolver.
        TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]

    def __init__(self, model, port=0):
        self.model = model
        self.prefix = '/' + secrets.token_urlsafe(32) + '/'
        super().__init__(('127.0.0.1', port), PreviewHandler)
        self.origin = 'http://127.0.0.1:' + str(self.server_port)


class PreviewHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Never log private URLs or request data.

    def do_GET(self):
        url = urlsplit(self.path)
        if (self.headers.get('Host') != self.server.origin[len('http://'):]
                or self.headers.get('Origin', self.server.origin) != self.server.origin
                or self.headers.get('Sec-Fetch-Site', 'none') not in ('none', 'same-origin')
                or not url.path.startswith(self.server.prefix)):
            self.send_error(404)
            return
        name = url.path[len(self.server.prefix):]
        if name == 'snapshot':
            query = parse_qs(url.query)
            try:
                revision = int(query.get('revision', ['-1'])[0])
            except ValueError:
                self.send_error(400)
                return
            value = self.server.model.payload(query.get('history', ['0'])[0] == '1', revision)
            data = json.dumps(value, ensure_ascii=False).encode('utf-8')
            mime = 'application/json'
        elif name == 'index.html':
            source = (ROOT / 'monitor-ui/index.html').read_text()
            source = source.replace("connect-src 'none'", "connect-src 'self'")
            source = source.replace('<script src="icons.js">', '<script src="preview.js"></script><script src="icons.js">')
            data, mime = source.encode(), 'text/html; charset=utf-8'
        elif name == 'preview.js':
            data, mime = (ROOT / 'tools/preview-monitor.js').read_bytes(), 'text/javascript'
        elif name == 'fonts/Nunito-variable.ttf':
            data, mime = (ROOT / 'monitor-ui/fonts/Nunito-variable.ttf').read_bytes(), 'font/ttf'
        elif name == 'codex.png':
            data, mime = (ROOT / 'assets/brand/router-256.png').read_bytes(), 'image/png'
        elif name in ('monitor.css', 'icons.js', 'core.js', 'characters.js', 'scenes.js', 'monitor.js'):
            data = (ROOT / 'monitor-ui' / name).read_bytes()
            mime = 'text/css' if name.endswith('.css') else 'text/javascript'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        for key, value in {'Content-Type': mime, 'Cache-Control': 'no-store',
                           'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
                           'Cross-Origin-Resource-Policy': 'same-origin',
                           'Content-Security-Policy': "frame-ancestors 'none'"}.items():
            self.send_header(key, value)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--live', action='store_true')
    source.add_argument('--fixture-root', type=Path)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    model = MonitorState(user_data_root() if args.live else args.fixture_root,
                         ROOT, preview=not args.live, read_only=True,
                         platform={'darwin': 'macos', 'win32': 'windows'}.get(sys.platform, 'linux'))
    server = PreviewServer(model, args.port)
    print(server.origin + server.prefix + 'index.html', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        model.close()


if __name__ == '__main__':
    main()
