"""Non-destructive process inspection for isolated native control probes."""
import ctypes
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time


def process_state(pid):
    if os.name == 'nt':
        # os.kill(pid, 0) on Windows can terminate the process. A wait handle
        # observes liveness without signalling or changing the target process.
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only
        if not handle:
            error = ctypes.get_last_error()
            if error == 87:  # PID no longer exists
                return ''
            raise ctypes.WinError(error)
        try:
            status = kernel.WaitForSingleObject(handle, 0)
            if status == 258:
                return 'R'
            if status == 0:
                return ''
            raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel.CloseHandle(handle)
    result = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)],
                            capture_output=True, text=True, timeout=2)
    if result.returncode not in (0, 1):
        raise RuntimeError('Unable to inspect probe process')
    return result.stdout.strip()[:1]


def process_alive(pid):
    return process_state(pid) not in ('', 'Z')


def read_process_marker(path, timeout=5):
    # Windows can expose the directory entry before the writer releases its
    # file handle. Existence alone is not evidence that JSON is ready to read.
    deadline = time.monotonic() + timeout
    while True:
        try:
            return json.loads(Path(path).read_text(encoding='utf-8'))
        except (FileNotFoundError, PermissionError, json.JSONDecodeError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(.02)


def safe_process_topology(targets):
    """Return ephemeral IDs and executable names only; never arguments."""
    rows = {}
    if os.name == 'nt':
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
            'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress'],
            capture_output=True, text=True, timeout=10, check=True,
            creationflags=subprocess.CREATE_NO_WINDOW)
        for row in json.loads(result.stdout):
            pid = row['ProcessId']
            rows[pid] = {'pid': pid, 'parent': row['ParentProcessId'],
                         'group': None, 'executable': row['Name']}
    else:
        result = subprocess.run(['ps', '-axo', 'pid=,ppid=,pgid=,comm='],
                                capture_output=True, text=True, timeout=2, check=True)
        for line in result.stdout.splitlines():
            fields = line.split(None, 3)
            if len(fields) == 4 and all(field.isdigit() for field in fields[:3]):
                pid, parent, group = map(int, fields[:3])
                rows[pid] = {'pid': pid, 'parent': parent, 'group': group,
                             'executable': Path(fields[3]).name}
    wanted = {int(value) for value in targets
              if (type(value) is int and value > 1) or
              (isinstance(value, str) and value.isascii() and value.isdigit() and int(value) > 1)}
    frontier = list(wanted)
    while frontier:
        row = rows.get(frontier.pop())
        if row and row['parent'] > 1 and row['parent'] not in wanted:
            wanted.add(row['parent'])
            frontier.append(row['parent'])
    return [rows[pid] for pid in sorted(wanted) if pid in rows]


def sleep_command(process_marker):
    # Retain the probe owner's ACL when the native Windows sandbox writes IDs.
    Path(process_marker).write_text('', encoding='utf-8')
    script = Path(process_marker).with_suffix('.py')
    script.write_text('import os, json, subprocess, sys\nfrom pathlib import Path\n'
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(45)'])\n"
        + 'Path(' + repr(str(process_marker)) + ').write_text(json.dumps([os.getpid(), child.pid]))\n'
        + 'child.wait()\n', encoding='utf-8')
    if os.name == 'nt':
        return '& ' + ' '.join("'" + path.replace("'", "''") + "'" for path in (sys.executable, str(script)))
    return shlex.join([sys.executable, str(script)])


def host_probe_pids(marker, namespace_pids, proc_root=Path('/proc')):
    """Translate sandbox PIDs only after identifying our exact synthetic script.

    Linux's native sandbox has its own PID namespace (commonly 2 and 3).
    Those numbers must never be interpreted as host processes.
    """
    if sys.platform != 'linux':
        return namespace_pids
    if len(namespace_pids) != 2 or not all(type(pid) is int and pid > 1 for pid in namespace_pids):
        raise ValueError('Invalid probe PID marker')
    script = str(Path(marker).with_suffix('.py').resolve())
    rows, parents = {}, []
    for directory in Path(proc_root).glob('[0-9]*'):
        try:
            fields = dict(line.split(':', 1) for line in (directory / 'status').read_text().splitlines() if ':' in line)
            ids = [int(value) for value in fields.get('NSpid', '').split()]
            if not ids:
                continue
            pid, parent = int(directory.name), int(fields['PPid'])
            rows[pid] = (parent, ids[-1])
            if ids[-1] == namespace_pids[0]:
                args = (directory / 'cmdline').read_bytes().split(b'\0')
                if script.encode() in args:
                    parents.append(pid)
        except (OSError, ValueError, KeyError):
            continue
    if len(parents) != 1:
        raise RuntimeError('Cannot uniquely identify synthetic sandbox parent on host')
    parent = parents[0]
    children = [pid for pid, (ppid, nsid) in rows.items() if ppid == parent and nsid == namespace_pids[1]]
    if len(children) != 1:
        raise RuntimeError('Cannot uniquely identify synthetic sandbox child on host')
    return [parent, children[0]]
