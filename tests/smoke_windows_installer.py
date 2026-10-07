"""Exercise a relocated frozen payload and optionally an isolated setup lifecycle.

Never register Desktop, import owner data or run paid inference. The lifecycle
compiles a fixture-only installer with no uninstall registry entry/shortcuts and
an explicit synthetic data root. The production setup is not executed here.
"""
import argparse
import hashlib
import json
import os
import queue
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_windows_installer import build_environment


def probe_interactive_bridge(command, env):
    """Handshake/catalog must reply while stdin stays open; no task or turn."""
    process=subprocess.Popen([str(v) for v in command]+['app-server'],env=env,
                             stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    messages=queue.Queue()
    def read():
        try:
            for line in process.stdout:messages.put(json.loads(line))
        finally:messages.put(None)
    reader=threading.Thread(target=read,daemon=True);reader.start()
    def send(value):process.stdin.write(json.dumps(value).encode()+b'\n');process.stdin.flush()
    def response(identifier):
        deadline=time.monotonic()+30
        while True:
            message=messages.get(timeout=max(.01,deadline-time.monotonic()))
            if message is None:raise RuntimeError('Frozen bridge closed before protocol response')
            if message.get('id')==identifier and 'method' not in message:
                if 'error' in message:raise RuntimeError('Frozen bridge rejected protocol request')
                return message.get('result') or {}
    try:
        send({'id':1,'method':'initialize','params':{'clientInfo':{'name':'router_connection_check','version':'1.0'}}})
        response(1)
        send({'method':'initialized','params':{}})
        send({'id':2,'method':'model/list','params':{}})
        catalog=response(2)
        assert isinstance(catalog.get('data'),list) and catalog['data']
        assert process.poll() is None
    finally:
        process.stdin.close()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        reader.join(timeout=2);process.stdout.close()


def run(command, env, **kwargs):
    gui=Path(command[0]).name.lower() in ('initial.exe','latest.exe','unins000.exe')
    streams={'stdout':subprocess.DEVNULL,'stderr':subprocess.DEVNULL} if gui else {'capture_output':True}
    # Inno's final uninstaller cleanup child can inherit redirected pipes.
    # GUI installers have no stdout protocol; do not wait for their pipe EOF.
    result=subprocess.run([str(x) for x in command],env=env,timeout=120,**streams,**kwargs)
    if result.returncode:
        # Fixture commands contain no owner data. Keep diagnostics out of Git.
        log=ROOT/'state/windows-installer-fixture-failure.txt';log.parent.mkdir(exist_ok=True)
        log.write_text(str(command)+'\n'+(result.stdout or b'').decode(errors='replace')+'\n'+(result.stderr or b'').decode(errors='replace'))
        raise RuntimeError('Isolated package command failed: '+str(Path(command[0]).name)+' exit '+str(result.returncode))
    return result.stdout or b''


def smoke(receipt, compiler=None, bootstrapper=None, previous=None, shortcuts=False):
    report=json.loads(Path(receipt).read_text());payload=Path(report['payload'])
    artifact=Path(report['artifact'])
    assert hashlib.sha256(artifact.read_bytes()).hexdigest()==report['sha256']
    assert not any(path.name in ('config.local.json','state','.git') or path.suffix=='.secret' for path in payload.rglob('*'))
    env=build_environment()
    for name in list(env):
        if name.startswith('PERSONAL_CODEX_') or name in ('CODEX_CLI_PATH','PYTHONPATH'):del env[name]
    with tempfile.TemporaryDirectory(prefix='router-setup-smoke-') as folder:
        temporary=Path(folder);app=temporary/'relocated';shutil.copytree(payload,app)
        data=temporary/'data';version=report['version']+'-'+report['build'];resources=app/'versions'/version/'Resources'
        wrapper=app/'bin/codex-router.exe'
        command=[wrapper,'--data-root',data]
        # Empty PATH: no development Python, compiler or source checkout lookup.
        empty=dict(env,PATH='')
        run(command+['--activate-version',version],empty)
        if bootstrapper:run([wrapper,'--verify-webview2',Path(bootstrapper).resolve()],env)
        unsigned=subprocess.run([str(wrapper),'--verify-webview2',str(wrapper)],env=env,capture_output=True,timeout=60)
        assert unsigned.returncode!=0
        actual=json.loads(run(command+['--identity'],empty))
        assert actual['build']==report['build'] and actual['routerBuild']==report['routerBuild'] and actual['packaged']
        native_stamp=temporary/'native-stamp.ps1'
        native_stamp.write_text("param([string]$File)\nWrite-Output ((Get-Item -LiteralPath $File).VersionInfo.ProductVersion)")
        powershell=Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        for native in (wrapper,resources.parent/'bin/codex-monitor.exe'):
            stamp=run([powershell,'-NoProfile','-ExecutionPolicy','Bypass','-File',native_stamp,native],env).decode().strip()
            assert stamp==report['version']+'+'+report['build']+'+'+report['routerBuild']
        run(command+['--bootstrap'],empty)
        config=data/'config.local.json';value=json.loads(config.read_text());value['enabled']=False;value['fixture']='retained';config.write_text(json.dumps(value))
        before=config.read_bytes();run(command+['--bootstrap'],empty);assert config.read_bytes()==before
        probe_interactive_bridge(command,empty)
        # Migrate synthetic data and a real DPAPI CurrentUser blob without keys.
        legacy=temporary/'legacy';(legacy/'state').mkdir(parents=True)
        (legacy/'config.local.json').write_bytes(before)
        (legacy/'state/history.jsonl').write_text('{"event":"synthetic"}\n')
        secret=legacy/'state/jev-vercel.secret'
        crypto=temporary/'crypto.ps1'
        crypto.write_text("param([string]$Action,[string]$File)\nAdd-Type -AssemblyName System.Security\nif($Action -eq 'protect'){[IO.File]::WriteAllBytes($File,[Security.Cryptography.ProtectedData]::Protect([Text.Encoding]::UTF8.GetBytes('SYNTHETIC_ROUTER_FIXTURE'),$null,[Security.Cryptography.DataProtectionScope]::CurrentUser))}else{if([Text.Encoding]::UTF8.GetString([Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($File),$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)) -ne 'SYNTHETIC_ROUTER_FIXTURE'){exit 1}}")
        powershell=Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        run([powershell,'-NoProfile','-ExecutionPolicy','Bypass','-File',crypto,'protect',secret],env)
        original={name: (legacy/name).read_bytes() for name in ('config.local.json','state/history.jsonl','state/jev-vercel.secret')}
        # Simulate a crashed legacy bridge whose PID Windows has reused for this
        # fixture process. A live PID alone must not prevent an offline import.
        stale_status=legacy/'state/status-fixture.json'
        stale_status.write_text(json.dumps({'pid':os.getpid(),'heartbeat':1,'events':[]}))
        stale_bytes=stale_status.read_bytes()
        imported=temporary/'imported'
        run([wrapper,'--data-root',imported,'--import-legacy',legacy],empty)
        assert stale_status.read_bytes()==stale_bytes
        for name,content in original.items():assert (imported/name).read_bytes()==content and (legacy/name).read_bytes()==content
        run([powershell,'-NoProfile','-ExecutionPolicy','Bypass','-File',crypto,'verify',imported/'state/jev-vercel.secret'],env)
        assert not (imported/'state/desktop-integration.json').exists()
        runtime=resources.parent/'runtime/router-runtime.exe'
        # Original Windows configs had no platform marker. Normalize only the copy.
        legacy_value=json.loads(before);legacy_value.pop('platform')
        (legacy/'config.local.json').write_text(json.dumps(legacy_value))
        old_bytes=(legacy/'config.local.json').read_bytes()
        original_import=temporary/'original-import'
        run([wrapper,'--data-root',original_import,'--import-legacy',legacy],empty)
        assert (legacy/'config.local.json').read_bytes()==old_bytes
        assert json.loads((original_import/'config.local.json').read_bytes())==dict(legacy_value,platform='win32')
        run([wrapper,'--data-root',original_import,'--bootstrap'],empty)
        for source,target,code in ((legacy,original_import,'occupied_destination'),(temporary/'absent',temporary/'no-data','missing_config')):
            failure=subprocess.run([str(runtime),'--data-root',str(target),'import-legacy',str(source)],env=empty,capture_output=True,timeout=30)
            assert failure.returncode==1 and json.loads(failure.stdout)=={'error':{'code':code}}
        with subprocess.Popen([str(runtime),'--data-root',str(data),'monitor-service'],env=empty,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as service:
            stdout,stderr=service.communicate(b'{"requestId":1,"action":"snapshot","keys":{}}\n',timeout=30)
            assert service.returncode==0
            response=json.loads(stdout);assert response['requestId']==1 and not response.get('error')
        # Reject incomplete/version-tampered candidates without moving active.json.
        active=(app/'active.json').read_bytes()
        bad=version[:-16]+'f'*16;broken=app/'versions'/bad;shutil.copytree(resources.parent,broken)
        result=subprocess.run([str(x) for x in command+['--activate-version',bad]],env=empty,capture_output=True,timeout=60)
        assert result.returncode and (app/'active.json').read_bytes()==active
        probe=temporary/'native-probe'
        run([resources.parent/'bin/codex-monitor.exe','--root',probe,'--self-test'],empty)
        receipts=list(probe.rglob('ui-review-checks.txt'));assert len(receipts)==1 and receipts[0].read_text().startswith('PASS:')
        assert not (probe/'config.local.json').exists()
        assert run(command+['--version'],env).startswith(b'codex-cli ')
        assert not (data/'state/desktop-integration.json').exists()
        result={'runtime':True,'identity':True,'nativeAssemblyIdentity':True,'nativeProtocol':True,'ipc':True,'preferencesPreserved':True,'nativePreview':True,'offlineImport':True,'legacyWindowsConfig':True,'safeImportDiagnostics':True,'dpapiFixtureRetained':True,
                'sourceCheckoutRequired':False,'developerPythonRequired':False,'registeredDesktop':False,'liveInference':False,
                'rejectedCandidatePreservedActive':True,'productionSetupExecuted':False,'fixtureLifecycle':False}
        if compiler:
            result.update(lifecycle(temporary,report,compiler,bootstrapper,previous,env,shortcuts))
        return result


def lifecycle(temporary,report,compiler,bootstrapper,previous,env,shortcuts=False):
    compiler=Path(compiler).resolve();bootstrapper=Path(bootstrapper).resolve()
    install=temporary/'installed';data=temporary/'installed-data';builds=temporary/'setups';builds.mkdir()
    group='Codex Router QA '+temporary.name
    fixture_script=temporary/'fixture.iss'
    script=(ROOT/'installer/windows.iss').read_text(encoding='utf-8')
    assert script.count('DefaultGroupName=Codex Model Router')==1
    fixture_script.write_text(script.replace('DefaultGroupName=Codex Model Router','DefaultGroupName='+group),encoding='utf-8')
    def compile_setup(item,name):
        command=[compiler,'/DPayload='+item['payload'],'/DOutput='+str(builds),'/DProductVersion='+item['version'],
                 '/DVersionDirectory='+item['version']+'-'+item['build'],'/DBootstrapper='+str(bootstrapper),
                 '/DTestDataRoot='+str(data),'/F'+name,fixture_script]
        run(command,env)
        return builds/(name+'.exe')
    old=json.loads(Path(previous).read_text()) if previous else report
    first=compile_setup(old,'initial');latest=compile_setup(report,'latest')
    # The group page is hidden: Inno uses DefaultGroupName, not /GROUP.
    options=['/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/DIR='+str(install),'/LOG='+str(temporary/'setup.log')]
    if not shortcuts:options.append('/NOICONS')
    # This is the fixture build, with no registration entry or user launchers.
    run([first,*options],env)
    shortcut_folder=None
    if shortcuts:
        shortcut_probe=temporary/'shortcuts.ps1'
        shortcut_probe.write_text("param([string]$Group)\n$root=Join-Path ([Environment]::GetFolderPath('Programs')) $Group\n$files=@(Get-ChildItem -LiteralPath $root -Filter '*.lnk' -ErrorAction Stop)\n$shell=New-Object -ComObject WScript.Shell\n$items=@($files | ForEach-Object {$link=$shell.CreateShortcut($_.FullName); @{target=$link.TargetPath;arguments=$link.Arguments}})\n@{folder=$root;items=$items} | ConvertTo-Json -Compress -Depth 3")
        powershell=Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        found=json.loads(run([powershell,'-NoProfile','-ExecutionPolicy','Bypass','-File',shortcut_probe,group],env))
        shortcut_folder=Path(found['folder'])
        assert len(found['items'])==3
        assert any(item['arguments']=='--status' and Path(item['target']).resolve()==(install/'bin/codex-router.exe').resolve() for item in found['items'])
        assert any(item['arguments']=='--rollback-ui' for item in found['items'])
    wrapper=install/'bin/codex-router.exe';command=[wrapper,'--data-root',data]
    run(command+['--bootstrap'],env)
    config=data/'config.local.json';value=json.loads(config.read_text());value['enabled']=False;value['fixture']='preserved';config.write_text(json.dumps(value));before=config.read_bytes()
    (data/'state/history.jsonl').write_text('{"event":"synthetic"}\n');history=(data/'state/history.jsonl').read_bytes()
    # Hold an installed component open. Setup must fail without replacing active.
    active=(install/'active.json').read_bytes();runtime=install/'versions'/(old['version']+'-'+old['build'])/'runtime/router-runtime.exe'
    import ctypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CreateFileW.restype=ctypes.c_void_p
    kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    def wait_cleanup():
        # The uninstall stub returns before its temporary finalizer releases logs.
        path=temporary/'uninstall.log';deadline=time.monotonic()+10
        while path.exists():
            check=kernel.CreateFileW(str(path),0x80000000,0,None,3,0,None)
            if check not in (None,ctypes.c_void_p(-1).value):kernel.CloseHandle(check);return
            if time.monotonic()>=deadline:raise RuntimeError('Owned uninstall finalizer did not finish.')
            time.sleep(.1)
    handle=kernel.CreateFileW(str(runtime),0x80000000,0,None,3,0,None)
    assert handle not in (None,ctypes.c_void_p(-1).value)
    try:
        blocked=subprocess.run([str(latest),*options],env=env,capture_output=True,timeout=120)
        assert blocked.returncode!=0 and (install/'active.json').read_bytes()==active
    finally:kernel.CloseHandle(handle)
    run([latest,*options],env);assert config.read_bytes()==before
    upgraded=json.loads(run(command+['--identity'],env));assert upgraded['build']==report['build']
    rollback=False
    if previous and old['build']!=report['build']:
        run(command+['--rollback'],env)
        assert json.loads(run(command+['--identity'],env))['build']==old['build'];rollback=True
        run(command+['--activate-version',report['version']+'-'+report['build']],env)
    run([install/'unins000.exe','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/LOG='+str(temporary/'uninstall.log')],env)
    wait_cleanup()
    if shortcut_folder:assert not shortcut_folder.exists()
    assert not wrapper.exists() and config.read_bytes()==before and (data/'state/history.jsonl').read_bytes()==history
    run([latest,*options],env);assert config.read_bytes()==before
    run([install/'unins000.exe','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/LOG='+str(temporary/'uninstall.log')],env)
    wait_cleanup()
    if shortcut_folder:assert not shortcut_folder.exists()
    return {'fixtureLifecycle':True,'installUpgradeUninstallReinstall':True,'lockedFileBlocked':True,
            'rollback':rollback,'historyRetained':True,'startMenuShortcuts':shortcuts,'shortcutCleanup':shortcuts,'productionSetupExecuted':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('receipt',type=Path)
    parser.add_argument('--compiler',type=Path);parser.add_argument('--webview2-bootstrapper',type=Path);parser.add_argument('--previous-receipt',type=Path)
    parser.add_argument('--shortcuts',action='store_true',help='Exercise an isolated unique Start-menu group.')
    args=parser.parse_args()
    print(json.dumps(smoke(args.receipt,args.compiler,args.webview2_bootstrapper,args.previous_receipt,args.shortcuts)))
