// Windows owns the window/tray/DPAPI only. monitor-ui and Python own the product.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Threading;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.Wpf;
using Forms = System.Windows.Forms;

sealed class MonitorPipe : IDisposable
{
    readonly string root, codeRoot;
    readonly bool preview;
    readonly object gate = new object();
    readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = 64 * 1024 * 1024 };
    Process child;
    int sequence;
    public MonitorPipe(string root, string codeRoot, bool preview) { this.root=root; this.codeRoot=codeRoot; this.preview=preview; }
    internal static string Quote(string value)
    {
        // Windows CommandLineToArgvW quoting, including trailing backslashes.
        var result = new StringBuilder("\""); int slashes=0;
        foreach (char c in value) {
            if (c=='\\') { slashes++; continue; }
            result.Append('\\', c=='"' ? slashes*2+1 : slashes); result.Append(c); slashes=0;
        }
        result.Append('\\', slashes*2); return result.Append('"').ToString();
    }
    public Dictionary<string,object> Request(Dictionary<string,object> request)
    {
        lock(gate) {
            if(child==null || child.HasExited) {
                Stop();
                var config=RouterMonitorWindow.Read(Path.Combine(root,"config.local.json"));
                string frozen=RouterMonitorWindow.Text(config,"monitor_runtime","");
                if(String.IsNullOrEmpty(frozen) && File.Exists(Path.Combine(codeRoot,"bin","codex-monitor-core.exe"))) frozen=Path.Combine("bin","codex-monitor-core.exe");
                string program=String.IsNullOrEmpty(frozen) ? RouterMonitorWindow.Text(config,"python","python.exe") : Path.GetFullPath(Path.Combine(codeRoot,frozen));
                string arguments=(String.IsNullOrEmpty(frozen) ? "-u "+Quote(Path.Combine(codeRoot,"monitor_service.py"))+" " : "")+
                    "--root "+Quote(root)+" --code-root "+Quote(codeRoot)+" --platform windows"+(preview ? " --preview" : "");
                if(WindowsLayout.Installed(codeRoot)) {
                    program=WindowsLayout.Component(codeRoot,"runtime");
                    arguments="--data-root "+Quote(root)+" monitor-service"+(preview?" --preview":"");
                }
                child=new Process { StartInfo=new ProcessStartInfo(program,arguments) {
                    WorkingDirectory=codeRoot,UseShellExecute=false,CreateNoWindow=true,RedirectStandardInput=true,
                    RedirectStandardOutput=true,RedirectStandardError=true,StandardOutputEncoding=Encoding.UTF8 } };
                // Drain without logging or forwarding private diagnostics.
                child.ErrorDataReceived += delegate { };
                child.Start(); child.BeginErrorReadLine();
            }
            sequence=sequence>=2147483646 ? 1 : sequence+1; request["requestId"]=sequence;
            string encoded=json.Serialize(request);
            if(Encoding.UTF8.GetByteCount(encoded)+1>65536) throw new InvalidDataException();
            var current=child;
            using(var watchdog=new System.Threading.Timer(delegate { try { if(!current.HasExited)current.Kill(); }catch{} },null,
                RouterMonitorWindow.Text(request,"action","")=="connection" ? 110000 : 15000,Timeout.Infinite)) {
                try {
                    child.StandardInput.WriteLine(encoded); child.StandardInput.Flush();
                    // Bound the response before JSON parsing; do not log pipe content.
                    var response=new StringBuilder(); int c;
                    while((c=child.StandardOutput.Read())>=0 && c!='\n') {
                        if(response.Length>=64*1024*1024)throw new InvalidDataException();
                        response.Append((char)c);
                    }
                    if(c<0)throw new EndOfStreamException();
                    var reply=json.Deserialize<Dictionary<string,object>>(response.ToString());
                    if(!reply.ContainsKey("requestId") || Convert.ToInt32(reply["requestId"])!=sequence)throw new InvalidDataException();
                    return reply;
                }catch{Stop();throw;}
            }
        }
    }
    void Stop() { if(child!=null){try{if(!child.HasExited)child.Kill();}catch{} child.Dispose();child=null;} }
    public void Dispose() { lock(gate){Stop();} }
}

