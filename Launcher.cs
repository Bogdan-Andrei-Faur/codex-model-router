using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Diagnostics;
using System.Threading;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using System.Windows.Forms;

// WinExe avoids opening console windows. Protocol bytes only go through pipes.
internal static class Launcher
{
    static readonly string Root = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".."));
    static readonly string ConfigPath = Path.Combine(Root, "config.local.json");
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer();

    [STAThread]
    static int Main(string[] args)
    {
        try
        {
            var config = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(ConfigPath));
            if (args.Length == 1 && args[0] == "--open") return Open(config);
            if (args.Length == 1 && args[0] == "--status")
            { OpenMonitor(false); return 0; }
            if (args.Length == 1 && args[0] == "--status-text")
            {
                var output = Console.OpenStandardOutput();
                var bytes = Encoding.UTF8.GetBytes(StatusText(config));
                output.Write(bytes, 0, bytes.Length); output.Flush(); return 0;
            }
            if (args.Length == 1 && (args[0] == "--pause" || args[0] == "--resume"))
            {
                config["enabled"] = args[0] == "--resume";
                var tmp = ConfigPath + ".tmp";
                File.WriteAllText(tmp, Json.Serialize(config), new UTF8Encoding(false));
                File.Replace(tmp, ConfigPath, null);
                MessageBox.Show((bool)config["enabled"] ? "Selector activado para los siguientes mensajes." :
                    "Selector pausado. Codex utilizara el modelo que elijas en la app.", "Codex automatico");
                return 0;
            }
            return Bridge(config, args);
        }
        catch
        {
            // No exception text: command lines, paths or messages may contain secrets.
            if (args.Contains("--open") || args.Contains("--status"))
                MessageBox.Show("No se ha podido iniciar el selector. Revisa config.local.json. Puedes abrir Codex con su acceso habitual.", "Codex automatico");
            return 1;
        }
    }

    static int Open(Dictionary<string, object> config)
    {
        var desktop = (string)config["desktop"];
        foreach (var process in Process.GetProcessesByName(Path.GetFileNameWithoutExtension(desktop)))
        {
            using (process)
            {
                try
                {
                    if (!String.Equals(process.MainModule.FileName, desktop, StringComparison.OrdinalIgnoreCase)) continue;
                }
                catch { }
                MessageBox.Show("Codex sigue abierto. Cuando hayas terminado tus tareas, cierralo por completo y vuelve a abrir este acceso. No es necesario cerrar sesion.", "Codex automatico");
                return 2;
            }
        }
        var start = new ProcessStartInfo(desktop) { UseShellExecute = false };
        start.EnvironmentVariables["CODEX_CLI_PATH"] = System.Reflection.Assembly.GetExecutingAssembly().Location;
        start.EnvironmentVariables["PERSONAL_CODEX_ROUTER_CONFIG"] = ConfigPath;
        Process.Start(start);
        try { OpenMonitor(true); } catch { /* Monitoring must not block Codex. */ }
        return 0;
    }

    static void OpenMonitor(bool hidden)
    {
        Process.Start(new ProcessStartInfo(Path.Combine(Root, "dist", "codex-monitor-v18.exe"), hidden ? "--tray" : "")
            { UseShellExecute = false, CreateNoWindow = true });
    }

    static string StatusText(Dictionary<string, object> config)
    {
        string state = (bool)config["enabled"] ? "Selector: activado" : "Selector: pausado";
        var folder = Path.Combine(Root, "state");
        var files = Directory.Exists(folder) ? Directory.GetFiles(folder, "status-*.json") : new string[0];
        if (files.Length > 0)
        {
            var last = files.OrderByDescending(File.GetLastWriteTimeUtc).First();
            var data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(last));
            var events = ((System.Collections.IEnumerable)data["events"]).Cast<Dictionary<string, object>>().ToList();
            var routed = events.LastOrDefault(x => x.ContainsKey("reason") && x.ContainsKey("model"));
            if (routed != null) state += "\nUltima seleccion: " + routed["model"] + "\nMotivo: " + routed["reason"];
            var recent = events.LastOrDefault();
            if (recent != null) state += "\n\nConexion automatica: " +
                ((string)recent["event"] == "bridge_stopped" ? "cerrada" : "iniciada") +
                "\nUltima actividad: " + recent["time"];
        }
        else state += "\nTodavia no se ha iniciado ninguna conexion con el selector.";
        state += "\n\nLuna: transformaciones delimitadas\nTerra: cambios concretos\nSol: ingenieria compleja de alcance definido\nAstra: UI/UX, auditorias, trabajo amplio y situaciones criticas\n\nLa seleccion usa reglas locales. Abre el monitor para ver modelo, razonamiento y evidencia.";
        return state;
    }

    static int Bridge(Dictionary<string, object> config, string[] args)
    {
        var start = new ProcessStartInfo((string)config["python"])
        {
            Arguments = String.Join(" ", new[] { Quote(Path.Combine(Root, "router.py")) }.Concat(args.Select(Quote))),
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        start.EnvironmentVariables["PYTHONUTF8"] = "1";
        start.EnvironmentVariables["PERSONAL_CODEX_ROUTER_CONFIG"] = ConfigPath;
        using (var job = new ChildJob())
        using (var child = Process.Start(start))
        {
            job.Assign(child);
            var input = new Thread(() => {
                try { Pump(Console.OpenStandardInput(), child.StandardInput.BaseStream); }
                catch (IOException) { }
                finally { try { child.StandardInput.Close(); } catch { } }
            }) { IsBackground = true };
            var errors = new Thread(() => {
                try { Pump(child.StandardError.BaseStream, Console.OpenStandardError()); }
                catch (IOException) { }
            }) { IsBackground = true };
            input.Start(); errors.Start();
            try { Pump(child.StandardOutput.BaseStream, Console.OpenStandardOutput()); }
            catch (IOException) { if (!child.HasExited) child.Kill(); }
            child.WaitForExit(); errors.Join(1000);
            return child.ExitCode;
        }
    }

    static void Pump(Stream input, Stream output)
    {
        var buffer = new byte[65536];
        int count;
        while ((count = input.Read(buffer, 0, buffer.Length)) > 0)
        { output.Write(buffer, 0, count); output.Flush(); }
    }

    // Windows CommandLineToArgvW escaping, including empty and trailing-slash args.
    static string Quote(string text)
    {
        var result = new StringBuilder("\"");
        int slashes = 0;
        foreach (var c in text)
        {
            if (c == '\\') { slashes++; continue; }
            result.Append('\\', c == '"' ? slashes * 2 + 1 : slashes);
            result.Append(c); slashes = 0;
        }
        return result.Append('\\', slashes * 2).Append('"').ToString();
    }

    // Close all bridge descendants if the desktop kills this launcher.
    sealed class ChildJob : IDisposable
    {
        IntPtr handle;
        [StructLayout(LayoutKind.Sequential)] struct BasicLimits
        { public long ProcessTime, JobTime; public uint Flags; public UIntPtr Min, Max; public uint Processes; public UIntPtr Affinity; public uint Priority, Scheduling; }
        [StructLayout(LayoutKind.Sequential)] struct IoCounters
        { public ulong ReadOps, WriteOps, OtherOps, ReadBytes, WriteBytes, OtherBytes; }
        [StructLayout(LayoutKind.Sequential)] struct ExtendedLimits
        { public BasicLimits Basic; public IoCounters Io; public UIntPtr ProcessMemory, JobMemory, PeakProcessMemory, PeakJobMemory; }
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode)] static extern IntPtr CreateJobObject(IntPtr attributes, string name);
        [DllImport("kernel32.dll")] static extern bool SetInformationJobObject(IntPtr job, int infoClass, ref ExtendedLimits info, uint size);
        [DllImport("kernel32.dll")] static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
        [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr value);
        public ChildJob()
        {
            handle = CreateJobObject(IntPtr.Zero, null);
            var info = new ExtendedLimits(); info.Basic.Flags = 0x2000;
            if (handle == IntPtr.Zero || !SetInformationJobObject(handle, 9, ref info, (uint)Marshal.SizeOf(info)))
                throw new InvalidOperationException("Cannot create process job");
        }
        public void Assign(Process process)
        {
            if (!AssignProcessToJobObject(handle, process.Handle))
            { process.Kill(); throw new InvalidOperationException("Cannot supervise bridge process"); }
        }
        public void Dispose() { if (handle != IntPtr.Zero) { CloseHandle(handle); handle = IntPtr.Zero; } }
    }
}
