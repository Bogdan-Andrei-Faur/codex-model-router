"""Adopt an explicitly imported, owned Windows connection after bridge preflight.

No source file or registration is changed here. The caller commits the new
registration only after validating the launcher and rechecking the environment.
"""
import json
from pathlib import Path

from codex_model_router.platforms.desktop_runtime import DiscoveryError
from codex_model_router.platforms.installation_migration import linked


def imported_connection(root, current):
    marker = Path(root) / 'state/legacy-installation.json'
    if not marker.is_file() or linked(marker):
        return None
    try:
        provenance=json.loads(marker.read_text())
        if not isinstance(provenance,dict) or provenance.get('schema')!=1:raise ValueError()
        selected=Path(provenance['root'])
        if linked(selected):raise ValueError()
        legacy = selected.resolve(strict=True)
        record_path = legacy / 'state/desktop-integration.json'
        if linked(record_path) or linked(record_path.parent):
            raise ValueError()
        record = json.loads(record_path.read_text())
        expected = str((legacy / 'dist/codex-router.exe').resolve(strict=True))
        if not isinstance(record,dict):raise ValueError()
        previous = record['previous']
        if (not isinstance(previous,dict) or type(previous.get('kind')) is not int
                or record.get('schema') != 1 or record.get('platform') != 'win32'
                or record.get('status') != 'registered' or record.get('wrapper') != expected
                or current['value'] != expected or previous.get('kind') not in (1, 2)
                or previous.get('value') is not None and not isinstance(previous['value'], str)):
            raise ValueError()
        # Registration selects the next Desktop launch. It neither migrates
        # live data nor interrupts the existing source bridge; offline import
        # keeps its separate active-writer guard.
        return {'previous': previous, 'legacy': str(legacy), 'wrapper': expected}
    except (OSError, ValueError, KeyError, TypeError):
        raise DiscoveryError('No se pudo verificar la conexión anterior. Se ha conservado sin cambios.',
                             code='source_connection_unverified') from None
