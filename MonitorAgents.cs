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
        public RotateTransform CompactionRotation;
        public ScaleTransform CompactionScale;
        public bool Leaving, ActivityView;
    }

    sealed class AgentIdentity
    {
        public string Name, Path, Icon;
        public AgentIdentity(string name, string icon) { Name = name; Icon = icon; Path = LucidePath(icon); }
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
    Button quotaButton, panelQuotaButton;
    readonly TextBlock quotaPanelText = Txt("", 12, Muted);
    readonly Border quotaDetailsPanel = new Border { Visibility = Visibility.Collapsed };
    readonly Border featuredAgentHost = new Border();
    AgentAvatar featuredAvatar;
    static readonly DateTime AgentOrbitEpoch = DateTime.UtcNow;
    string peekAgentId, peekSignature;

    void BuildAgentCapsule()
    {
        compactView.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        compactView.RowDefinitions.Add(new RowDefinition { Height = new GridLength(80) });
        agentPeek.Content = agentPeekContent;
        agentPeek.Margin = new Thickness(18, 14, 18, 0);
        Grid.SetRow(agentPeek, 0); compactView.Children.Add(agentPeek);
        var bar = new Grid { Margin = new Thickness(12, 8, 12, 8) };
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(40) });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(48) });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(40) });
        var crew = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
        agentStrip.Height = 44; crew.Children.Add(agentStrip);
        var codexLogo = Logo(40);
        codexLogo.ToolTip = "Codex automático";
        Grid.SetColumn(codexLogo, 0); bar.Children.Add(codexLogo);
        Grid.SetColumn(crew, 1); bar.Children.Add(crew);
        quotaButton = Btn("—", delegate { ShowQuotaPeek(); }, true);
        quotaButton.Width = 44; quotaButton.MinWidth = 44; quotaButton.Height = 44;
        quotaButton.Padding = new Thickness(0); quotaButton.Template = AvatarTemplate();
        Grid.SetColumn(quotaButton, 2); bar.Children.Add(quotaButton);
        RefreshQuota(new Dictionary<string, object>(), false);
        expandAgents = Btn("", delegate { SwitchMode(MonitorMode.Expanded, true); }, true);
        expandAgents.MinWidth = 28; expandAgents.VerticalAlignment = VerticalAlignment.Center;
        expandAgents.Content = LucideGlyph("panel-left-open", 18, Muted);
        expandAgents.ToolTip = "Desplegar panel lateral";
        System.Windows.Automation.AutomationProperties.SetName(expandAgents, "Desplegar panel lateral");
        var expandDivider = new Border { BorderBrush = Line, BorderThickness = new Thickness(1, 0, 0, 0),
            Padding = new Thickness(6, 0, 0, 0), Height = 38, VerticalAlignment = VerticalAlignment.Center, Child = expandAgents };
        Grid.SetColumn(expandDivider, 3); bar.Children.Add(expandDivider);
        Grid.SetRow(bar, 1); compactView.Children.Add(bar);
        moreAgents = Btn("", delegate { SwitchMode(MonitorMode.Expanded, true); }, false);
        moreAgents.MinWidth = 0; moreAgents.Width = 34; moreAgents.Padding = new Thickness(0);
        moreAgents.Background = Panel2; moreAgents.VerticalAlignment = VerticalAlignment.Center;
        agentsIdle.HorizontalAlignment = HorizontalAlignment.Center; agentsIdle.VerticalAlignment = VerticalAlignment.Center;
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
        var routed = IdentityFromCategory(String(row, "agent_category"));
        if (routed != null) return routed;
        string name = String(row, "name").ToLowerInvariant();
        var found = MatchAgentIdentity(name);
        return found ?? MatchAgentIdentity(String(row, "model_reason", String(row, "reason")).ToLowerInvariant())
            ?? new AgentIdentity("Tarea", "circle-plus");
    }

    static AgentIdentity IdentityFromCategory(string category)
    {
        switch (category)
        {
            case "audit": return new AgentIdentity("Auditoría", "clipboard-check");
            case "tests": return new AgentIdentity("Pruebas", "flask-conical");
            case "architecture": return new AgentIdentity("Arquitectura", "network");
            case "correction": return new AgentIdentity("Corrección", "bug");
            case "text": return new AgentIdentity("Textos", "text");
            case "interface": return new AgentIdentity("Interfaces", "panels-top-left");
            case "research": return new AgentIdentity("Investigación", "search");
            case "configuration": return new AgentIdentity("Configuración", "settings-2");
            case "automation": return new AgentIdentity("Automatización", "workflow");
            case "general": return new AgentIdentity("Tarea", "circle-plus");
            case "data": return new AgentIdentity("Datos", "database");
            case "performance": return new AgentIdentity("Rendimiento", "gauge");
            case "deployment": return new AgentIdentity("Despliegues", "rocket");
            case "versioning": return new AgentIdentity("Versiones", "git-branch");
            case "integration": return new AgentIdentity("Integraciones", "plug");
            case "accessibility": return new AgentIdentity("Accesibilidad", "accessibility");
            default: return null;
        }
    }

    static AgentIdentity MatchAgentIdentity(string text)
    {
        if (Regex.IsMatch(text, @"auditor|audit|seguridad|security|accesibilidad"))
            return new AgentIdentity("Auditoría", "clipboard-check");
        if (Regex.IsMatch(text, @"\b(test|tests|prueba|pruebas|e2e)\b|comprobar|verificar|validar"))
            return new AgentIdentity("Pruebas", "flask-conical");
        if (Regex.IsMatch(text, @"arquitect|architect|migraci|infraestructura"))
            return new AgentIdentity("Arquitectura", "network");
        if (Regex.IsMatch(text, @"correg|corrig|error|fallo|bug|arregl|fix"))
            return new AgentIdentity("Corrección", "bug");
        if (Regex.IsMatch(text, @"traduc|translat|texto|textos|document|resum"))
            return new AgentIdentity("Textos", "text");
        if (Regex.IsMatch(text, @"interfaz|interfaces|frontend|front.end|diseñ|design|cápsula|capsula|\b(ui|ux)\b"))
            return new AgentIdentity("Interfaces", "panels-top-left");
        if (Regex.IsMatch(text, @"investig|investiga|research|analiz"))
            return new AgentIdentity("Investigación", "search");
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

    AgentAvatar MakeAgentAvatar(string id, Dictionary<string, object> row, bool activityView = false)
    {
        var visual = new AgentAvatar { Id = id, Row = row, ActivityView = activityView };
        visual.Button = new Button { Width = 44, Height = 44, Padding = new Thickness(0),
            BorderThickness = new Thickness(0), Template = AvatarTemplate(), Cursor = Cursors.Hand };
        visual.Slot = new Border { Width = 44, Height = 44, Child = visual.Button, Background = TransparentBrush,
            RenderTransform = new TranslateTransform(), VerticalAlignment = VerticalAlignment.Center };
        visual.Slot.Tag = visual;
        if (activityView)
            visual.Button.Click += delegate { SelectFeatured(id); };
        else
        {
            visual.Button.MouseEnter += delegate { ShowAgentPeek(id, true); };
            visual.Button.GotKeyboardFocus += delegate { ShowAgentPeek(id, true); };
            visual.Button.Click += delegate { ShowAgentPeek(id, true); };
        }
        visual.Slot.IsVisibleChanged += delegate { SetAgentOrbit(visual, visual.Slot.IsVisible); };
        visual.Slot.Unloaded += delegate { SetAgentOrbit(visual, false); };
        UpdateAgentAvatar(visual, row);
        return visual;
    }

    void UpdateAgentAvatar(AgentAvatar visual, Dictionary<string, object> row)
    {
        visual.Row = row;
        string model = Model(Setting(row, "model", "Sin confirmar"));
        string effort = Effort(Setting(row, "effort", ""));
        var identity = IdentifyAgent(row);
        bool working = Active(String(row, "status"));
        var context = Dict(row.ContainsKey("context_window") ? row["context_window"] : null);
        string compactionState = String(Dict(row.ContainsKey("context_compaction") ? row["context_compaction"] : null), "state");
        bool compacting = compactionState == "compacting";
        string contextLabel = ContextLabel(context, row);
        string signature = model + ":" + effort + ":" + identity.Name + ":" + String(row, "status") + Json.Serialize(context) +
            compactionState;
        System.Windows.Automation.AutomationProperties.SetName(visual.Button,
            String(row, "name", visual.Id) + " · " + model + " · " + Effort(Setting(row, "effort", "")) + " · " + Status(String(row, "status")) + " · " + contextLabel);
        visual.Button.ToolTip = contextLabel;
        if (signature == visual.Signature) return;
        visual.Signature = signature;
        if (visual.Orbit != null) visual.Orbit.BeginAnimation(RotateTransform.AngleProperty, null);
        StopCompactionAnimation(visual);
        visual.CompactionRotation = null; visual.CompactionScale = null;
        Brush color = BadgeColor(model, true);
        visual.Button.Background = TransparentBrush;
        // Keep the face and orbit on the same geometric center at fractional DPI.
        // Inherited pixel rounding can offset the 32 DIP face from the 44 DIP ring.
        var art = new Grid { Width = 44, Height = 44, UseLayoutRounding = false };
        art.Children.Add(new Border { Tag = "agent-face", Width = 32, Height = 32, CornerRadius = new CornerRadius(16),
            Background = Badge(model, true).Background, HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center });
        art.Children.Add(new System.Windows.Shapes.Path { Tag = "orbit-track",
            Data = new EllipseGeometry(new Point(22, 22), 20, 20), Stroke = color, StrokeThickness = 1,
            Opacity = .22, Width = 44, Height = 44, IsHitTestVisible = false });
        var glyph = LucideGlyph(identity.Icon, 19, color);
        art.Children.Add(glyph);
        if (compacting)
        {
            var ring = new Grid { Tag = "compacting-ring", Width = 44, Height = 44, IsHitTestVisible = false };
            ring.Children.Add(new System.Windows.Shapes.Path {
                Data = System.Windows.Media.Geometry.Parse("M22,6 A16,16 0 0 1 38,22 M22,38 A16,16 0 0 1 6,22"),
                Stroke = color, StrokeThickness = 2.5, StrokeStartLineCap = PenLineCap.Round, StrokeEndLineCap = PenLineCap.Round });
            visual.CompactionRotation = new RotateTransform(0, 22, 22);
            visual.CompactionScale = new ScaleTransform(1, 1, 22, 22);
            var transforms = new TransformGroup();
            transforms.Children.Add(visual.CompactionRotation); transforms.Children.Add(visual.CompactionScale);
            ring.RenderTransform = transforms; art.Children.Add(ring);
        }
        else art.Children.Add(UsageRing(16, compactionState == "awaiting_usage" ? null : ContextPercent(context), color, "context-ring"));
        var tint = ((SolidColorBrush)color).Color;
        var orbitBrush = new LinearGradientBrush();
        orbitBrush.StartPoint = new Point(0, 0); orbitBrush.EndPoint = new Point(1, 1);
        orbitBrush.GradientStops.Add(new GradientStop(Color.FromArgb(0, tint.R, tint.G, tint.B), 0));
        orbitBrush.GradientStops.Add(new GradientStop(tint, 1));
        // Rotate a fixed square around an explicit center. A partial path's own
        // bounding box is not its circle's center and makes the orbit wobble.
        var orbitLayer = new Grid { Tag = "orbit-sweep", Width = 44, Height = 44, IsHitTestVisible = false, Visibility = working && !compacting ? Visibility.Visible : Visibility.Collapsed };
        orbitLayer.Children.Add(new System.Windows.Shapes.Path {
            Data = System.Windows.Media.Geometry.Parse("M22,2 A20,20 0 0 1 42,22"),
            Stroke = orbitBrush, StrokeThickness = 1.6, StrokeStartLineCap = PenLineCap.Round,
            StrokeEndLineCap = PenLineCap.Round, Width = 44, Height = 44 });
        visual.Orbit = new RotateTransform(0, 22, 22); orbitLayer.RenderTransform = visual.Orbit; art.Children.Add(orbitLayer);
        art.Children.Add(new Border { Tag = "agent-effort", Width = 8, Height = 8, CornerRadius = new CornerRadius(4),
            Background = effort == "" ? Muted : BadgeColor(effort, false),
            BorderBrush = Panel, BorderThickness = new Thickness(1), HorizontalAlignment = HorizontalAlignment.Right,
            VerticalAlignment = VerticalAlignment.Bottom, Margin = new Thickness(0, 0, 5, 5), IsHitTestVisible = false });
        visual.Button.Content = art;
        SetAgentOrbit(visual, visual.ActivityView ? visual.Slot.IsVisible : mode == MonitorMode.Compact && IsVisible);
    }

    static void SetAgentOrbit(AgentAvatar visual, bool active)
    {
        if (visual.Orbit == null) return;
        bool animate = active && Active(String(visual.Row, "status")) && !visual.Leaving && SystemParameters.ClientAreaAnimation;
        if (animate && visual.CompactionRotation != null)
        {
            if (!visual.CompactionRotation.HasAnimatedProperties)
            {
                visual.CompactionRotation.BeginAnimation(RotateTransform.AngleProperty,
                    new DoubleAnimation(0, -180, TimeSpan.FromSeconds(1.6)) { RepeatBehavior = RepeatBehavior.Forever });
                var pulse = new DoubleAnimation(1, .84, TimeSpan.FromSeconds(.8)) { AutoReverse = true, RepeatBehavior = RepeatBehavior.Forever };
                visual.CompactionScale.BeginAnimation(ScaleTransform.ScaleXProperty, pulse);
                visual.CompactionScale.BeginAnimation(ScaleTransform.ScaleYProperty, pulse);
            }
        }
        else StopCompactionAnimation(visual);
        if (animate && visual.CompactionRotation == null)
        {
            if (!visual.Orbit.HasAnimatedProperties)
            {
                double phase = ((DateTime.UtcNow - AgentOrbitEpoch).TotalSeconds % 3.2) / 3.2 * 360;
                visual.Orbit.BeginAnimation(RotateTransform.AngleProperty,
                    new DoubleAnimation(phase, phase + 360, TimeSpan.FromSeconds(3.2)) { RepeatBehavior = RepeatBehavior.Forever });
            }
        }
        else visual.Orbit.BeginAnimation(RotateTransform.AngleProperty, null);
    }

    static void StopCompactionAnimation(AgentAvatar visual)
    {
        if (visual.CompactionRotation != null) visual.CompactionRotation.BeginAnimation(RotateTransform.AngleProperty, null);
        if (visual.CompactionScale != null)
        {
            visual.CompactionScale.BeginAnimation(ScaleTransform.ScaleXProperty, null);
            visual.CompactionScale.BeginAnimation(ScaleTransform.ScaleYProperty, null);
        }
    }

    void RefreshAgentCapsule(IEnumerable<KeyValuePair<string, Dictionary<string, object>>> rows, bool animate = true)
    {
        activeAgentRows.Clear();
        foreach (var pair in rows.Where(pair => Active(String(pair.Value, "status")))) activeAgentRows[pair.Key] = pair.Value;
        agentOrder.RemoveAll(id => !activeAgentRows.ContainsKey(id));
        foreach (string id in activeAgentRows.Keys) if (!agentOrder.Contains(id)) agentOrder.Add(id);
        int limit = Math.Max(1, Math.Min(5, (int)((TargetGeometry(MonitorMode.Compact).Width - 16 - 2 - 24 - 40 - 40 - 48 - 34) / 44)));
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
        if (peekAgentId != null && peekAgentId != "@account")
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

    void UpdateFeaturedAgent(string id, Dictionary<string, object> row)
    {
        if (featuredAvatar == null || featuredAvatar.Id != id)
        {
            featuredAvatar = MakeAgentAvatar(id, row, true);
            featuredAgentHost.Child = featuredAvatar.Slot;
        }
        else UpdateAgentAvatar(featuredAvatar, row);
    }

    void ShowAgentPeek(string id, bool animate)
    {
        if (mode != MonitorMode.Compact || !activeAgentRows.ContainsKey(id)) return;
        peekCloseTimer.Stop();
        var row = activeAgentRows[id];
        string signature = id + ":" + Json.Serialize(row.Where(pair => new[] { "name", "model", "effort", "requested_model", "requested_effort", "status", "reason", "agent_category", "agent_confidence", "context_window", "context_compaction" }.Contains(pair.Key)).ToDictionary(pair => pair.Key, pair => pair.Value));
        if (peekAgentId == id && signature == peekSignature) return;
        peekAgentId = id; peekSignature = signature;
        agentPeekContent.Children.Clear();
        string model = Model(Setting(row, "model", "Sin confirmar"));
        var identity = IdentifyAgent(row);
        var category = Txt(identity.Name, 11, BadgeColor(model, true), FontWeights.SemiBold);
        string confidence = String(row, "agent_confidence");
        category.ToolTip = confidence == "" ? "Tipo orientativo según el título y la descripción de la tarea" :
            "Tipo determinado al iniciar la tarea · confianza " + confidence;
        agentPeekContent.Children.Add(category);
        var name = Txt(String(row, "name", id), 15, Ink, FontWeights.SemiBold);
        name.TextWrapping = TextWrapping.Wrap; name.Margin = new Thickness(0, 6, 0, 10); agentPeekContent.Children.Add(name);
        var tags = new StackPanel { Orientation = Orientation.Horizontal };
        FillTags(tags, model, Effort(Setting(row, "effort", ""))); agentPeekContent.Children.Add(tags);
        var status = Txt(Status(String(row, "status")), 12, Muted); status.Margin = new Thickness(0, 10, 0, 12);
        agentPeekContent.Children.Add(status);
        var contextText = Txt(ContextLabel(Dict(row.ContainsKey("context_window") ? row["context_window"] : null), row), 12, Muted);
        contextText.TextWrapping = TextWrapping.Wrap; contextText.Margin = new Thickness(0, 0, 0, 12);
        agentPeekContent.Children.Add(contextText);
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

    static double? GaugeValue(Dictionary<string, object> data, string key)
    {
        object raw; double value;
        if (!data.TryGetValue(key, out raw) || raw == null || raw is bool || raw is string ||
            !double.TryParse(Convert.ToString(raw, System.Globalization.CultureInfo.InvariantCulture),
                System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out value) ||
            double.IsNaN(value) || double.IsInfinity(value) || value < 0) return null;
        return value;
    }

    static double? ContextPercent(Dictionary<string, object> context)
    {
        var capacity = GaugeValue(context, "capacity_tokens");
        var used = GaugeValue(context, "used_percent");
        return capacity.HasValue && capacity.Value > 0 && used.HasValue ? (double?)Math.Min(100, used.Value) : null;
    }

    static string ContextLabel(Dictionary<string, object> context, Dictionary<string, object> row)
    {
        string state = String(Dict(row.ContainsKey("context_compaction") ? row["context_compaction"] : null), "state");
        if (state == "compacting") return "Compactando contexto…";
        if (state == "awaiting_usage") return "Contexto: esperando nueva medición tras compactar";
        var value = ContextPercent(context);
        return value.HasValue ? "Contexto usado: " + value.Value.ToString("0.#") + " % · " +
            String(context, "used_tokens") + " / " + String(context, "capacity_tokens") + " tokens · última medición" :
            "Contexto: sin medición disponible";
    }

    static Grid UsageRing(double radius, double? percent, Brush color, string tag, double thickness = 2, bool rounded = false)
    {
        var ring = new Grid { Width = 44, Height = 44, UseLayoutRounding = false, IsHitTestVisible = false, Tag = tag };
        var track = new System.Windows.Shapes.Path { Data = new EllipseGeometry(new Point(22, 22), radius, radius),
            Stroke = color, StrokeThickness = thickness, Opacity = .2 };
        if (!percent.HasValue) track.StrokeDashArray = new DoubleCollection(new[] { 2 / thickness, 3 / thickness });
        ring.Children.Add(track);
        if (percent.HasValue && percent.Value > 0)
        {
            Geometry geometry;
            if (percent.Value >= 100) geometry = new EllipseGeometry(new Point(22, 22), radius, radius);
            else
            {
                double angle = percent.Value / 100 * Math.PI * 2;
                var figure = new PathFigure { StartPoint = new Point(22, 22 - radius), IsClosed = false };
                figure.Segments.Add(new ArcSegment(new Point(22 + radius * Math.Sin(angle), 22 - radius * Math.Cos(angle)),
                    new Size(radius, radius), 0, percent.Value > 50, SweepDirection.Clockwise, true));
                geometry = new PathGeometry(new[] { figure });
            }
            ring.Children.Add(new System.Windows.Shapes.Path { Data = geometry, Stroke = color, StrokeThickness = thickness,
                StrokeStartLineCap = rounded ? PenLineCap.Round : PenLineCap.Flat,
                StrokeEndLineCap = rounded ? PenLineCap.Round : PenLineCap.Flat });
        }
        return ring;
    }

    void RefreshQuota(Dictionary<string, object> usage, bool connected)
    {
        var value = GaugeValue(usage, "remaining_percent");
        bool fresh = connected && (GaugeValue(usage, "valid_until") ?? 0) > DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        double? percent = fresh && value.HasValue ? (double?)Math.Min(100, value.Value) : null;
        string label = percent.HasValue ? "Cuota disponible: " + percent.Value + " % · límite más restrictivo" : "Cuota de Codex: sin datos actuales";
        var lines = new List<string> { label };
        object raw;
        var windows = usage.TryGetValue("windows", out raw) ? raw as System.Collections.IEnumerable : null;
        if (windows != null) foreach (var item in windows)
        {
            var w = Dict(item); double minutes = GaugeValue(w, "duration_minutes") ?? 0;
            string duration = minutes == 10080 ? "semanal" : minutes > 0 && minutes % 1440 == 0 ? (minutes / 1440) + " días" :
                minutes > 0 && minutes % 60 == 0 ? (minutes / 60) + " h" : minutes > 0 ? minutes + " min" : String(w, "window");
            string detail = String(w, "limit_id") + " · " + duration + ": " + String(w, "remaining_percent") + " % disponible";
            var reset = GaugeValue(w, "resets_at");
            if (reset.HasValue && reset.Value < 253402300800) detail += " · se renueva " + DateTimeOffset.FromUnixTimeSeconds((long)reset.Value).LocalDateTime;
            lines.Add(detail);
        }
        if (String(usage, "ordinary_usage_allowed").ToLowerInvariant() == "false") lines.Add("Codex informa que el uso incluido no está disponible.");
        if (!fresh && lines.Count > 1) lines.Add("Última lectura; pendiente de actualizar.");
        string details = System.String.Join("\n", lines);
        foreach (var button in new[] { quotaButton, panelQuotaButton })
        {
            if (button == null) continue;
            button.Content = QuotaArt(percent);
            button.ToolTip = details;
            System.Windows.Automation.AutomationProperties.SetName(button, details);
        }
        quotaPanelText.Text = details;
        if (peekAgentId == "@account") ShowQuotaPeek();
    }

    static Grid QuotaArt(double? percent)
    {
        var color = percent.HasValue ? Accent : Muted;
        var art = UsageRing(16, percent, color, "quota-ring", 3.5, true);
        art.Children.Insert(0, new System.Windows.Shapes.Path { Tag = "quota-face",
            Data = new EllipseGeometry(new Point(22, 22), 16, 16), Fill = Brush("#FF373343") });
        string label = percent.HasValue ? percent.Value + "%" : "—";
        var formatted = new FormattedText(label, System.Globalization.CultureInfo.CurrentCulture, FlowDirection.LeftToRight,
            new Typeface(new FontFamily("Segoe UI"), FontStyles.Normal, FontWeights.SemiBold, FontStretches.Normal),
            10, color);
        var glyphs = formatted.BuildGeometry(new Point());
        var bounds = glyphs.Bounds;
        glyphs.Transform = new TranslateTransform(22 - bounds.Left - bounds.Width / 2, 22 - bounds.Top - bounds.Height / 2);
        art.Children.Add(new System.Windows.Shapes.Path { Tag = "quota-number", Data = glyphs,
            Fill = color, Stretch = Stretch.None });
        return art;
    }

    void ShowQuotaPeek()
    {
        if (mode != MonitorMode.Compact) return;
        peekCloseTimer.Stop(); peekAgentId = "@account";
        agentPeekContent.Children.Clear();
        agentPeekContent.Children.Add(Txt("CUOTA DE LA CUENTA", 11, Accent));
        var detail = Txt(Convert.ToString(quotaButton.ToolTip), 12, Muted);
        detail.TextWrapping = TextWrapping.Wrap; detail.Margin = new Thickness(0, 8, 0, 12);
        agentPeekContent.Children.Add(detail); agentPeek.Visibility = Visibility.Visible;
        agentPeekContent.Measure(new Size(Math.Max(1, TargetGeometry(MonitorMode.Compact).Width - 54), double.PositiveInfinity));
        ResizeAgentSurface(Math.Min(Height - 16, 96 + agentPeekContent.DesiredSize.Height), false);
    }
}
