"""Exact, bounded command allowlist for the isolated approval probe."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess


def approval_command(marker, windows=None):
    windows = os.name == 'nt' if windows is None else windows
    if windows:
        return "[System.IO.File]::WriteAllText('" + marker.replace("'", "''") + "', 'APPROVED')"
    return 'printf APPROVED > ' + shlex.quote(marker)


def exact_approval_command(command, marker, windows=None):
    windows = os.name == 'nt' if windows is None else windows
    if windows:
        expected = approval_command(marker, windows=True)
        # Only the exact synthetic write, optionally wrapped by a trusted shell.
        # Do not parse/evaluate PowerShell or accept appended commands.
        shells = ['powershell', 'powershell.exe', 'pwsh', 'pwsh.exe']
        system_root = os.environ.get('SystemRoot', r'C:\Windows')
        shells.append(system_root + r'\System32\WindowsPowerShell\v1.0\powershell.exe')
        if os.name == 'nt' and shutil.which('pwsh'):
            shells.append(shutil.which('pwsh'))
            shells.append(str(Path(shutil.which('pwsh')).with_suffix('.exe')))
        wrappers = [subprocess.list2cmdline([shell, *flags, '-Command', expected])
                    for shell in shells
                    for flags in ([], ['-NoProfile'], ['-NoProfile', '-NonInteractive'])]
        # Native Windows command descriptions also escape each backslash.
        return command == expected or command in wrappers or command in [value.replace('\\', '\\\\') for value in wrappers]
    try:
        words = shlex.split(command)
        if len(words) == 3 and words[0] in ('/bin/zsh', '/bin/bash', '/bin/sh') and words[1] in ('-lc', '-c'):
            words = shlex.split(words[2])
        return words == ['printf', 'APPROVED', '>', marker]
    except (ValueError, TypeError):
        return False
