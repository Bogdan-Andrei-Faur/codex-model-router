"""Build an unsigned local macOS pkg with bundled runtime and no user data.

This produces a reviewable native artifact; it does not install, register Desktop,
use signing credentials, notarize or publish anything. Each build owns a fresh
workspace and preserves all previous outputs and local configuration.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile

from build_identity import identity, router_identity
from updates import installer_name, architecture

ROOT = Path(__file__).resolve().parent
APP_NAME = 'Codex Model Router.app'


def run(command, log, cwd=None):
    with log.open('ab') as output:
        subprocess.run([str(arg) for arg in command], cwd=cwd, stdout=output, stderr=subprocess.STDOUT, check=True)


def build(python, output_parent):
    if sys.platform != 'darwin':
        raise ValueError('El paquete Mac se compila en macOS.')
    # Resolving the venv's Python symlink would lose its site-packages context.
    python = Path(python).absolute()
    if not python.is_file():raise ValueError('Intérprete de build no disponible.')
    dependency = subprocess.check_output([str(python), '-c', 'import PyInstaller; print(PyInstaller.__version__)'], text=True).strip()
    if dependency != '6.22.3':
        raise ValueError('El build requiere PyInstaller6.22.3 en un entorno aislado.')
    output_parent = Path(output_parent).resolve()
    output_parent.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix='macos-package-', dir=output_parent))
    source = workspace / 'source'; source.mkdir()
    version, fingerprint = identity(ROOT); engine = router_identity(ROOT)
    # Only source code and selected public assets enter the build. No recursive
    # repository copy, ignored state/config.local or developer credentials.
    for path in ROOT.glob('*.py'):
        if path.name != 'build_stamp.py': shutil.copy2(path, source / path.name)
    shutil.copy2(ROOT / 'MonitorMac.swift', source / 'MonitorMac.swift')
    shutil.copy2(ROOT / 'BridgeMac.swift', source / 'BridgeMac.swift')
    (source / 'build_stamp.py').write_text('PRODUCT_VERSION = '+repr(version)+'\nBUILD_ID = '+repr(fingerprint)+'\nROUTER_BUILD_ID = '+repr(engine)+'\n')
    app = workspace / 'payload/Applications' / APP_NAME
    contents = app / 'Contents'
    macos = contents / 'MacOS'; macos.mkdir(parents=True)
    resources = contents / 'Resources'; resources.mkdir()
    helpers = contents / 'Helpers'; helpers.mkdir()
    log = workspace / 'build.log'
    # Keep console=True for private JSONL IPC, but use a proper nested bundle so
    # frameworks/code/resources occupy macOS signing-compatible locations.
    spec=workspace/'router-runtime.spec'
    spec.write_text('a=Analysis(['+repr(str(source/'packaged_main.py'))+'],pathex=['+repr(str(source))+'],hiddenimports=["build_stamp"])\n'
                    'pyz=PYZ(a.pure)\n'
                    'exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name="router-runtime",console=True,upx=False)\n'
                    'coll=COLLECT(exe,a.binaries,a.datas,name="router-runtime",upx=False)\n'
                    'app=BUNDLE(coll,name="RouterRuntime.app",bundle_identifier="local.codex-model-router.runtime",version='+repr(version)+')\n')
    run([python, '-m', 'PyInstaller', '--noconfirm', '--distpath', workspace / 'frozen',
         '--workpath', workspace / 'work', spec], log, cwd=source)
    shutil.copytree(workspace / 'frozen/RouterRuntime.app', helpers / 'RouterRuntime.app', symlinks=True)
    run(['/usr/bin/xcrun','swiftc', source / 'MonitorMac.swift', '-o', macos / 'codex-monitor-mac',
         '-framework', 'AppKit', '-framework', 'WebKit', '-framework', 'Security',
         '-target', platform.machine() + '-apple-macosx12.0'], log)
    bridge = macos / 'codex-router'
    run(['/usr/bin/xcrun','swiftc',source/'BridgeMac.swift','-o',bridge,
         '-target',platform.machine()+'-apple-macosx12.0'],log)
    shutil.copytree(ROOT / 'monitor-ui', resources / 'ui')
    shutil.copy2(ROOT / 'assets/codex-ui-1024.png', resources / 'ui/codex.png')
    shutil.copy2(ROOT / 'VERSION', resources / 'VERSION')
    config = json.loads((ROOT / 'config.example.json').read_text())
    for key in ('python', 'desktop_runtime', 'router_runtime', 'monitor_runtime'): config.pop(key, None)
    config['comparison_engines'] = []
    (resources / 'config.example.json').write_text(json.dumps(config,indent=2)+'\n')
    metadata = {'schema':1, 'layout':'macos-bundle-v1', 'runtime':'Helpers/RouterRuntime.app/Contents/MacOS/router-runtime',
                'bridge':'MacOS/codex-router', 'version':version, 'build':fingerprint,
                'publisherVerified':False, 'distribution':'unsigned-local'}
    (resources / 'application.json').write_text(json.dumps(metadata)+'\n')
    (contents / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'codex-monitor-mac',
        'CFBundleIdentifier':'local.codex-model-router.application', 'CFBundleName':'Codex Model Router',
        'CFBundlePackageType':'APPL', 'CFBundleVersion':version, 'CFBundleShortVersionString':version,
        'RouterBuildId':fingerprint, 'RouterEngineBuildId':engine, 'RouterPackaged':True,
        'LSMinimumSystemVersion':'12.0', 'LSUIElement':True}))
    run(['/usr/bin/codesign','--force','--deep','--sign','-',app],log)
    run(['/usr/bin/codesign','--verify','--deep','--strict',app],log)
    components=workspace / 'components.plist'
    run(['/usr/bin/pkgbuild','--analyze','--root',workspace/'payload',components],log)
    descriptions=plistlib.loads(components.read_bytes())
    for description in descriptions:
        description.update(BundleIsRelocatable=False, BundleHasStrictIdentifier=True, BundleOverwriteAction='upgrade')
    components.write_bytes(plistlib.dumps(descriptions))
    artifact=workspace / installer_name(version,'macos',architecture())
    run(['/usr/bin/pkgbuild','--root',workspace/'payload','--component-plist',components,
         '--identifier','local.codex-model-router.installer','--version',version,'--install-location','/',artifact],log)
    if identity(ROOT) != (version,fingerprint) or router_identity(ROOT) != engine:
        raise ValueError('Las fuentes cambiaron durante el build; el artefacto no es publicable.')
    report={'version':version,'build':fingerprint,'routerBuild':engine,'architecture':architecture(),
            'app':str(app),'package':str(artifact),'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),
            'publisherVerified':False,'installed':False,'notarized':False,'published':False,
            'buildDependency':dependency}
    (workspace/'build-result.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',type=Path,required=True,help='Isolated build interpreter with pinned requirements-build.txt')
    parser.add_argument('--output',type=Path,default=ROOT/'release')
    args=parser.parse_args()
    print(json.dumps(build(args.python,args.output),ensure_ascii=False))


if __name__ == '__main__':main()
