"""Content-free usage gauges from native app-server observations only."""
import math
import time
import uuid


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def context_window(usage, now=None):
    usage = usage if isinstance(usage, dict) else {}
    last = usage.get('last') or {}
    used = last.get('totalTokens') if isinstance(last, dict) else None
    capacity = usage.get('modelContextWindow')
    result = {'updated': time.time() if now is None else now}
    # total is lifetime consumption, not the contents of the current context.
    # last.totalTokens already includes cached input and reasoning output.
    if finite(used) and used >= 0 and finite(capacity) and capacity > 0:
        result.update(used_tokens=used, capacity_tokens=capacity,
                      used_percent=min(100, 100 * used / capacity))
    return result


class AccountUsage:
    """Bounded read-only RPC polling; internal replies never reach Desktop."""
    def __init__(self):
        self.prefix = 'personal-router-usage-' + uuid.uuid4().hex + '-'
        self.pending = None
        self.next_read = 0
        self.buckets = {}
        self.snapshot = {}

    def clear(self, now):
        self.pending = None
        self.next_read = 0
        self.buckets = {}
        self.snapshot = {'updated': now}

    def poll(self, ready, now=None):
        now = time.time() if now is None else now
        if not ready or now < self.next_read:
            return None
        rid = self.prefix + uuid.uuid4().hex
        self.pending = rid
        self.next_read = now + 60
        return {'id': rid, 'method': 'account/rateLimits/read', 'params': {}}

    def consume(self, message, now=None):
        now = time.time() if now is None else now
        rid = message.get('id')
        if 'method' not in message and isinstance(rid, str) and rid.startswith(self.prefix):
            if rid == self.pending:
                self.pending = None
                if isinstance(message.get('result'), dict):
                    self.update(message['result'], now, replace=True)
            return True  # Suppress late replies after timeout/account change too.
        if message.get('method') == 'account/updated':
            self.clear(now)
        elif message.get('method') == 'account/rateLimits/updated':
            self.update(message.get('params') or {}, now)
        return False

    def update(self, data, now, replace=False):
        if not isinstance(data, dict):
            return
        if replace:
            self.buckets = {}
        buckets = data.get('rateLimitsByLimitId')
        if not isinstance(buckets, dict):
            legacy = data.get('rateLimits')
            buckets = {(legacy.get('limitId') or 'codex'): legacy} if isinstance(legacy, dict) else {}
        for identifier, bucket in buckets.items():
            if not isinstance(identifier, str) or not isinstance(bucket, dict):
                continue
            windows = []
            for key in ('primary', 'secondary'):
                window = bucket.get(key)
                if not isinstance(window, dict):
                    continue
                used = window.get('usedPercent')
                if not finite(used) or used < 0:
                    continue
                reset, duration = window.get('resetsAt'), window.get('windowDurationMins')
                expires = min(now + 180, reset) if finite(reset) and reset > 0 else now + 180
                windows.append({'limit_id': identifier[:100], 'window': key,
                                'remaining_percent': max(0, 100 - used),
                                'duration_minutes': duration if finite(duration) and duration > 0 else None,
                                'resets_at': reset if finite(reset) and reset > 0 else None,
                                'valid_until': expires})
            self.buckets[identifier] = windows
        windows = [w for bucket in self.buckets.values() for w in bucket]
        # Keep only the meter contract; never persist account IDs, balances,
        # credentials, upsells, or reset-credit identifiers in monitor files.
        allowed = self.snapshot.get('ordinary_usage_allowed') if not replace else None
        self.snapshot = {'updated': now, 'windows': windows}
        if windows:
            self.snapshot.update(remaining_percent=min(w['remaining_percent'] for w in windows),
                                 valid_until=min(w['valid_until'] for w in windows))
        if type(data.get('ordinaryUsageAllowed')) is bool:
            allowed = data['ordinaryUsageAllowed']
        if allowed is not None:
            self.snapshot['ordinary_usage_allowed'] = allowed
