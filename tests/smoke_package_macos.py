"""Verify a real unsigned pkg after extraction/relocation without installing it.

All mutable data and monitor windows are synthetic. No Desktop registration,
provider inference, keys, real user data or active bridge are touched.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);args=p.parse_args()
    if sys.platform!='darwin':raise SystemExit('Mac artifact verification requires macOS')
    package=args.package.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='router-package-smoke-') as folder:
        base=Path(folder).resolve();expanded=base/'expanded'
        subprocess.run(['/usr/sbin/pkgutil','--expand-full',str(package),str(expanded)],check=True,capture_output=True)
        apps=list(expanded.glob('**/Payload/Applications/Codex Model Router.app'))
        assert len(apps)==1,'Expected exactly one application payload'
        contents=apps[0]/'Contents';resources=contents/'Resources'
        manifest=json.loads((resources/'application.json').read_text())
        assert manifest['distribution']=='unsigned-local' and manifest['publisherVerified'] is False
        forbidden={'config.local.json','history.jsonl','prompts.jsonl','desktop-integration.json','build.log'}
        assert not any(p.name in forbidden or p.suffix=='.secret' for p in apps[0].rglob('*'))
        moved=base/'relocated/Codex Model Router.app';moved.parent.mkdir();shutil.copytree(apps[0],moved,symlinks=True)
        subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(moved)],check=True,capture_output=True)
        runtime=moved/'Contents'/manifest['runtime'];root=base/'synthetic-data'
        env=dict(os.environ)
        for key in tuple(env):
            if key.startswith('PERSONAL_CODEX_') or key in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV','CODEX_CLI_PATH'):env.pop(key,None)
        env['PATH']='/no-development-tools';env['PERSONAL_CODEX_MONITOR_CODE_ROOT']='/not-a-checkout'
        def command(service,*arguments,timeout=30):
            return subprocess.run([str(runtime),'--data-root',str(root),service,*arguments],env=env,capture_output=True,check=True,timeout=timeout)
        identity=json.loads(command('identity').stdout)
        assert identity['packaged'] and identity['build']==manifest['build']
        assert not root.exists(),'Identity query unexpectedly created user data'
        assert json.loads(command('bootstrap').stdout)['createdConfig']
        assert not json.loads(command('bootstrap').stdout)['createdConfig']
        config_path=root/'config.local.json';config=json.loads(config_path.read_text())
        config.update(enabled=False,python='/not-installed/python',owner_preference='synthetic-fixture',updates_auto_check=False)
        config_path.write_text(json.dumps(config));config_before=config_path.read_bytes()
        # The exact installed service responds over private pipes with empty PATH.
        child=subprocess.Popen([str(runtime),'--data-root',str(root),'monitor-service'],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            child.stdin.write(b'{"requestId":1,"action":"snapshot","history":false,"revision":-1}\n');child.stdin.flush()
            # Bound the protocol read by communicate, which also verifies EOF shutdown.
            output,errors=child.communicate(timeout=15)
            reply=json.loads(output)
            assert child.returncode==0 and not errors and reply['ok']
            assert reply['payload']['productVersion']==identity['version']
            assert reply['payload']['connections']==0 and reply['payload']['threads']=={}
        finally:
            if child.poll() is None:child.kill();child.wait()
        assert config_path.read_bytes()==config_before
        # A new copy of the same version cannot overwrite mutable preferences.
        sentinel=root/'state/upgrade-sentinel';sentinel.write_text('preserve')
        assert json.loads(command('bootstrap').stdout)['createdConfig'] is False
        assert sentinel.read_text()=='preserve' and config_path.read_bytes()==config_before
        assert not (root/'state/desktop-integration.json').exists()
        # Version forwarding uses the original installed Desktop engine, no inference.
        # Desktop's own Codex launcher needs standard OS utilities (dirname);
        # the product runtime/IPC above still use no executable search path.
        bridge_env=dict(env,PATH='/usr/bin:/bin')
        bridge=subprocess.run([str(moved/'Contents/MacOS/codex-router'),'--version'],env=dict(bridge_env,PERSONAL_CODEX_ROUTER_ROOT=str(root)),capture_output=True,timeout=30)
        assert bridge.returncode==0 and bridge.stdout.startswith(b'codex-cli '),'Bundled bridge version forwarding failed'
        # Launch the exact packaged native host with synthetic preview data. The
        # private child is created only after shared WebKit sends ready.
        (root/'preview.json').write_text(json.dumps({'threads':{'synthetic':{'name':'Synthetic fixture','status':'active','model':'gpt-6.1-sol','effort':'high'}}}))
        monitor=subprocess.Popen([str(moved/'Contents/MacOS/codex-monitor-mac'),str(root),'--preview'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        native_child=None
        try:
            libproc=ctypes.CDLL('/usr/lib/libproc.dylib')
            libproc.proc_pidpath.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32]
            deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                assert monitor.poll() is None,'Packaged monitor exited before readiness'
                rows=[line.strip().split(None,2) for line in subprocess.check_output(['/bin/ps','-ww','-axo','pid=,ppid=,comm='],text=True).splitlines()]
                for row in rows:
                    if len(row)!=3 or row[1]!=str(monitor.pid):continue
                    path=ctypes.create_string_buffer(4096)
                    if libproc.proc_pidpath(int(row[0]),path,4096)>0 and Path(os.fsdecode(path.value)).resolve()==runtime.resolve():
                        native_child=row;break
                if native_child:break
                time.sleep(.1)
            assert native_child,'Packaged WebKit host never started its bundled service'
            # In preview the protocol retains the same build and cannot modify config.
            assert config_path.read_bytes()==config_before
        finally:
            if monitor.poll() is None:monitor.terminate();monitor.wait(timeout=5)
        print(json.dumps({'pass':True,'version':identity['version'],'build':identity['build'],
                          'package_sha256':hashlib.sha256(package.read_bytes()).hexdigest(),
                          'extracted_and_relocated':True,'empty_path_runtime_and_ipc':True,
                          'native_packaged_monitor_ready':True,'native_backend_version_forwarded':True,
                          'preferences_preserved':True,'desktop_registered':False,'system_installer_executed':False,
                          'publisher_verified':False,'native_windows_ubuntu_validated':False}))


if __name__=='__main__':main()
