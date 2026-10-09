using System;
using System.IO;
using System.Linq;
using System.Drawing;
using System.Diagnostics;
using System.Collections;
using System.Collections.Generic;
using System.Threading;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using System.Windows.Forms;

internal sealed class RouterMonitor : Form
{
    const string WindowTitle = "Codex automático · Monitor v2";
    static readonly string Root = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".."));
    static readonly string[] Efforts = { "low", "medium", "high", "xhigh", "max", "ultra" };
    static readonly string[] Labels = { "Ligero", "Medio", "Alto", "Muy alto", "Máx.", "Ultra" };
    static readonly Color Bg = Color.FromArgb(20, 24, 30), Card = Color.FromArgb(31, 37, 46), Ink = Color.FromArgb(229, 234, 241);
    readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = 8 * 1024 * 1024 };
    readonly DataGridView activity = Grid(), levels = Grid();
    readonly Label connection = new Label(), baseline = new Label();
    readonly Button pause = new Button();
    readonly NotifyIcon tray = new NotifyIcon();
    readonly System.Windows.Forms.Timer timer = new System.Windows.Forms.Timer();
    readonly TabControl tabs = new TabControl();
    TableLayoutPanel layout;
    bool compact;
    bool quitting, startHidden;
    Dictionary<string, object> catalog = new Dictionary<string, object>();

    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern IntPtr FindWindow(string cls, string title);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr window, int cmd);
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr window);
    [STAThread] static int Main(string[] args)
    {
        SetProcessDPIAware(); Application.EnableVisualStyles();
        bool created;
        using (var mutex = new Mutex(true, "Local\\PersonalCodexRouterMonitorV2Final", out created))
        {
            if (!created && !args.Contains("--render"))
            {
                if (!args.Contains("--tray")) { var h = FindWindow(null, WindowTitle); ShowWindow(h, 9); SetForegroundWindow(h); }
                return 0;
            }
            using (var panel = new RouterMonitor(args.Contains("--tray")))
            {
                if (args.Contains("--render"))
                {
                    panel.Show(); Application.DoEvents(); panel.RefreshData(); Application.DoEvents();
                    for (int i = 0; i < panel.tabs.TabCount; i++)
                    {
                        panel.tabs.SelectedIndex = i; Application.DoEvents();
                        using (var bmp = new Bitmap(panel.Width, panel.Height))
                        { panel.DrawToBitmap(bmp, new Rectangle(Point.Empty, panel.Size)); bmp.Save(Path.Combine(Root, "state", "monitor-preview-" + i + ".png")); }
                    }
                    panel.ToggleCompact(); Application.DoEvents();
                    using (var bmp = new Bitmap(panel.Width, panel.Height))
                    { panel.DrawToBitmap(bmp, new Rectangle(Point.Empty, panel.Size)); bmp.Save(Path.Combine(Root, "state", "monitor-preview-compact.png")); }
                    panel.quitting = true; panel.Close(); return 0;
                }
                Application.Run(panel);
            }
        }
        return 0;
    }

    static string S(IDictionary<string, object> value, string key, string fallback = "")
    { object found; return value != null && value.TryGetValue(key, out found) && found != null ? Convert.ToString(found) : fallback; }
    static Dictionary<string, object> D(object value) { return value as Dictionary<string, object> ?? new Dictionary<string, object>(); }
    static string Effort(string value) { var i = Array.IndexOf(Efforts, value); return i < 0 ? "Sin confirmar" : Labels[i]; }
    static string Model(string value) { return value.Replace("gpt-5.6-", "").Replace("gpt-6-", ""); }
    static DataGridView Grid()
    {
        var g = new DataGridView { Dock = DockStyle.Fill, ReadOnly = true, AllowUserToAddRows = false,
            AllowUserToDeleteRows = false, AllowUserToResizeRows = false, RowHeadersVisible = false,
            SelectionMode = DataGridViewSelectionMode.FullRowSelect, MultiSelect = false,
            BackgroundColor = Bg, BorderStyle = BorderStyle.None, EnableHeadersVisualStyles = false,
            AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill, AutoSizeRowsMode = DataGridViewAutoSizeRowsMode.AllCells };
        g.DefaultCellStyle.BackColor = Card; g.DefaultCellStyle.ForeColor = Ink;
        g.DefaultCellStyle.SelectionBackColor = Color.FromArgb(47, 70, 99);
        g.DefaultCellStyle.SelectionForeColor = Color.White; g.DefaultCellStyle.Padding = new Padding(9);
        g.DefaultCellStyle.WrapMode = DataGridViewTriState.True;
        g.ColumnHeadersDefaultCellStyle.BackColor = Bg; g.ColumnHeadersDefaultCellStyle.ForeColor = Color.LightSteelBlue;
        g.ColumnHeadersDefaultCellStyle.Padding = new Padding(8); g.ColumnHeadersHeight = 44;
        g.GridColor = Color.FromArgb(47, 53, 64); return g;
    }
    static Button Button(string text)
    { return new Button { Text = text, AutoSize = true, Height = 34, FlatStyle = FlatStyle.Flat, BackColor = Card, ForeColor = Ink, Padding = new Padding(8, 3, 8, 3) }; }

    RouterMonitor(bool hidden)
    {
        startHidden = hidden; Text = WindowTitle; Size = new Size(1100, 650); MinimumSize = new Size(820, 520);
        StartPosition = FormStartPosition.CenterScreen; Font = new Font("Segoe UI", 10); BackColor = Bg; ForeColor = Ink;
        var icon = Path.Combine(Root, "assets", "brand", "router.ico"); if (File.Exists(icon)) Icon = new Icon(icon);
        layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 4, Padding = new Padding(18) };
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 52)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 52));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 62));
        connection.Dock = DockStyle.Fill; connection.Font = new Font("Segoe UI Semibold", 13); connection.TextAlign = ContentAlignment.MiddleLeft;
        layout.Controls.Add(connection, 0, 0);
        var controls = new FlowLayoutPanel { Dock = DockStyle.Fill };
        pause.Text = "Pausar selección"; pause.AutoSize = true; pause.FlatStyle = FlatStyle.Flat; pause.BackColor = Card; pause.ForeColor = Ink;
        pause.Click += (s, e) => TogglePause(); controls.Controls.Add(pause);
        var top = new CheckBox { Text = "Siempre visible", AutoSize = true, Margin = new Padding(20, 6, 8, 0) };
        top.CheckedChanged += (s, e) => TopMost = top.Checked; controls.Controls.Add(top);
        var refresh = Button("Actualizar"); refresh.Click += (s, e) => RefreshData(); controls.Controls.Add(refresh);
        var small = Button("Vista compacta"); small.Click += (s, e) => { ToggleCompact(); small.Text = compact ? "Vista completa" : "Vista compacta"; }; controls.Controls.Add(small);
        layout.Controls.Add(controls, 0, 1);
        foreach (var name in new[] { "Tarea / agente", "Modelo", "Razonamiento", "Estado", "Evidencia", "Motivo" }) activity.Columns.Add(name, name);
        activity.Columns[0].FillWeight = 130; activity.Columns[1].FillWeight = 65; activity.Columns[2].FillWeight = 75;
        activity.Columns[3].FillWeight = 75; activity.Columns[4].FillWeight = 100; activity.Columns[5].FillWeight = 180;
        var live = new TabPage("Actividad") { BackColor = Bg }; live.Controls.Add(activity); tabs.TabPages.Add(live);
        var policy = Grid(); policy.Columns.Add("modelo", "Modelo"); policy.Columns.Add("cuando", "Cuándo lo elegimos"); policy.Columns.Add("limites", "Cuándo subir de capacidad");
        policy.Columns[0].FillWeight = 45;
        policy.Rows.Add("Luna", "Traducción, extracción, formato y explicaciones delimitadas. Ligero o Medio.", "Ambigüedad, trabajo de ingeniería abierto o necesidad de criterio visual.");
        policy.Rows.Add("Terra", "Correcciones concretas, formularios definidos, validaciones y cambios pequeños verificables. Ligero–Alto.", "Varios componentes, investigación difícil o diseño que exija criterio.");
        policy.Rows.Add("Sol", "Refactorización e ingeniería compleja de alcance definido; diagnóstico y comparación técnica. Medio–Muy alto.", "Auditoría profunda, rediseño UX, referencias visuales o trabajo amplio.");
        policy.Rows.Add("Astra", "UI/UX, diseño y revisión visual, auditorías, arquitectura amplia, investigación difícil y situaciones críticas. Alto–Máx.", "Es el modelo de máxima capacidad. Ultra solo por petición expresa.");
        var policyPage = new TabPage("Criterio de selección") { BackColor = Bg }; policyPage.Controls.Add(policy); tabs.TabPages.Add(policyPage);
        foreach (var name in new[] { "Nivel", "Uso previsto", "Disponibilidad en el catálogo" }) levels.Columns.Add(name, name);
        levels.Columns[0].FillWeight = 55;
        var levelPage = new TabPage("Razonamiento") { BackColor = Bg }; levelPage.Controls.Add(levels); tabs.TabPages.Add(levelPage);
        tabs.Dock = DockStyle.Fill; layout.Controls.Add(tabs, 0, 2);
        baseline.Dock = DockStyle.Fill; baseline.TextAlign = ContentAlignment.MiddleLeft; baseline.ForeColor = Color.LightSteelBlue;
        layout.Controls.Add(baseline, 0, 3); Controls.Add(layout);
        var menu = new ContextMenuStrip(); menu.Items.Add("Abrir monitor", null, (s, e) => Reveal());
        menu.Items.Add("Pausar / activar selección", null, (s, e) => TogglePause());
        menu.Items.Add("Salir del monitor", null, (s, e) => { quitting = true; Close(); });
        tray.Icon = Icon; tray.Text = WindowTitle; tray.ContextMenuStrip = menu; tray.Visible = true;
        tray.DoubleClick += (s, e) => Reveal();
        FormClosing += (s, e) => { if (!quitting && e.CloseReason == CloseReason.UserClosing) { e.Cancel = true; Hide(); } };
        Shown += (s, e) => { if (startHidden) Hide(); };
        timer.Interval = 2000; timer.Tick += (s, e) => RefreshData(); timer.Start(); RefreshData();
    }
    void Reveal() { Show(); WindowState = FormWindowState.Normal; Activate(); }
    void ToggleCompact()
    {
        compact = !compact; tabs.SelectedIndex = 0;
        activity.Columns[4].Visible = activity.Columns[5].Visible = !compact;
        baseline.Visible = !compact; layout.RowStyles[3].Height = compact ? 0 : 62;
        connection.Font = new Font("Segoe UI Semibold", compact ? 10 : 13);
        MinimumSize = compact ? new Size(650, 330) : new Size(820, 520);
        Size = compact ? new Size(700, 400) : new Size(1100, 650);
    }
    void TogglePause()
    {
        try
        {
            var path = Path.Combine(Root, "config.local.json"); var data = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(path));
            data["enabled"] = !Convert.ToBoolean(data["enabled"]); var temp = path + ".monitor.tmp";
            File.WriteAllText(temp, json.Serialize(data), new System.Text.UTF8Encoding(false)); File.Replace(temp, path, null); RefreshData();
        }
        catch { MessageBox.Show("No se ha podido cambiar la selección. Inténtalo de nuevo.", WindowTitle); }
    }
    string Status(string status)
    {
        switch (status) { case "inProgress": case "active": case "running": return "Trabajando";
            case "pending": return "Enviando"; case "completed": case "idle": return "Finalizada / en espera";
            case "interrupted": return "Interrumpida"; case "failed": case "error": return "Error";
            case "waiting": return "Esperando"; default: return "Sin confirmar"; }
    }
    void RefreshData()
    {
        try
        {
            var cfg = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(Root, "config.local.json")));
            bool enabled = Convert.ToBoolean(cfg["enabled"]); pause.Text = enabled ? "Pausar selección" : "Activar selección";
            var folder = Path.Combine(Root, "state"); var rows = new Dictionary<string, Dictionary<string, object>>();
            Directory.CreateDirectory(folder);
            bool cachedCatalog = catalog.Count > 0;
            if (catalog.Count == 0 && File.Exists(Path.Combine(folder, "catalog.json")))
            {
                catalog = D(json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(folder, "catalog.json")))["models"]);
                cachedCatalog = true;
            }
            int connected = 0, modern = 0, accepted = 0, cheaper = 0;
            foreach (var file in Directory.GetFiles(folder, "status-*.json").OrderBy(File.GetLastWriteTimeUtc))
            {
                Dictionary<string, object> data;
                try
                {
                    data = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(file));
                    using (var p = Process.GetProcessById(Convert.ToInt32(data["pid"])))
                    { if (p.HasExited || !p.ProcessName.StartsWith("python", StringComparison.OrdinalIgnoreCase)) continue; }
                    if (data.ContainsKey("heartbeat") && DateTimeOffset.UtcNow.ToUnixTimeSeconds() - Convert.ToDouble(data["heartbeat"]) > 12) continue;
                }
                catch { continue; }
                connected++;
                if (data.ContainsKey("threads"))
                {
                    modern++; foreach (var pair in D(data["threads"])) rows[pair.Key] = D(pair.Value);
                    if (data.ContainsKey("catalog")) foreach (var pair in D(data["catalog"])) { catalog[pair.Key] = pair.Value; cachedCatalog = false; }
                    if (data.ContainsKey("stats")) { var stats = D(data["stats"]); accepted += Convert.ToInt32(stats["accepted"]); cheaper += Convert.ToInt32(stats["non_astra"]); }
                }
                else if (data.ContainsKey("events"))
                {
                    foreach (var entry in (IEnumerable)data["events"])
                    {
                        var ev = D(entry); var tid = S(ev, "thread"); if (tid == "") continue;
                        Dictionary<string, object> row; if (!rows.TryGetValue(tid, out row)) rows[tid] = row = new Dictionary<string, object>();
                        foreach (var key in new[] { "model", "effort", "reason" }) if (ev.ContainsKey(key)) row[key] = ev[key];
                        row["name"] = tid.Substring(0, Math.Min(8, tid.Length)); row["confirmation"] = "Registro v1; último ajuste"; row["status"] = "unknown";
                    }
                }
            }
            string selected = activity.SelectedRows.Count > 0 ? Convert.ToString(activity.SelectedRows[0].Tag) : null;
            activity.Rows.Clear();
            foreach (var pair in rows.OrderByDescending(x => S(x.Value, "status") == "inProgress").ThenByDescending(x => S(x.Value, "updated")).Take(200))
            {
                var row = pair.Value; string name = S(row, "name", pair.Key.Substring(0, Math.Min(8, pair.Key.Length)));
                if (S(row, "parent") != "") name = "↳ " + name;
                bool pending = S(row, "status") == "pending";
                var index = activity.Rows.Add(name, Model(pending ? S(row, "requested_model", "Sin confirmar") : S(row, "model", "Sin confirmar")),
                    Effort(pending ? S(row, "requested_effort") : S(row, "effort")), Status(S(row, "status")),
                    pending ? "Pendiente de aceptación" : S(row, "confirmation", "Sin confirmar"), S(row, "reason", "Observado; sin decisión del selector"));
                activity.Rows[index].Tag = pair.Key;
                if (pair.Key == selected) activity.Rows[index].Selected = true;
            }
            connection.Text = connected == 0 ? "Sin conexión con Codex automático" :
                modern == 0 ? "Conectado a v1 · La mejora se cargará al reabrir Codex" :
                enabled ? "Selección automática activa · Actualización cada 2 segundos" : "Selección pausada · Monitor conectado";
            baseline.Text = "Referencia personal: Astra · Muy alto. " + (modern == 0 ? "Contadores disponibles al reabrir Codex con la mejora." : cheaper + " de " + accepted + " envíos aceptados con otro modelo (esta conexión).") + "\n" +
                "Esto no es un porcentaje de cuota ahorrada. Solo se muestran tareas y agentes observables por esta conexión.";
            levels.Rows.Clear();
            string[] usage = { "Transformaciones sencillas y cambios mecánicos.", "Explicaciones y trabajo habitual delimitado.", "Ingeniería compleja y trabajo visual con alcance claro.", "Auditorías, UX, arquitectura amplia e investigación exigente.", "Problemas especialmente difíciles o intentos fallidos reiterados.", "Petición expresa. En Codex activa también delegación proactiva." };
            for (int i = 0; i < Efforts.Length; i++)
            {
                var available = catalog.Where(x => new[] { "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "gpt-6-astra" }.Contains(x.Key) && ((IEnumerable)x.Value).Cast<object>().Any(e => Convert.ToString(e) == Efforts[i])).Select(x => Model(x.Key)).ToArray();
                levels.Rows.Add(Labels[i], usage[i], catalog.Count == 0 ? "Pendiente de recibir el catálogo de Codex" : available.Length == 0 ? "No disponible" : String.Join(", ", available) + (cachedCatalog ? " (última consulta)" : ""));
            }
        }
        catch { connection.Text = "Esperando una lectura válida del estado…"; }
    }
    protected override void Dispose(bool disposing)
    { if (disposing) { timer.Dispose(); tray.Visible = false; tray.Dispose(); } base.Dispose(disposing); }
}
