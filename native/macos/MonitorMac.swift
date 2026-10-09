import AppKit
import WebKit
import Security
import CryptoKit
import LocalAuthentication
import Darwin

final class RouterPanel: NSPanel {
    // This accessory deliberately occupies the menu-bar band.
    override func constrainFrameRect(_ frameRect: NSRect, to screen: NSScreen?) -> NSRect { frameRect }
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
    override func sendEvent(_ event: NSEvent) {
        // WebKit's hit view is a descendant. Make this nonactivating panel key
        // before dispatching its first click, rather than swallowing that click.
        if event.type == .leftMouseDown && !isKeyWindow { makeKey() }
        super.sendEvent(event)
    }
}

struct NotchPlacement {
    let frame: NSRect
    let cameraWidth: CGFloat
    let cameraHeight: CGFloat
    init(screen: NSRect, work: NSRect, inset: CGFloat, left: NSRect?, right: NSRect?) {
        let width = min(800,max(1,screen.width-20))
        let height = max(1,screen.maxY-work.minY-20)
        let cutout = inset > 0 && left != nil && right != nil ? max(0,right!.minX-left!.maxX) : 0
        let center = cutout > 0 ? (left!.maxX+right!.minX)/2 : screen.midX
        frame = NSRect(x:min(screen.maxX-width,max(screen.minX,center-width/2)),y:screen.maxY-height,width:width,height:height)
        cameraHeight = max(0,inset)
        cameraWidth = cutout
    }
}

final class RouterWebView: WKWebView {
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
}

// Private JSON-line IPC; no local HTTP endpoint and no stored credentials.
final class MonitorService {
    let root:URL, codeRoot:URL, preview:Bool
    var process:Process?, input:FileHandle?, output:FileHandle?, sequence=0
    init(root:URL, codeRoot:URL, preview:Bool) {self.root=root;self.codeRoot=codeRoot;self.preview=preview}
    func stop() { if let child=process,child.isRunning {child.terminate()};try? input?.close();try? output?.close();process=nil;input=nil;output=nil }
    deinit {stop()}
    func request(_ body:[String:Any]) throws -> [String:Any] {
        if process?.isRunning != true {
            stop()
            let child=Process(),incoming=Pipe(),outgoing=Pipe()
            let configURL=root.appendingPathComponent("config.local.json")
            let config=(try? Data(contentsOf:configURL)).flatMap{try? JSONSerialization.jsonObject(with:$0) as? [String:Any]} ?? [:]
            if Bundle.main.object(forInfoDictionaryKey:"RouterPackaged") as? Bool == true {
                child.executableURL=Bundle.main.bundleURL.appendingPathComponent("Contents/Helpers/RouterRuntime.app/Contents/MacOS/router-runtime")
                child.arguments=["--data-root",root.path,"monitor-service"]+(preview ? ["--preview"] : [])
            } else {
                child.executableURL=URL(fileURLWithPath:config["python"] as? String ?? "/usr/bin/python3")
                child.arguments=["-u",codeRoot.appendingPathComponent("monitor_service.py").path,"--root",root.path,"--code-root",codeRoot.path,"--platform","macos"]+(preview ? ["--preview"] : [])
            }
            child.standardInput=incoming;child.standardOutput=outgoing;child.standardError=FileHandle.nullDevice
            try child.run();process=child;input=incoming.fileHandleForWriting;output=outgoing.fileHandleForReading
        }
        guard let child=process,let input=input,let output=output else {throw CocoaError(.fileReadUnknown)}
        sequence = sequence >= 2147483646 ? 1 : sequence+1
        var request=body;request["requestId"]=sequence
        var bytes=try JSONSerialization.data(withJSONObject:request);bytes.append(10)
        guard bytes.count<=65536 else {throw CocoaError(.fileWriteUnknown)}
        let watchdog=DispatchWorkItem{if child.isRunning {child.terminate()}}
        DispatchQueue.global(qos:.utility).asyncAfter(deadline:.now()+(body["action"] as? String == "connection" ? 110 : 15),execute:watchdog)
        defer {watchdog.cancel()}
        do {
            try input.write(contentsOf:bytes)
            var response=Data()
            while response.last != 10 {
                let chunk=output.availableData
                guard !chunk.isEmpty,response.count+chunk.count<=64*1024*1024+1 else {throw CocoaError(.fileReadCorruptFile)}
                response.append(chunk)
            }
            guard let reply=try JSONSerialization.jsonObject(with:response) as? [String:Any],reply["requestId"] as? Int == sequence else {throw CocoaError(.fileReadCorruptFile)}
            return reply
        } catch {stop();throw error}
    }
}

