"""Real signed .deb/helper/GTK transactions in an isolated Ubuntu account.

Run: xvfb-run -a dbus-run-session -- python3 tests/probe_linux_managed_update.py
Requires build dependencies. Never installs into /usr or uses production keys.
This tests helper handoff/native readiness, NOT Settings buttons or GUI login.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from tools.packaging.source_tree import stage_source
from tools.packaging.release_manifest import sign
from codex_model_router import update_portable as u
from codex_model_router.storage.state_store import atomic_json
from codex_model_router.updates import architecture, installer_name
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


def wait_for(check, timeout=90):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        result=check()
        if result:return result
        time.sleep(.1)
    raise TimeoutError('fixture deadline')


def main():
    if sys.platform!='linux' or os.getuid()==0:
        raise SystemExit('Use an unprivileged isolated Linux account and Xvfb/DBus.')
    with tempfile.TemporaryDirectory(prefix='router-managed-') as folder:
        base=Path(folder); source=base/'source';stage_source(ROOT,source)
        key=Ed25519PrivateKey.generate()
        public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        atomic_json(source/'assets/update-trust.json',dict(schema=1,keys={hashlib.sha256(public).hexdigest():base64.b64encode(public).decode()}))
        original=(source/'src/codex_model_router/monitor/monitor_linux.py').read_text()
        packages={}
        for case in ('old','success','rollback','interrupted'):
            version='0.0.1' if case=='old' else '0.0.2'
            (source/'VERSION').write_text(version+'\n')
            text=original
            if case=='rollback':text=text.replace('def main():','def main():\n    raise RuntimeError("injected fixture startup failure")',1)
            if case=='interrupted':text=text.replace('def main():','def main():\n    time.sleep(180) # fixture interrupted before readiness',1)
            (source/'src/codex_model_router/monitor/monitor_linux.py').write_text(text)
            output=base/case;output.mkdir()
            subprocess.run([sys.executable,str(source/'tools/packaging/build_linux_package.py'),'--output',str(output),'--release-name'],check=True,stdout=subprocess.DEVNULL)
            packages[case]=output/installer_name(version,'linux',architecture())
        old=u.extract_linux(packages['old'],base/'baseline')
        original_popen=subprocess.Popen
        for case in ('success','rollback','interrupted'):
            root=base/('data '+case+' ñ');root.mkdir()
            atomic_json(root/'config.local.json',dict(platform='linux',enabled=False,installation_mode='auto',updates_auto_check=False,fixture='preserved'))
            before=(root/'config.local.json').read_bytes(); children=[]
            archive=packages[case]
            package=dict(version='0.0.2',name=archive.name,size=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
            envelope=sign(key,'0.0.2',[('linux/'+architecture(),archive)])
            env=dict(os.environ,HOME=str(base/'home'),XDG_CONFIG_HOME=str(base/'xdg config ñ'))
            Path(env['HOME']).mkdir(exist_ok=True)
            def spawn(*args,**kwargs):
                child=original_popen(*args,**kwargs);children.append(child);return child
            try:
                with patch.dict(os.environ,env,clear=True),patch.object(u.subprocess,'Popen',side_effect=spawn):
                    with u.monitor_lease(root,'linux'):
                        assert u.PortableApplier(root,old,'linux').prepare(archive,package,envelope,threading.Event())
                    job=next((root/'state/updates/jobs').iterdir())
                    if case=='interrupted':
                        wait_for(lambda:u.read(job/'operation.json')['phase']=='confirming')
                        time.sleep(.5)
                        os.killpg(children[0].pid,signal.SIGKILL);children[0].wait()
                        wait_for(lambda: not (job/'ready').exists(),5)
                        replay=original_popen([str(job/'worker/bin/router-runtime'),'--data-root',str(root),'update-helper',job.name],env=u.clean_environment(),start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                        children.append(replay)
                    expected='completed' if case=='success' else 'rolled_back'
                    wait_for(lambda:u.read(job/'operation.json')['phase']==expected)
                    assert (root/'config.local.json').read_bytes()==before
                    assert u.selection_path(root).exists()==(case=='success')
                    if case=='success':assert (job/'ready').exists()
                    # Recovery's restored monitor has no update token. Require
                    # its actual GTK process lease, not just the rollback receipt.
                    else:
                        def locked():
                            try:
                                with u.monitor_lease(root,'linux'):return False
                            except TimeoutError:return True
                        wait_for(locked)
                    assert not list((Path(env['XDG_CONFIG_HOME'])/'autostart').glob('CodexRouterUpdate-*.desktop'))
                    print(json.dumps(dict(scenario=case,passed=True,signedDeb=True,realHelper=True,newNativeReady=case=='success',restoredNativeLease=case!='success',settingsButtons=False,actualLogin=False,ownerInstallationTouched=False)),flush=True)
            finally:
                for child in children:
                    try:os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    child.wait(timeout=10)


if __name__=='__main__':main()
