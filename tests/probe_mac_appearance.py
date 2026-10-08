"""Real WebKit -> AppKit -> private Python IPC -> disk -> acknowledgement.

Owned temporary root and synthetic agent only; no Desktop/global input/provider.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = (ROOT/'MonitorMac.swift').read_text().rsplit('let app=NSApplication.shared', 1)[0]
    harness = r'''
let app=NSApplication.shared
app.setActivationPolicy(.accessory)
let monitor=Monitor(root:URL(fileURLWithPath:CommandLine.arguments[1]))
app.delegate=monitor
var phase=0,checking=false
let timer=Timer.scheduledTimer(withTimeInterval:0.1,repeats:true){ timer in
    guard monitor.ready,!monitor.hitRect.isEmpty else{return}
    if phase==0 {
        phase=1;monitor.setMode("Expanded")
        monitor.web.callAsyncJavaScript("""
            window.monitorPointer=()=>{};
            window.receive({connections:1,preview:false,readOnly:false,threads:{fixture:{name:'Synthetic agent',status:'active'}},agentThreads:{fixture:{name:'Synthetic agent',status:'active'}}});
            showTab('activity');openAppearance('fixture');
            const name=document.querySelector('[data-appearance-field=name]');
            name.value='Native fixture';name.dispatchEvent(new Event('input',{bubbles:true}));
            document.querySelector('.appearance-categories button:nth-child(4)').click();
            document.querySelector('[data-appearance-choice=cap]').click();
            document.querySelector('.appearance-categories button:nth-child(2)').click();
            document.querySelector('[data-appearance-choice=overalls]').click();
            saveAppearance('fixture');return true;
            """,arguments:[:],in:nil,in:.page){ result in
                if case .failure=result {exit(3)}
            }
    }
    let stored=monitor.read(monitor.state.appendingPathComponent("agent-appearances.json"))
    if phase==1,!checking,let agents=stored["agents"] as? [String:[String:Any]],let look=agents["fixture"],look["name"] as? String=="Native fixture" {
        assert(look["head"] as? String=="cap");assert(look["outfit"] as? String=="overalls");assert(agents.count==1)
        checking=true
        monitor.web.evaluateJavaScript("!document.querySelector('.appearance-editor') && document.querySelector('.agent-identity-copy .companion-alias')?.textContent==='Native fixture'"){ value,error in
            checking=false
            if value as? Bool==true {timer.invalidate();print("PASS: isolated native appearance save and acknowledgement");app.terminate(nil)}
        }
    }
}
DispatchQueue.main.asyncAfter(deadline:.now()+15){print("FAIL: native appearance timeout");exit(4)}
app.run()
'''
    with tempfile.TemporaryDirectory(prefix='router-native-appearance-') as folder:
        base=Path(folder);contents=base/'Probe.app/Contents';binary=contents/'MacOS/probe'
        binary.parent.mkdir(parents=True)
        ui=contents/'Resources/ui';shutil.copytree(ROOT/'monitor-ui',ui)
        shutil.copyfile(ROOT/'assets/codex-ui-1024.png',ui/'codex.png')
        root=base/'fixture';(root/'state').mkdir(parents=True)
        (root/'config.local.json').write_text(json.dumps({'updates_auto_check':False}))
        (root/'state/status-fixture.json').write_text(json.dumps({'pid':os.getpid(),'heartbeat':time.time(),'client_name':'fixture','threads':{'fixture':{'name':'Synthetic agent','status':'active'}},'agent_threads':{'fixture':{'name':'Synthetic agent','status':'active'}}}))
        swift=base/'main.swift';swift.write_text(source+harness)
        subprocess.run(['xcrun','swiftc',str(swift),'-o',str(binary),'-framework','AppKit','-framework','WebKit','-framework','Security'],check=True,timeout=90)
        result=subprocess.run([str(binary),str(root)],capture_output=True,text=True,timeout=25,env=dict(os.environ,PERSONAL_CODEX_MONITOR_CODE_ROOT=str(ROOT)))
        print(json.dumps({'native_appearance_exit':result.returncode,'isolated_fixture':True,'owner_data_modified':False}))
        if result.returncode:print(result.stdout.strip())
        raise SystemExit(result.returncode)


if __name__=='__main__':main()
