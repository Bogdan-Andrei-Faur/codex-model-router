"""Static entrypoint for the frozen runtime's dependency analysis and dispatch."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from codex_model_router.packaged_main import main

if __name__ == '__main__':
    try:
        sys.exit(main() or 0)
    except (OSError, ValueError, KeyError):
        print('La instalación no pudo iniciarse. Se han conservado tus datos.', file=sys.stderr)
        sys.exit(1)
