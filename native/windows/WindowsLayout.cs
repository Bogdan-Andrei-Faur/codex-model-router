// Owned installed paths. User settings never select installed executables.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;

static class WindowsLayout
{
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode)]static extern uint GetLongPathName(string input,StringBuilder output,uint size);
    internal static string Normalize(string path)
    {
        path=Path.GetFullPath(path);var buffer=new StringBuilder(32768);
        uint size=GetLongPathName(path,buffer,(uint)buffer.Capacity);
        return size>0 && size<buffer.Capacity?buffer.ToString():path;
    }
    internal static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength=65536 };
    internal static Dictionary<string,object> Read(string path)
    {
        var info=new FileInfo(path);
        if(info.Length>65536)throw new InvalidDataException();
        return Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(path,Encoding.UTF8));
    }
    internal static string DataRoot {get{return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"codex-model-router");}}
    internal static bool Installed(string resources) {return File.Exists(Path.Combine(resources,"application.json"));}
    internal static string Owned(string basePath,string relative)
    {
        basePath=Normalize(basePath).TrimEnd(Path.DirectorySeparatorChar);
        if(String.IsNullOrEmpty(relative)||Path.IsPathRooted(relative)||relative.Split('\\','/').AnyPartIsParent())throw new InvalidDataException();
        string path=Path.GetFullPath(Path.Combine(basePath,relative));
        if(!path.StartsWith(basePath+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException();
        for(string current=path;current.Length>=basePath.Length;current=Path.GetDirectoryName(current)) {
            if((File.Exists(current)||Directory.Exists(current)) && (File.GetAttributes(current)&FileAttributes.ReparsePoint)!=0)throw new InvalidDataException();
            if(current.Equals(basePath,StringComparison.OrdinalIgnoreCase))break;
        }
        return path;
    }
    static bool AnyPartIsParent(this string[] parts) {foreach(string part in parts)if(part==".."||part=="."||part.Contains(":"))return true;return false;}
    internal static string Component(string resources,string name)
    {
        var manifest=Read(Path.Combine(resources,"application.json"));
        if(Convert.ToInt32(manifest["schema"])!=1 || (string)manifest["layout"]!="windows-install-v1")throw new InvalidDataException();
        string path=Owned(Path.GetDirectoryName(resources),(string)manifest[name]);
        if(!File.Exists(path))throw new FileNotFoundException();
        return path;
    }
    internal static string VersionResources(string application,string version)
    {
        if(!Regex.IsMatch(version??"","^[0-9]+\\.[0-9]+\\.[0-9]+-[a-f0-9]{16}$"))throw new InvalidDataException();
        string resources=Owned(application,"versions/"+version+"/Resources");
        Component(resources,"runtime");Component(resources,"monitor");
        return resources;
    }
    internal static string ActiveResources(string application)
    {
        var active=Read(Owned(application,"active.json"));
        if(Convert.ToInt32(active["schema"])!=1)throw new InvalidDataException();
        return VersionResources(application,(string)active["versionDirectory"]);
    }
    internal static string MonitorResources()
    {
        string parent=Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,".."));
        string resources=Path.Combine(parent,"Resources");
        return Installed(resources)?resources:parent;
    }
    internal static string Quote(string value)
    {
        var result=new StringBuilder("\"");int slashes=0;
        foreach(char c in value){if(c=='\\'){slashes++;continue;}result.Append('\\',c=='"'?slashes*2+1:slashes);result.Append(c);slashes=0;}
        return result.Append('\\',slashes*2).Append('"').ToString();
    }
    internal static ProcessStartInfo Runtime(string resources,string root,string service,string arguments)
    {
        var info=new ProcessStartInfo(Component(resources,"runtime"),"--data-root "+Quote(root)+" "+service+(String.IsNullOrEmpty(arguments)?"":" "+arguments)) {
            UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=resources };
        info.EnvironmentVariables["PERSONAL_CODEX_ROUTER_CODE_ROOT"]=resources;
        info.EnvironmentVariables["PERSONAL_CODEX_ROUTER_ROOT"]=root;
        info.EnvironmentVariables["PERSONAL_CODEX_ROUTER_CONFIG"]=Path.Combine(root,"config.local.json");
        info.EnvironmentVariables["PERSONAL_CODEX_ROUTER_STATE"]=Path.Combine(root,"state");
        info.EnvironmentVariables["PYTHONUTF8"]="1";
        return info;
    }
    internal static int Run(string resources,string root,string service,string arguments)
    {
        string ignored;return Run(resources,root,service,arguments,out ignored);
    }
    internal static int Run(string resources,string root,string service,string arguments,out string result)
    {
        result="";
        var info=Runtime(resources,root,service,arguments);info.RedirectStandardOutput=true;info.RedirectStandardError=true;
        using(var process=Process.Start(info)) {
            var output=process.StandardOutput.ReadToEndAsync();var error=process.StandardError.ReadToEndAsync();
            if(!process.WaitForExit(100000)){process.Kill();return 1;}
            System.Threading.Tasks.Task.WaitAll(output,error);result=output.Result;return process.ExitCode;
        }
    }
    internal static void Atomic(string path,string value)
    {
        string temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";
        File.WriteAllText(temp,value,new UTF8Encoding(false));
        try{if(File.Exists(path))File.Replace(temp,path,null);else File.Move(temp,path);}
        finally{if(File.Exists(temp))File.Delete(temp);}
    }
}
