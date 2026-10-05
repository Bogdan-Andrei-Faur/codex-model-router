"""Private parent/child monitor IPC. No sockets, credentials, or raw error output."""
import argparse
import json
from pathlib import Path
import sys

from monitor_state import MonitorState

MAX_REQUEST = 65536
MAX_RESPONSE = 64 * 1024 * 1024


def dispatch(model, request):
    identifier = request.get('requestId')
    if type(identifier) is not int or not 0 <= identifier <= 2147483647:
        return {'requestId': None, 'ok': False, 'feedback': 'Solicitud no válida.'}
    reply = {'requestId': identifier, 'ok': True}
    if request.get('action') == 'snapshot':
        history = request.get('history', False)
        revision = request.get('revision', -1)
        if type(history) is not bool or type(revision) is not int or revision < -1:
            raise ValueError('Solicitud no válida.')
        reply['payload'] = model.payload(history, revision)
    else:
        reply['feedback'] = model.action(request)
    return reply


def serve(model, source, target):
    while True:
        line = source.readline(MAX_REQUEST + 1)
        if not line:
            return
        identifier = None
        try:
            if len(line) > MAX_REQUEST or not line.endswith(b'\n'):
                # Reject oversized/partial framing and close the owned pipe.
                return
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError()
            identifier = request.get('requestId')
            reply = dispatch(model, request)
        except Exception:
            reply = {'requestId': identifier if type(identifier) is int else None, 'ok': False,
                     'feedback': 'No se pudo completar la operación. Se conserva la última vista.'}
        try:
            encoded = json.dumps(reply, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode('utf-8')
        except (ValueError, TypeError):
            encoded = json.dumps({'requestId': identifier, 'ok': False, 'feedback': 'El estado contiene datos no válidos. Se conserva la última vista.'}).encode('utf-8')
        if len(encoded) > MAX_RESPONSE:
            encoded = json.dumps({'requestId': identifier, 'ok': False,
                                  'feedback': 'El historial supera el límite de la vista. Exporta la evidencia para analizarlo.'}).encode('utf-8')
        target.write(encoded + b'\n')
        target.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--code-root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--platform', choices=('macos', 'windows', 'linux'), required=True)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    model = MonitorState(args.root, args.code_root, args.preview, args.platform)
    try:
        serve(model, sys.stdin.buffer, sys.stdout.buffer)
    finally:
        model.close()


if __name__ == '__main__':
    main()
