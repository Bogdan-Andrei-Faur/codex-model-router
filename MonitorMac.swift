import AppKit
import WebKit
import Security
import CryptoKit
import LocalAuthentication
import Darwin

final class RouterPanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
}

// Native lifecycle and storage, with a local-only WebKit presentation surface.
final class Monitor: NSObject, NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate {
    let root: URL
    var state: URL { root.appendingPathComponent("state") }
    var configPath: URL { root.appendingPathComponent("config.local.json") }
    let productVersion: String = Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "sin identificar"
    let productBuildId: String = Bundle.main.object(forInfoDictionaryKey:"RouterBuildId") as? String ?? ""
    var uiPath: URL { state.appendingPathComponent("monitor-ui-mac.json") }
    let resources = Bundle.main.resourceURL!.appendingPathComponent("ui")
    var service: String { "local.codex-model-router." + SHA256.hash(data: Data(root.path.utf8)).map { String(format:"%02x",$0) }.joined() }
    var preview: Bool { CommandLine.arguments.contains("--preview") }
    var panel: RouterPanel!, web: WKWebView!, status: NSStatusItem!
    var mode = "Compact", topmost = true, ready = false, busy = false
    var panelHeights = [String:Double](), resizing = false
    var panelHeight: Double = 760
    var lockFD: Int32 = -1
    var timer: Timer?, hitTimer: Timer?
    var hitRect = NSRect.zero
    var lastPayload = Data(), journal = [[String: Any]](), journalSignature = ""
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
        do { try FileManager.default.createDirectory(at:state,withIntermediateDirectories:true) } catch { NSApp.terminate(nil); return }
        lockFD = Darwin.open(state.appendingPathComponent("monitor-mac.lock").path,O_CREAT|O_RDWR,0o600)
        guard lockFD >= 0, flock(lockFD,LOCK_EX|LOCK_NB) == 0 else { NSApp.terminate(nil); return }
        let saved = read(uiPath)
        if let value = saved["mode"] as? String, ["Compact","Expanded","Hidden"].contains(value) { mode = value }
        topmost = saved["topmost"] as? Bool ?? true
        panelHeights = (saved["panelHeights"] as? [String:Double] ?? [:]).filter { $0.value.isFinite && $0.value > 0 && $0.value <= 1 }
        let configuration = WKWebViewConfiguration(); configuration.websiteDataStore = .nonPersistent()
        configuration.userContentController.add(self,name:"monitor")
        web = WKWebView(frame:.zero,configuration:configuration); web.navigationDelegate = self
        web.setValue(false,forKey:"drawsBackground"); web.underPageBackgroundColor = .clear
        panel = RouterPanel(contentRect:.zero,styleMask:[.borderless,.nonactivatingPanel],backing:.buffered,defer:false)
        panel.title = "Codex automático · Monitor · v" + productVersion; panel.isOpaque = false; panel.backgroundColor = .clear; panel.hasShadow = false
        panel.hidesOnDeactivate = false; panel.isReleasedWhenClosed = false
        panel.collectionBehavior = [.canJoinAllSpaces,.fullScreenAuxiliary]; panel.contentView = web
        panel.level = topmost ? .floating : .normal; position()
        status = NSStatusBar.system.statusItem(withLength:NSStatusItem.squareLength)
        status.button?.image = NSImage(systemSymbolName:"circle.hexagongrid.fill",accessibilityDescription:"Codex automático")
        status.button?.target = self; status.button?.action = #selector(statusClick)
        status.button?.sendAction(on:[.leftMouseUp,.rightMouseUp])
        if !preview { for key in ["jev-typesafe", "jev-vercel"] { keys[key] = hasKey(key) } }
        loadPage()
        timer = Timer.scheduledTimer(timeInterval:2,target:self,selector:#selector(refresh),userInfo:nil,repeats:true)
        hitTimer = Timer.scheduledTimer(withTimeInterval:1.0/30,repeats:true) { [weak self] _ in self?.updateHit() }
        NotificationCenter.default.addObserver(self,selector:#selector(displayChanged),name:NSApplication.didChangeScreenParametersNotification,object:nil)
        NSWorkspace.shared.notificationCenter.addObserver(self,selector:#selector(displayChanged),name:NSWorkspace.accessibilityDisplayOptionsDidChangeNotification,object:nil)
    }
    func loadPage() { journalSignature = ""; ready = false; web.loadFileURL(resources.appendingPathComponent("index.html"),allowingReadAccessTo:resources) }
    func position() {
        let screen = panel.screen ?? NSScreen.screens.first { NSMouseInRect(NSEvent.mouseLocation,$0.frame,false) } ?? NSScreen.main
        guard let work = screen?.visibleFrame else { return }
        let width = min(432,max(1,work.width-20)), height = max(1,work.height-20)
        panelHeight = min(height,max(560,work.height * (panelHeights[screenKey(screen)] ?? 0.9)))
        panel.setFrame(NSRect(x:work.maxX-width-10,y:work.minY+10,width:width,height:height),display:true)
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
    @objc func displayChanged() { position(); lastPayload = Data(); refresh() }
    func updateHit() {
        guard mode != "Hidden" else { return }
        if resizing {panel.ignoresMouseEvents = false; return}
        let inside = NSBezierPath(roundedRect:hitRect,xRadius:26,yRadius:26).contains(panel.convertPoint(fromScreen:NSEvent.mouseLocation))
        if panel.ignoresMouseEvents == inside { panel.ignoresMouseEvents = !inside }
    }
    @objc func statusClick() {
        if NSApp.currentEvent?.type == .rightMouseUp { showMenu() }
        else { setMode(mode == "Hidden" ? "Compact" : mode == "Compact" ? "Expanded" : "Compact") }
    }
    func showMenu() {
        let menu = NSMenu(); let title = menu.addItem(withTitle:"Codex automático",action:nil,keyEquivalent:""); title.isEnabled = false; menu.addItem(.separator())
        for (label,key) in [("Vista compacta","Compact"),("Panel lateral","Expanded"),("Ocultar monitor","Hidden")] {
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
        saveUI(); lastPayload = Data(); refresh()
    }
    func setTopmost(_ value:Bool) { topmost = value; panel.level = value ? .floating : .normal; saveUI(); lastPayload = Data(); refresh() }
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
        case "ready": ready = true; lastPayload = Data(); refresh(); if mode != "Hidden" { panel.orderFrontRegardless() }
        case "bounds":
            if let x = data["x"] as? Double, let y = data["y"] as? Double, let width = data["width"] as? Double, let height = data["height"] as? Double,
               x.isFinite,y.isFinite,width.isFinite,height.isFinite {
                hitRect = NSRect(x:x,y:panel.frame.height-y-height,width:max(0,width),height:max(0,height)).intersection(NSRect(origin:.zero,size:panel.frame.size)); updateHit()
            }
        case "mode": if let value = data["value"] as? String { setMode(value) }
        case "resizeStart": resizing = true
        case "resizeEnd": resizing = false; resizePanel(data["height"] as? Double,finished:true)
        case "resizeReset": resizePanel(nil,finished:true)
        case "topmost": if let value = data["value"] as? Bool { setTopmost(value) }
        case "config": if let key = data["key"] as? String, let value = data["value"] { configure(key,value) }
        case "quality": saveQuality(data)
        case "taskMode": if let id=data["thread"] as? String,let mode=data["value"] as? String { setTaskMode(id,mode) }
        case "connection": if let value = data["value"] as? String, ["doctor","install","uninstall"].contains(value) { manageConnection(value) }
        case "secret": if let provider = data["provider"] as? String, ["jev-typesafe", "jev-vercel"].contains(provider), let value = data["value"] as? String, !value.isEmpty,value.utf8.count<16384 { storeKey(provider,value) }
        default: break
        }
    }
    func taskModePath(_ id:String)->URL {
        let key=SHA256.hash(data:Data(id.utf8)).map{String(format:"%02x",$0)}.joined()
        return state.appendingPathComponent("task-modes").appendingPathComponent(key+".json")
    }
    func taskMode(_ id:String)->String {
        let path=taskModePath(id)
        if !FileManager.default.fileExists(atPath:path.path) {return "automatic"}
        let data=read(path)
        return data["thread"] as? String == id && data["mode"] as? String == "automatic" ? "automatic" : "manual"
    }
    func setTaskMode(_ id:String,_ mode:String) {
        guard !preview,!id.isEmpty,id.count<=200,["automatic","manual"].contains(mode) else{return}
        do {
            let path=taskModePath(id)
            try FileManager.default.createDirectory(at:path.deletingLastPathComponent(),withIntermediateDirectories:true)
            try write(["schema":1,"thread":id,"mode":mode],path)
            lastPayload=Data();refresh();feedback("Modo guardado para el próximo mensaje de esta tarea.")
        } catch {feedback("No se pudo guardar el modo de esta tarea.")}
    }
    var connectionBusy = false
    func manageConnection(_ action:String) {
        guard !preview,!connectionBusy,let python=read(configPath)["python"] as? String else {return}
        connectionBusy=true;feedback("Comprobando conexión…")
        DispatchQueue.global(qos:.utility).async {
            let process=Process(),pipe=Pipe()
            process.executableURL=URL(fileURLWithPath:python)
            process.arguments=[self.root.appendingPathComponent("desktop.py").path,action]
            process.standardOutput=pipe;process.standardError=pipe
            var message="No se pudo completar la conexión. Tus tareas siguen abiertas."
            do {
                try process.run()
                let output=pipe.fileHandleForReading.readDataToEndOfFile();process.waitUntilExit()
                if let data=(try? JSONSerialization.jsonObject(with:output)) as? [String:Any] {
                    if let error=data["error"] as? String {message=error}
                    else if let detail=data["message"] as? String {message=detail}
                    else if data["connection"] as? String == "desktop_connected" {message="Desktop conectado al selector."}
                    else if data["connection"] as? String == "bridge_observed" {message="Hay un puente activo; falta confirmar la conexión de Desktop."}
                    else if data["registered"] as? Bool == true {message="Conexión instalada. Falta observar el nuevo arranque de Desktop."}
                    else {message="Desktop detectado. El inicio habitual todavía no está conectado."}
                }
            } catch {}
            DispatchQueue.main.async {self.connectionBusy=false;self.feedback(message);self.refresh()}
        }
    }
    func configure(_ key:String,_ value:Any) {
        var valid = false
        switch key {
        case "enabled": valid = CFGetTypeID(value as CFTypeRef) == CFBooleanGetTypeID()
        case "inference_telemetry": valid = CFGetTypeID(value as CFTypeRef) == CFBooleanGetTypeID()
        case "history_days": valid = [0,30,90,180].contains(value as? Int ?? -1)
        case "routing_engine": valid = ["rules","jev"].contains(value as? String ?? "")
        case "comparison_engines": if let values = value as? [String] { valid = values.count<=2 && Set(values).count==values.count && values.allSatisfy { ["rules","jev"].contains($0) } }
        case "jev.connection": valid = ["vercel","typesafe"].contains(value as? String ?? "")
        default: break
        }
        guard valid else { feedback("Ajuste no válido."); return }
        var config = read(configPath); guard !config.isEmpty else { feedback("No se pudo leer la configuración."); return }
        let parts = key.split(separator:".").map(String.init)
        if parts.count==2 { var nested = config[parts[0]] as? [String:Any] ?? [:]; nested[parts[1]]=value; config[parts[0]]=nested }
        else { config[key]=value }
        do { try write(config,configPath); refresh() } catch { feedback("No se pudo guardar el ajuste.") }
    }
    func saveQuality(_ data:[String:Any]) {
        guard let id = data["id"] as? String,let quality = data["value"] as? String,["","insufficient","adequate","excessive"].contains(quality),journal.contains(where:{$0["decision_id"] as? String == id}) else { feedback("Decisión no disponible.");return }
        let aspect=data["aspect"] as? String ?? "overall",field=aspect == "model" ? "model_quality" : aspect == "effort" ? "effort_quality" : "quality"
        let record:[String:Any] = ["schema":2,"event":"decision_quality","decision_id":id,field:quality,"time":Date().timeIntervalSince1970,"time_iso":ISO8601DateFormatter().string(from:Date())]
        guard var bytes = try? JSONSerialization.data(withJSONObject:record) else {return};bytes.append(10)
        let gate = Darwin.open(state.appendingPathComponent("history.lock").path,O_RDWR|O_CREAT,0o600)
        guard gate>=0 else {feedback("No se pudo guardar la valoración.");return}
        guard flock(gate,LOCK_EX|LOCK_NB)==0 else {Darwin.close(gate);feedback("Historial ocupado. Reintenta la valoración.");return}
        defer {flock(gate,LOCK_UN);Darwin.close(gate)}
        let fd = Darwin.open(state.appendingPathComponent("history.jsonl").path,O_WRONLY|O_CREAT|O_APPEND,0o600)
        guard fd>=0 else {feedback("No se pudo guardar la valoración.");return}
        let count = bytes.withUnsafeBytes {Darwin.write(fd,$0.baseAddress,$0.count)};Darwin.close(fd)
        if count != bytes.count {feedback("No se pudo guardar la valoración.")} else {refresh()}
    }
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
        guard ready,!busy else{return};busy=true
        io.async { [weak self] in
            guard let self=self else{return}
            let config=self.read(self.configPath)
            var rows=[String:Any](),connections=0
            var bridgeVersions=Set<String>()
            var bridgeBuildMismatch=false
            var telemetry=[String:Any](dictionaryLiteral:("enabled",false))
            let files=(try? FileManager.default.contentsOfDirectory(at:self.state,includingPropertiesForKeys:nil)) ?? []
            for file in files.sorted(by:{$0.lastPathComponent<$1.lastPathComponent}) where file.lastPathComponent.hasPrefix("status-") && file.pathExtension=="json" {
                let data=self.read(file)
                if data["client_name"] as? String == "other" {continue}
                guard let heartbeat=data["heartbeat"] as? Double,abs(Date().timeIntervalSince1970-heartbeat)<12,let pid=data["pid"] as? Int32,kill(pid,0)==0,let threads=data["threads"] as? [String:[String:Any]] else{continue}
                connections+=1
                bridgeVersions.insert(data["product_version"] as? String ?? "desconocida")
                if let build=data["build_id"] as? String,!self.productBuildId.isEmpty,build != self.productBuildId {bridgeBuildMismatch=true}
                if let health=data["telemetry"] as? [String:Any] {
                    telemetry["enabled"] = (telemetry["enabled"] as? Bool ?? false) || (health["enabled"] as? Bool ?? false)
                    for key in ["requests","records_scanned","eligible_records","events_without_model","unrecognized_records","invalid_requests","unexpected_path"] { telemetry[key]=(telemetry[key] as? Double ?? 0)+(health[key] as? Double ?? 0) }
                    if let stats=data["stats"] as? [String:Any] { for key in ["telemetry_events","telemetry_confirmed","telemetry_probable","telemetry_unattributed"] { telemetry[key]=(telemetry[key] as? Double ?? 0)+(stats[key] as? Double ?? 0) } }
                }
                for (id,row) in threads {let old=rows[id] as? [String:Any] ?? [:];if (row["updated"] as? Double ?? 0)>=(old["updated"] as? Double ?? 0){rows[id]=row}}
            }
            if self.preview { let fixture=self.read(self.root.appendingPathComponent("preview.json"));rows=fixture["threads"] as? [String:Any] ?? [:];connections=1 }
            let paths=["history.jsonl","history.recovered.jsonl"].map{self.state.appendingPathComponent($0)}
            let signature=paths.map{path->String in let info=try? path.resourceValues(forKeys:[.contentModificationDateKey,.fileSizeKey]);return "\(info?.contentModificationDate?.timeIntervalSince1970 ?? 0):\(info?.fileSize ?? 0)"}.joined(separator:"|")
            var records:[[String:Any]]?
            if signature != self.journalSignature {
                records=paths.flatMap{path->[[String:Any]] in guard let text=try? String(contentsOf:path,encoding:.utf8) else{return []};return text.split(separator:"\n").compactMap{(try? JSONSerialization.jsonObject(with:Data($0.utf8))) as? [String:Any]}}
                self.journalSignature=signature
            }
            let currentJournal=records ?? self.journal
            let ids=Set(rows.keys).union(currentJournal.compactMap{$0["thread"] as? String})
            let taskModes=Dictionary(uniqueKeysWithValues:ids.map{($0,self.taskMode($0))})
            DispatchQueue.main.async {
                self.busy=false;if let records=records{self.journal=records}
                let safeConfig=config.filter{["enabled","inference_telemetry","history_days","routing_engine","comparison_engines","jev","routes"].contains($0.key)}
                var payload:[String:Any]=["productVersion":self.productVersion,"bridgeVersions":Array(bridgeVersions).sorted(),"bridgeBuildMismatch":bridgeBuildMismatch,"threads":rows,"connections":connections,"config":safeConfig,"taskModes":taskModes,"keys":self.keys,"telemetry":telemetry,"preview":self.preview,"ui":["mode":self.mode,"topmost":self.topmost,"panelHeight":self.panelHeight,"reduced":NSWorkspace.shared.accessibilityDisplayShouldReduceMotion]]
                if records != nil {payload["history"]=self.journal}
                guard let encoded=try? JSONSerialization.data(withJSONObject:payload,options:[.sortedKeys]),encoded != self.lastPayload else{return}
                self.lastPayload=encoded
                self.web.callAsyncJavaScript("window.receive(payload)",arguments:["payload":payload],in:nil,in:.page){ result in if case .failure=result {self.lastPayload=Data()} }
            }
        }
    }
}
let app=NSApplication.shared
app.setActivationPolicy(.accessory)
let defaultRoot=Bundle.main.bundleURL.deletingLastPathComponent().deletingLastPathComponent().path
let delegate=Monitor(root:URL(fileURLWithPath:CommandLine.arguments.dropFirst().first ?? defaultRoot))
app.delegate=delegate
app.run()