sealed class RouterMonitorWindow : Window
{
    const string Origin="https://monitor.local/", Page=Origin+"index.html";
    internal static JavaScriptSerializer Json {get{return new JavaScriptSerializer { MaxJsonLength=64*1024*1024 };}}
    readonly string root, codeRoot;
    readonly bool preview, selfTest;
    readonly MonitorPipe service;
    readonly EventWaitHandle reveal;
    readonly WebView2CompositionControl web=new WebView2CompositionControl();
    readonly Dictionary<string,bool> keys=new Dictionary<string,bool> {{"jev-typesafe",false},{"jev-vercel",false}};
    readonly Dictionary<string,double> heights=new Dictionary<string,double>();
    readonly DispatcherTimer poll=new DispatcherTimer(), pointer=new DispatcherTimer();
    Forms.NotifyIcon tray;
    HwndSource source;
    Rect hit=Rect.Empty;
    string mode="Compact", lastSnapshot="";
    bool ready, busy, actionBusy, pending, quitting, testStarted;
    int journalRevision=-1;
    bool historyRequested;
    object modeRequest=null;
    double panelHeight=760;
    Point? previousPointer;
    bool previousActive;
    string UiPath {get{return Path.Combine(root,"state","monitor-ui.json");}}
    string ProbeDirectory {get{return Path.Combine(WindowsLayout.Installed(codeRoot)?root:codeRoot,"state");}}
    public RouterMonitorWindow(string root,string codeRoot,bool preview,bool selfTest,EventWaitHandle reveal,bool hidden)
    {
        this.root=root;this.codeRoot=codeRoot;this.preview=preview;this.selfTest=selfTest;this.reveal=reveal;
        service=new MonitorPipe(root,codeRoot,preview);
        Title="Codex automático";WindowStyle=WindowStyle.None;ResizeMode=ResizeMode.NoResize;AllowsTransparency=true;
        Background=Brushes.Transparent;ShowInTaskbar=false;Topmost=true;Content=web;
        web.DefaultBackgroundColor=System.Drawing.Color.Transparent;
        var saved=Read(UiPath);string savedMode=Text(saved,"mode","Compact");
        if(new[]{"Compact","Expanded","Hidden"}.Contains(savedMode))mode=savedMode;
        if(saved.ContainsKey("topmost") && saved["topmost"] is bool)Topmost=(bool)saved["topmost"];
        foreach(var item in Dict(Get(saved,"panelHeights"))) {double value=Numeric(item.Value);if(value>0&&value<=1)heights[item.Key]=value;}
        if(hidden)mode="Hidden";
        if(!preview)foreach(string provider in keys.Keys.ToArray())keys[provider]=File.Exists(Path.Combine(root,"state",provider+".secret"));
        SourceInitialized += delegate {source=HwndSource.FromHwnd(new WindowInteropHelper(this).Handle);source.AddHook(Hook);};
        Loaded += async delegate {await Initialize();};
        Closing += delegate(object sender,System.ComponentModel.CancelEventArgs e){if(!quitting&&!preview){e.Cancel=true;SetMode("Hidden");}};
        Closed += delegate {poll.Stop();pointer.Stop();if(tray!=null)tray.Dispose();web.Dispose();Task.Run((Action)service.Dispose);};
        poll.Interval=TimeSpan.FromSeconds(2);poll.Tick += delegate {if(reveal!=null&&reveal.WaitOne(0)){SetMode(mode=="Hidden"?"Compact":mode);Activate();}Refresh();};
        pointer.Interval=TimeSpan.FromSeconds(1.0/30);pointer.Tick += delegate {UpdatePointer();};
        Position();
    }
    internal static Dictionary<string,object> Read(string path) {try{return Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(path,Encoding.UTF8))??new Dictionary<string,object>();}catch{return new Dictionary<string,object>();}}
    internal static object Get(Dictionary<string,object> data,string key){object value;return data.TryGetValue(key,out value)?value:null;}
    internal static Dictionary<string,object> Dict(object value){return value as Dictionary<string,object>??new Dictionary<string,object>();}
    internal static string Text(Dictionary<string,object> data,string key,string fallback){return Get(data,key) as string??fallback;}
    static double Numeric(object value){try{double number=Convert.ToDouble(value);return Double.IsNaN(number)||Double.IsInfinity(number)?0:number;}catch{return 0;}}
    static void Atomic(string path,byte[] bytes){Directory.CreateDirectory(Path.GetDirectoryName(path));string temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";File.WriteAllBytes(temp,bytes);if(File.Exists(path))File.Replace(temp,path,null);else File.Move(temp,path);}
    async Task Initialize()
    {
        try {
            var environment=await CoreWebView2Environment.CreateAsync(null,Path.Combine(root,"state","monitor-webview2"));
            var options=environment.CreateCoreWebView2ControllerOptions();options.IsInPrivateModeEnabled=true;
            await web.EnsureCoreWebView2Async(environment,options);
            var core=web.CoreWebView2;
            core.Settings.AreDevToolsEnabled=false;core.Settings.AreDefaultContextMenusEnabled=false;core.Settings.AreHostObjectsAllowed=false;
            core.Settings.IsStatusBarEnabled=false;core.Settings.IsPasswordAutosaveEnabled=false;core.Settings.IsGeneralAutofillEnabled=false;
            core.SetVirtualHostNameToFolderMapping("monitor.local",WindowsLayout.Installed(codeRoot)?Path.Combine(codeRoot,"ui"):Path.Combine(codeRoot,"dist","windows-ui"),CoreWebView2HostResourceAccessKind.DenyCors);
            core.NavigationStarting += delegate(object sender,CoreWebView2NavigationStartingEventArgs e){if(e.Uri!=Page)e.Cancel=true;};
            core.FrameNavigationStarting += delegate(object sender,CoreWebView2NavigationStartingEventArgs e){e.Cancel=true;};
            core.NewWindowRequested += delegate(object sender,CoreWebView2NewWindowRequestedEventArgs e){e.Handled=true;};
            core.PermissionRequested += delegate(object sender,CoreWebView2PermissionRequestedEventArgs e){e.State=CoreWebView2PermissionState.Deny;};
            core.DownloadStarting += delegate(object sender,CoreWebView2DownloadStartingEventArgs e){e.Cancel=true;};
            core.AddWebResourceRequestedFilter("*",CoreWebView2WebResourceContext.All);
            core.WebResourceRequested += delegate(object sender,CoreWebView2WebResourceRequestedEventArgs e){
                Uri uri; bool valid=Uri.TryCreate(e.Request.Uri,UriKind.Absolute,out uri)&&uri.Scheme=="https"&&uri.Host=="monitor.local"&&uri.Port==443&&String.IsNullOrEmpty(uri.Query)&&String.IsNullOrEmpty(uri.UserInfo);
                string[] assets={"/index.html","/monitor.css","/icons.js","/core.js","/characters.js","/monitor.js","/codex.png","/fonts/Nunito-variable.ttf"};
                if(!valid||!assets.Contains(uri.AbsolutePath))e.Response=environment.CreateWebResourceResponse(new MemoryStream(),403,"Blocked","");
            };
            core.WebMessageReceived += delegate(object sender,CoreWebView2WebMessageReceivedEventArgs e){
                if(e.Source!=Page||e.WebMessageAsJson.Length>20000)return;
                try{var data=Json.Deserialize<Dictionary<string,object>>(e.WebMessageAsJson);if(data!=null)Action(data);}catch{Feedback("No se pudo procesar la acción.");}
            };
            core.ProcessFailed += delegate {ready=false;lastSnapshot="";journalRevision=-1;try{core.Reload();}catch{if(selfTest)FinishTest(false,"WebView2 process unavailable.");else{MessageBox.Show("La interfaz se ha detenido. Vuelve a abrir el monitor; tus tareas siguen abiertas.","Codex automático");Quit();}}};
            MakeTray();core.Navigate(Page);poll.Start();pointer.Start();if(mode=="Hidden")Hide();
        }catch{
            if(selfTest){FinishTest(false,"WebView2 initialization failed; install Evergreen runtime.");return;}
            MessageBox.Show("No se pudo iniciar la interfaz. Instala Microsoft Edge WebView2 Runtime (Evergreen) y vuelve a abrir el monitor.","Codex automático");
            Quit();
        }
    }
    void MakeTray()
    {
        if(preview)return;
        tray=new Forms.NotifyIcon {Icon=new System.Drawing.Icon(Path.Combine(codeRoot,"assets","brand","router.ico")),Text="Codex automático",Visible=true};
        var menu=new Forms.ContextMenuStrip();
        menu.Items.Add("Cápsula",null,delegate{SetMode("Compact");});menu.Items.Add("Desplegar isla",null,delegate{SetMode("Expanded");});
        menu.Items.Add("Ocultar",null,delegate{SetMode("Hidden");});menu.Items.Add("Mantener delante",null,delegate{Topmost=!Topmost;SaveUi();PublishUi();});
        menu.Items.Add("Pausar / reanudar selector",null,delegate{var config=Read(Path.Combine(root,"config.local.json"));Perform(new Dictionary<string,object>{{"action","config"},{"key","enabled"},{"value",!(Get(config,"enabled") as bool? ?? true)}});});
        menu.Items.Add("Salir",null,delegate{Quit();});tray.ContextMenuStrip=menu;tray.DoubleClick += delegate{SetMode("Expanded");};
    }
    Forms.Screen Screen(){return Forms.Screen.FromHandle(new WindowInteropHelper(this).Handle);}
    void Position()
    {
        var screen=Screen();var area=screen.WorkingArea;
        var transform=source==null?Matrix.Identity:source.CompositionTarget.TransformFromDevice;
        var topLeft=transform.Transform(new Point(area.Left,area.Top));var bottomRight=transform.Transform(new Point(area.Right,area.Bottom));
        double available=bottomRight.Y-topLeft.Y;Width=Math.Min(800,Math.Max(1,bottomRight.X-topLeft.X-20));Height=Math.Max(1,available-20);
        double ratio;panelHeight=Math.Min(Height,Math.Max(560,available*(heights.TryGetValue(screen.DeviceName,out ratio)?ratio:.9)));
        Left=topLeft.X+(bottomRight.X-topLeft.X-Width)/2;Top=topLeft.Y;
        // A centered notch can move without a size change. Ask for
        // fresh CSS bounds rather than retaining the initial native clip region.
        PublishBounds();
    }
    Dictionary<string,object> Ui(){return new Dictionary<string,object>{{"mode",mode},{"topmost",Topmost},{"panelHeight",panelHeight},{"reduced",!SystemParameters.ClientAreaAnimation},{"lazyHistory",true},{"acknowledgesMode",true},{"connectionProgress",true},{"modeRequest",modeRequest},{"nativeGlass",false}};}
    async Task<bool> Script(string function,object value){if(!ready||web.CoreWebView2==null)return false;try{await web.CoreWebView2.ExecuteScriptAsync("window."+function+"("+Json.Serialize(value)+")");return true;}catch{lastSnapshot="";journalRevision=-1;return false;}}
    async void PublishUi(){await Script("receiveUI",Ui());}
    async void PublishBounds(){await Script("monitorBounds",null);}
    async void Feedback(string message){await Script("monitorFeedback",message);}
    async void ConnectionProgress(bool pending){await Script("monitorConnectionState",new Dictionary<string,object>{{"pending",pending}});}
    void SetMode(string value)
    {
        if(!new[]{"Compact","Expanded","Hidden"}.Contains(value))return;mode=value;
        if(mode=="Hidden")Hide();else{Position();Show();}
        // Acknowledge immediately; never wait for the Python journal or a provider.
        PublishUi();SaveUi();lastSnapshot="";Refresh();
    }
    void SaveUi(){if(preview)return;try{Atomic(UiPath,Encoding.UTF8.GetBytes(Json.Serialize(new Dictionary<string,object>{{"mode",mode},{"topmost",Topmost},{"panelHeights",heights}})));}catch{Feedback("No se pudo guardar la vista.");}}
    void Action(Dictionary<string,object> data)
    {
        string action=Text(data,"action","");
        switch(action){
            case "ready":ready=true;journalRevision=-1;lastSnapshot="";Position();PublishUi();Refresh();break;
            case "mode":modeRequest=Get(data,"request") is int?Get(data,"request"):null;SetMode(Text(data,"value",""));break;
            case "topmost":if(Get(data,"value") is bool){Topmost=(bool)data["value"];SaveUi();PublishUi();}break;
            case "history":if(Get(data,"value") is bool){historyRequested=(bool)data["value"];lastSnapshot="";Refresh();}break;
            case "bounds":
                double x=Numeric(Get(data,"x")),y=Numeric(Get(data,"y")),w=Numeric(Get(data,"width")),h=Numeric(Get(data,"height"));
                if(w>0&&h>0){hit=Rect.Intersect(new Rect(x,y,w,h),new Rect(0,0,Width,Height));ApplyRegion();}break;
            case "resizeEnd":
                double height=Numeric(Get(data,"height"));if(height>0){heights[Screen().DeviceName]=Math.Min(1,Math.Max(.1,height/Math.Max(1,Height+20)));Position();SaveUi();PublishUi();}break;
            case "resizeReset":heights.Remove(Screen().DeviceName);Position();SaveUi();PublishUi();break;
            case "resizeStart":break;
            case "secret":StoreKey(Text(data,"provider",""),Text(data,"value",""));break;
            case "config":case "quality":case "taskMode":case "connection":case "update":case "appearance":Perform(data);break;
        }
    }
    async void Perform(Dictionary<string,object> data)
    {
        if(preview||actionBusy){Feedback("Vista previa o una operación todavía en curso.");AppearanceResult(data,false);return;}
        actionBusy=true;
        bool connection=Text(data,"action","")=="connection";
        if(connection)await Script("monitorConnectionState",new Dictionary<string,object>{{"pending",true},{"value",Text(data,"value","")}});
        try{var reply=await Task.Run(()=>service.Request(data));Feedback(Text(reply,"feedback","Guardado."));object ok=Get(reply,"ok");AppearanceResult(data,ok is bool && (bool)ok);}
        catch{Feedback("No se pudo completar la operación. Tus tareas siguen abiertas.");AppearanceResult(data,false);}
        finally{if(connection)ConnectionProgress(false);actionBusy=false;lastSnapshot="";Refresh();}
    }
    async void AppearanceResult(Dictionary<string,object> data,bool ok)
    {
        if(Text(data,"action","")=="appearance")await Script("monitorAppearanceResult",new Dictionary<string,object>{{"thread",Get(data,"thread")},{"request",Get(data,"request")},{"ok",ok}});
    }
    void StoreKey(string provider,string value)
    {
        if(preview||!keys.ContainsKey(provider)||String.IsNullOrWhiteSpace(value)||Encoding.UTF8.GetByteCount(value)>=16384)return;
        try{byte[] cipher=ProtectedData.Protect(Encoding.UTF8.GetBytes(value.Trim()),null,DataProtectionScope.CurrentUser);Atomic(Path.Combine(root,"state",provider+".secret"),cipher);keys[provider]=true;lastSnapshot="";Refresh();Feedback("Clave guardada con Windows DPAPI.");}
        catch{Feedback("No se pudo guardar la clave.");}
    }
    async void Refresh()
    {
        if(!ready)return;if(busy){pending=true;return;}busy=true;
        try{
            bool needs=mode=="Expanded"&&historyRequested;int sent=journalRevision;
            var reply=await Task.Run(()=>service.Request(new Dictionary<string,object>{{"action","snapshot"},{"history",needs},{"revision",sent}}));
            if(!(Get(reply,"ok") as bool? ?? false)){Feedback(Text(reply,"feedback","No se pudo leer el estado."));return;}
            var payload=Dict(Get(reply,"payload"));bool history=payload.ContainsKey("history")&&mode=="Expanded"&&historyRequested;
            if(!history)payload.Remove("history");payload["historyLoaded"]=journalRevision>=0||history;payload["keys"]=keys;payload["ui"]=Ui();
            var small=new Dictionary<string,object>(payload);small.Remove("history");string encoded=Json.Serialize(small);
            if(encoded!=lastSnapshot||history){if(await Script("receive",payload)){lastSnapshot=encoded;if(history)journalRevision=Convert.ToInt32(payload["journalRevision"]);}}
            if(selfTest&&!testStarted){testStarted=true;RunSelfTest();}
        }catch{Feedback("No se pudo leer el estado. Se conserva la última vista.");}
        finally{busy=false;if(pending){pending=false;Refresh();}}
    }
    void Quit(){quitting=true;Close();Application.Current.Shutdown();}
    [StructLayout(LayoutKind.Sequential)] struct NativePoint {public int X,Y;}
    [DllImport("user32.dll")]static extern bool GetCursorPos(out NativePoint p);
    [DllImport("gdi32.dll")]static extern IntPtr CreateRoundRectRgn(int left,int top,int right,int bottom,int width,int height);
    [DllImport("gdi32.dll")]static extern IntPtr CreateRectRgn(int left,int top,int right,int bottom);
    [DllImport("gdi32.dll")]static extern int CombineRgn(IntPtr target,IntPtr first,IntPtr second,int mode);
    [DllImport("gdi32.dll")]static extern bool DeleteObject(IntPtr handle);
    [DllImport("user32.dll")]static extern int SetWindowRgn(IntPtr hwnd,IntPtr region,bool redraw);
    [DllImport("user32.dll")]static extern int GetWindowRgn(IntPtr hwnd,IntPtr region);
    [DllImport("gdi32.dll")]static extern bool PtInRegion(IntPtr region,int x,int y);
    void ApplyRegion()
    {
        if(source==null||hit.IsEmpty)return;previousPointer=null;var matrix=source.CompositionTarget.TransformToDevice;
        var a=matrix.Transform(hit.TopLeft);var b=matrix.Transform(hit.BottomRight);
        var region=CreateRectRgn(0,0,0,0);double scale=matrix.M11;
        double shoulder=Math.Min(20,hit.Width/2),radius=Math.Min(32,Math.Min(Math.Max(0,(hit.Width-2*shoulder)/2),hit.Height/2));
        for(int line=(int)Math.Floor(a.Y);line<(int)Math.Ceiling(b.Y);line++){
            double y=(line+.5-a.Y)/scale,inset=shoulder;
            if(y<shoulder)inset=Math.Sqrt(Math.Max(0,shoulder*shoulder-Math.Pow(shoulder-y,2)));
            if(y>hit.Height-radius)inset+=radius-Math.Sqrt(Math.Max(0,radius*radius-Math.Pow(y-hit.Height+radius,2)));
            int end=line+1;
            if(y>=shoulder && y<=hit.Height-radius)end=Math.Max(end,(int)Math.Floor(b.Y-radius*scale));
            var strip=CreateRectRgn((int)Math.Ceiling(a.X+inset*scale),line,(int)Math.Floor(b.X-inset*scale),end);
            CombineRgn(region,region,strip,2);DeleteObject(strip);line=end-1;
        }
        if(SetWindowRgn(source.Handle,region,true)==0)DeleteObject(region); // Successful transfer belongs to Windows.
    }
    IntPtr Hook(IntPtr hwnd,int message,IntPtr wParam,IntPtr lParam,ref bool handled)
    {
        if(message==0x0084&&!hit.IsEmpty){long raw=lParam.ToInt64();var p=PointFromScreen(new Point((short)(raw&65535),(short)((raw>>16)&65535)));if(!hit.Contains(p)){handled=true;return new IntPtr(-1);}}
        // WM_MOUSEACTIVATE defaults to activation without eating the first click.
        if(message==0x02E0||message==0x007E)Dispatcher.BeginInvoke(new Action(delegate{Position();PublishUi();}));
        return IntPtr.Zero;
    }
    async void UpdatePointer()
    {
        if(!ready||mode=="Hidden"||source==null)return;NativePoint native;if(!GetCursorPos(out native))return;
        var point=PointFromScreen(new Point(native.X,native.Y));if(previousPointer.HasValue&&previousPointer.Value==point&&previousActive==IsActive)return;previousPointer=point;previousActive=IsActive;
        double y=point.Y-hit.Y,shoulder=Math.Min(20,hit.Width/2),radius=Math.Min(32,Math.Min(Math.Max(0,(hit.Width-2*shoulder)/2),hit.Height/2)),inset=shoulder;
        if(y<shoulder)inset=Math.Sqrt(Math.Max(0,shoulder*shoulder-Math.Pow(shoulder-y,2)));
        if(y>hit.Height-radius)inset+=radius-Math.Sqrt(Math.Max(0,radius*radius-Math.Pow(y-hit.Height+radius,2)));
        bool inside=hit.Contains(point)&&point.X>=hit.Left+inset&&point.X<=hit.Right-inset;
        var data=inside?new Dictionary<string,object>{{"x",point.X},{"y",point.Y}}:null;
        // Project exits even while active; native clipping may suppress DOM leave.
        try{await web.CoreWebView2.ExecuteScriptAsync("window.monitorPointer("+Json.Serialize(data)+",true)");}catch{}
    }
    async Task AssertScript(string expression,string check)
    {
        for(int i=0;i<80;i++){if(await web.CoreWebView2.ExecuteScriptAsync("Boolean("+expression+")")=="true")return;await Task.Delay(100);}
        throw new InvalidOperationException(check);
    }
    async void RunSelfTest()
    {
        try{
            // This synthetic fixture drives DOM actions; the runner's unrelated
            // mouse position must not collapse it. Physical hover remains owner QA.
            pointer.Stop();
            await AssertScript("document.querySelectorAll('#agents .avatar').length===1","capsule active-only fixture");
            await AssertScript("Array.from(document.fonts).some(face=>face.family==='Router Nunito' && face.status==='loaded')","bundled Nunito font in native allowlist");
            await AssertNativeBounds();
            Height=Math.Max(200,Height-64);
            await AssertNativeBounds();
            Position();await AssertNativeBounds();
            SetMode("Hidden");SetMode("Compact");await AssertNativeBounds();
            await web.CoreWebView2.ExecuteScriptAsync("document.querySelector('#expand').click()");
            await AssertScript("state.ui.mode==='Expanded' && currentTab==='home' && document.querySelectorAll('.companion-hero').length===1 && document.querySelectorAll('.task-row').length===0","native mode ACK and Home principal without inactive rows");
            await AssertScript("document.querySelector('#activity').textContent.includes('Sol 6.1') && document.querySelector('#activity').textContent.includes('Alto')","shared model and effort pills");
            await web.CoreWebView2.ExecuteScriptAsync("document.querySelector('[data-tab=activity]').click()");
            await AssertScript("document.querySelectorAll('.agent-pick').length===2 && document.querySelectorAll('.agent-portrait').length===1","Agents catalog includes inactive fixture and portrait");
            await web.CoreWebView2.ExecuteScriptAsync("document.querySelector('[data-tab=history]').click()");
            await AssertScript("state.historyLoaded===true && document.querySelectorAll('.history-row').length===1","private Python lazy journal");
            using(var image=File.Create(Path.Combine(ProbeDirectory,"review-webview2-history.png")))await web.CoreWebView2.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png,image);
            await web.CoreWebView2.ExecuteScriptAsync("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))");
            await AssertScript("state.ui.mode==='Compact'","native compact ACK");
            if(hit.IsEmpty||File.Exists(UiPath)||File.Exists(Path.Combine(root,"config.local.json")))throw new InvalidOperationException("preview isolation and native bounds");
            FinishTest(true,"Shared WebView2 capsule/agents/pills/history; private Python IPC; native mode ACK/bounds; compact startup/resize/hidden-show clip region; isolated preview. First-click/hover/DPI/DPAPI visual acceptance still requires Windows owner QA.");
        }catch{FinishTest(false,"Shared WebView2 native fixture failed. No private data was captured.");}
    }
    async Task AssertNativeBounds()
    {
        UpdateLayout();
        await AssertScript("Math.abs(innerHeight-"+web.ActualHeight.ToString(System.Globalization.CultureInfo.InvariantCulture)+")<1","native viewport resize delivery");
        for(int i=0;i<80;i++) {
            var bounds=Json.Deserialize<Dictionary<string,object>>(await web.CoreWebView2.ExecuteScriptAsync("(()=>{const r=document.querySelector('#surface').getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};})()"));
            double x=Numeric(Get(bounds,"x")),y=Numeric(Get(bounds,"y")),w=Numeric(Get(bounds,"width")),h=Numeric(Get(bounds,"height"));
            if(!hit.IsEmpty && Math.Abs(hit.X-x)<1 && Math.Abs(hit.Y-y)<1 && Math.Abs(hit.Width-w)<1 && Math.Abs(hit.Height-h)<1) {
                var region=CreateRoundRectRgn(0,0,1,1,0,0);
                try {
                    var center=source.CompositionTarget.TransformToDevice.Transform(new Point(x+w/2,y+h/2));
                    if(IsVisible && GetWindowRgn(source.Handle,region)>0 && PtInRegion(region,(int)center.X,(int)center.Y))return;
                }finally{DeleteObject(region);}
            }
            await Task.Delay(100);
        }
        throw new InvalidOperationException("compact bounds/visible native clip region");
    }
    void FinishTest(bool success,string evidence)
    {
        Directory.CreateDirectory(ProbeDirectory);File.WriteAllText(Path.Combine(ProbeDirectory,"ui-review-checks.txt"),(success?"PASS: ":"FAIL: ")+evidence+Environment.NewLine);
        Environment.ExitCode=success?0:1;Quit();
    }
}

