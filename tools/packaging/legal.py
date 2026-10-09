"""Copy an explicit set of license notices into an isolated package payload."""
from pathlib import Path
import shutil


NOTICES = {
    'LICENSE': 'LICENSE',
    'THIRD_PARTY_NOTICES.md': 'THIRD_PARTY_NOTICES.md',
    'licenses/Lucide.txt': 'assets/lucide/LICENSE',
    'licenses/Nunito.txt': 'monitor-ui/fonts/OFL-Nunito.txt',
}


def copy_legal_notices(root, destination):
    root, destination = Path(root).resolve(), Path(destination)
    sources = []
    # Validate every input before copying: a missing notice must fail packaging.
    for target, relative in NOTICES.items():
        source = root / relative
        if not source.is_file() or source.is_symlink() or root not in source.resolve().parents:
            raise ValueError('Missing or unsafe package license notice: ' + relative)
        sources.append((source, destination / target))
    for source, target in sources:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