// Native lifecycle and storage, with a local-only WebKit presentation surface.
final class Monitor: NSObject, NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate {
    let root: URL
    var state: URL { root.appendingPathComponent("state") }
    var configPath: URL { root.appendingPathComponent("config.local.json") }
    var restartPath: URL { state.appendingPathComponent("restart-required.json") }
    let productVersion: String = Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "sin identificar"
    let productBuildId: String = Bundle.main.object(forInfoDictionaryKey:"RouterBuildId") as? String ?? ""
    let routerBuildId: String = Bundle.main.object(forInfoDictionaryKey:"RouterEngineBuildId") as? String ?? ""
    var uiPath: URL { state.appendingPathComponent("monitor-ui-mac.json") }
    let resources = Bundle.main.resourceURL!.appendingPathComponent("ui")
    var service: String {
        let stored=read(state.appendingPathComponent("credential-namespace.json"))["namespace"] as? String
        let namespace=(stored?.range(of:"^[0-9a-f]{64}$",options:.regularExpression) != nil ? stored! : SHA256.hash(data:Data(root.path.utf8)).map{String(format:"%02x",$0)}.joined())
        return "local.codex-model-router." + namespace
    }
    var preview: Bool { CommandLine.arguments.contains("--preview") }
    var panel: RouterPanel!, web: WKWebView!, status: NSStatusItem!
    let glass = NSVisualEffectView(frame:.zero)
    var mode = "Compact", topmost = true, ready = false, busy = false, refreshPending = false
    var panelHeights = [String:Double](), resizing = false, historyRequested = false
    var panelHeight: Double = 760
    var cameraWidth: CGFloat = 0, cameraHeight: CGFloat = 0
    var lockFD: Int32 = -1
    var timer: Timer?, hitTimer: Timer?
    var hitRect = NSRect.zero
    var lastPayload = Data(), sentJournalRevision = -1
    lazy var dataService = MonitorService(root:root,codeRoot:codeRoot,preview:preview)
    var codeRoot:URL {
        if Bundle.main.object(forInfoDictionaryKey:"RouterPackaged") as? Bool == true {return Bundle.main.resourceURL!}
        return URL(fileURLWithPath:ProcessInfo.processInfo.environment["PERSONAL_CODEX_MONITOR_CODE_ROOT"] ?? Bundle.main.object(forInfoDictionaryKey:"RouterCodeRoot") as? String ?? root.path)
    }
    var lastPointer: NSPoint?, lastModeRequest: Int?
    var pointerDirty = true
    var keys = ["jev-typesafe": false, "jev-vercel": false]
    let io = DispatchQueue(label:"local.codex-model-router.monitor-data",qos:.utility)
    init(root: URL) { self.root = root.standardizedFileURL.resolvingSymlinksInPath(); super.init() }
    func read(_ path: URL) -> [String: Any] {
        guard let data = try? Data(contentsOf:path), let result = try? JSONSerialization.jsonObject(with:data) as? [String: Any] else { return [:] }; return result
    }
    func write(_ value: [String: Any], _ path: URL) throws {
        try JSONSerialization.data(withJSONObject:value,options:[.prettyPrinted,.sortedKeys]).write(to:path,options:.atomic)
        try FileManager.default.setAttributes([.posixPermissions:0o600],ofItemAtPath:path.path)
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        if !preparePackagedData() { NSApp.terminate(nil); return }
        do { try FileManager.default.createDirectory(at:state,withIntermediateDirectories:true) } catch { NSApp.terminate(nil); return }
        lockFD = Darwin.open(state.appendingPathComponent("monitor-mac.lock").path,O_CREAT|O_RDWR,0o600)
        guard lockFD >= 0, flock(lockFD,LOCK_EX|LOCK_NB) == 0 else { NSApp.terminate(nil); return }
        let saved = read(uiPath)
        if let value = saved["mode"] as? String, ["Compact","Expanded","Hidden"].contains(value) { mode = value }
        topmost = saved["topmost"] as? Bool ?? true
        panelHeights = (saved["panelHeights"] as? [String:Double] ?? [:]).filter { $0.value.isFinite && $0.value > 0 && $0.value <= 1 }
        let configuration = WKWebViewConfiguration(); configuration.websiteDataStore = .nonPersistent()
        configuration.userContentController.add(self,name:"monitor")
        web = RouterWebView(frame:.zero,configuration:configuration); web.navigationDelegate = self
        web.setValue(false,forKey:"drawsBackground"); web.underPageBackgroundColor = .clear
        panel = RouterPanel(contentRect:.zero,styleMask:[.borderless,.nonactivatingPanel],backing:.buffered,defer:false)
        panel.title = "Codex automático · Monitor · v" + productVersion; panel.isOpaque = false; panel.backgroundColor = .clear; panel.hasShadow = false
        panel.acceptsMouseMovedEvents = true
        panel.hidesOnDeactivate = false; panel.isReleasedWhenClosed = false
        panel.collectionBehavior = [.canJoinAllSpaces,.fullScreenAuxiliary]
        let content = NSView(frame:.zero)
        glass.material = .hudWindow; glass.blendingMode = .behindWindow; glass.state = .active
        glass.wantsLayer = true; glass.layer?.cornerRadius = 26; glass.layer?.masksToBounds = true
        glass.isHidden = true
        web.autoresizingMask = [.width,.height]
        content.addSubview(glass);content.addSubview(web);panel.contentView = content
        panel.level = topmost ? .statusBar : .normal; position()
        status = NSStatusBar.system.statusItem(withLength:NSStatusItem.squareLength)
        let trayImage = NSImage(contentsOf:resources.appendingPathComponent("tray-route.png"))
        trayImage?.size = NSSize(width:18,height:18);trayImage?.isTemplate = true
        status.button?.image = trayImage;status.button?.setAccessibilityLabel("Codex automático")
        status.button?.target = self; status.button?.action = #selector(statusClick)
        status.button?.sendAction(on:[.leftMouseUp,.rightMouseUp])
        if !preview { for key in ["jev-typesafe", "jev-vercel"] { keys[key] = hasKey(key) } }
        loadPage()
        timer = Timer.scheduledTimer(timeInterval:2,target:self,selector:#selector(refresh),userInfo:nil,repeats:true)
        hitTimer = Timer(timeInterval:1.0/30,repeats:true) { [weak self] _ in self?.updateHit() }
        RunLoop.main.add(hitTimer!,forMode:.common)
        NotificationCenter.default.addObserver(self,selector:#selector(displayChanged),name:NSApplication.didChangeScreenParametersNotification,object:nil)
        NSWorkspace.shared.notificationCenter.addObserver(self,selector:#selector(displayChanged),name:NSWorkspace.accessibilityDisplayOptionsDidChangeNotification,object:nil)
    }
    func preparePackagedData() -> Bool {
        guard Bundle.main.object(forInfoDictionaryKey:"RouterPackaged") as? Bool == true,
              !preview, !FileManager.default.fileExists(atPath:configPath.path) else { return true }
        while true {
            let welcome=NSAlert()
            welcome.messageText="Bienvenido a Codex Model Router"
            welcome.informativeText="Puedes importar tus ajustes, personajes, historial y referencias a las claves. Para importar, termina las tareas y cierra Codex y el monitor anterior. La carpeta original se conserva."
            welcome.addButton(withTitle:"Importar instalación…")
            welcome.addButton(withTitle:"Empezar de cero")
            welcome.addButton(withTitle:"Cancelar")
            let answer=welcome.runModal()
            if answer == .alertThirdButtonReturn { return false }
            var arguments=["--data-root",root.path]
            if answer == .alertFirstButtonReturn {
                let picker=NSOpenPanel();picker.canChooseDirectories=true;picker.canChooseFiles=false;picker.allowsMultipleSelection=false
                picker.message="Selecciona la carpeta de la instalación anterior que contiene config.local.json."
                guard picker.runModal() == .OK, let source=picker.url else { continue }
                arguments += ["import-legacy",source.path]
            } else { arguments += ["bootstrap"] }
            let child=Process(),pipe=Pipe()
            child.executableURL=Bundle.main.bundleURL.appendingPathComponent("Contents/Helpers/RouterRuntime.app/Contents/MacOS/router-runtime")
            child.arguments=arguments;child.standardOutput=pipe;child.standardError=FileHandle.nullDevice
            do {
                try child.run()
                let data=pipe.fileHandleForReading.readDataToEndOfFile();child.waitUntilExit()
                if child.terminationStatus == 0 { return true }
                let result=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any]
                let error=result?["error"] as? [String:Any]
                let messages=["occupied_destination":"El destino ya contiene datos. No se importará encima de ellos.",
                              "active_bridge":"Codex sigue usando la instalación anterior. Ciérralo cuando terminen tus tareas.",
                              "busy_source":"El monitor anterior sigue abierto o hay datos en uso.",
                              "missing_config":"La carpeta elegida no contiene config.local.json.",
                              "foreign_platform":"Elige una instalación de este mismo Mac."]
                let alert=NSAlert();alert.messageText="No se pudo preparar la instalación"
                alert.informativeText=messages[error?["code"] as? String ?? ""] ?? "La instalación original y tus datos se han conservado."
                alert.runModal()
            } catch {
                let alert=NSAlert();alert.messageText="No se pudo iniciar la preparación";alert.informativeText="Tus datos se han conservado.";alert.runModal()
            }
        }
    }
    func loadPage() { sentJournalRevision = -1; ready = false; web.loadFileURL(resources.appendingPathComponent("index.html"),allowingReadAccessTo:resources) }
    func position() {
        let screen = panel.screen ?? NSScreen.screens.first { NSMouseInRect(NSEvent.mouseLocation,$0.frame,false) } ?? NSScreen.main
        guard let screen = screen else { return }
        let placement = NotchPlacement(screen:screen.frame,work:screen.visibleFrame,inset:screen.safeAreaInsets.top,left:screen.auxiliaryTopLeftArea,right:screen.auxiliaryTopRightArea)
        cameraWidth = placement.cameraWidth; cameraHeight = placement.cameraHeight
        panelHeight = min(placement.frame.height,max(560,screen.visibleFrame.height * (panelHeights[screenKey(screen)] ?? 0.9)))
        panel.setFrame(placement.frame,display:true)
    }
    func screenKey(_ screen:NSScreen?) -> String {
        return String(describing:screen?.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] ?? "main")
    }
    func resizePanel(_ height:Double?, finished:Bool) {
        guard mode == "Expanded",let screen = panel.screen else {return}
        if let height = height, height.isFinite {
            let work = screen.visibleFrame
            panelHeight = min(max(1,work.height-20),max(560,height))
            panelHeights[screenKey(screen)] = panelHeight/work.height
        } else if height == nil {
            panelHeights.removeValue(forKey:screenKey(screen)); position()
        }
        if finished {saveUI()}
        lastPayload = Data(); refresh()
    }
    @objc func displayChanged() { position(); updateGlass(); publishUI(); lastPayload = Data(); refresh() }
    func updateGlass() {
        // Keep the legacy material view hidden; the shared notch owns its shape.
        glass.frame = hitRect
        glass.isHidden = true // The shared notch is intentionally opaque.
    }
    func updateHit() {
        guard mode != "Hidden" else { return }
        if resizing {panel.ignoresMouseEvents = false; return}
        let pointInPanel = panel.convertPoint(fromScreen:NSEvent.mouseLocation)
        let y = hitRect.maxY-pointInPanel.y
        let shoulder = min(20,hitRect.width/2), radius = min(32,max(0,(hitRect.width-2*shoulder)/2),hitRect.height/2)
        var inset = shoulder
        if y < shoulder {inset = sqrt(max(0,shoulder*shoulder-pow(shoulder-y,2)))}
        if y > hitRect.height-radius {inset += radius-sqrt(max(0,radius*radius-pow(y-hitRect.height+radius,2)))}
        let camera = NSRect(x:(panel.frame.width-cameraWidth)/2,y:panel.frame.height-cameraHeight,width:cameraWidth,height:cameraHeight)
        let inside = !camera.contains(pointInPanel) && hitRect.contains(pointInPanel) && pointInPanel.x >= hitRect.minX+inset && pointInPanel.x <= hitRect.maxX-inset
        if panel.ignoresMouseEvents == inside { panel.ignoresMouseEvents = !inside }
        // Project local pointer geometry even while key: clipped windows can
        // miss DOM leave events. This never activates or keys the panel.
        let point = panel.convertPoint(fromScreen:NSEvent.mouseLocation)
        let projected = inside ? NSPoint(x:round(point.x),y:round(panel.frame.height-point.y)) : nil
        if ready && (projected != lastPointer || pointerDirty) {
            lastPointer=projected;pointerDirty=false
            let value:Any = projected.map { ["x":$0.x,"y":$0.y] } ?? NSNull()
            if ready { web.callAsyncJavaScript("window.monitorPointer(point,inactive)",arguments:["point":value,"inactive":true],in:nil,in:.page,completionHandler:nil) }
        }
    }
    @objc func statusClick() {
        if NSApp.currentEvent?.type == .rightMouseUp { showMenu() }
        else { setMode(mode == "Hidden" ? "Compact" : mode == "Compact" ? "Expanded" : "Compact") }
    }
    func showMenu() {
        let menu = NSMenu(); let title = menu.addItem(withTitle:"Codex automático",action:nil,keyEquivalent:""); title.isEnabled = false; menu.addItem(.separator())
        for (label,key) in [("Vista compacta","Compact"),("Desplegar isla","Expanded"),("Ocultar monitor","Hidden")] {
            let item = menu.addItem(withTitle:label,action:#selector(menuMode(_:)),keyEquivalent:""); item.target = self; item.representedObject = key; item.state = mode == key ? .on : .off
        }
        menu.addItem(.separator())
        let enabled = read(configPath)["enabled"] as? Bool ?? false
        let pause = menu.addItem(withTitle:enabled ? "Pausar selección" : "Activar selección",action:#selector(togglePause),keyEquivalent:""); pause.target = self
        let pin = menu.addItem(withTitle:"Mantener delante · " + (topmost ? "Activado" : "Desactivado"),action:#selector(toggleTopmost),keyEquivalent:""); pin.target = self; pin.state = topmost ? .on : .off
        menu.addItem(.separator()); let quit = menu.addItem(withTitle:"Salir del monitor",action:#selector(quitMonitor),keyEquivalent:""); quit.target = self
        status.menu = menu; status.button?.performClick(nil); status.menu = nil
    }
    @objc func menuMode(_ sender:NSMenuItem) { if let value = sender.representedObject as? String { setMode(value) } }
    @objc func togglePause() { configure("enabled",!(read(configPath)["enabled"] as? Bool ?? false)) }
    @objc func toggleTopmost() { setTopmost(!topmost) }
    @objc func quitMonitor() { NSApp.terminate(nil) }
    func setMode(_ value:String) {
        guard ["Compact","Expanded","Hidden"].contains(value) else { return }; mode = value
        if value == "Hidden" { panel.orderOut(nil) } else { position(); panel.orderFrontRegardless() }
        updateGlass();publishUI(); saveUI(); lastPayload = Data(); refresh()
    }
    func uiSnapshot() -> [String:Any] {
        return ["mode":mode,"topmost":topmost,"panelHeight":panelHeight,"cameraWidth":cameraWidth,"cameraHeight":cameraHeight,"reduced":NSWorkspace.shared.accessibilityDisplayShouldReduceMotion,"reduceTransparency":NSWorkspace.shared.accessibilityDisplayShouldReduceTransparency,"nativeGlass":true,"acknowledgesMode":true,"lazyHistory":true,"modeRequest":lastModeRequest as Any? ?? NSNull()]
    }
    func publishUI() {
        guard ready else {return}
        web.callAsyncJavaScript("window.receiveUI(ui,request)",arguments:["ui":uiSnapshot(),"request":lastModeRequest as Any? ?? NSNull()],in:nil,in:.page,completionHandler:nil)
    }
    func setTopmost(_ value:Bool) { topmost = value; panel.level = value ? .statusBar : .normal; saveUI(); lastPayload = Data(); refresh() }
    func saveUI() { if preview {return}; do { try write(["mode":mode,"topmost":topmost,"panelHeights":panelHeights],uiPath) } catch { feedback("No se pudo guardar la vista.") } }
    func feedback(_ value:String) { web.callAsyncJavaScript("window.monitorFeedback(message)",arguments:["message":value],in:nil,in:.page,completionHandler:nil) }
    func webView(_ webView:WKWebView,decidePolicyFor action:WKNavigationAction,decisionHandler:@escaping(WKNavigationActionPolicy)->Void) {
        decisionHandler(action.request.url?.standardizedFileURL == resources.appendingPathComponent("index.html").standardizedFileURL ? .allow : .cancel)
    }
    func webViewWebContentProcessDidTerminate(_ webView:WKWebView) { loadPage() }
    func userContentController(_ controller:WKUserContentController,didReceive message:WKScriptMessage) {
        guard message.frameInfo.isMainFrame, message.frameInfo.request.url?.standardizedFileURL == resources.appendingPathComponent("index.html").standardizedFileURL,
              let data = message.body as? [String:Any], let action = data["action"] as? String else { return }
        switch action {
        case "ready":
            ready = true; lastPayload = Data(); refresh(); if mode != "Hidden" { panel.orderFrontRegardless() }
        case "bounds":
            if let x = data["x"] as? Double, let y = data["y"] as? Double, let width = data["width"] as? Double, let height = data["height"] as? Double,
               x.isFinite,y.isFinite,width.isFinite,height.isFinite {
                hitRect = NSRect(x:x,y:panel.frame.height-y-height,width:max(0,width),height:max(0,height)).intersection(NSRect(origin:.zero,size:panel.frame.size)); pointerDirty=true;updateGlass();updateHit()
            }
        case "mode": if let value = data["value"] as? String { lastModeRequest=data["request"] as? Int; setMode(value) }
        case "history":
            if let requested=data["value"] as? Bool, requested != historyRequested {
                historyRequested=requested;lastPayload=Data();refresh()
            }
        case "resizeStart": resizing = true
        case "resizeEnd": resizing = false; resizePanel(data["height"] as? Double,finished:true)
        case "resizeReset": resizePanel(nil,finished:true)
        case "topmost": if let value = data["value"] as? Bool { setTopmost(value) }
        case "config", "quality", "taskMode", "connection", "update", "appearance": performAction(data)
        case "secret": if let provider = data["provider"] as? String, ["jev-typesafe", "jev-vercel"].contains(provider), let value = data["value"] as? String, !value.isEmpty,value.utf8.count<16384 { storeKey(provider,value) }
        default: break
        }
    }
    var actionBusy=false
    func performAction(_ data:[String:Any]) {
        guard !preview,!actionBusy else {feedback("Vista previa o una operación todavía en curso."); appearanceResult(data,false);return}
        actionBusy=true
        io.async { [weak self] in
            guard let self=self else{return}
            let reply=try? self.dataService.request(data)
            DispatchQueue.main.async {
                self.actionBusy=false;self.lastPayload=Data();self.appearanceResult(data,reply?["ok"] as? Bool == true)
                self.feedback(reply?["feedback"] as? String ?? "No se pudo completar la operación. Tus tareas siguen abiertas.")
                self.refresh()
            }
        }
    }
    func appearanceResult(_ data:[String:Any],_ ok:Bool) {
        guard data["action"] as? String == "appearance" else {return}
        let result:[String:Any] = ["thread":data["thread"] as Any? ?? NSNull(),"request":data["request"] as Any? ?? NSNull(),"ok":ok]
        web.callAsyncJavaScript("window.monitorAppearanceResult(result)",arguments:["result":result],in:nil,in:.page,completionHandler:nil)
    }
    func configure(_ key:String,_ value:Any) {performAction(["action":"config","key":key,"value":value])}
    func applicationWillTerminate(_ notification:Notification) {timer?.invalidate();hitTimer?.invalidate();dataService.stop();if lockFD>=0 {Darwin.close(lockFD)}}
    func keyQuery(_ provider:String)->[String:Any] { [kSecClass as String:kSecClassGenericPassword,kSecAttrService as String:service,kSecAttrAccount as String:provider] }
    func markKeyChanged(_ provider:String) throws {
        let path=state.appendingPathComponent("keychain-revision.json")
        var revisions=read(path);revisions[provider]=UUID().uuidString
        try write(revisions,path)
    }
    func hasKey(_ provider:String)->Bool {
        let context=LAContext();context.interactionNotAllowed=true
        var query=keyQuery(provider);query[kSecReturnAttributes as String]=true;query[kSecMatchLimit as String]=kSecMatchLimitOne;query[kSecUseAuthenticationContext as String]=context
        return SecItemCopyMatching(query as CFDictionary,nil)==errSecSuccess
    }
    func storeKey(_ provider:String,_ value:String) {
        guard !preview else {feedback("Las claves están desactivadas en la vista previa.");return}
        let query=keyQuery(provider),attributes=[kSecValueData as String:Data(value.utf8)]
        var result=SecItemUpdate(query as CFDictionary,attributes as CFDictionary)
        if result==errSecItemNotFound {var item=query;item.merge(attributes){_,new in new};result=SecItemAdd(item as CFDictionary,nil)}
        guard result==errSecSuccess else {feedback("No se pudo guardar la clave en el llavero.");return}
        do {try markKeyChanged(provider)} catch {feedback("Clave guardada. Reinicia Codex para aplicarla.");return}
        keys[provider]=true;lastPayload=Data();refresh();feedback("Clave guardada en el llavero.")
    }
    @objc func refresh() {
        guard ready else{return}
        guard !busy else{refreshPending=true;return};busy=true
        let needsHistory = mode == "Expanded" && historyRequested, sentRevision = sentJournalRevision
        io.async { [weak self] in
            guard let self=self else{return}
            let reply=try? self.dataService.request(["action":"snapshot","history":needsHistory,"revision":sentRevision])
            let snapshot = reply?["ok"] as? Bool == true ? reply?["payload"] as? [String:Any] : nil
            DispatchQueue.main.async {
                self.busy=false
                defer {if self.refreshPending {self.refreshPending=false;self.refresh()}}
                guard var payload=snapshot else {self.feedback(reply?["feedback"] as? String ?? "No se pudo leer el estado. Se conserva la última vista.");return}
                if let updates=payload["updates"] as? [String:Any], updates["shutdownForUpdate"] as? Bool == true,
                   Bundle.main.object(forInfoDictionaryKey:"RouterPackaged") as? Bool == true, !self.preview {
                    NSApp.terminate(nil); return
                }
                let deliverHistory=payload["history"] != nil && self.mode == "Expanded" && self.historyRequested
                if !deliverHistory {payload.removeValue(forKey:"history")}
                payload["historyLoaded"]=self.sentJournalRevision >= 0 || deliverHistory
                payload["keys"]=self.keys;payload["ui"]=self.uiSnapshot()
                var comparison=payload;comparison.removeValue(forKey:"history")
                guard let encoded=try? JSONSerialization.data(withJSONObject:comparison,options:[.sortedKeys]),encoded != self.lastPayload || deliverHistory else{return}
                self.lastPayload=encoded
                let revision=payload["journalRevision"] as? Int ?? -1
                self.web.callAsyncJavaScript("window.receive(payload)",arguments:["payload":payload],in:nil,in:.page){ result in
                    if case .failure=result {self.lastPayload=Data();self.sentJournalRevision = -1}
                    else {
                        if deliverHistory {self.sentJournalRevision=revision}
                        if let argument=CommandLine.arguments.first(where:{$0.hasPrefix("--update-ready=")}) {
                            let token=String(argument.dropFirst("--update-ready=".count))
                            if token.range(of:"^[0-9a-f]{32}$",options:.regularExpression) != nil {
                                let path=self.state.appendingPathComponent("updates/jobs/"+token+"/ready")
                                if FileManager.default.fileExists(atPath:path.deletingLastPathComponent().appendingPathComponent("operation.json").path) {
                                    try? Data("ready".utf8).write(to:path,options:.atomic)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

}
let app=NSApplication.shared
app.setActivationPolicy(.accessory)
let defaultRoot: String
if Bundle.main.object(forInfoDictionaryKey:"RouterPackaged") as? Bool == true {
    defaultRoot=ProcessInfo.processInfo.environment["PERSONAL_CODEX_ROUTER_ROOT"] ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/codex-model-router").path
} else {defaultRoot=Bundle.main.bundleURL.deletingLastPathComponent().deletingLastPathComponent().path}
let delegate=Monitor(root:URL(fileURLWithPath:CommandLine.arguments.dropFirst().first(where:{!$0.hasPrefix("--")}) ?? defaultRoot))
app.delegate=delegate
app.run()
