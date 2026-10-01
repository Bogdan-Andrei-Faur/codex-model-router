"""Read-only native quota probe; no turns, credits or account changes."""
import json
import time

from smoke_native import Client


def main():
    client = Client()
    try:
        client.call('initialize', {'clientInfo': {'name': 'codex_desktop', 'version': 'router-usage-probe'}})
        client.send({'method': 'initialized', 'params': {}})
        deadline = time.monotonic() + 30
        snapshot = {}
        while time.monotonic() < deadline:
            for path in client.state.glob('status-*.json'):
                snapshot = json.loads(path.read_text()).get('account_usage', {})
            if 'remaining_percent' in snapshot:
                break
            time.sleep(.1)
        assert 'remaining_percent' in snapshot, 'Native account did not provide quota windows within 30s'
        assert snapshot['valid_until'] > time.time(), 'Native quota sample is already expired'
        # This ordinary client RPC must still roundtrip after the injected read.
        catalog = client.call('model/list', {})
        assert catalog.get('data'), 'Normal RPC traffic failed after quota polling'
        assert not any(str(n.get('id', '')).startswith('personal-router-usage-') for n in client.notifications), 'Internal response leaked to client'
        print(json.dumps({'native_quota': True, 'windows': len(snapshot['windows']),
                          'client_rpc_after_poll': True, 'internal_reply_hidden': True,
                          'inference_requests': 0}))
    finally:
        client.close()
        client.temp.cleanup()


if __name__ == '__main__':
    main()
