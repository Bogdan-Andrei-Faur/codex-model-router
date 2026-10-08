// Pure display fixtures also cover negative origins and a menu bar on a flat screen.
for origin in [NSPoint.zero,NSPoint(x:-1920,y:240)] {
    let screen=NSRect(origin:origin,size:NSSize(width:1728,height:1117))
    let work=NSRect(x:origin.x,y:origin.y+85,width:1728,height:999)
    let left=NSRect(x:origin.x,y:screen.maxY-32,width:771.5,height:32)
    let right=NSRect(x:origin.x+956.5,y:screen.maxY-32,width:771.5,height:32)
    let camera=NotchPlacement(screen:screen,work:work,inset:32,left:left,right:right)
    assert(camera.frame.maxY==screen.maxY && camera.frame.midX==screen.midX)
    assert(camera.frame.minY==work.minY+20 && camera.cameraWidth==185 && camera.cameraHeight==32)
    let flat=NotchPlacement(screen:screen,work:work,inset:0,left:nil,right:nil)
    assert(flat.frame.maxY==screen.maxY && flat.cameraWidth==0 && flat.cameraHeight==0)
    let hiddenMenu=NotchPlacement(screen:screen,work:screen,inset:0,left:nil,right:nil)
    assert(hiddenMenu.frame.maxY==screen.maxY && hiddenMenu.frame.height==1097)
}
// Append to the monitor's actual RouterPanel/RouterWebView declarations.
// This exercises native dispatch; it does not synthesize OS/global mouse input.
final class ClickProbe: NSObject, WKScriptMessageHandler, WKNavigationDelegate {
    var panel: RouterPanel!, other: RouterPanel!, web: RouterWebView!, clicks=0, initialKey=false
    func begin() {
        let config=WKWebViewConfiguration()
        config.userContentController.add(self,name:"probe")
        web=RouterWebView(frame:.zero,configuration:config);web.navigationDelegate=self
        panel=RouterPanel(contentRect:NSRect(x:20,y:20,width:240,height:100),
            styleMask:[.borderless,.nonactivatingPanel],backing:.buffered,defer:false)
        panel.contentView=web;panel.hidesOnDeactivate=false;panel.acceptsMouseMovedEvents=true
        panel.orderFrontRegardless()
        web.loadHTMLString("<body style='margin:0'><button style='width:240px;height:100px' onclick='webkit.messageHandlers.probe.postMessage(1)'>Synthetic button</button></body>",baseURL:nil)
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        // AppKit may initially choose the only window as key. Establish a
        // controlled non-key starting state, rather than assuming startup focus.
        other=RouterPanel(contentRect:NSRect(x:0,y:0,width:1,height:1),
            styleMask:[.borderless,.nonactivatingPanel],backing:.buffered,defer:false)
        other.alphaValue=0;other.orderFrontRegardless();other.makeKey()
        initialKey=panel.isKeyWindow
        guard !initialKey else {exit(2)}
        // Actual WK descendant receives one native down/up pair while panel
        // starts non-key. A parent-only acceptsFirstMouse override is not assumed.
        for type in [NSEvent.EventType.leftMouseDown,.leftMouseUp] {
            let event=NSEvent.mouseEvent(with:type,location:NSPoint(x:120,y:50),
                modifierFlags:[],timestamp:ProcessInfo.processInfo.systemUptime,
                windowNumber:panel.windowNumber,context:nil,eventNumber:1,clickCount:1,pressure:1)!
            panel.sendEvent(event)
        }
        DispatchQueue.main.asyncAfter(deadline:.now()+0.5) {
            guard self.clicks==1 else {print("FAIL: native click delivery");exit(3)}
            print("PASS: non-key nonactivating panel; one native down/up; exactly one WebKit click")
            self.panel.orderOut(nil);self.other.orderOut(nil);NSApp.terminate(nil)
        }
    }
    func userContentController(_ controller: WKUserContentController,didReceive message: WKScriptMessage) {clicks+=1}
}
let app=NSApplication.shared
app.setActivationPolicy(.accessory)
let probe=ClickProbe();probe.begin()
DispatchQueue.main.asyncAfter(deadline:.now()+10) {exit(4)}
app.run()
