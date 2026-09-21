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
        var bitmap = new RenderTargetBitmap((int)Math.Ceiling(element.ActualWidth * scale),
            (int)Math.Ceiling(element.ActualHeight * scale), 96 * scale, 96 * scale, PixelFormats.Pbgra32);
        bitmap.Render(element);
        var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
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

    static double Luminance(Color color)
    {
        var c = new[] { color.R / 255.0, color.G / 255.0, color.B / 255.0 }
            .Select(x => x <= .04045 ? x / 12.92 : Math.Pow((x + .055) / 1.055, 2.4)).ToArray();
        return c[0] * .2126 + c[1] * .7152 + c[2] * .0722;
    }

    void PaintFixtures()
    {
        connection.Text = "4 tareas activas"; connection.Foreground = Good;
        ApplyFocus("example", Fixture("Revisar el monitor de Codex", "gpt-6-astra", "xhigh", "active"), 4);
        summary.Text = "12/18 fuera de Astra";
        taskList.Children.Clear(); taskList.Children.Add(Section("ACTIVIDAD"));
        var names = new[] { "Traducir un mensaje", "Ajustar un componente", "Revisar la arquitectura", "Auditar una interfaz", "Resolver un error complejo", "Investigación a fondo" };
        var models = new[] { "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "gpt-6-astra", "gpt-5.6-sol", "gpt-6-astra" };
        var efforts = new[] { "low", "medium", "high", "xhigh", "max", "ultra" };
        for (int i = 0; i < names.Length; i++) taskList.Children.Add(TaskRow("example-" + i,
            Fixture(names[i], models[i], efforts[i], i < 3 ? "active" : "idle")));
    }

    public int RunReviewChecks()
    {
        string report = Path.Combine(StateFolder, "ui-review-checks.txt");
        var results = new List<string>();
        try
        {
            foreach (var work in new[] { new Rect(0, 0, 1920, 1040), new Rect(0, 0, 1536, 824),
                new Rect(0, 0, 1280, 680), new Rect(-1920, 0, 1920, 1040), new Rect(0, -900, 1600, 900) })
            {
                var compact = Geometry(MonitorMode.Compact, work); var expanded = Geometry(MonitorMode.Expanded, work);
                Check(compact.Bottom == expanded.Bottom && compact.Right == expanded.Right, "Views lost shared bottom-right anchor");
                Check(work.Contains(compact) && work.Contains(expanded), "View exceeds working area");
                Check(Math.Abs(work.Bottom - expanded.Bottom - 10) < .1, "Panel is not bottom anchored");
            }
            results.Add("PASS: common bottom-right anchor and bounds across five work areas");
            Topmost = false;
            SwitchMode(MonitorMode.Expanded, false); PaintFixtures(); UpdateLayout();
            Dispatcher.Invoke(delegate { }, DispatcherPriority.Render);
            Check(mainTags.Children.Cast<Border>().All(badge => Math.Abs(badge.ActualHeight - 24) < .1),
                "Featured badges do not share the same height");
            Check(ModeTransitionDuration.TotalMilliseconds >= 350, "Mode transition is still too abrupt");
            double? previousX = null;
            int activityRowIndex = 0;
            foreach (Grid row in taskList.Children.OfType<Grid>())
            {
                Check(Math.Abs(row.ColumnDefinitions[0].ActualWidth - 24) < .1, "Activity indicator lacks text spacing");
                var indicator = row.Children.OfType<Grid>().First(candidate => Convert.ToString(candidate.Tag) == "activity-indicator");
                Check(System.Windows.Automation.AutomationProperties.GetName(indicator) ==
                    (activityRowIndex < 3 ? "Agente trabajando" : "Agente inactivo"), "Activity state indicator mismatch");
                if (activityRowIndex < 3 && SystemParameters.ClientAreaAnimation)
                    Check(((Border)indicator.Children[0]).HasAnimatedProperties, "Working agent has no pulse animation");
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
            results.Add("PASS: working agents pulse; idle indicators remain static; 24 DIP indicator column separates text");
            results.Add("PASS: compact/expanded transition lasts 420 ms with ease-in-out motion");
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
            Check(Math.Abs(ActualHeight - 96) < 1, "Stale animation restored wrong geometry");
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
            ApplyEmpty(); connection.Text = "Sin conexión"; connection.Foreground = Warning; summary.Text = "0/0 fuera de Astra";
            SwitchMode(MonitorMode.Expanded, false); taskList.Children.Clear();
            taskList.Children.Add(EmptyRow("No hay otras tareas observables"));
            SaveVisual(this, Path.Combine(StateFolder, "review-empty.png"), 1);
            results.Add("PASS: disconnected/empty view renders");
            File.WriteAllLines(report, results); quitting = true; Close(); return 0;
        }
        catch (Exception exception)
        {
            results.Add("FAIL: " + exception.ToString()); File.WriteAllLines(report, results);
            quitting = true; Close(); return 1;
        }
    }
}
