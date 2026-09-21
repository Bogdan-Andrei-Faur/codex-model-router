using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Threading;

internal sealed partial class ModernRouterMonitor
{
    sealed class AgentAvatar
    {
        public string Id, Signature;
        public Dictionary<string, object> Row;
        public Border Slot;
        public Button Button;
        public RotateTransform Orbit;
        public bool Leaving;
    }

    sealed class AgentIdentity
    {
        public string Name, Path;
        public AgentIdentity(string name, string path) { Name = name; Path = path; }
    }

    readonly StackPanel agentStrip = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Center };
    readonly StackPanel agentPeekContent = new StackPanel();
    readonly ScrollViewer agentPeek = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
        HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, Visibility = Visibility.Collapsed };
    readonly Dictionary<string, AgentAvatar> agentAvatars = new Dictionary<string, AgentAvatar>();
    readonly List<string> agentOrder = new List<string>();
    readonly Dictionary<string, Dictionary<string, object>> activeAgentRows = new Dictionary<string, Dictionary<string, object>>();
    readonly DispatcherTimer peekCloseTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(220) };
    readonly TextBlock agentsIdle = Txt("Todo en calma", 13, Muted);
    Button moreAgents, expandAgents;
    string peekAgentId, peekSignature;

    void BuildAgentCapsule()
    {
        compactView.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        compactView.RowDefinitions.Add(new RowDefinition { Height = new GridLength(80) });
        agentPeek.Content = agentPeekContent;
        agentPeek.Margin = new Thickness(18, 14, 18, 0);
        Grid.SetRow(agentPeek, 0); compactView.Children.Add(agentPeek);
        var bar = new Grid { Margin = new Thickness(14, 8, 10, 8) };
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(32) });
        var crew = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
        agentStrip.Height = 44; crew.Children.Add(agentStrip);
        compactCount.FontSize = 11; compactCount.Foreground = Muted;
        compactCount.HorizontalAlignment = HorizontalAlignment.Center;
        compactCount.Margin = new Thickness(0, 2, 0, 0); crew.Children.Add(compactCount);
        bar.Children.Add(crew);
        expandAgents = Btn("", delegate { SwitchMode(MonitorMode.Expanded, true); }, true);
        expandAgents.MinWidth = 28; expandAgents.VerticalAlignment = VerticalAlignment.Center;
        expandAgents.Content = new System.Windows.Shapes.Path { Data = System.Windows.Media.Geometry.Parse("M5,0 L0,5 L5,10"),
            Stroke = Muted, StrokeThickness = 1.6, StrokeStartLineCap = PenLineCap.Round, StrokeEndLineCap = PenLineCap.Round,
            Width = 6, Height = 10, Stretch = Stretch.Uniform };
        expandAgents.ToolTip = "Desplegar panel lateral";
        System.Windows.Automation.AutomationProperties.SetName(expandAgents, "Desplegar panel lateral");
        Grid.SetColumn(expandAgents, 1); bar.Children.Add(expandAgents);
        Grid.SetRow(bar, 1); compactView.Children.Add(bar);
        moreAgents = Btn("", delegate { SwitchMode(MonitorMode.Expanded, true); }, false);
        moreAgents.MinWidth = 0; moreAgents.Width = 34; moreAgents.Padding = new Thickness(0);
        moreAgents.Background = Panel2; moreAgents.VerticalAlignment = VerticalAlignment.Center;
        agentsIdle.HorizontalAlignment = HorizontalAlignment.Center; agentsIdle.Margin = new Thickness(0, 9, 0, 0);
        peekCloseTimer.Tick += delegate { peekCloseTimer.Stop(); CloseAgentPeek(true); };
        compactView.MouseEnter += delegate { peekCloseTimer.Stop(); };
        compactView.MouseLeave += delegate { peekCloseTimer.Stop(); peekCloseTimer.Start(); };
        compactView.LostKeyboardFocus += delegate { if (!compactView.IsKeyboardFocusWithin) peekCloseTimer.Start(); };
        compactView.PreviewKeyDown += delegate(object sender, KeyEventArgs e)
        { if (e.Key == Key.Escape) { CloseAgentPeek(true); e.Handled = true; } };
    }

    // Task category is an indicative local classification. It never affects routing.
    static AgentIdentity IdentifyAgent(Dictionary<string, object> row)
    {
        string name = String(row, "name").ToLowerInvariant();
        var found = MatchAgentIdentity(name);
        return found ?? MatchAgentIdentity(String(row, "model_reason", String(row, "reason")).ToLowerInvariant())
            ?? new AgentIdentity("Tarea", "M12,2 A10,10 0 1 1 11.99,2 M12,7 L12,17 M7,12 L17,12");
    }

    static AgentIdentity MatchAgentIdentity(string text)
    {
        if (Regex.IsMatch(text, @"auditor|audit|seguridad|security|accesibilidad"))
            return new AgentIdentity("Auditoría", "M9,2 L15,2 L15,4 L20,4 L20,12 M12,22 L4,22 L4,4 L9,4 Z M8,8 L12,8 M8,12 L10,12 M16,12 A4,4 0 1 1 15.99,12 M19,19 L23,23");
        if (Regex.IsMatch(text, @"\b(test|tests|prueba|pruebas|e2e)\b|comprobar|verificar|validar"))
            return new AgentIdentity("Pruebas", "M8,2 L16,2 M10,2 L10,9 L4,19 Q3,22 6,22 L18,22 Q21,22 20,19 L14,9 L14,2 M7,15 L17,15 M9,18 L10,18 M14,19 L15,19");
        if (Regex.IsMatch(text, @"arquitect|architect|migraci|infraestructura"))
            return new AgentIdentity("Arquitectura", "M9,2 L15,2 L15,8 L9,8 Z M2,16 L8,16 L8,22 L2,22 Z M16,16 L22,16 L22,22 L16,22 Z M12,8 L12,12 M5,16 L5,12 L19,12 L19,16");
        if (Regex.IsMatch(text, @"correg|corrig|error|fallo|bug|arregl|fix"))
            return new AgentIdentity("Corrección", "M8,7 L16,7 L17,11 L17,16 A5,5 0 0 1 7,16 L7,11 Z M9,7 L9,4 L15,4 L15,7 M9,4 L7,2 M15,4 L17,2 M3,10 L7,12 M17,12 L21,10 M3,16 L7,16 M17,16 L21,16 M5,22 L8,19 M16,19 L19,22 M12,8 L12,20");
        if (Regex.IsMatch(text, @"traduc|translat|texto|textos|document|resum"))
            return new AgentIdentity("Textos", "M4,3 L20,3 M12,3 L12,21 M8,21 L16,21 M4,3 L4,7 M20,3 L20,7");
        if (Regex.IsMatch(text, @"interfaz|interfaces|frontend|front.end|diseñ|design|cápsula|capsula|\b(ui|ux)\b"))
            return new AgentIdentity("Interfaces", "M3,3 L21,3 L21,21 L3,21 Z M3,8 L21,8 M8,8 L8,21 M5,5.5 L6,5.5 M9,5.5 L10,5.5");
        if (Regex.IsMatch(text, @"investig|investiga|research|analiz"))
            return new AgentIdentity("Investigación", "M10,2 A8,8 0 1 1 9.99,2 M16,16 L23,23 M6,10 L14,10 M10,6 L10,14");
        return null;
    }

    static ControlTemplate AvatarTemplate()
    {
        var border = new FrameworkElementFactory(typeof(Border));
        border.SetValue(Border.CornerRadiusProperty, new CornerRadius(21));
        border.SetBinding(Border.BackgroundProperty, new System.Windows.Data.Binding("Background") {
            RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        var content = new FrameworkElementFactory(typeof(ContentPresenter));
        content.SetValue(ContentPresenter.HorizontalAlignmentProperty, HorizontalAlignment.Center);
        content.SetValue(ContentPresenter.VerticalAlignmentProperty, VerticalAlignment.Center);
        border.AppendChild(content);
        var template = new ControlTemplate(typeof(Button)) { VisualTree = border };
        var hover = new Trigger { Property = Button.IsMouseOverProperty, Value = true };
        hover.Setters.Add(new Setter(Button.OpacityProperty, .85)); template.Triggers.Add(hover);
        var focus = new Trigger { Property = Button.IsKeyboardFocusedProperty, Value = true };
        focus.Setters.Add(new Setter(Button.BackgroundProperty, Panel2)); template.Triggers.Add(focus);
        return template;
    }

    AgentAvatar MakeAgentAvatar(string id, Dictionary<string, object> row)
    {
        var visual = new AgentAvatar { Id = id, Row = row };
        visual.Button = new Button { Width = 40, Height = 40, Padding = new Thickness(0),
            BorderThickness = new Thickness(0), Template = AvatarTemplate(), Cursor = Cursors.Hand };
        visual.Slot = new Border { Width = 44, Height = 44, Child = visual.Button, Background = TransparentBrush,
            RenderTransform = new TranslateTransform(), VerticalAlignment = VerticalAlignment.Center };
        visual.Button.MouseEnter += delegate { ShowAgentPeek(id, true); };
        visual.Button.GotKeyboardFocus += delegate { ShowAgentPeek(id, true); };
        visual.Button.Click += delegate { ShowAgentPeek(id, true); };
        UpdateAgentAvatar(visual, row);
        return visual;
    }

    void UpdateAgentAvatar(AgentAvatar visual, Dictionary<string, object> row)
    {
        visual.Row = row;
        string model = Model(Setting(row, "model", "Sin confirmar"));
        var identity = IdentifyAgent(row);
        string signature = model + ":" + identity.Name;
        System.Windows.Automation.AutomationProperties.SetName(visual.Button,
            String(row, "name", visual.Id) + " · " + model + " · " + Effort(Setting(row, "effort", "")) + " · " + Status(String(row, "status")));
        if (signature == visual.Signature) return;
        visual.Signature = signature;
        if (visual.Orbit != null) visual.Orbit.BeginAnimation(RotateTransform.AngleProperty, null);
        Brush color = BadgeColor(model, true);
        visual.Button.Background = ((Border)Badge(model, true)).Background;
        var art = new Grid { Width = 40, Height = 40 };
        var glyph = new System.Windows.Shapes.Path { Data = System.Windows.Media.Geometry.Parse(identity.Path), Stroke = color,
            StrokeThickness = 1.5, StrokeStartLineCap = PenLineCap.Round, StrokeEndLineCap = PenLineCap.Round,
            StrokeLineJoin = PenLineJoin.Round, Width = 19, Height = 19, Stretch = Stretch.Uniform,
            HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center };
        art.Children.Add(glyph);
        var tint = ((SolidColorBrush)color).Color;
        var orbitBrush = new LinearGradientBrush();
        orbitBrush.StartPoint = new Point(0, 0); orbitBrush.EndPoint = new Point(1, 1);
        orbitBrush.GradientStops.Add(new GradientStop(Color.FromArgb(0, tint.R, tint.G, tint.B), 0));
        orbitBrush.GradientStops.Add(new GradientStop(tint, 1));
        var ring = new System.Windows.Shapes.Path { Data = System.Windows.Media.Geometry.Parse("M20,0 A20,20 0 1 1 0,20"),
            Stroke = orbitBrush, StrokeThickness = 1.4, IsHitTestVisible = false, RenderTransformOrigin = new Point(.5, .5),
            Width = 42, Height = 42, HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center };
        visual.Orbit = new RotateTransform(); ring.RenderTransform = visual.Orbit; art.Children.Add(ring);
        art.Children.Add(new Border { Width = 7, Height = 7, CornerRadius = new CornerRadius(4), Background = color,
            BorderBrush = Panel, BorderThickness = new Thickness(1), HorizontalAlignment = HorizontalAlignment.Right,
            VerticalAlignment = VerticalAlignment.Bottom, Margin = new Thickness(0, 0, 1, 1), IsHitTestVisible = false });
        visual.Button.Content = art;
        SetAgentOrbit(visual, mode == MonitorMode.Compact && IsVisible);
    }

    static void SetAgentOrbit(AgentAvatar visual, bool active)
    {
        if (visual.Orbit == null) return;
        if (active && !visual.Leaving && SystemParameters.ClientAreaAnimation)
        {
            if (!visual.Orbit.HasAnimatedProperties)
                visual.Orbit.BeginAnimation(RotateTransform.AngleProperty,
                    new DoubleAnimation(0, 360, TimeSpan.FromSeconds(3.2)) { RepeatBehavior = RepeatBehavior.Forever });
        }
        else visual.Orbit.BeginAnimation(RotateTransform.AngleProperty, null);
    }

    void RefreshAgentCapsule(IEnumerable<KeyValuePair<string, Dictionary<string, object>>> rows, bool animate = true)
    {
        activeAgentRows.Clear();
        foreach (var pair in rows.Where(pair => Active(String(pair.Value, "status")))) activeAgentRows[pair.Key] = pair.Value;
        agentOrder.RemoveAll(id => !activeAgentRows.ContainsKey(id));
        foreach (string id in activeAgentRows.Keys) if (!agentOrder.Contains(id)) agentOrder.Add(id);
        int limit = Math.Max(1, Math.Min(5, (int)((TargetGeometry(MonitorMode.Compact).Width - 16 - 2 - 24 - 32 - 34) / 44)));
        var visibleIds = new HashSet<string>(agentOrder.Take(limit));
        agentStrip.Children.Remove(moreAgents); agentStrip.Children.Remove(agentsIdle);
        foreach (var visual in agentAvatars.Values.ToList())
        {
            if (visibleIds.Contains(visual.Id)) continue;
            if (visual.Leaving) continue;
            visual.Leaving = true; SetAgentOrbit(visual, false);
            AnimateAgentSlot(visual, false, animate && mode == MonitorMode.Compact && IsVisible);
        }
        foreach (string id in agentOrder.Take(limit))
        {
            AgentAvatar visual;
            if (!agentAvatars.TryGetValue(id, out visual))
            {
                visual = MakeAgentAvatar(id, activeAgentRows[id]); agentAvatars[id] = visual;
                agentStrip.Children.Add(visual.Slot);
                AnimateAgentSlot(visual, true, animate && mode == MonitorMode.Compact && IsVisible);
            }
            else
            {
                UpdateAgentAvatar(visual, activeAgentRows[id]);
                if (visual.Leaving) { visual.Leaving = false; AnimateAgentSlot(visual, true, animate && IsVisible); }
            }
            SetAgentOrbit(visual, mode == MonitorMode.Compact && IsVisible);
        }
        int overflow = Math.Max(0, activeAgentRows.Count - limit);
        if (overflow > 0)
        {
            moreAgents.Content = "+" + overflow;
            moreAgents.ToolTip = "Ver los " + activeAgentRows.Count + " agentes en el panel lateral";
            agentStrip.Children.Add(moreAgents);
        }
        if (activeAgentRows.Count == 0) agentStrip.Children.Add(agentsIdle);
        compactCount.Text = activeAgentRows.Count == 0 ? "Sin tareas activas" : activeAgentRows.Count +
            (activeAgentRows.Count == 1 ? " agente activo" : " agentes activos");
        if (peekAgentId != null)
        {
            if (!activeAgentRows.ContainsKey(peekAgentId)) CloseAgentPeek(animate);
            else ShowAgentPeek(peekAgentId, animate);
        }
    }

    void AnimateAgentSlot(AgentAvatar visual, bool entering, bool animate)
    {
        double from = visual.Slot.ActualWidth;
        visual.Slot.BeginAnimation(WidthProperty, null); visual.Slot.BeginAnimation(OpacityProperty, null);
        var translation = (TranslateTransform)visual.Slot.RenderTransform;
        translation.BeginAnimation(TranslateTransform.YProperty, null);
        if (!animate || !SystemParameters.ClientAreaAnimation)
        {
            visual.Slot.Width = entering ? 44 : 0; visual.Slot.Opacity = entering ? 1 : 0;
            if (!entering) RemoveAgentAvatar(visual); return;
        }
        visual.Slot.Width = entering ? 44 : 0; visual.Slot.Opacity = entering ? 1 : 0;
        var easing = new CubicEase { EasingMode = EasingMode.EaseOut };
        var width = new DoubleAnimation(from, entering ? 44 : 0, ModeTransitionDuration) { EasingFunction = easing, FillBehavior = FillBehavior.Stop };
        if (!entering) width.Completed += delegate { if (visual.Leaving) RemoveAgentAvatar(visual); };
        visual.Slot.BeginAnimation(WidthProperty, width);
        visual.Slot.BeginAnimation(OpacityProperty, new DoubleAnimation(entering ? 0 : 1, entering ? 1 : 0, ModeTransitionDuration) { FillBehavior = FillBehavior.Stop });
        translation.BeginAnimation(TranslateTransform.YProperty, new DoubleAnimation(entering ? 8 : 0, entering ? 0 : 8, ModeTransitionDuration) { EasingFunction = easing, FillBehavior = FillBehavior.Stop });
    }

    void RemoveAgentAvatar(AgentAvatar visual)
    {
        SetAgentOrbit(visual, false);
        agentStrip.Children.Remove(visual.Slot); agentAvatars.Remove(visual.Id);
    }

    void ShowAgentPeek(string id, bool animate)
    {
        if (mode != MonitorMode.Compact || !activeAgentRows.ContainsKey(id)) return;
        peekCloseTimer.Stop();
        var row = activeAgentRows[id];
        string signature = id + ":" + Json.Serialize(row.Where(pair => new[] { "name", "model", "effort", "requested_model", "requested_effort", "status", "reason" }.Contains(pair.Key)).ToDictionary(pair => pair.Key, pair => pair.Value));
        if (peekAgentId == id && signature == peekSignature) return;
        peekAgentId = id; peekSignature = signature;
        agentPeekContent.Children.Clear();
        string model = Model(Setting(row, "model", "Sin confirmar"));
        var identity = IdentifyAgent(row);
        var category = Txt(identity.Name, 11, BadgeColor(model, true), FontWeights.SemiBold);
        category.ToolTip = "Tipo orientativo según el título y la descripción de la tarea"; agentPeekContent.Children.Add(category);
        var name = Txt(String(row, "name", id), 15, Ink, FontWeights.SemiBold);
        name.TextWrapping = TextWrapping.Wrap; name.Margin = new Thickness(0, 6, 0, 10); agentPeekContent.Children.Add(name);
        var tags = new StackPanel { Orientation = Orientation.Horizontal };
        FillTags(tags, model, Effort(Setting(row, "effort", ""))); agentPeekContent.Children.Add(tags);
        var status = Txt(Status(String(row, "status")), 12, Muted); status.Margin = new Thickness(0, 10, 0, 12);
        agentPeekContent.Children.Add(status);
        agentPeekContent.Children.Add(new Border { Height = 1, Background = Line });
        agentPeek.Visibility = Visibility.Visible;
        double width = Math.Max(1, TargetGeometry(MonitorMode.Compact).Width - 16 - 38);
        agentPeekContent.Measure(new Size(width, double.PositiveInfinity));
        ResizeAgentSurface(Math.Min(Height - 16, 80 + agentPeekContent.DesiredSize.Height + 16), animate);
    }

    void CloseAgentPeek(bool animate)
    {
        peekCloseTimer.Stop(); peekAgentId = null; peekSignature = null;
        if (mode == MonitorMode.Compact) ResizeAgentSurface(Math.Min(80, Height - 16), animate);
    }

    void ResizeAgentSurface(double height, bool animate)
    {
        double from = surface.ActualHeight;
        surface.BeginAnimation(HeightProperty, null); surface.Height = Math.Max(1, height);
        if (animate && IsVisible && SystemParameters.ClientAreaAnimation)
            surface.BeginAnimation(HeightProperty, new DoubleAnimation(from, surface.Height, ModeTransitionDuration)
            { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseInOut }, FillBehavior = FillBehavior.Stop });
    }
}
