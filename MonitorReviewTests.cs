using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Globalization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

// Local layout regressions. Fixtures are never written as router status snapshots.
internal sealed partial class ModernRouterMonitor
{
    static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    static void SaveVisual(FrameworkElement element, string path, double scale)
    {
        element.UpdateLayout();
        var monitor = element as ModernRouterMonitor;
        var bitmap = new RenderTargetBitmap((int)Math.Ceiling(element.ActualWidth * scale),
            (int)Math.Ceiling(element.ActualHeight * scale), 96 * scale, 96 * scale, PixelFormats.Pbgra32);
        bitmap.Render(element);
        BitmapSource output = bitmap;
        if (monitor != null)
        {
            var offset = monitor.surface.TransformToAncestor(monitor).Transform(new Point());
            output = new CroppedBitmap(bitmap, new Int32Rect((int)Math.Round(offset.X * scale), (int)Math.Round(offset.Y * scale),
                (int)Math.Floor(monitor.surface.ActualWidth * scale), (int)Math.Floor(monitor.surface.ActualHeight * scale)));
        }
        var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(output));
        using (var stream = File.Create(path)) encoder.Save(stream);
    }

    static Dictionary<string, object> Fixture(string name, string model, string effort, string status)
    {
        return new Dictionary<string, object> { { "name", name }, { "model", model }, { "effort", effort },
            { "status", status }, { "confirmation", "Aceptado por Codex" },
            { "reason", "Revisión de interfaces y experiencia de usuario: se prioriza la calidad visual y la comprensión del conjunto." } };
    }

    static string TagText(StackPanel panel, int index)
    {
        return ((TextBlock)((Border)panel.Children[index]).Child).Text;
    }

    static bool ContainsText(DependencyObject node, string value)
    {
        var block = node as TextBlock;
        if (block != null && (block.Text ?? "").Contains(value)) return true;
        for (int i = 0; i < VisualTreeHelper.GetChildrenCount(node); i++)
            if (ContainsText(VisualTreeHelper.GetChild(node, i), value)) return true;
        return false;
    }

    static double Luminance(Color color)
    {
        var c = new[] { color.R / 255.0, color.G / 255.0, color.B / 255.0 }
            .Select(x => x <= .04045 ? x / 12.92 : Math.Pow((x + .055) / 1.055, 2.4)).ToArray();
        return c[0] * .2126 + c[1] * .7152 + c[2] * .0722;
    }

    void PaintFixtures()
    {
        connection.Text = "4 tareas activas"; connection.Foreground = Good;
        var avatarRows = new List<KeyValuePair<string, Dictionary<string, object>>> {
            new KeyValuePair<string, Dictionary<string, object>>("ui", Fixture("Pulir la cápsula de agentes", "gpt-6-astra", "high", "active")),
            new KeyValuePair<string, Dictionary<string, object>>("fix", Fixture("Corregir el formulario", "gpt-5.6-terra", "medium", "active")),
            new KeyValuePair<string, Dictionary<string, object>>("test", Fixture("Comprobar el historial", "gpt-5.6-sol", "high", "active")) };
        RefreshAgentCapsule(avatarRows, false);
        ApplyFocus("example", Fixture("Revisar el monitor de Codex", "gpt-6-astra", "xhigh", "active"), 4);
        taskList.Children.Clear(); taskList.Children.Add(Section("ACTIVIDAD"));
        var names = new[] { "Traducir un mensaje", "Ajustar un componente", "Revisar la arquitectura", "Auditar una interfaz", "Resolver un error complejo", "Investigación a fondo" };
        var models = new[] { "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "gpt-6-astra", "gpt-5.6-sol", "gpt-6-astra" };
        var efforts = new[] { "low", "medium", "high", "xhigh", "max", "ultra" };
        for (int i = 0; i < names.Length; i++) taskList.Children.Add(TaskRow("example-" + i,
            Fixture(names[i], models[i], efforts[i], i < 3 ? "active" : "idle")));
    }

    void CheckAnimatedAnchor(MonitorMode target)
    {
        double bottom = shell.TransformToAncestor(this).Transform(new Point(0, shell.ActualHeight)).Y + Top;
        double windowTop = Top, windowHeight = ActualHeight;
        int frames = 0; double maxDrift = 0;
        var loop = new DispatcherFrame();
        EventHandler handler = delegate
        {
            frames++;
            var current = shell.TransformToAncestor(this).Transform(new Point(0, shell.ActualHeight)).Y + Top;
            maxDrift = Math.Max(maxDrift, Math.Abs(current - bottom));
            maxDrift = Math.Max(maxDrift, Math.Abs(Top - windowTop));
            maxDrift = Math.Max(maxDrift, Math.Abs(ActualHeight - windowHeight));
        };
        var stop = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(650) };
        stop.Tick += delegate { loop.Continue = false; stop.Stop(); };
        CompositionTarget.Rendering += handler;
        try { SwitchMode(target, true); stop.Start(); Dispatcher.PushFrame(loop); }
        finally { CompositionTarget.Rendering -= handler; stop.Stop(); }
        Check(frames >= 2 && maxDrift < 1.1, "Animated bottom edge drift: " + maxDrift + "; frames: " + frames);
    }

    void CheckLiveStatistics()
    {
        string path = Path.GetTempFileName();
        var rows = new List<KeyValuePair<string, Dictionary<string, object>>>();
        try
        {
            analyticsSignature = null; analyticsConnected = true;
            File.WriteAllText(path, "");
            rows.Add(new KeyValuePair<string, Dictionary<string, object>>("legacy", Fixture("Legacy task", "gpt-5.6-sol", "medium", "active")));
            RefreshAnalytics(rows, path); SelectMonitorTab(2); UpdateLayout();
            Check(decisions.Count == 0 && !ContainsText(statisticsContent, "vuelve a abrir"), "Resumed tasks counted as decisions or triggered a false restart warning");
            rows.Clear();
            var created = new Dictionary<string, object> { { "decision_id", "one" }, { "event", "decision_created" },
                { "thread", "same" }, { "model", "gpt-5.6-terra" }, { "effort", "medium" }, { "time", 100 } };
            File.AppendAllText(path, Json.Serialize(created) + Environment.NewLine);
            RefreshAnalytics(rows, path); Check(decisions.Count == 1, "First decision missing");
            created["decision_id"] = "two"; created["time"] = 101;
            File.AppendAllText(path, Json.Serialize(created) + Environment.NewLine);
            RefreshAnalytics(rows, path); Check(decisions.Count == 2, "Repeated task did not increase decision count");
            File.AppendAllText(path, Json.Serialize(new { decision_id = "two", @event = "decision_usage", inputTokens = 40, time = 102 }) + Environment.NewLine);
            RefreshAnalytics(rows, path); Check(decisions.Count == 2 && decisions.First(d => d.Id == "two").InputTokens == 40, "Usage duplicated a decision or failed to refresh");
            var live = Fixture("Live task", "gpt-5.6-terra", "medium", "active"); live["decision_id"] = "two";
            live["tokens"] = new Dictionary<string, object> { { "inputTokens", 55 } }; rows.Add(new KeyValuePair<string, Dictionary<string, object>>("same", live));
            RefreshAnalytics(rows, path); Check(decisions.Count == 2 && decisions.First(d => d.Id == "two").InputTokens == 55, "Live usage failed to refresh without timestamp change");
            live["tokens"] = new Dictionary<string, object> { { "inputTokens", 61 } };
            RefreshAnalytics(rows, path); Check(decisions.First(d => d.Id == "two").InputTokens == 61, "Unchanged timestamp blocked live usage refresh");
            File.AppendAllText(path, Json.Serialize(new { decision_id = "two", @event = "decision_accepted", time = 103 }) + Environment.NewLine);
            rows.Clear(); analyticsSignature = null; decisions.Clear(); analyticsConnected = false;
            RefreshAnalytics(rows, path);
            Check(decisions.Count == 2 && decisions.Count(d => d.Accepted) == 1, "Persisted totals lost on reconnect without live rows");
            string recoveredPath = Path.ChangeExtension(path, ".recovered.jsonl");
            File.WriteAllText(recoveredPath, Json.Serialize(new { decision_id = "old", @event = "decision_recovered", source = "recovered",
                model = "gpt-5.6-sol", effort = "high", time = 50 }) + Environment.NewLine);
            RefreshAnalytics(rows, path);
            Check(decisions.Count == 3 && decisions.Count(d => d.Accepted) == 2, "Recovered history not added to accumulated totals");
            analyticsSignature = null; decisions.Clear(); RefreshAnalytics(rows, path);
            Check(decisions.Count == 3 && decisions.Count(d => d.Accepted) == 2, "Second load duplicated or lost historical decisions");
            File.AppendAllText(path, Json.Serialize(new { decision_id = "two", @event = "decision_quality", quality = "adequate", time = 200 }) + Environment.NewLine);
            RefreshAnalytics(rows, path);
            Check(decisions.First(d => d.Id == "two").Quality == "adequate", "Quality rating not loaded");
            File.AppendAllText(path, Json.Serialize(new { decision_id = "two", @event = "decision_quality", quality = "", time = 201 }) + Environment.NewLine);
            analyticsSignature = null; decisions.Clear(); RefreshAnalytics(rows, path);
            Check(decisions.First(d => d.Id == "two").Quality == "" && decisions.First(d => d.Id == "two").Time == 103,
                "Cleared rating did not survive reload or changed execution time");
            File.AppendAllText(path, Json.Serialize(new { decision_id = "two", @event = "engine_comparison", routing_engine = "jev", engine_active = true, time = 104 }) + Environment.NewLine);
            File.AppendAllText(path, Json.Serialize(new { decision_id = "two", @event = "engine_comparison", routing_engine = "rules", engine_active = false, time = 104 }) + Environment.NewLine);
            File.AppendAllText(path, Json.Serialize(new { decision_id = "two", @event = "decision_routed", routing_engine = "jev", engine_applied = true, time = 104 }) + Environment.NewLine);
            RefreshAnalytics(rows, path);
            Check(decisions.First(d => d.Id == "two").RoutingEngine == "jev" && decisions.First(d => d.Id == "two").Comparisons.Count == 2,
                "Shadow engine overwrote deciding engine in statistics");
            Check(ContainsText(statisticsContent, "FIABILIDAD DE LOS MOTORES") && ContainsText(statisticsContent, "respuestas válidas"),
                "Engine reliability telemetry is absent from statistics");
        }
        finally { File.Delete(path); File.Delete(Path.ChangeExtension(path, ".recovered.jsonl")); analyticsSignature = null; }
    }

    static void RunUiFor(int milliseconds)
    {
        var frame = new DispatcherFrame();
        var stop = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(milliseconds) };
        stop.Tick += delegate { stop.Stop(); frame.Continue = false; };
        stop.Start(); Dispatcher.PushFrame(frame);
    }

    static IEnumerable<T> Descendants<T>(DependencyObject node) where T : DependencyObject
    {
        for (int i = 0; i < VisualTreeHelper.GetChildrenCount(node); i++)
        {
            var child = VisualTreeHelper.GetChild(node, i);
            if (child is T) yield return (T)child;
            foreach (var descendant in Descendants<T>(child)) yield return descendant;
        }
    }

    void CheckSettingsInteraction()
    {
        foreach (string engine in new[] { "rules", "jev" })
        {
            settingsContent.Children.Clear(); BuildRoutingEngineSettings(engine); UpdateLayout();
            Check(settingsContent.Children.OfType<TextBlock>().Any(text => text.Text == "JEV") == (engine == "jev"), "Jev configuration visible under wrong engine");
            if (engine == "jev")
                Check(ContainsText(settingsContent, "Vercel AI Gateway") && ContainsText(settingsContent, "TypeSafe directo"),
                    "Jev connection selector is incomplete on Windows");
            var comparisons = settingsContent.Children.OfType<WrapPanel>().ElementAt(1).Children.OfType<Button>().ToList();
            Check(comparisons.Count == 2 && comparisons.Count(button => !button.IsEnabled) == 1, "Missing Rules comparison or active engine duplicated");
            foreach (var button in settingsContent.Children.OfType<WrapPanel>().SelectMany(panel => panel.Children.OfType<Button>()))
                Check(button.BorderThickness.Left == 1 && button.Background != TransparentBrush, "Unselected option has no visible outline");
            if (engine != "rules")
            {
                var key = settingsContent.Children.OfType<StackPanel>().First();
                var open = (Button)key.Children[0];
                int windows = Application.Current.Windows.Count;
                open.RaiseEvent(new RoutedEventArgs(Button.ClickEvent)); UpdateLayout();
                var password = Descendants<PasswordBox>(key).Single();
                Check(password.IsVisible && windows == Application.Current.Windows.Count, "Key editor opened another window or stayed hidden");
                var scroll = (ScrollViewer)settingsPage.Children[0]; scroll.ScrollToEnd(); UpdateLayout();
                SaveVisual(this, Path.Combine(StateFolder, "review-settings-" + engine + "-inline.png"), 1);
                password.Password = "test-only-not-saved";
                var cancel = Descendants<Button>(key).First(button => Convert.ToString(button.Content) == "Cancelar");
                cancel.RaiseEvent(new RoutedEventArgs(Button.ClickEvent)); UpdateLayout();
                Check(password.Password == "" && !password.IsVisible, "Cancel retained the secret or editor");
            }
            SaveVisual(this, Path.Combine(StateFolder, "review-settings-" + engine + ".png"), 1);
        }
        RefreshSettings();
    }

    void CheckAgentCapsule()
    {
        SwitchMode(MonitorMode.Compact, false); PaintFixtures(); UpdateLayout();
        Check(agentAvatars.Count == 3 && activeAgentRows.Count == 3, "Active avatars missing");
        Check(IdentifyAgent(activeAgentRows["ui"]).Name == "Interfaces" && IdentifyAgent(activeAgentRows["fix"]).Name == "Corrección", "Task icon catalog is not differentiated");
        var catalog = new Dictionary<string, string> { { "interface", "Interfaces" }, { "correction", "Corrección" },
            { "tests", "Pruebas" }, { "audit", "Auditoría" }, { "architecture", "Arquitectura" }, { "text", "Textos" },
            { "research", "Investigación" }, { "configuration", "Configuración" }, { "automation", "Automatización" }, { "general", "Tarea" } };
        foreach (var entry in catalog)
        {
            var row = Fixture("Título genérico", "gpt-5.6-terra", "medium", "active"); row["agent_category"] = entry.Key;
            Check(IdentifyAgent(row).Name == entry.Value, "Stored agent category did not select " + entry.Value);
        }
        var original = agentAvatars["ui"];
        // Check the rendered arc against the face center at every rotation quadrant.
        // This catches a moving/off-center orbit even when its source arc is circular.
        SetAgentOrbit(original, false); UpdateLayout();
        var art = (Grid)original.Button.Content;
        var face = art.Children.OfType<Border>().First(child => Convert.ToString(child.Tag) == "agent-face");
        var sweep = art.Children.OfType<Grid>().First(child => Convert.ToString(child.Tag) == "orbit-sweep");
        var arc = (System.Windows.Shapes.Path)sweep.Children[0];
        Point faceCenter = face.TransformToAncestor(art).Transform(new Point(face.ActualWidth / 2, face.ActualHeight / 2));
        var drawn = arc.RenderedGeometry.GetFlattenedPathGeometry();
        for (int angle = 0; angle < 360; angle += 30)
        {
            original.Orbit.Angle = angle;
            for (int part = 0; part <= 8; part++)
            {
                Point point, tangent; drawn.GetPointAtFractionLength(part / 8.0, out point, out tangent);
                point = arc.TransformToAncestor(art).Transform(point);
                double radius = (point - faceCenter).Length;
                Check(Math.Abs(radius - 20) < .35 && radius > face.ActualWidth / 2 + 3,
                    "Rendered orbit is not circular and outside the face: radius=" + radius);
            }
        }
        SetAgentOrbit(original, true);
        // Reasoning can change without changing model, task or working state.
        foreach (string level in new[] { "low", "medium", "high", "xhigh", "max", "ultra", "" })
        {
            var changed = new Dictionary<string, object>(original.Row); changed["effort"] = level;
            UpdateAgentAvatar(original, changed);
            var dot = ((Grid)original.Button.Content).Children.OfType<Border>().First(child => Convert.ToString(child.Tag) == "agent-effort");
            Brush expected = level == "" ? Muted : BadgeColor(Effort(level), false);
            Check(((SolidColorBrush)dot.Background).Color == ((SolidColorBrush)expected).Color, "Reasoning dot did not refresh for " + level);
        }
        UpdateAgentAvatar(original, activeAgentRows["ui"]);
        var rows = activeAgentRows.Reverse().ToList();
        RefreshAgentCapsule(rows, false);
        Check(agentOrder.First() == "ui" && object.ReferenceEquals(original, agentAvatars["ui"]), "Refresh reordered or recreated active agents");
        if (SystemParameters.ClientAreaAnimation) Check(original.Orbit.HasAnimatedProperties, "Working avatar lacks orbit");
        double bottom = Top + shell.TransformToAncestor(this).Transform(new Point(0, shell.ActualHeight)).Y;
        double drift = 0;
        EventHandler sample = delegate { drift = Math.Max(drift, Math.Abs(Top + shell.TransformToAncestor(this).Transform(new Point(0, shell.ActualHeight)).Y - bottom)); };
        CompositionTarget.Rendering += sample;
        try
        {
            original.Button.RaiseEvent(new System.Windows.Input.MouseEventArgs(System.Windows.Input.Mouse.PrimaryDevice, 0) { RoutedEvent = UIElement.MouseEnterEvent });
            RunUiFor(500); UpdateLayout();
            Check(mode == MonitorMode.Compact && peekAgentId == "ui" && surface.ActualHeight > 160, "Hover did not expand an attached detail");
            Check(ContainsText(agentPeekContent, "Pulir") && ContainsText(agentPeekContent, "Astra") && ContainsText(agentPeekContent, "Alto"), "Peek lacks task/model/effort");
            SaveVisual(this, Path.Combine(StateFolder, "review-agent-peek.png"), 1);
            compactView.RaiseEvent(new System.Windows.Input.MouseEventArgs(System.Windows.Input.Mouse.PrimaryDevice, 0) { RoutedEvent = UIElement.MouseLeaveEvent });
            RunUiFor(100);
            compactView.RaiseEvent(new System.Windows.Input.MouseEventArgs(System.Windows.Input.Mouse.PrimaryDevice, 0) { RoutedEvent = UIElement.MouseEnterEvent });
            RunUiFor(180); Check(peekAgentId == "ui", "Moving toward the detail closed it");
            CloseAgentPeek(true); RunUiFor(500); UpdateLayout();
            Check(Math.Abs(surface.ActualHeight - 80) < 1 && drift < 1.1, "Peek displaced bottom edge or failed to collapse");
        }
        finally { CompositionTarget.Rendering -= sample; }
        rows = rows.Where(pair => pair.Key != "ui").ToList(); RefreshAgentCapsule(rows, true);
        RunUiFor(80);
        rows.Add(new KeyValuePair<string, Dictionary<string, object>>("ui", Fixture("Pulir la cápsula de agentes", "gpt-5.6-terra", "medium", "active")));
        RefreshAgentCapsule(rows, true); RunUiFor(500);
        Check(agentAvatars.Count == 3 && !agentAvatars["ui"].Leaving, "Reactivation during exit lost or duplicated avatar");
        ShowAgentPeek("ui", false); UpdateLayout();
        Check(ContainsText(agentPeekContent, "Terra") && ContainsText(agentPeekContent, "Medio"), "Changed model or effort was not reflected in peek");
        CloseAgentPeek(false);
        for (int i = 0; i < 5; i++) rows.Add(new KeyValuePair<string, Dictionary<string, object>>("extra-" + i, Fixture("Prueba adicional " + i, "gpt-5.6-sol", "high", "active")));
        RefreshAgentCapsule(rows, false); UpdateLayout();
        Check(agentAvatars.Count == 5 && moreAgents.Content.ToString() == "+3", "Overflow agents are not capped at five");
        Check(agentStrip.ActualWidth < surface.ActualWidth - 50, "Avatar strip overflows capsule");
        SaveVisual(this, Path.Combine(StateFolder, "review-agents-overflow.png"), 1);
        moreAgents.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Check(mode == MonitorMode.Expanded, "Overflow action did not open the detailed panel");
        Check(agentAvatars.Values.All(v => !v.Orbit.HasAnimatedProperties), "Hidden capsule keeps orbit clocks running");
        SwitchMode(MonitorMode.Compact, false);
        RefreshAgentCapsule(new List<KeyValuePair<string, Dictionary<string, object>>>(), true); RunUiFor(500); UpdateLayout();
        Check(agentAvatars.Count == 0 && compactCount.Text == "Sin tareas activas", "Inactive agents were not removed");
        SaveVisual(this, Path.Combine(StateFolder, "review-agents-idle.png"), 1);
        PaintFixtures(); UpdateLayout();
    }

    public int RunReviewChecks()
    {
        string report = Path.Combine(StateFolder, "ui-review-checks.txt");
        var results = new List<string>();
        try
        {
            foreach (var work in new[] { new Rect(0, 0, 1920, 1040), new Rect(0, 0, 2560, 1400), new Rect(0, 0, 1536, 824),
                new Rect(0, 0, 1280, 680), new Rect(-1920, 0, 1920, 1040), new Rect(0, -900, 1600, 900), new Rect(0, 0, 800, 480) })
            {
                var compact = Geometry(MonitorMode.Compact, work); var expanded = Geometry(MonitorMode.Expanded, work);
                Check(compact.Bottom == expanded.Bottom && compact.Right == expanded.Right, "Views lost shared bottom-right anchor");
                Check(work.Contains(compact) && work.Contains(expanded), "View exceeds working area");
                Check(Math.Abs(work.Bottom - expanded.Bottom - 10) < .1, "Panel is not bottom anchored");
                Check(Math.Abs(expanded.Height - Math.Min(work.Height - 20, Math.Max(560, work.Height * .9))) < .1, "Panel does not use available display height");
                foreach (var ratio in new[] { .2, .7, 1.0, 2.0, Double.NaN, Double.PositiveInfinity })
                {
                    var resized = Geometry(MonitorMode.Expanded, work, ratio);
                    Check(work.Contains(resized) && resized.Bottom == compact.Bottom, "Manual height escaped screen or moved bottom");
                }
            }
            results.Add("PASS: adaptive/manual heights and fixed bottom-right anchor across seven work areas, including 1080p, 1440p and small scaled displays");
            Topmost = false;
            SwitchMode(MonitorMode.Expanded, false); PaintFixtures(); UpdateLayout();
            Dispatcher.Invoke(delegate { }, DispatcherPriority.Render);
            double resizeBottom = Top + surface.TransformToAncestor(this).Transform(new Point(0, surface.ActualHeight)).Y;
            SetPanelHeight(CurrentScreen(), 600); UpdateLayout();
            Check(Math.Abs(Top + surface.TransformToAncestor(this).Transform(new Point(0, surface.ActualHeight)).Y - resizeBottom) < 1.1, "Resizing shifted bottom edge");
            double preferred = surface.ActualHeight;
            SwitchMode(MonitorMode.Compact, false); SwitchMode(MonitorMode.Expanded, false); UpdateLayout();
            Check(Math.Abs(surface.ActualHeight-preferred) < 1.1, "Height preference lost when collapsing");
            Check(heightGrip.Visibility == Visibility.Visible, "Expanded panel lacks resize handle");
            panelHeights.Clear(); ApplyPanelHeight(); UpdateLayout();
            results.Add("PASS: manual resize preserves lower edge and survives compact/expanded transition");
            Check(mainTags.Children.Cast<Border>().All(badge => Math.Abs(badge.ActualHeight - 24) < .1),
                "Featured badges do not share the same height");
            Check(ModeTransitionDuration.TotalMilliseconds >= 350, "Mode transition is still too abrupt");
            double? previousX = null;
            int activityRowIndex = 0;
            foreach (Border card in taskList.Children.OfType<Border>())
            {
                var row = (Grid)card.Child;
                Check(card.CornerRadius.TopLeft >= 10 && card.Padding.Left >= 8, "Activity hover card lacks rounded padding");
                Check(Math.Abs(row.ColumnDefinitions[0].ActualWidth - 56) < .1, "Activity avatar lacks text spacing");
                var avatar = (AgentAvatar)row.Children.OfType<Border>().First(child => child.Tag is AgentAvatar).Tag;
                Check(avatar.ActivityView, "Activity row is not using the shared agent avatar");
                Check(System.Windows.Automation.AutomationProperties.GetName(avatar.Button).Contains(activityRowIndex < 3 ? "Trabajando" : "En espera"), "Activity state indicator mismatch");
                if (SystemParameters.ClientAreaAnimation)
                    Check(avatar.Orbit.HasAnimatedProperties == (activityRowIndex < 3), "Activity orbit does not match working state");
                activityRowIndex++;
                var tags = row.Children.OfType<StackPanel>().Last();
                double x = tags.TransformToAncestor(taskList).Transform(new Point()).X;
                Check(!previousX.HasValue || Math.Abs(previousX.Value - x) < .1, "Activity tags are ragged"); previousX = x;
                foreach (Border tag in tags.Children)
                {
                    var text = (TextBlock)tag.Child;
                    var formatted = new FormattedText(text.Text, CultureInfo.CurrentCulture, FlowDirection.LeftToRight,
                        new Typeface(text.FontFamily, text.FontStyle, text.FontWeight, text.FontStretch), text.FontSize, text.Foreground);
                    Check(formatted.Width <= tag.ActualWidth - tag.Padding.Left - tag.Padding.Right + 1, "Clipped badge: " + text.Text);
                    Check(text.TextAlignment == TextAlignment.Center, "Badge text not centered");
                    double contrast = (Luminance(((SolidColorBrush)text.Foreground).Color) + .05) /
                        (Luminance(((SolidColorBrush)tag.Background).Color) + .05);
                    Check(contrast >= 4.5, "Insufficient text contrast: " + text.Text);
                }
            }
            results.Add("PASS: featured badges share 24 DIP height; all six efforts fit and contrast >= 4.5:1");
            results.Add("PASS: Activity uses shared model/task avatars; active agents orbit and idle agents stay still with text spacing");
            CheckAnimatedAnchor(MonitorMode.Compact); CheckAnimatedAnchor(MonitorMode.Expanded);
            results.Add("PASS: render-frame sampling keeps native window and lower surface edge fixed during both 420 ms transitions");
            foreach (double scale in new[] { 1.0, 1.25, 1.5, 2.0 })
                SaveVisual(this, Path.Combine(StateFolder, "review-panel-" + (int)(scale * 100) + ".png"), scale);

            for (int i = 0; i < 20; i++) taskList.Children.Add(TaskRow("overflow-" + i,
                Fixture("Tarea adicional " + i, "gpt-5.6-terra", "medium", "active")));
            UpdateLayout();
            Check(activityScroll.ExtentHeight > activityScroll.ViewportHeight, "Overflow has no scrollable area");
            activityScroll.ScrollToEnd(); UpdateLayout();
            Check(activityScroll.VerticalOffset > 0, "Cannot reach last tasks");
            SaveVisual(this, Path.Combine(StateFolder, "review-scroll.png"), 1);
            results.Add("PASS: long activity list scrolls to final task");

            var pending = Fixture("Cambio de modelo pendiente", "gpt-5.6-luna", "low", "pending");
            pending["requested_model"] = "gpt-6-astra"; pending["requested_effort"] = "xhigh";
            ApplyFocus("pending", pending, 1);
            Check(TagText(mainTags, 0) == "Astra" && TagText(mainTags, 1) == "Muy alto", "Pending turn shows previous settings");
            Check(confirmation.Text.Contains("pendiente"), "Pending selection shown as accepted");
            results.Add("PASS: pending selection shows requested settings and unconfirmed evidence");

            SwitchMode(MonitorMode.Compact, true);
            SwitchMode(MonitorMode.Hidden, true);
            SwitchMode(MonitorMode.Expanded, true);
            SwitchMode(MonitorMode.Compact, false); PaintFixtures(); UpdateLayout();
            Check(compactView.Visibility == Visibility.Visible && expandedView.Visibility == Visibility.Collapsed, "Both views visible");
            Check(Math.Abs(surface.ActualHeight - 80) < 1, "Stale animation restored wrong geometry");
            var arrow = expandAgents;
            var glyph = (FrameworkElement)arrow.Content;
            double arrowY = glyph.TransformToAncestor(compactView).Transform(new Point(0, glyph.ActualHeight / 2)).Y;
            Check(!double.IsNaN(arrowY), "Capsule arrow has invalid geometry");
            CheckAgentCapsule();
            results.Add("PASS: agent orbit, stable ordering, attached hover, exit/reactivation race, model changes, overflow and idle cleanup");
            SaveVisual(this, Path.Combine(StateFolder, "review-capsule.png"), 1);
            results.Add("PASS: rapid expand/hide/reveal/collapse keeps a single correctly sized surface");
            Check(trayCompact.IsChecked && !trayExpanded.IsChecked && !trayHidden.IsChecked, "Tray view selection missing");
            foreach (bool pinned in new[] { true, false })
            {
                Topmost = !pinned;
                trayTopmost.RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
                Check(Topmost == pinned, "Topmost menu action did not toggle the window");
                Check(trayTopmost.IsChecked == pinned, "Tray topmost state is incorrect");
                var header = (Grid)trayTopmost.Header;
                Check(((TextBlock)header.Children[1]).Text == (pinned ? "Activado" : "Desactivado"), "Topmost state label missing");
                trayMenu.PlacementTarget = this; trayMenu.HorizontalOffset = Left; trayMenu.VerticalOffset = Top;
                trayMenu.IsOpen = true; trayMenu.UpdateLayout();
                Dispatcher.Invoke(delegate { }, DispatcherPriority.Render);
                SaveVisual(trayMenu, Path.Combine(StateFolder, "review-menu-" + (pinned ? "on" : "off") + ".png"), 1);
                trayMenu.IsOpen = false;
            }
            results.Add("PASS: tray topmost action toggles the window; view and on/off indicators render correctly");
            ApplyEmpty(); connection.Text = "Sin conexión"; connection.Foreground = Warning;
            SwitchMode(MonitorMode.Expanded, false); taskList.Children.Clear();
            taskList.Children.Add(EmptyRow("No hay otras tareas observables"));
            SaveVisual(this, Path.Combine(StateFolder, "review-empty.png"), 1);
            results.Add("PASS: disconnected/empty view renders");

            CheckLiveStatistics();
            results.Add("PASS: decisions and accepted totals persist without live tasks; recovered records merge without duplicates; resumed tasks trigger no false warning");
            var savedTelemetry = new Dictionary<string, double>(telemetryHealth);
            bool savedReceiver = telemetryReceiverAvailable;
            try
            {
                var noTasks = new List<KeyValuePair<string, Dictionary<string, object>>>();
                string absentHistory = Path.Combine(StateFolder, "review-telemetry-" + Guid.NewGuid().ToString("N") + ".jsonl");
                telemetryHealth.Clear(); telemetryReceiverAvailable = true;
                RefreshAnalytics(noTasks, absentHistory);
                var firstStatistics = statisticsContent.Children[0];
                telemetryHealth["requests"] = 2;
                RefreshAnalytics(noTasks, absentHistory);
                Check(!Object.ReferenceEquals(firstStatistics, statisticsContent.Children[0]),
                    "Telemetry counters changed but the statistics view did not refresh");
                if (ReadConfigBool("inference_telemetry", false))
                {
                    SelectMonitorTab(2); UpdateLayout();
                    Check(ContainsText(statisticsContent, "Recibiendo"), "Received telemetry is not reflected in receiver status");
                }
            }
            finally
            {
                telemetryHealth.Clear(); foreach (var pair in savedTelemetry) telemetryHealth[pair.Key] = pair.Value;
                telemetryReceiverAvailable = savedReceiver; analyticsSignature = null;
            }
            results.Add("PASS: telemetry-only changes refresh statistics without a new task or history event");
            SelectMonitorTab(2); UpdateLayout();
            SaveVisual(this, Path.Combine(StateFolder, "review-statistics-live.png"), 1);
            PaintAnalyticsFixtures();
            Check(monitorTabs.Count == 4, "Expected four monitor tabs");
            SelectMonitorTab(1); UpdateLayout(); Dispatcher.Invoke(delegate { }, DispatcherPriority.Render);
            Check(historyPage.Visibility == Visibility.Visible && activityScroll.Visibility == Visibility.Collapsed,
                "History tab is not exclusive");
            Check(historyList.Children.Count >= 5, "History list did not render decisions");
            Check(ContainsText(historyDetail, "Revisar el monitor"),
                "History details did not select a decision");
            Check(ContainsText(historyDetail, "interfaces"),
                "Model reason is absent from decision details");
            Check(ContainsText(historyDetail, "profunda"),
                "Effort reason is absent from decision details");
            var historyHover = historyList.Children.OfType<Button>().First();
            historyHover.RaiseEvent(new System.Windows.Input.MouseEventArgs(System.Windows.Input.Mouse.PrimaryDevice, 0) { RoutedEvent = UIElement.MouseEnterEvent });
            Check(historyHover.Background == Panel2, "History hover is not visible");
            SaveVisual(this, Path.Combine(StateFolder, "review-history.png"), 1);
            historyHover.RaiseEvent(new System.Windows.Input.MouseEventArgs(System.Windows.Input.Mouse.PrimaryDevice, 0) { RoutedEvent = UIElement.MouseLeaveEvent });
            OpenHistoryForThread("translation"); UpdateLayout();
            Check(ContainsText(historyDetail, "Traducir"),
                "Activity-to-history navigation did not select its thread");
            results.Add("PASS: Activity opens matching History; model and effort reasons remain available after completion");

            SelectMonitorTab(2); UpdateLayout(); Dispatcher.Invoke(delegate { }, DispatcherPriority.Render);
            Check(statisticsContent.Children.OfType<StackPanel>().Any(), "Statistics metrics are empty");
            SaveVisual(this, Path.Combine(StateFolder, "review-statistics.png"), 1);
            SelectMonitorTab(3); UpdateLayout(); Dispatcher.Invoke(delegate { }, DispatcherPriority.Render);
            Check(settingsContent.Children.OfType<Button>().Count() >= 2, "Settings controls are missing");
            SaveVisual(this, Path.Combine(StateFolder, "review-settings.png"), 1);
            CheckSettingsInteraction();
            results.Add("PASS: outlined selectors, Rules comparison, engine-specific settings, inline keys with cancel, persistent rating removal and active-engine attribution");
            results.Add("PASS: Statistics and Settings tabs contain real metrics and working controls");
            var phases = Fixture("Pipeline de Windows", "gpt-5.6-terra", "medium", "active");
            phases["phase_status"] = "active"; phases["pipeline_mode"] = "plan_and_observation";
            phases["accepted_model"] = "gpt-5.6-terra"; phases["accepted_effort"] = "medium";
            phases["configured_model"] = "gpt-5.6-sol"; phases["configured_effort"] = "high";
            phases["phase_pipeline"] = new object[] {
                new Dictionary<string, object> { { "id", "investigate" }, { "label", "Investigar" }, { "state", "selected" }, { "evidence", "plan" } },
                new Dictionary<string, object> { { "id", "decide" }, { "label", "Decidir" }, { "state", "planned" }, { "evidence", "plan" } },
                new Dictionary<string, object> { { "id", "codex_execution" }, { "label", "Ejecución en Codex" }, { "state", "active" }, { "evidence", "observed" } }
            };
            SelectMonitorTab(0); ApplyFocus("phase-test", phases, 1); UpdateLayout();
            Check(ContainsText(phaseHost, "PLAN DE TRABAJO") && ContainsText(phaseHost, "Investigar") && ContainsText(phaseHost, "Planificada") && ContainsText(phaseHost, "En curso"),
                "Native Windows Activity omitted the phase pipeline");
            SaveVisual(this, Path.Combine(StateFolder, "review-phase-activity.png"), 1.25);
            var phaseDecision = new DecisionRecord { Id = "phase-test", Title = "Pipeline de Windows", Model = "Terra", Effort = "Medio" };
            ApplyHistoryEvent(phaseDecision, phases);
            Check(String(phaseDecision.PhaseEvidence, "configured_model") == "gpt-5.6-sol" && String(phaseDecision.PhaseEvidence, "observed_model") == "",
                "Settings were promoted to inference evidence");
            SelectMonitorTab(1); ShowDecision(phaseDecision); UpdateLayout();
            Check(ContainsText(historyDetail, "EVIDENCIA DEL MODELO") && ContainsText(historyDetail, "sin confirmación disponible"),
                "Native history omitted provenance or claimed inference");
            SaveVisual(this, Path.Combine(StateFolder, "review-phase-history.png"), 1.25);
            decisions.Clear(); decisions.Add(phaseDecision); SelectMonitorTab(2); RebuildStatistics(); UpdateLayout();
            Check(ContainsText(statisticsContent, "Configuraciones publicadas") && ContainsText(statisticsContent, "Inferencias confirmadas"),
                "Native statistics omitted phase evidence");
            results.Add("PASS: native phase pipeline, history provenance and statistics preserve unknown inference evidence");
            Check(ContainsText(expandedView, "v" + ProductVersion), "Product version is not visible in the monitor footer");
            results.Add("PASS: product version is embedded at build time and visible in the footer");
            foreach (int count in new[] { 1000, 10000 })
            {
                string benchmark = Path.Combine(StateFolder, "review-benchmark.jsonl");
                using (var writer = new StreamWriter(benchmark, false, new System.Text.UTF8Encoding(false)))
                    for (int i = 0; i < count; i++) writer.WriteLine(Json.Serialize(new Dictionary<string, object> {
                        {"event", "decision_created"}, {"decision_id", "benchmark-" + i}, {"thread", "synthetic-" + i},
                        {"title", "Synthetic task " + i}, {"time", 1000 + i}, {"model", "gpt-5.6-terra"},
                        {"effort", "medium"}, {"product_version", "0.3.0"}, {"routing_policy_version", 3}}));
                var clock = System.Diagnostics.Stopwatch.StartNew();
                RefreshAnalytics(new List<KeyValuePair<string, Dictionary<string, object>>>(), benchmark);
                clock.Stop();
                Check(decisions.Count == count, "Large history lost decisions");
                Check(historyList.Children.Count <= 43, "History rendering exceeded one page");
                Check(clock.ElapsedMilliseconds < 5000, "Large history projection is unexpectedly slow");
                results.Add("PASS: " + count + " decisions projected in " + clock.ElapsedMilliseconds + " ms; history rows bounded to 40");
            }
            File.WriteAllLines(report, results); quitting = true; Close(); return 0;
        }
        catch (Exception exception)
        {
            results.Add("FAIL: " + exception.ToString()); File.WriteAllLines(report, results);
            quitting = true; Close(); return 1;
        }
    }
}