static class RouterMonitorProgram
{
    [STAThread]static int Main(string[] args)
    {
        string codeRoot=WindowsLayout.MonitorResources();
        string root=WindowsLayout.Installed(codeRoot)?WindowsLayout.DataRoot:codeRoot;int index=Array.IndexOf(args,"--root");if(index>=0&&index+1<args.Length)root=Path.GetFullPath(args[index+1]);
        bool selfTest=args.Contains("--self-test"),preview=selfTest||args.Contains("--preview");
        if(!preview && WindowsLayout.Installed(codeRoot) && !WindowsOnboarding.Prepare(codeRoot,root))return 0;
        if(selfTest){root=Path.Combine(root,"state","windows-monitor-probe-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(Path.Combine(root,"state"));
            File.WriteAllText(Path.Combine(root,"preview.json"),"{\"threads\":{\"fixture\":{\"name\":\"Synthetic fixture\",\"status\":\"active\",\"model\":\"gpt-6.1-sol\",\"effort\":\"high\"},\"idle\":{\"status\":\"idle\"}}}");
            File.WriteAllText(Path.Combine(root,"state","history.jsonl"),"{\"event\":\"decision_created\",\"decision_id\":\"fixture-decision\",\"thread\":\"fixture\",\"time\":1,\"title\":\"Synthetic fixture\",\"model\":\"gpt-6.1-sol\",\"effort\":\"high\"}\n");
        }
        Directory.CreateDirectory(Path.Combine(root,"state"));
        string hash;using(var sha=SHA256.Create())hash=BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(root.ToUpperInvariant()))).Replace("-","");
        bool created;using(var mutex=new Mutex(true,"Local\\CodexRouterMonitor-"+hash,out created))
        using(var reveal=new EventWaitHandle(false,EventResetMode.AutoReset,"Local\\CodexRouterMonitorReveal-"+hash)) {
            if(!created){reveal.Set();return 0;}
            try{
                var app=new Application();var window=new RouterMonitorWindow(root,codeRoot,preview,selfTest,reveal,args.Contains("--tray"));
                if(selfTest){var deadline=new DispatcherTimer {Interval=TimeSpan.FromSeconds(50)};deadline.Tick+=delegate{File.WriteAllText(Path.Combine(WindowsLayout.Installed(codeRoot)?root:codeRoot,"state","ui-review-checks.txt"),"FAIL: native fixture timeout");Environment.ExitCode=1;app.Shutdown();};deadline.Start();}
                app.Run(window);return Environment.ExitCode;
            }finally{mutex.ReleaseMutex();}
        }
    }
}
