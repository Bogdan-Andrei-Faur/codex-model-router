"""Copy the installed crypto dependency license texts into a frozen payload."""
from importlib.metadata import distribution
from pathlib import Path
import shutil
import sys


def copy_notices(destination):
    destination = Path(destination)
    count = 0
    for name in ('cryptography', 'cffi', 'pycparser'):
        package = distribution(name)
        files = [p for p in package.files or [] if '.dist-info/' in str(p)
                 and ('license' in str(p).lower() or 'copying' in str(p).lower())]
        if not files:
            raise ValueError('Dependency license is missing: ' + name)
        for item in files:
            source = Path(package.locate_file(item))
            target = destination / name / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            count += 1
    return count


if __name__ == '__main__':
    print(copy_notices(sys.argv[1]))
