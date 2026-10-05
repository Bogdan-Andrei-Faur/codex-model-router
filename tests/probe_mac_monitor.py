"""Native non-key click fixture. No global mouse events or owner data."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != 'darwin':
        raise SystemExit('macOS AppKit/WebKit required')
    declarations = (ROOT / 'MonitorMac.swift').read_text().split('// Native lifecycle', 1)[0]
    harness = (ROOT / 'tests/mac_first_click.swift').read_text()
    with tempfile.TemporaryDirectory(prefix='router-native-click-') as folder:
        source = Path(folder) / 'main.swift'
        source.write_text(declarations + '\n' + harness)
        binary = Path(folder) / 'probe'
        subprocess.run(['xcrun', 'swiftc', str(source), '-o', str(binary),
                        '-framework', 'AppKit', '-framework', 'WebKit'], check=True)
        result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
        print(json.dumps({'native_fixture_exit': result.returncode,
                          'one_click_delivered': result.returncode == 0,
                          'physical_os_mouse_delivery_verified': False}))
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
