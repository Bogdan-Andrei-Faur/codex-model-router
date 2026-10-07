// Stable Windows entry point; private bridge stdio and native recovery.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Security.Cryptography.X509Certificates;
using Microsoft.Win32;

static class InstalledLauncher
{
    [DllImport("user32.dll",CharSet=CharSet.Unicode)]static extern IntPtr SendMessageTimeout(IntPtr hwnd,uint msg,UIntPtr wparam,string lparam,uint flags,uint timeout,out UIntPtr result);
    static readonly string ApplicationRoot=WindowsLayout.Normalize(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,".."));
    [DllImport("wintrust.dll",ExactSpelling=true,SetLastError=true)]static extern int WinVerifyTrust(IntPtr window,ref Guid action,ref TrustData data);
    [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)]struct TrustFile {public uint size;[MarshalAs(UnmanagedType.LPWStr)]public string path;public IntPtr file,subject;}
    [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)]struct TrustData {public uint size;public IntPtr callback,sip;public uint ui,revocation,choice;public IntPtr file;public uint stateAction;public IntPtr state;public IntPtr url;public uint flags,context;}
    [STAThread]static int Main(string[] args)
    {
        try {
            if(args.Length==2 && args[0]=="--verify-webview2")return VerifyMicrosoft(args[1]);
            if(args.Length==2 && args[0]=="--check-installation")return CheckInstallation(args[1]);
            if(args.Length==2 && args[0]=="--check-uninstall")return CheckInstallation(args[1],true);
            string root=WindowsLayout.DataRoot;
            if(args.Length>=2 && args[0]=="--data-root"){root=Path.GetFullPath(args[1]);args=args.Skip(2).ToArray();}
            if(args.SequenceEqual(new[]{"--remove-integration-json"})||args.SequenceEqual(new[]{"--remove-integration"}))return Disconnect(root);
            if(args.Length==2 && args[0]=="--activate-version")return Activate(args[1],root);
            if(args.SequenceEqual(new[]{"--rollback"}))return Rollback(root);
            if(args.SequenceEqual(new[]{"--rollback-ui"})) {
                if(System.Windows.Forms.MessageBox.Show("Se restaurará la versión anterior para los próximos arranques. Tus tareas abiertas conservarán su versión. ¿Continuar?","Codex Model Router",System.Windows.Forms.MessageBoxButtons.YesNo)!=System.Windows.Forms.DialogResult.Yes)return 0;
                int status=Rollback(root);
                System.Windows.Forms.MessageBox.Show(status==0?"Versión anterior restaurada. Vuelve a abrir el monitor y reinicia Desktop cuando terminen tus tareas.":"No hay una versión anterior recuperable. Tus datos se conservan.","Codex Model Router");return status;
            }
            string resources=WindowsLayout.ActiveResources(ApplicationRoot);
            if(args.Length==0 || args[0]=="--status") {
                var start=new ProcessStartInfo(WindowsLayout.Component(resources,"monitor"),"--root "+WindowsLayout.Quote(root)) {UseShellExecute=false,CreateNoWindow=true};
                Process.Start(start);return 0;
            }
            string service="bridge";
            if(args[0]=="--identity"){service="identity";args=args.Skip(1).ToArray();}
            else if(args[0]=="--bootstrap"){service="bootstrap";args=args.Skip(1).ToArray();}
            else if(args[0]=="--import-legacy"){service="import-legacy";args=args.Skip(1).ToArray();}
            else if(args[0]=="--doctor-json"){service="desktop";args=new[]{"doctor"};}
            return Forward(WindowsLayout.Runtime(resources,root,service,String.Join(" ",args.Select(WindowsLayout.Quote))));
        }catch{Console.Error.WriteLine("Codex Model Router: no se pudo iniciar. Tus datos se conservan.");return 1;}
    }
    static int VerifyMicrosoft(string path)
    {
        var file=new TrustFile {size=(uint)Marshal.SizeOf(typeof(TrustFile)),path=Path.GetFullPath(path)};
        IntPtr pointer=Marshal.AllocHGlobal(Marshal.SizeOf(file));Marshal.StructureToPtr(file,pointer,false);
        try {
            var data=new TrustData {size=(uint)Marshal.SizeOf(typeof(TrustData)),ui=2,choice=1,file=pointer};
            var action=new Guid("00AAC56B-CD44-11d0-8CC2-00C04FC295EE");
            if(WinVerifyTrust(IntPtr.Zero,ref action,ref data)!=0)return 1;
            using(var cert=new X509Certificate2(X509Certificate.CreateFromSignedFile(path)))
                return cert.GetNameInfo(X509NameType.SimpleName,false)=="Microsoft Corporation"?0:1;
        }finally{Marshal.DestroyStructure(pointer,typeof(TrustFile));Marshal.FreeHGlobal(pointer);}
    }
    static int CheckInstallation(string application,bool uninstall=false)
    {
        application=WindowsLayout.Normalize(application);
        if(!Directory.Exists(application))return 0;
        // No termination or scheduling replacement of files for the next reboot.
        string self=WindowsLayout.Normalize(Process.GetCurrentProcess().MainModule.FileName);
        string uninstaller=Path.Combine(application,"unins000.exe");
        int ownPid=Process.GetCurrentProcess().Id;
        foreach(var process in Process.GetProcesses()) {
            using(process)try {
                string path=WindowsLayout.Normalize(process.MainModule.FileName);
                if(process.Id!=ownPid && path.StartsWith(application.TrimEnd('\\')+"\\",StringComparison.OrdinalIgnoreCase)
                    && !(uninstall && path.Equals(uninstaller,StringComparison.OrdinalIgnoreCase)))return 1;
            }catch(System.ComponentModel.Win32Exception){}catch(InvalidOperationException){}
        }
        var directories=new Stack<string>();directories.Push(application);int count=0;
        while(directories.Count>0)foreach(string file in Directory.EnumerateFileSystemEntries(directories.Pop())) {
            if(++count>50000)return 1;
            WindowsLayout.Owned(application,file.Substring(application.TrimEnd('\\').Length+1));
            if(Directory.Exists(file)){directories.Push(file);continue;}
            if(!file.Equals(self,StringComparison.OrdinalIgnoreCase) && !(uninstall && file.Equals(uninstaller,StringComparison.OrdinalIgnoreCase)) && new[]{".exe",".dll",".pyd"}.Contains(Path.GetExtension(file).ToLowerInvariant()))
                using(var handle=new FileStream(file,FileMode.Open,FileAccess.ReadWrite,FileShare.None)){}
        }
        return 0;
    }
    static int Forward(ProcessStartInfo info)
    {
        info.RedirectStandardInput=true;info.RedirectStandardOutput=true;info.RedirectStandardError=true;
        using(var child=Process.Start(info)) {
            var input=new Thread(delegate(){try{Pump(Console.OpenStandardInput(),child.StandardInput.BaseStream);}catch{}finally{try{child.StandardInput.Close();}catch{}}}){IsBackground=true};input.Start();
            Task output=child.StandardOutput.BaseStream.CopyToAsync(Console.OpenStandardOutput());
            Task error=child.StandardError.BaseStream.CopyToAsync(Console.OpenStandardError());
            child.WaitForExit();Task.WaitAll(output,error);return child.ExitCode;
        }
    }
    static void Pump(Stream source,Stream target)
    {
        var buffer=new byte[65536];int count;
        while((count=source.Read(buffer,0,buffer.Length))>0){target.Write(buffer,0,count);target.Flush();}
    }
    static int Activate(string version,string root,bool recovery=false)
    {
        using(var handle=new FileStream(Path.Combine(ApplicationRoot,"activation.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)) {
            string resources=WindowsLayout.VersionResources(ApplicationRoot,version);
            var info=WindowsLayout.Runtime(resources,root,"identity","");info.RedirectStandardOutput=true;info.RedirectStandardError=true;
            using(var process=Process.Start(info)) {
                var output=process.StandardOutput.ReadToEndAsync();var error=process.StandardError.ReadToEndAsync();
                if(!process.WaitForExit(45000)){process.Kill();return 1;}
                Task.WaitAll(output,error);if(process.ExitCode!=0)return 1;
                var actual=WindowsLayout.Json.Deserialize<Dictionary<string,object>>(output.Result);
                var expected=WindowsLayout.Read(Path.Combine(resources,"application.json"));
                foreach(string name in new[]{"version","build","routerBuild"})if((string)actual[name]!=(string)expected[name])return 1;
                if(version!=(string)actual["version"]+"-"+(string)actual["build"])return 1;
            }
            string active=Path.Combine(ApplicationRoot,"active.json");
            string value=WindowsLayout.Json.Serialize(new Dictionary<string,object>{{"schema",1},{"versionDirectory",version}});
            if(File.Exists(active)) {
                if(File.ReadAllText(active)==value)return 0;
                bool valid=true;
                try{WindowsLayout.ActiveResources(ApplicationRoot);}catch{valid=false;}
                if(!valid && !recovery)return 1;
                WindowsLayout.Atomic(Path.Combine(ApplicationRoot,valid?"active.previous.json":"active.failed.json"),File.ReadAllText(active));
            }
            WindowsLayout.Atomic(active,value);return 0;
        }
    }
    static int Rollback(string root)
    {
        var previous=WindowsLayout.Read(Path.Combine(ApplicationRoot,"active.previous.json"));
        return Activate((string)previous["versionDirectory"],root,true);
    }
    static int Disconnect(string root)
    {
        string receipt=Path.Combine(root,"state/desktop-integration.json");
        if(!File.Exists(receipt)){Console.WriteLine("{\"registered\":false}");return 0;}
        var record=WindowsLayout.Read(receipt);
        string wrapper=(string)record["wrapper"],expected=WindowsLayout.Normalize(Path.Combine(ApplicationRoot,"bin","codex-router.exe"));
        if((string)record["platform"]!="win32" || !WindowsLayout.Normalize(wrapper).Equals(expected,StringComparison.OrdinalIgnoreCase))return 2;
        var previous=(Dictionary<string,object>)record["previous"];
        int kind=Convert.ToInt32(previous["kind"]);if(kind!=1&&kind!=2)return 2;
        object before=previous["value"];if(before!=null && !(before is string))return 2;
        using(var key=Registry.CurrentUser.CreateSubKey("Environment")) {
            string current=key.GetValue("CODEX_CLI_PATH",null,RegistryValueOptions.DoNotExpandEnvironmentNames) as string;
            if(current==wrapper){if(before==null)key.DeleteValue("CODEX_CLI_PATH",false);else key.SetValue("CODEX_CLI_PATH",before,(RegistryValueKind)kind);}
            else if(!String.IsNullOrEmpty(current)&&current!=before as string)return 2;
        }
        File.Delete(receipt);UIntPtr result;SendMessageTimeout(new IntPtr(0xffff),0x001a,UIntPtr.Zero,"Environment",2,3000,out result);
        Console.WriteLine("{\"registered\":false}");return 0;
    }
}
