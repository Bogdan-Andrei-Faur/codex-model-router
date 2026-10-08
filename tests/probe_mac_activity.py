"""Isolated AppKit/WebKit activity styles; synthetic events, never owner data."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != 'darwin':
        print('SKIP: requires macOS AppKit/WebKit'); return
    source = (ROOT / 'MonitorMac.swift').read_text().split('let app=NSApplication.shared')[0]
    harness = r'''
let app=NSApplication.shared
app.setActivationPolicy(.accessory)
let monitor=Monitor(root:URL(fileURLWithPath:CommandLine.arguments[1]))
app.delegate=monitor
var checked=false
let timer=Timer.scheduledTimer(withTimeInterval:0.1,repeats:true){timer in
    guard monitor.ready,!checked else{return}
    checked=true
    monitor.panel.level = .normal
    monitor.setMode("Expanded")
    monitor.web.callAsyncJavaScript("""
      window.monitorPointer=()=>{};
      const names=['thinking','writing','planning','executing','editing','searching','tool','collaborating','inspecting','generating','reviewing','compacting','approval','question','retrying','error','interrupted','done'];
      for(const kind of names){
        window.receive({connections:1,ui:{mode:'Expanded',reduced:false},threads:{fixture:{name:'Synthetic agent',status:'active',turn_id:'synthetic',activity:{version:1,source:'native',turn_id:'synthetic',kind,attention:kind==='approval'?['approval']:kind==='question'?['input']:[],observed_at:Date.now()/1000}}}});
        const pet=document.querySelector('.hero-character');
        if(pet?.dataset.state!==kind)throw Error('pose: '+kind);
        const target=pet.querySelector(kind==='collaborating'?'.hand-right':'.character-body');
        if(getComputedStyle(target).animationName==='none')throw Error('animation: '+kind);
        if(['approval','question'].includes(kind)&&pet.querySelector('.character-attention').hidden)throw Error('attention: '+kind);
      }
      window.receive({ui:{reduced:true}});
      if(getComputedStyle(document.querySelector('.hero-character .character-body')).animationName!=='none')throw Error('reduced motion');
      return names.length;
    """,arguments:[:],in:nil,in:.page){result in
        switch result{
          case .success(let value):
            guard (value as? Int)==18 else{print("FAIL: incomplete native activity check");exit(3)}
            timer.invalidate();print("PASS: isolated WebKit18 observed pose styles, attention and reduced motion");app.terminate(nil)
          case .failure(let error):print("FAIL: native activity JS \(error)");exit(3)
        }
    }
}
DispatchQueue.main.asyncAfter(deadline:.now()+15){print("FAIL: native activity timeout");exit(4)}
app.run()
'''
    with tempfile.TemporaryDirectory(prefix='router-native-activity-') as folder:
        base = Path(folder); contents = base / 'Probe.app/Contents'
        binary = contents / 'MacOS/probe'; binary.parent.mkdir(parents=True)
        ui = contents / 'Resources/ui'; shutil.copytree(ROOT / 'monitor-ui', ui)
        shutil.copyfile(ROOT / 'assets/codex-ui-1024.png', ui / 'codex.png')
        root = base / 'fixture'; (root / 'state').mkdir(parents=True)
        (root / 'config.local.json').write_text(json.dumps({'updates_auto_check': False}))
        swift = base / 'main.swift'; swift.write_text(source + harness)
        subprocess.run(['xcrun', 'swiftc', str(swift), '-o', str(binary), '-framework', 'AppKit',
                        '-framework', 'WebKit', '-framework', 'Security'], check=True, timeout=90)
        result = subprocess.run([str(binary), str(root)], capture_output=True, text=True, timeout=25,
                                env=dict(os.environ, PERSONAL_CODEX_MONITOR_CODE_ROOT=str(ROOT)))
        print(json.dumps({'native_activity_exit': result.returncode, 'synthetic_fixture': True,
                          'owner_data_modified': False, 'real_desktop_events': False}))
        print(result.stdout.strip())
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
