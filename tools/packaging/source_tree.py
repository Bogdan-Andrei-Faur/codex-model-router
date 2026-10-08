"""Explicit immutable build snapshot; no private data or generated artifacts."""
from pathlib import Path
import shutil


def stage_source(root, destination):
    root, destination = Path(root), Path(destination)
    paths = [*root.glob('*.py'), root / 'build.ps1', root / 'VERSION', root / 'config.example.json']
    for directory, extensions in {
        'src': {'.py'}, 'native': {'.swift', '.cs'},
        'tools': {'.py', '.ps1', '.json', '.txt', '.iss', '.js'},
        'monitor-ui': None, 'assets': None,
    }.items():
        paths.extend(path for path in (root / directory).rglob('*')
                     if path.is_file() and (extensions is None or path.suffix in extensions))
    for path in sorted(set(paths)):
        if path.name == 'build_stamp.py' or '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        target = destination / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
