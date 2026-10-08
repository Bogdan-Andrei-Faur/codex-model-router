"""Opaque notch lifecycle in an isolated preview bundle, with safe fixtures.

The historical script/capture names remain compatible; desktop blur is hidden.
"""
import json
import os
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture-dir', type=Path, help='Optional safe synthetic-backdrop window captures')
    args = parser.parse_args()
    source = (ROOT / 'native/macos/MonitorMac.swift').read_text().rsplit('let app=NSApplication.shared', 1)[0]
    harness = r'''
let app=NSApplication.shared
app.setActivationPolicy(.accessory)
final class Backdrop: NSView {
    var alternate=false
    override func draw(_ dirtyRect:NSRect) {
        (alternate ? NSColor.systemOrange : NSColor.systemTeal).setFill();bounds.fill()
        (alternate ? NSColor.systemBlue : NSColor.systemPink).setFill()
        NSRect(x:bounds.midX,y:0,width:bounds.width/2,height:bounds.height).fill()
    }
}
let backdrop=NSWindow(contentRect:.zero,styleMask:.borderless,backing:.buffered,defer:false)
let pattern=Backdrop(frame:.zero);backdrop.contentView=pattern
backdrop.level=NSWindow.Level(rawValue:NSWindow.Level.floating.rawValue+1)
backdrop.isOpaque=true;backdrop.ignoresMouseEvents=true;backdrop.isReleasedWhenClosed=false
func capture(_ name:String) {
    guard CommandLine.arguments.count>3,CGPreflightScreenCaptureAccess() else{return}
    let process=Process();process.executableURL=URL(fileURLWithPath:"/usr/sbin/screencapture")
    // Capture the compositor's safe fixture rectangle. Window-only captures
    // can omit the backdrop sampled by a behind-window material.
    let frame=monitor.panel.frame
    let screenTop=NSScreen.screens.first!.frame.maxY
    let rect="\(Int(frame.minX)),\(Int(screenTop-frame.maxY)),\(Int(frame.width)),\(Int(frame.height))"
    process.arguments=["-x","-R",rect,CommandLine.arguments[3]+"/"+name+".png"]
    process.standardOutput=FileHandle.nullDevice;process.standardError=FileHandle.nullDevice
    try? process.run();process.waitUntilExit()
}
let monitor=Monitor(root:URL(fileURLWithPath:CommandLine.arguments[1]))
app.delegate=monitor
var phase=0
let timer=Timer.scheduledTimer(withTimeInterval:0.1,repeats:true) { timer in
    guard monitor.ready,!monitor.hitRect.isEmpty else {return}
    if phase==0 {
        assert(monitor.panel.frame.maxY==monitor.panel.screen!.frame.maxY,"Island detached from screen edge")
        assert(monitor.panel.level == .statusBar,"Island hidden behind menu bar")
        assert(monitor.cameraHeight==monitor.panel.screen!.safeAreaInsets.top)
        assert(monitor.web.bounds.width>0 && monitor.web.bounds.height>0,"Web view did not resize with container")
        assert(monitor.status.button?.image?.isTemplate==true,"Lucide tray template missing")
        assert(monitor.glass.frame==monitor.hitRect,"Glass escaped the interactive surface")
        assert(monitor.glass.blendingMode == .behindWindow && monitor.glass.material == .hudWindow)
        assert(monitor.glass.isHidden,"Opaque notch must keep legacy material hidden")
        monitor.panel.level=NSWindow.Level(rawValue:NSWindow.Level.floating.rawValue+2)
        backdrop.setFrame(monitor.panel.frame,display:true);backdrop.orderFrontRegardless();monitor.panel.orderFrontRegardless()
        // Synthetic lifecycle, not physical hover: ignore the owner's pointer.
        phase=1
        monitor.web.callAsyncJavaScript("""
            window.monitorPointer=()=>{};
            window.receiveUI(ui,null);
            await new Promise(resolve=>setTimeout(resolve,500));
            const left=(innerWidth-ui.cameraWidth)/2,right=(innerWidth+ui.cameraWidth)/2;
            return [...document.querySelectorAll('.capsule-bar button')].every(node=>{
                const r=node.getBoundingClientRect();
                return !r.width || !ui.cameraWidth || r.right<=left || r.left>=right || r.top>=ui.cameraHeight;
            });
            """,arguments:["ui":monitor.uiSnapshot()],in:nil,in:.page) { result in
            guard case .success(let value)=result,value as? Bool==true else {exit(3)}
            monitor.setMode("Expanded")
        }
        return
    }
    if phase==1 && monitor.hitRect.height>200 {
        assert(monitor.glass.frame==monitor.hitRect)
        phase=2
        monitor.web.evaluateJavaScript("JSON.stringify({rows:document.querySelectorAll('.task-row').length,heroes:document.querySelectorAll('.companion-hero').length,title:document.querySelector('#view-title').textContent,glass:document.body.classList.contains('native-glass'),topNav:!document.body.classList.contains('camera-nav')||document.querySelector('nav').getBoundingClientRect().top<10})") { value,error in
            guard error==nil,let text=value as? String,let data=text.data(using:.utf8),let result=try? JSONSerialization.jsonObject(with:data) as? [String:Any],result["rows"] as? Int==0,result["heroes"] as? Int==1,result["title"] as? String=="Inicio",result["glass"] as? Bool==true,result["topNav"] as? Bool==true else {exit(3)}
            timer.invalidate()
            monitor.web.evaluateJavaScript("window.receiveUI({reduced:true},null)",completionHandler:nil)
            DispatchQueue.main.asyncAfter(deadline:.now()+0.5) {
                capture("native-glass-backdrop-a")
                pattern.alternate=true;pattern.needsDisplay=true
                DispatchQueue.main.asyncAfter(deadline:.now()+0.5) {
                    capture("native-glass-backdrop-b")
                    monitor.setMode("Hidden");assert(monitor.glass.isHidden);backdrop.orderOut(nil)
                    print("PASS: real isolated AppKit/WebKit lifecycle, resizing, opaque notch, Home principal without inactive rows and hide")
                    app.terminate(nil)
                }
            }
        }
    }
}
DispatchQueue.main.asyncAfter(deadline:.now()+15){
    print("fixture_phase=\(phase) ready=\(monitor.ready) native_mode=\(monitor.mode) hit_height=\(monitor.hitRect.height) panel=\(monitor.panel.frame) web=\(monitor.web.frame)")
    monitor.web.evaluateJavaScript("JSON.stringify({fixtureErrors:window.fixtureErrors||[],icons:typeof RouterIcons,receive:typeof window.receive,uiMode:state.ui.mode,body:document.body.className,viewport:[innerWidth,innerHeight],surface:document.querySelector('#surface').getBoundingClientRect().toJSON(),reported:window.fixtureBounds||null})") { value,error in
        print(value as? String ?? "Fixture JavaScript unavailable");exit(4)
    }
}
app.run()
'''
    with tempfile.TemporaryDirectory(prefix='router-glass-probe-') as folder:
        base = Path(folder)
        contents = base / 'Probe.app' / 'Contents'
        binary = contents / 'MacOS' / 'probe'
        binary.parent.mkdir(parents=True)
        ui = contents / 'Resources' / 'ui'
        shutil.copytree(ROOT / 'monitor-ui', ui)
        shutil.copyfile(ROOT / 'assets/codex-ui-1024.png', ui / 'codex.png')
        script=ui/'monitor.js'
        script.write_text(script.read_text().replace("native({action:'bounds',x:r.x", "window.fixtureBounds={x:r.x,y:r.y,width:r.width,height:r.height};native({action:'bounds',x:r.x"))
        (ui / 'probe-errors.js').write_text("window.fixtureErrors=[];window.addEventListener('error',e=>window.fixtureErrors.push(e.message));\n")
        index = ui / 'index.html'
        index.write_text(index.read_text().replace('<script src="icons.js">', '<script src="probe-errors.js"></script><script src="icons.js">'))
        fixture = base / 'fixture'
        fixture.mkdir()
        (fixture / 'preview.json').write_text(json.dumps({'threads': {
            'synthetic': {'name': 'Synthetic fixture', 'status': 'active', 'model': 'gpt-6.1-sol', 'effort': 'high'},
            'idle': {'name': 'Inactive fixture', 'status': 'idle'}}}))
        swift = base / 'main.swift'
        swift.write_text(source + harness)
        subprocess.run(['xcrun', 'swiftc', str(swift), '-o', str(binary), '-framework', 'AppKit',
                        '-framework', 'WebKit', '-framework', 'Security'], check=True, timeout=90)
        command = [str(binary), str(fixture), '--preview']
        if args.capture_dir:
            args.capture_dir.mkdir(parents=True, exist_ok=True)
            command.append(str(args.capture_dir.resolve()))
        result = subprocess.run(command, capture_output=True, text=True, timeout=25,
                                env=dict(os.environ, PERSONAL_CODEX_MONITOR_CODE_ROOT=str(ROOT)))
        if result.returncode:
            print(result.stdout.strip())
        print(json.dumps({'native_glass_fixture_exit': result.returncode, 'isolated_preview': True,
                          'safe_backdrop_captures': bool(args.capture_dir and (args.capture_dir / 'native-glass-backdrop-b.png').exists()),
                          'live_owner_visual_acceptance': False}))
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
