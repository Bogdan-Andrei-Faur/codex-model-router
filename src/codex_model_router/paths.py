"""Location of immutable checkout resources, independent of package/data paths."""
from pathlib import Path
import sys


def resource_root():
    # Both a checkout and the Linux Resources payload contain src/<package>.
    # Frozen services select their owned Resources directory before importing.
    if getattr(sys, 'frozen', False):
        # Legacy portable Windows ZIPs launch bin/<core>.exe without a manifest.
        return Path(sys.executable).resolve().parent.parent
    return Path(__file__).resolve().parents[2]
