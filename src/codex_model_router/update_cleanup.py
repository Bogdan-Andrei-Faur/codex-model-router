"""Bound Mac update artifacts using terminal receipts, never broad app discovery.

The running monitor retries this maintenance off the UI thread. The application
replacement lock and live-process inventory protect copied helpers, including
legacy helpers without a maintenance lease. Receipts remain for recovery/audit.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess

from codex_model_router.storage.state_store import file_lock
from codex_model_router.update_install import APP_NAME, app_info, recovery_agent
from codex_model_router.updates import UpdateError, installer_name, version_key

TERMINAL = {'completed', 'rolled_back', 'failed', 'cancelled'}


def _directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or path.resolve() != path:
        raise ValueError('unsafe_cleanup_directory')


def _json(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > 16384:
        raise ValueError('unsafe_cleanup_receipt')
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError('unsafe_cleanup_receipt')
    return value


def _process_commands():
    # Keep command lines in memory only; never log them (they can hold secrets).
    return subprocess.check_output(['/bin/ps', '-ww', '-axo', 'command='], text=True, timeout=10).splitlines()


def cleanup_macos(root, app, *, dry_run=False):
    """Keep one identified last-good bundle; delete only terminal job payloads.

    Unknown/corrupt receipts, pending commits, a live helper or unavailable
    process inventory defer the whole pass. Missing backups are never invented.
    Downloads newer than the running installation are never eligible.
    """
    result = {'status': 'deferred', 'removed': 0, 'previous_retained': 0}
    root, app = Path(root).absolute(), Path(app).absolute()
    updates = root / 'state/updates'
    jobs = updates / 'jobs'
    if not jobs.exists():
        return dict(result, status='nothing_to_clean')
    try:
        for folder in (root, root / 'state', updates, jobs, app.parent, app):
            _directory(folder)
        if app.name != APP_NAME or app == root or app in root.parents or root in app.parents:
            return result
        current = app_info(app)
        current_version = version_key(current['CFBundleShortVersionString'])
        with file_lock(app.parent / '.codex-router-update.lock', timeout=.05):
            receipts = []
            for job in sorted(jobs.iterdir()):
                if not re.fullmatch('[0-9a-f]{32}', job.name):
                    continue
                _directory(job)
                op = _json(job / 'operation.json')
                if (op.get('schema') != 1 or op.get('token') != job.name
                        or op.get('app') != str(app) or op.get('phase') not in TERMINAL
                        or recovery_agent(job.name).exists()):
                    return result
                package = op['package']
                target = version_key(package['version'])
                old = version_key(op['oldVersion'])
                names = {installer_name(package['version'], 'macos', arch) for arch in ('arm64', 'x64')}
                if (old >= target or target > current_version or not isinstance(op.get('oldBuild'), str)
                        or package['name'] not in names):
                    return result
                receipts.append((job, op))
            # Only a positively confirmed installation authorizes housekeeping.
            if not any(op['phase'] == 'completed' and op['package']['version'] == current['CFBundleShortVersionString']
                       for _, op in receipts):
                return result
            commands = _process_commands()
            if not commands:
                return result
            backups = []
            candidates = []
            for job, op in receipts:
                previous = app.parent / ('.router-previous-' + job.name + '.app')
                staged = app.parent / ('.router-new-' + job.name + '.app')
                if any(str(p) in command for command in commands for p in (job, previous, staged)):
                    return result
                if previous.exists() or previous.is_symlink():
                    _directory(previous)
                    info = app_info(previous)
                    if (op['phase'] != 'completed' or info.get('CFBundleShortVersionString') != op['oldVersion']
                            or info.get('RouterBuildId') != op['oldBuild']):
                        return result
                    backups.append((version_key(op['oldVersion']), (job / 'operation.json').stat().st_mtime_ns, previous))
                if staged.exists() or staged.is_symlink():
                    _directory(staged)
                    if app_info(staged).get('CFBundleShortVersionString') != op['package']['version']:
                        return result
                    candidates.append(staged)
                worker = job / APP_NAME
                if worker.exists() or worker.is_symlink():
                    _directory(worker)
                    info = app_info(worker)
                    if info.get('CFBundleShortVersionString') != op['oldVersion'] or info.get('RouterBuildId') != op['oldBuild']:
                        return result
                    candidates.append(worker)
                for name in ('expanded', 'rechecked'):
                    path = job / name
                    if path.exists() or path.is_symlink():
                        _directory(path)
                        candidates.append(path)
                for path in (job / op['package']['name'], job / ('checked-' + op['package']['name']), updates / op['package']['name']):
                    if path.exists() or path.is_symlink():
                        info = path.lstat()
                        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                                or info.st_size != op['package']['size']
                                or hashlib.sha256(path.read_bytes()).hexdigest() != op['package']['sha256']):
                            return result
                        candidates.append(path)
            if not backups:
                return dict(result, status='no_recovery_copy')
            backups.sort(reverse=True)
            candidates.extend(item[2] for item in backups[1:])
            # Validate the entire plan before deleting anything. rmtree does not
            # traverse inner symlinks; top-level/ancestor symlinks are rejected.
            for path in dict.fromkeys(candidates):
                if not dry_run:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                result['removed'] += 1
            return dict(result, status='planned' if dry_run else 'cleaned', previous_retained=1)
    except (OSError, ValueError, KeyError, TypeError, UpdateError, subprocess.SubprocessError):
        # Retrying must not turn a housekeeping failure into an update failure.
        return result
