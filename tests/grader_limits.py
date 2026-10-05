"""Trusted entrypoint: verify a kernel memory quota before loading a worker.

Never substitute RSS polling or an unverified rlimit for a hard quota. Hosts
that ignore address-space limits refuse generated-code evaluation.
"""
import os
from pathlib import Path
import resource
import runpy
import subprocess
import sys

MEMORY_BYTES = 256 * 1024 * 1024
UNAVAILABLE = 78


def enforce_memory_budget():
    # The probe's bounded allocation is safe even on kernels ignoring RLIMIT_AS.
    # Exercise both mmap and Python's heap: either bypass invalidates the quota.
    probe = '''import mmap,resource,sys
limit=64*1024*1024
resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
small=bytearray(1024*1024)
for allocate in (lambda:bytearray(96*1024*1024),lambda:mmap.mmap(-1,96*1024*1024)):
 try:
  value=allocate()
 except (MemoryError,OSError):
  continue
 sys.exit(91)
sys.exit(0)
'''
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
        if resource.getrlimit(resource.RLIMIT_AS) != (MEMORY_BYTES, MEMORY_BYTES):
            return False
        result = subprocess.run([os.path.realpath(sys.executable), '-I', '-S', '-B', '-c', probe],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=5,
                                env={'PATH': '/usr/bin:/bin'})
        return result.returncode == 0
    except (OSError, ValueError, AttributeError, subprocess.TimeoutExpired):
        return False


def main():
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
