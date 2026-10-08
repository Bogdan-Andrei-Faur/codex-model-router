"""Cross-compile the actual WPF/launcher C# sources against supplied Framework refs.

Uses an explicit, already installed .NET SDK compiler. Does not download tools,
run WPF, register Desktop, change configuration or overwrite previous outputs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT / "src"))
from codex_model_router.build_identity import identity, router_identity

SOURCES = ('native/windows/MonitorWindows.cs', 'native/windows/WindowsLayout.cs', 'native/windows/WindowsOnboarding.cs')
REFERENCES = ('mscorlib','System','System.Core','System.Windows.Forms','System.Drawing','System.Web.Extensions',
              'System.Security','System.Xaml','WindowsBase','PresentationCore','PresentationFramework')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dotnet','compiler','framework','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--webview2', type=Path, required=True)
    args=p.parse_args()
    sys.path.insert(0,str(ROOT/'tools'))
    from webview2_sdk import prepare
    prepare(args.webview2)
    if args.framework.name != 'v4.8':
        p.error('Shared Windows monitor requires Framework 4.8 references.')
    refs=[args.framework/(name+'.dll') for name in REFERENCES]
    if not all(path.is_file() for path in [args.dotnet,args.compiler,*refs]):
        p.error('Explicit SDK compiler and all Framework reference assemblies are required.')
    args.output.mkdir(parents=True,exist_ok=False)
    version,build=identity(ROOT)
    stamp=args.output/'BuildInfo.cs'
    stamp.write_text('[assembly: System.Reflection.AssemblyInformationalVersion("'+version+'+'+build+'+'+router_identity(ROOT)+'")]\n')
    env=dict(os.environ,DOTNET_ROOT=str(args.dotnet.parent),DOTNET_CLI_HOME=str(args.output/'cli-home'),
             DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
    for name,sources,entry in (('monitor',[ROOT/s for s in SOURCES]+[stamp],'RouterMonitorProgram'),
                               ('launcher',[ROOT/'native/windows/Launcher.cs'],None)):
        flags=['/nologo','/noconfig','/nostdlib+','/langversion:5','/target:winexe','/optimize+',
               '/out:'+str(args.output/(name+'.exe')),'/win32icon:'+str(ROOT/'assets/codex.ico')]
        if entry:flags.append('/main:'+entry)
        active_refs=refs+([args.webview2/'lib/net462'/('Microsoft.Web.WebView2.'+part+'.dll') for part in ('Core','Wpf')] if entry else [])
        flags += ['/reference:'+str(ref) for ref in active_refs]
        result=subprocess.run([str(args.dotnet),str(args.compiler),*flags,*map(str,sources)],
                              env=env,capture_output=True,text=True,timeout=120)
        (args.output/(name+'-compiler.txt')).write_text(result.stdout+result.stderr)
        if result.returncode:
            print(result.stdout+result.stderr)
            raise SystemExit(result.returncode)
        assert (args.output/(name+'.exe')).read_bytes()[:2]==b'MZ'
    report={'product_version':version,'build_id':build,'compile_host':sys.platform,
            'webview2_version':'1.0.4258.31','framework_target':args.framework.name,'language_version':'5','compiled':True,
            'native_compiler_used':False,'native_wpf_execution':False,'visual_acceptance':False,
            'sources_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (*SOURCES,'native/windows/Launcher.cs')},
            'artifacts_sha256':{name:hashlib.sha256((args.output/name).read_bytes()).hexdigest() for name in ('monitor.exe','launcher.exe')}}
    (args.output/'compilation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
