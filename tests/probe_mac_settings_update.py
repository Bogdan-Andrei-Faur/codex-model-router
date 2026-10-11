"""Native Settings DOM -> frozen IPC -> signed helper -> automatic exit/relaunch.

Builds a TEST-ONLY old app snapshot with a DOM driver. By default transport uses
local files; --github-release retains production anonymous GitHub transport.
Neither hook is present in production sources/packages. The candidate package is
unmodified. Recovery agents are redirected to the owned fixture; Desktop, user
data, installed applications, global input and real login items are untouched.
Only --github-release tests GitHub transport. Neither mode establishes physical
input, Installer/Gatekeeper or actual login acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from tools.packaging.source_tree import stage_source
from codex_model_router.update_install import APP_NAME, app_info, extract_app, clean_environment
from codex_model_router.updates import REPOSITORY
from codex_model_router.update_trust import MANIFEST_NAME


TRANSPORT = r'''
import json,os,time
from pathlib import Path
def configure(root, service):
    import codex_model_router.update_install as installer
    installer.recovery_agent=lambda token:root/'fixture-agents'/(token+'.plist')
    fixture=json.loads((root/'fixture.json').read_text()) if (root/'fixture.json').exists() else {}
    if service=='update-helper' and fixture.get('scenario')=='rollback':
        original=installer.replace_and_confirm
        def failed_readiness(app,staged,previous,launch,confirm,record):
            return original(app,staged,previous,launch,lambda child:False,record)
        installer.replace_and_confirm=failed_readiness
    if service=='update-helper' and fixture.get('scenario')=='interrupted':
        rename=installer.os.rename
        def crash_after_first_rename(source,target):
            result=rename(source,target)
            marker=root/'fixture-crashed'
            if Path(target).name.startswith('.router-previous-') and not marker.exists():
                marker.touch();os._exit(73)
            return result
        installer.os.rename=crash_after_first_rename
    if service!='monitor-service' or fixture.get('githubRelease'):return
    import codex_model_router.updates as updates
    original=updates.UpdateManager.__init__
    def init(self,*args,**kwargs):
        def fetch():return fixture['release']
        class Response:
            def __init__(self,path,slow):
                self.stream=open(path,'rb');self.headers={'Content-Length':str(Path(path).stat().st_size)};self.slow=slow
            def __enter__(self):return self
            def __exit__(self,*args):self.stream.close()
            def read(self,size):
                if self.slow:time.sleep(.04)
                return self.stream.read(size)
        def open_url(url):
            files=fixture['files']
            if url not in files:raise ValueError('Unexpected fixture request')
            marker=root/'fixture-downloaded'
            slow=url.endswith('.pkg') and not marker.exists()
            if slow:marker.touch()
            return Response(files[url],slow)
        kwargs.update(fetcher=fetch,opener=open_url)
        original(self,*args,**kwargs)
    updates.UpdateManager.__init__=init
'''

DRIVER = r'''
var probing=false
let probeTimer=Timer.scheduledTimer(withTimeInterval:0.15,repeats:true){timer in
    guard delegate.ready,!probing else{return}
    // A recovered old app must display its result, never retry automatically.
    if CommandLine.arguments.contains(where:{$0.hasPrefix("--update-ready=")}) {timer.invalidate();return}
    probing=true
    delegate.web.callAsyncJavaScript("""
        window.monitorPointer=()=>{};showTab('settings');settings();
        window.updateProbe ??= {phase:0,events:[]};const p=window.updateProbe,u=state.updates||{},live=LIVE_GITHUB;
        const click=text=>{const b=[...document.querySelectorAll('#settings button')].find(b=>b.textContent.trim()===text&&!b.disabled);if(!b)return false;b.click();p.events.push(text);return true;};
        if(p.phase===0&&u.status==='idle'&&click('Comprobar ahora'))p.phase=1;
        else if(p.phase===1&&u.status==='available'&&u.publisherVerified&&click('Actualizar a '+u.latestVersion))p.phase=2;
        else if(!live&&p.phase===2&&u.status==='downloading'&&u.progress>0&&click('Cancelar'))p.phase=3;
        else if(p.phase===3&&u.status==='cancelled'){p.events.push('cancelled-confirmed');p.phase=4;p.retryAt=Date.now()+600;}
        else if(p.phase===4&&Date.now()>p.retryAt&&click('Comprobar ahora'))p.phase=5;
        else if(p.phase===5&&u.status==='available'&&u.publisherVerified&&click('Actualizar a '+u.latestVersion))p.phase=6;
        if(u.status==='error')return {phase:p.phase,events:p.events,error:u.error};
        return {phase:p.phase,events:p.events,status:u.status};
        """,arguments:[:],in:nil,in:.page){result in
            probing=false
            if case .success(let value)=result,let data=try? JSONSerialization.data(withJSONObject:value,options:[.sortedKeys]) {
                try? data.write(to:delegate.root.appendingPathComponent("fixture-ui.json"),options:.atomic)
            }
        }
}
'''


def build_driver(output, python, old_version, github_release=False):
    source = output / 'old-source'; source.mkdir()
    stage_source(ROOT, source)
    (source / 'VERSION').write_text(old_version + '\n')
    entry = source / 'src/codex_model_router/packaged_main.py'
    text = entry.read_text().replace("    if args.service == 'update-helper':",
        "    from codex_model_router._settings_probe import configure\n    configure(root, args.service)\n    if args.service == 'update-helper':", 1)
    entry.write_text(text)
    (source / 'src/codex_model_router/_settings_probe.py').write_text(TRANSPORT)
    swift = source / 'native/macos/MonitorMac.swift'
    driver = DRIVER.replace('LIVE_GITHUB', 'true' if github_release else 'false')
    swift.write_text(swift.read_text().replace('app.run()', driver + '\napp.run()'))
    result = subprocess.run([str(python), str(source / 'tools/packaging/package_macos.py'),
        '--python', str(python), '--output', str(output / 'build')], capture_output=True, text=True, timeout=600)
    (output / 'fixture-build.log').write_text(result.stdout + result.stderr)
    result.check_returncode()
    report = json.loads(result.stdout)
    (output / 'old-result.json').write_text(json.dumps(report, indent=2))
    return Path(report['package'])


def stop_owned(root):
    # Only processes whose exact argv contain this unique fixture data directory.
    rows = subprocess.check_output(['/bin/ps', '-ww', '-axo', 'pid=,command='], text=True).splitlines()
    for row in rows:
        fields = row.strip().split(None, 1)
        if len(fields) == 2 and str(root) in fields[1] and any(s in fields[1] for s in ('codex-monitor-mac', 'router-runtime')):
            try: os.kill(int(fields[0]), signal.SIGTERM)
            except ProcessLookupError: pass


def exercise(old_package, new_package, signature, output, scenario, github_release=False, verify_cleanup=False):
    folder = output / scenario; folder.mkdir()
    expanded = folder / 'expanded'
    subprocess.run(['/usr/sbin/pkgutil', '--expand-full', str(old_package), str(expanded)], check=True, capture_output=True, timeout=120)
    old = next(expanded.glob('**/Payload/Applications/' + APP_NAME))
    app = folder / 'Applications' / APP_NAME; app.parent.mkdir(); old.rename(app)
    old_info = app_info(app); version = new_package.name.split('-macos-')[0].removeprefix('codex-model-router-')
    base = f'https://github.com/{REPOSITORY}/releases/download/v{version}/'
    fixture = {'scenario': scenario, 'githubRelease': github_release}
    if not github_release:
        assets = [{'name': new_package.name, 'browser_download_url': base + new_package.name,
               'state': 'uploaded', 'size': new_package.stat().st_size,
               'digest': 'sha256:' + hashlib.sha256(new_package.read_bytes()).hexdigest()},
              {'name': MANIFEST_NAME, 'browser_download_url': base + MANIFEST_NAME,
                   'state': 'uploaded', 'size': signature.stat().st_size}]
        fixture.update(release={'tag_name':'v'+version, 'draft':False, 'prerelease':False, 'assets':assets},
                       files={base + new_package.name:str(new_package), base + MANIFEST_NAME:str(signature)})
    root = folder / 'data'
    resources = app / 'Contents/Resources'
    manifest = json.loads((resources / 'application.json').read_text())
    runtime = app / 'Contents' / manifest['runtime']; env = clean_environment(); env['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'
    subprocess.run([str(runtime), '--data-root', str(root), 'bootstrap'], check=True, capture_output=True, env=env, timeout=30)
    config = root / 'config.local.json'; value = json.loads(config.read_text())
    value.update(enabled=False, updates_auto_check=False, owner_preference='synthetic-settings'); config.write_text(json.dumps(value)); before = config.read_bytes()
    (root / 'state/monitor-ui-mac.json').write_text(json.dumps({'mode':'Hidden'}))
    (root / 'fixture.json').write_text(json.dumps(fixture))
    monitor = subprocess.Popen([str(app / 'Contents/MacOS/codex-monitor-mac'), str(root)], env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    restarted = False; result = {}; job = None
    try:
        deadline = time.monotonic() + (450 if github_release else 150)
        while time.monotonic() < deadline:
            receipt = root / 'state/updates/result.json'
            if receipt.exists():result = json.loads(receipt.read_text())
            jobs = list((root / 'state/updates/jobs').glob('*/operation.json'))
            if jobs:job = jobs[0].parent
            if scenario == 'interrupted' and job and (root / 'fixture-crashed').exists() and not restarted:
                # Replay the real frozen helper just as its recovery plist would;
                # this does not claim a real login/power-loss test.
                helper = job / APP_NAME / 'Contents' / manifest['runtime']
                subprocess.run([str(helper), '--data-root', str(root), 'update-helper', job.name], env=env,
                               check=True, capture_output=True, timeout=90)
                restarted = True
            expected = 'completed' if scenario == 'success' else 'rolled_back'
            if result.get('status') == expected and job and (job / 'ready').exists():break
            if result.get('status') == 'failed':raise AssertionError('Helper failed')
            ui = root / 'fixture-ui.json'
            if ui.exists() and json.loads(ui.read_text()).get('error'):raise AssertionError(json.loads(ui.read_text()))
            time.sleep(.15)
        else:raise AssertionError('Native Settings timeout: ' + json.dumps(result))
        assert monitor.wait(timeout=10) == 0, 'Old host did not exit itself normally'
        events = json.loads((root / 'fixture-ui.json').read_text())['events']
        if github_release:
            assert events == ['Comprobar ahora', 'Actualizar a ' + version], events
            assert hashlib.sha256((job / new_package.name).read_bytes()).digest() == hashlib.sha256(new_package.read_bytes()).digest()
        else:
            assert events.count('Comprobar ahora') == 2 and 'Cancelar' in events and 'cancelled-confirmed' in events, events
        assert config.read_bytes() == before and not (root / 'state/desktop-integration.json').exists()
        assert not list((root / 'fixture-agents').glob('*.plist'))
        assert app_info(app)['CFBundleShortVersionString'] == (version if scenario == 'success' else old_info['CFBundleShortVersionString'])
        if verify_cleanup and scenario == 'success':
            # The new packaged monitor must do this itself, after its helper
            # exits; calling cleanup from this driver would hide integration bugs.
            cleanup_deadline = time.monotonic() + 85
            while time.monotonic() < cleanup_deadline:
                if not (job / APP_NAME).exists():
                    break
                time.sleep(.2)
            assert not (job / APP_NAME).exists(), 'New monitor did not clean the terminal helper'
            assert not (job / 'expanded').exists() and not (job / 'rechecked').exists()
            assert not (job / new_package.name).exists()
            assert len(list(app.parent.glob('.router-previous-*.app'))) == 1
            assert (job / 'operation.json').exists() and config.read_bytes() == before
        return dict(scenario=scenario, passed=True, nativeSettingsButtons=True, cancelledThenRetried=not github_release,
                    signedFrozenHelper=True, automaticOldHostExit=True, newOrRestoredNativeReady=True,
                    preferencesPreserved=True, recoveryHelperReplayed=restarted,
                    localFixtureTransport=not github_release, realGitHubTransport=github_release,
                    downloadedPackageMatches=github_release, ownerInstallationTouched=False, actualLoginTested=False,
                    automaticCleanupVerified=verify_cleanup and scenario == 'success')
    finally:
        stop_owned(root)
        if monitor.poll() is None:monitor.terminate()
        monitor.wait(timeout=10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--signature', type=Path)
    parser.add_argument('--github-release', action='store_true', help='Check/download the real public latest release; no transport replacement')
    parser.add_argument('--verify-cleanup', action='store_true', help='Require the new monitor to prune terminal payloads automatically')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--driver-package', type=Path)
    parser.add_argument('--old-version', default='0.9.6', help='Synthetic installed version, older than the candidate')
    args = parser.parse_args()
    if not args.github_release and args.signature is None:
        parser.error('--signature is required for local fixture transport')
    if args.github_release and args.driver_package:
        parser.error('--github-release builds a fresh driver to exclude local transport hooks')
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    old = args.driver_package.resolve() if args.driver_package else build_driver(output, args.python.absolute(), args.old_version, args.github_release)
    reports = []
    for scenario in (('success',) if args.github_release else ('success', 'rollback', 'interrupted')):
        report = exercise(old, args.package.resolve(), args.signature.resolve() if args.signature else None, output, scenario, args.github_release, args.verify_cleanup)
        reports.append(report); print(json.dumps(report), flush=True)
        (output / 'report.json').write_text(json.dumps(reports, indent=2) + '\n')
