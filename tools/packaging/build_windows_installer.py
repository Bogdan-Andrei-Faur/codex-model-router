"""Build an isolated per-user Windows setup; never install or register Desktop."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from codex_model_router.build_identity import identity, router_identity
from tools.packaging.legal import copy_legal_notices

ROOT = Path(__file__).resolve().parents[2]


def run(command, log, cwd=None):
    with log.open('ab') as output:
        subprocess.run([str(arg) for arg in command], cwd=cwd, env=build_environment(), stdout=output, stderr=subprocess.STDOUT, check=True)


def build_environment():
    env=dict(os.environ)
    # PowerShell 7 module paths cannot be imported by Windows PowerShell 5.1.
    for name in list(env):
        if name.lower()=='psmodulepath':del env[name]
    return env


def build(python, compiler, bootstrapper, output, framework=None):
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise ValueError('The initial installer requires a native Windows x64 build.')
    python, compiler, bootstrapper = (Path(path).absolute() for path in (python, compiler, bootstrapper))
    dependency = subprocess.check_output([str(python), '-c', 'import PyInstaller; print(PyInstaller.__version__)'], text=True).strip()
    if dependency != '6.22.3':
        raise ValueError('Use the pinned isolated tools/packaging/requirements-build.txt environment.')
    lock=json.loads((ROOT/'tools/inno-setup.lock.json').read_text())
    if compiler.name.lower()!='iscc.exe' or any(not (compiler.parent/name).is_file()
            or hashlib.sha256((compiler.parent/name).read_bytes()).hexdigest()!=digest
            for name,digest in lock['files'].items()):
        raise ValueError('Use the verified, pinned Inno Setup 6.7.3 toolchain.')
    # Verify the prerequisite before including it; never retrieve user credentials.
    verify = "$s=Get-AuthenticodeSignature -LiteralPath $args[0]; if($s.Status -ne 'Valid' -or $s.SignerCertificate.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName,$false) -ne 'Microsoft Corporation'){exit 1}"
    with tempfile.TemporaryDirectory(prefix='router-signature-') as folder:
        script=Path(folder)/'verify.ps1'; script.write_text(verify)
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),str(bootstrapper)],env=build_environment(),check=True,capture_output=True)
    version, fingerprint = identity(ROOT); engine=router_identity(ROOT)
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('A semantic product version is required.')
    output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=True)
    workspace=Path(tempfile.mkdtemp(prefix='windows-installer-',dir=output))
    source=workspace/'source'; source.mkdir(); log=workspace/'build.log'
    from tools.packaging.source_tree import stage_source
    stage_source(ROOT, source)
    # Only build in the private snapshot: live dist/ and integration stay untouched.
    command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',source/'build.ps1','-BuildOnly']
    if framework:command+=['-FrameworkReferencePath',Path(framework).resolve()]
    run(command,log)
    if identity(source)!=(version,fingerprint) or router_identity(source)!=engine:
        raise ValueError('The isolated native build does not match the source identity.')
    (source/'build_stamp.py').write_text('PRODUCT_VERSION = '+repr(version)+'\nBUILD_ID = '+repr(fingerprint)+'\nROUTER_BUILD_ID = '+repr(engine)+'\n')
    payload=workspace/'payload'; stable=payload/'bin'; stable.mkdir(parents=True)
    directory=version+'-'+fingerprint; application=payload/'versions'/directory
    resources=application/'Resources'; resources.mkdir(parents=True); binaries=application/'bin'; binaries.mkdir()
    windows=os.environ['WINDIR']; csc=Path(windows)/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    run([csc,'/nologo','/target:winexe','/optimize+','/r:System.Core.dll','/r:System.Web.Extensions.dll','/r:System.Windows.Forms.dll',
         '/win32icon:'+str(source/'assets/brand/router.ico'),'/out:'+str(stable/'codex-router.exe'),source/'native/windows/InstalledLauncher.cs',source/'native/windows/WindowsLayout.cs',source/'dist/BuildInfo.cs'],log)
    spec=workspace/'runtime.spec'
    spec.write_text('a=Analysis(['+repr(str(source/'tools/packaging/runtime_entry.py'))+'],pathex=['+repr(str(source/'src'))+','+repr(str(source))+'],hiddenimports=["build_stamp"])\n'
                    'pyz=PYZ(a.pure)\nexe=EXE(pyz,a.scripts,[],exclude_binaries=True,name="router-runtime",console=True,upx=False)\n'
                    'coll=COLLECT(exe,a.binaries,a.datas,name="runtime",upx=False)\n')
    run([python,'-m','PyInstaller','--noconfirm','--distpath',workspace/'frozen','--workpath',workspace/'work',spec],log,cwd=source)
    shutil.copytree(workspace/'frozen/runtime',application/'runtime')
    shutil.copy2(source/'dist/codex-monitor-v24.exe',binaries/'codex-monitor.exe')
    for name in ('Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.Wpf.dll'):shutil.copy2(source/'dist'/name,binaries/name)
    shutil.copytree(source/'dist/runtimes',binaries/'runtimes')
    shutil.copytree(source/'monitor-ui',resources/'ui'); shutil.copy2(source/'assets/brand/router-1024.png',resources/'ui/codex.png')
    shutil.copytree(source/'assets',resources/'assets');shutil.copy2(source/'VERSION',resources/'VERSION')
    copy_legal_notices(source, resources)
    run([python, source/'tools/packaging/bundled_notices.py', resources/'licenses'], log)
    defaults=json.loads((source/'config.example.json').read_text())
    for key in ('python','router_runtime','monitor_runtime','desktop_runtime'):defaults.pop(key,None)
    defaults['comparison_engines']=[]
    (resources/'config.example.json').write_text(json.dumps(defaults,indent=2)+'\n')
    manifest={'schema':1,'layout':'windows-install-v1','runtime':'runtime/router-runtime.exe','bridge':'bin/codex-router.exe',
              'monitor':'bin/codex-monitor.exe','version':version,'build':fingerprint,'routerBuild':engine,
              'publisherVerified':False,'distribution':'unsigned-local'}
    (resources/'application.json').write_text(json.dumps(manifest)+'\n')
    run([compiler,'/DPayload='+str(payload),'/DOutput='+str(workspace),'/DProductVersion='+version,
         '/DVersionDirectory='+directory,'/DBootstrapper='+str(bootstrapper),source/'tools/packaging/windows.iss'],log)
    if identity(ROOT)!=(version,fingerprint) or router_identity(ROOT)!=engine:
        raise ValueError('Sources changed during the build; the artifact is not publishable.')
    artifact=workspace/('codex-model-router-'+version+'-windows-x64-setup.exe')
    report={'artifact':str(artifact),'payload':str(payload),'version':version,'build':fingerprint,'routerBuild':engine,
            'architecture':'x64','sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),
            'bootstrapperSha256':hashlib.sha256(bootstrapper.read_bytes()).hexdigest(),
            'buildDependency':dependency,'compilerVersion':'6.7.3','publisherVerified':False,'installed':False,'published':False}
    (workspace/'build-result.json').write_text(json.dumps(report,indent=2)+'\n')
    artifact.with_suffix('.exe.sha256').write_text(report['sha256']+'  '+artifact.name+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',type=Path,required=True)
    parser.add_argument('--compiler',type=Path,required=True)
    parser.add_argument('--webview2-bootstrapper',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'release')
    parser.add_argument('--framework-reference-path',type=Path)
    args=parser.parse_args()
    print(json.dumps(build(args.python,args.compiler,args.webview2_bootstrapper,args.output,args.framework_reference_path)))
