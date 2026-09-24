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
            // Recovery must work even if Python or config.local.json is broken.
            if (args.Length == 1 && (args[0] == "--remove-integration" || args[0] == "--remove-integration-json"))
                return Disconnect(args[0].EndsWith("-json"));
            var config = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(ConfigPath));
            if (args.Length == 1 && args[0] == "--open") return Manage(config, "open", true);
            if (args.Length == 1 && args[0] == "--doctor") return Manage(config, "doctor", true);
            if (args.Length == 1 && args[0] == "--doctor-json") return Manage(config, "doctor", false);
            if (args.Length == 1 && args[0] == "--install-integration") return Manage(config, "install", true);
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
            if (args.Any(x => new[] { "--open", "--status", "--doctor", "--install-integration", "--remove-integration" }.Contains(x)))
                MessageBox.Show("No se ha podido iniciar el selector. Ejecuta el diagnóstico de conexión. Si está conectado al inicio habitual, usa Desconectar integración antes de volver a abrir Desktop.", "Codex automatico");
            else
                Console.Error.WriteLine("Codex automático: no se pudo iniciar el puente; ejecuta el diagnóstico de conexión.");
            return 1;
        }
    }

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern IntPtr SendMessageTimeout(IntPtr window, uint message, UIntPtr wparam, string lparam, uint flags, uint timeout, out UIntPtr result);

    static void RecoveryMessage(string message, bool quiet)
    {
        if (!quiet) MessageBox.Show(message, "Codex automático");
        else { var bytes = Encoding.UTF8.GetBytes(Json.Serialize(new { message = message })); Console.OpenStandardOutput().Write(bytes, 0, bytes.Length); }
    }
    static int Disconnect(bool quiet)
    {
        string path = Path.Combine(Root, "state", "desktop-integration.json");
        if (!File.Exists(path)) { RecoveryMessage("Esta instalación no tiene una conexión registrada.", quiet); return 0; }
        var record = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(path));
        if (!record.ContainsKey("platform") || (string)record["platform"] != "win32")
        { RecoveryMessage("El registro pertenece a otra plataforma. Se ha conservado sin cambios.", quiet); return 2; }
        var previous = (Dictionary<string, object>)record["previous"];
        using (var key = Microsoft.Win32.Registry.CurrentUser.CreateSubKey("Environment"))
        {
            string current = key.GetValue("CODEX_CLI_PATH", null, Microsoft.Win32.RegistryValueOptions.DoNotExpandEnvironmentNames) as string;
            if (current == (string)record["wrapper"])
            {
                if (previous["value"] == null) key.DeleteValue("CODEX_CLI_PATH", false);
                else key.SetValue("CODEX_CLI_PATH", previous["value"], (Microsoft.Win32.RegistryValueKind)Convert.ToInt32(previous["kind"]));
            }
            else if (!String.IsNullOrEmpty(current) && current != previous["value"] as string)
            {
                RecoveryMessage("Otra herramienta cambió la conexión. Se ha conservado su configuración.", quiet); return 2;
            }
        }
        File.Delete(path);
        UIntPtr result; SendMessageTimeout(new IntPtr(0xffff), 0x001a, UIntPtr.Zero, "Environment", 2, 3000, out result);
        RecoveryMessage("Conexión retirada. El siguiente arranque habitual usará el motor original. Tu historial se conserva.", quiet);
        return 0;
    }

    static int Manage(Dictionary<string, object> config, string action, bool visible)
    {
        var start = new ProcessStartInfo((string)config["python"])
        {
            Arguments = Quote(Path.Combine(Root, "desktop.py")) + " " + action,
            UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardOutput = true, RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
        };
        start.EnvironmentVariables["PYTHONUTF8"] = "1";
        using (var child = Process.Start(start))
        {
            var errors = child.StandardError.ReadToEndAsync();
            string output = child.StandardOutput.ReadToEnd();
            child.WaitForExit();
            string result = child.ExitCode == 0 ? output : errors.Result;
            if (!visible) { var bytes = Encoding.UTF8.GetBytes(result); Console.OpenStandardOutput().Write(bytes, 0, bytes.Length); }
            else if (action != "open" || child.ExitCode != 0)
            {
                string message = "Conexión actualizada.";
                try
                {
                    var data = Json.Deserialize<Dictionary<string, object>>(result);
                    if (data.ContainsKey("error")) message = (string)data["error"];
                    else if (data.ContainsKey("message")) message = (string)data["message"];
                    else message = "Instalación: " + data["discovery"] + "\nVersión: " +
                        (data.ContainsKey("desktop_version") ? data["desktop_version"] : "sin detectar") +
                        "\nConexión registrada: " + data["registered"] + "\nEstado: " + data["connection"];
                }
                catch { message = "No se pudo completar el diagnóstico. Revisa el informe local de conexión."; }
                MessageBox.Show(message, "Codex automático");
            }
            return child.ExitCode;
        }
    }

    static void OpenMonitor(bool hidden)
    {
        Process.Start(new ProcessStartInfo(Path.Combine(Root, "dist", "codex-monitor-v20.exe"), hidden ? "--tray" : "")
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
