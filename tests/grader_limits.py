"""Trusted entrypoint: verify a kernel memory quota before loading a worker.

Never substitute RSS polling or an unverified rlimit for a hard quota. Hosts
that ignore address-space limits refuse generated-code evaluation.
"""
import json
import os
from pathlib import Path
import resource
import runpy
import subprocess
import sys

MEMORY_BYTES = 256 * 1024 * 1024
UNAVAILABLE = 78


def container_controls():
    """Verify real cgroup limits and stack a socket filter on Docker seccomp."""
    import ctypes
    import errno
    import platform
    import socket
    try:
        status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
        if (os.getuid() != 65534 or int(status['CapEff'].strip(), 16) != 0
                or status['NoNewPrivs'].strip() != '1' or status['Seccomp'].strip() != '2'):
            return False
        base = Path('/sys/fs/cgroup')
        if not 0 < int((base / 'memory.max').read_text()) <= MEMORY_BYTES:
            return False
        if int((base / 'memory.swap.max').read_text()) != 0:
            return False
        if not 0 < int((base / 'pids.max').read_text()) <= 16:
            return False
        quota, period = map(int, (base / 'cpu.max').read_text().split())
        if not 0 < quota <= period:
            return False
        arch, sock, pair = {'x86_64': (0xc000003e, 41, 53),
                            'aarch64': (0xc00000b7, 198, 199)}[platform.machine()]
        class Filter(ctypes.Structure):
            _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte),
                        ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint)]
        class Program(ctypes.Structure):
            _fields_ = [('len', ctypes.c_ushort), ('filter', ctypes.POINTER(Filter))]
        # Validate syscall architecture; reject x32 and creation of any socket.
        # This ADDS a filter; Docker's default seccomp policy remains in force.
        rows = [(0x20, 0, 0, 4), (0x15, 1, 0, arch), (0x06, 0, 0, 0x80000000),
                (0x20, 0, 0, 0), (0x35, 0, 1, 0x40000000),
                (0x06, 0, 0, 0x50000 | errno.EPERM),
                (0x15, 1, 0, sock), (0x15, 0, 1, pair),
                (0x06, 0, 0, 0x50000 | errno.EPERM), (0x06, 0, 0, 0x7fff0000)]
        filters = (Filter * len(rows))(*(Filter(*row) for row in rows))
        program = Program(len(rows), filters)
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(38, ctypes.c_ulong(1), 0, 0, 0) != 0:
            return False
        if libc.prctl(22, ctypes.c_ulong(2), ctypes.byref(program), 0, 0) != 0:
            return False
        for family in (socket.AF_INET, socket.AF_INET6, socket.AF_UNIX):
            try:
                with socket.socket(family):
                    return False
            except OSError as exc:
                if exc.errno != errno.EPERM:
                    return False
        try:
            left, right = socket.socketpair()
            left.close(); right.close()
            return False
        except OSError as exc:
            if exc.errno != errno.EPERM:
                return False
        return True
    except (OSError, ValueError, KeyError, AttributeError):
        return False


def memory_budget_status():
    # An oversized mmap is checked first without touching pages. If a kernel
    # ignores the quota, stop before the larger heap allocation is attempted.
    probe = '''import errno,json,mmap,resource,sys
limit=int(sys.argv[1])
def stop(phase,reason):
 print(json.dumps({'phase':phase,'reason':reason}),flush=True)
 sys.exit(91)
try:
 resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
 small=bytearray(1024*1024)
 with mmap.mmap(-1,1024*1024) as small_map:small_map[0]=1
except (MemoryError,OSError,ValueError):
 stop('probe_setup','limit_or_small_allocation_failed')
for name,allocate in [('mmap',lambda:mmap.mmap(-1,limit+32*1024*1024)),('heap',lambda:bytearray(limit+32*1024*1024))]:
 try:
  value=allocate()
 except MemoryError:
  continue
 except OSError as exc:
  if exc.errno==errno.ENOMEM:continue
  stop(name,'allocation_failed_for_other_reason')
 stop(name,'allocation_exceeded_budget')
print(json.dumps({'phase':'complete','reason':'verified'}),flush=True)
sys.exit(0)
'''
    phase = 'set_limit'
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
        phase = 'read_limit'
        if resource.getrlimit(resource.RLIMIT_AS) != (MEMORY_BYTES, MEMORY_BYTES):
            return {'verified': False, 'phase': phase, 'reason': 'limit_mismatch'}
        phase = 'allocation_probe'
        probe_limit = 64 * 1024 * 1024
        result = subprocess.run([os.path.realpath(sys.executable), '-I', '-S', '-B', '-c', probe, str(probe_limit)],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=5,
                                env={'PATH': '/usr/bin:/bin'})
        expected = {'phase': 'complete', 'reason': 'verified'}
        try:
            detail = json.loads(result.stdout)
        except (ValueError, UnicodeError):
            detail = {}
        if result.returncode == 0 and detail == expected:
            return {'verified': True, 'phase': 'complete', 'reason': 'verified'}
        # Only fixed diagnostics from the trusted probe; never echo process data.
        phases = {'probe_setup', 'heap', 'mmap'}
        reasons = {'limit_or_small_allocation_failed', 'allocation_failed_for_other_reason', 'allocation_exceeded_budget'}
        if (isinstance(detail, dict) and isinstance(detail.get('phase'), str) and isinstance(detail.get('reason'), str)
                and detail['phase'] in phases and detail['reason'] in reasons):
            return {'verified': False, 'phase': detail['phase'], 'reason': detail['reason']}
        return {'verified': False, 'phase': phase, 'reason': 'probe_failed', 'returncode': result.returncode}
    except (OSError, ValueError, AttributeError, subprocess.TimeoutExpired, MemoryError) as exc:
        result = {'verified': False, 'phase': phase, 'reason': type(exc).__name__}
        if isinstance(exc, OSError) and isinstance(exc.errno, int):
            result['errno'] = exc.errno
        return result


def enforce_memory_budget():
    result = memory_budget_status()
    if not result['verified']:
        print('grader_memory_guard: ' + json.dumps(result, sort_keys=True), file=sys.stderr)
    return result['verified']


def main():
    if sys.argv[1:2] == ['--container']:
        del sys.argv[1]
        if not container_controls():
            return 79
    if sys.argv[1:] == ['--diagnose']:
        result = memory_budget_status()
        print(json.dumps(result, sort_keys=True))
        return 0 if result['verified'] else UNAVAILABLE
    if not enforce_memory_budget():
        return UNAVAILABLE
    if sys.argv[1:] == ['--check']:
        print('hard_memory_budget_verified')
        return 0
    if len(sys.argv) < 2:
        return UNAVAILABLE
    worker = Path(sys.argv[1]).resolve()
    sys.argv = sys.argv[1:]
    # Sibling trusted workers are staged into the same private grader root.
    sys.path.insert(0, str(worker.parent))
    runpy.run_path(str(worker), run_name='__main__')
    return 0


if __name__ == '__main__':
    sys.exit(main())
