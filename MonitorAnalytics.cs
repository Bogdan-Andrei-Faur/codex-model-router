using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using System.Security.Cryptography;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

internal sealed class DecisionRecord
{
    public string Id, Thread, Title, Model, Effort, ModelReason, EffortReason, ContinuityStrategy, Source, Status, Signal, Error, Quality, ModelQuality, EffortQuality;
    public string RoutingEngine, EngineModel, EngineStatus, ProductVersion, BuildId, PolicyVersion;
    public double EngineConfidence, EngineLatencyMs;
    public double Time, StartedTime, FinishedTime;
    public bool Accepted;
    public int NativeRetries;
    public string ErrorCode, ErrorHttpStatus;
    public readonly Dictionary<string, object> PhaseEvidence = new Dictionary<string, object>();
    public int InputTokens, OutputTokens, CachedTokens, ReasoningTokens;
    public readonly Dictionary<string, EngineComparison> Comparisons = new Dictionary<string, EngineComparison>();
}

internal sealed class EngineComparison
{
    public string Engine, Model, Effort, Status, EngineModel, Failure;
    public double Confidence, LatencyMs;
    public int InputTokens, OutputTokens, CachedTokens;
    public bool Active;
}

internal sealed partial class ModernRouterMonitor
{
    readonly Grid historyPage = new Grid(), statisticsPage = new Grid(), settingsPage = new Grid();
    readonly StackPanel historyList = new StackPanel(), historyDetail = new StackPanel();
    readonly StackPanel statisticsContent = new StackPanel(), settingsContent = new StackPanel();
    readonly List<Button> monitorTabs = new List<Button>();
    readonly List<UIElement> activityElements = new List<UIElement>();
    readonly List<DecisionRecord> decisions = new List<DecisionRecord>();
    string analyticsSignature, requestedHistoryThread;
    bool analyticsBusy;
    readonly Dictionary<string, Tuple<string, List<Dictionary<string, object>>>> journalCache = new Dictionary<string, Tuple<string, List<Dictionary<string, object>>>>();
    int selectedMonitorTab;
    bool analyticsConnected;
    string selectedDecisionId;
    int historyOffset;
    string historyQuery = "";
    readonly TextBlock analyticsFreshness = Txt("", 11, Muted);
    readonly TextBlock versionLabel = Txt("v" + ProductVersion, 10, Muted);

    UIElement BuildTabBar()
    {
        BuildHistoryPage(); BuildStatisticsPage(); BuildSettingsPage();
        var bar = new Grid { Margin = new Thickness(18, 3, 18, 12) };
        string[] labels = { "Actividad", "Historial", "Estadísticas", "Ajustes" };
        for (int index = 0; index < labels.Length; index++)
        {
            bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            int captured = index;
            var button = Btn(labels[index], delegate { SelectMonitorTab(captured); }, false);
            button.MinWidth = 0; button.Height = 34; button.Margin = new Thickness(index == 0 ? 0 : 3, 0, index == labels.Length - 1 ? 0 : 3, 0);
            button.ToolTip = labels[index]; Grid.SetColumn(button, index); bar.Children.Add(button); monitorTabs.Add(button);
        }
        return bar;
    }

    void RegisterActivityElements(params UIElement[] elements)
    {
        activityElements.AddRange(elements);
    }

    void SelectMonitorTab(int index)
    {
        selectedMonitorTab = index;
        foreach (var element in activityElements) element.Visibility = index == 0 ? Visibility.Visible : Visibility.Collapsed;
        historyPage.Visibility = index == 1 ? Visibility.Visible : Visibility.Collapsed;
        statisticsPage.Visibility = index == 2 ? Visibility.Visible : Visibility.Collapsed;
        settingsPage.Visibility = index == 3 ? Visibility.Visible : Visibility.Collapsed;
        for (int i = 0; i < monitorTabs.Count; i++)
        {
            monitorTabs[i].Background = i == index ? Panel2 : TransparentBrush;
            monitorTabs[i].Foreground = i == index ? Accent : Muted;
            monitorTabs[i].FontWeight = i == index ? FontWeights.SemiBold : FontWeights.Medium;
        }
        if (index == 1) RebuildHistory();
        if (index == 2) RebuildStatistics();
        if (index == 3) RefreshSettings();
    }

    void BuildHistoryPage()
    {
        historyPage.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        historyPage.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1) });
        historyPage.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        historyPage.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        var detailScroll = new ScrollViewer { MaxHeight = 300, VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            Content = historyDetail, Margin = new Thickness(18, 7, 12, 10) };
        Grid.SetRow(detailScroll, 0); historyPage.Children.Add(detailScroll);
        var rule = new Border { Height = 1, Background = Line, Margin = new Thickness(18, 0, 18, 0) };
        Grid.SetRow(rule, 1); historyPage.Children.Add(rule);
        var listScroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, Content = historyList };
        var search = new TextBox { Background = TransparentBrush, Foreground = Ink, BorderThickness = new Thickness(0),
            Padding = new Thickness(10, 7, 10, 7), FontSize = 12, ToolTip = "Buscar por tarea, modelo, motor o estado" };
        System.Windows.Automation.AutomationProperties.SetName(search, "Buscar en historial");
        var filters = new StackPanel { Margin = new Thickness(18, 7, 18, 4) };
        filters.Children.Add(Txt("Buscar por tarea, modelo, motor o estado", 11, Muted));
        filters.Children.Add(new Border { Background = Panel2, CornerRadius = new CornerRadius(12), Margin = new Thickness(0, 4, 0, 0), Child = search });
        search.TextChanged += delegate { historyQuery = search.Text; historyOffset = 0; RebuildHistory(); };
        Grid.SetRow(filters, 2); historyPage.Children.Add(filters);
        Grid.SetRow(listScroll, 3); historyPage.Children.Add(listScroll);
    }

    void BuildStatisticsPage()
    {
        var scroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, Content = statisticsContent };
        statisticsContent.Margin = new Thickness(18, 8, 18, 14); statisticsPage.Children.Add(scroll);
    }

    void BuildSettingsPage()
    {
        var scroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, Content = settingsContent };
        settingsContent.Margin = new Thickness(18, 8, 18, 14); settingsPage.Children.Add(scroll);
    }

    void OpenHistoryForThread(string thread)
    {
        requestedHistoryThread = thread; SelectMonitorTab(1);
        var decision = decisions.FirstOrDefault(item => item.Thread == thread);
        if (decision != null) ShowDecision(decision);
        else
        {
            requestedHistoryThread = thread; ShowUnrecordedThread(thread);
        }
    }

    void ShowUnrecordedThread(string thread)
    {
        selectedDecisionId = null; historyDetail.Children.Clear();
        historyDetail.Children.Add(Txt("Sin ejecución registrada todavía", 15, Ink, FontWeights.SemiBold));
        historyDetail.Children.Add(TaskModeControls(thread, delegate { ShowUnrecordedThread(thread); }));
        var note = Txt("La próxima ejecución de esta tarea aparecerá aquí. Abrir una conversación antigua no crea una decisión nueva.", 12, Muted);
        note.TextWrapping = TextWrapping.Wrap; note.Margin = new Thickness(0, 8, 0, 0); historyDetail.Children.Add(note);
    }

    void RefreshAnalytics(List<KeyValuePair<string, Dictionary<string, object>>> liveRows, string historyPath = null)
    {
        bool synchronous = preview || historyPath != null;
        if (analyticsBusy) return;
        historyPath = historyPath ?? Path.Combine(StateFolder, "history.jsonl");
        var historyPaths = new[] { historyPath, Path.ChangeExtension(historyPath, ".recovered.jsonl") };
        string signature = System.String.Join("|", historyPaths.Select(path => File.Exists(path)
            ? path + ":" + File.GetLastWriteTimeUtc(path).Ticks + ":" + new FileInfo(path).Length : path + ":none"));
        signature += ":" + System.String.Join("|", liveRows.Select(pair => pair.Key + ":" + Json.Serialize(pair.Value)));
        analyticsFreshness.Text = (analyticsConnected ? "Conectado · consultado " : "Sin conexión · consultado ") + DateTime.Now.ToString("HH:mm:ss") + " · cada 2 s";
        signature += ":" + analyticsConnected;
        signature += ":" + telemetryReceiverAvailable + ":" + Json.Serialize(telemetryHealth) + ":" + ReadConfigBool("inference_telemetry", false);
        if (signature == analyticsSignature) return;
        analyticsBusy = true;
        Action load = delegate {
        try {
        var serializer = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
        var indexed = new Dictionary<string, DecisionRecord>();
        foreach (string path in historyPaths.Where(File.Exists))
        {
            string stamp = File.GetLastWriteTimeUtc(path).Ticks + ":" + new FileInfo(path).Length;
            Tuple<string, List<Dictionary<string, object>>> cached;
            if (!journalCache.TryGetValue(path, out cached) || cached.Item1 != stamp)
            {
                var records = new List<Dictionary<string, object>>();
                using (var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
                using (var reader = new StreamReader(stream, Encoding.UTF8))
                {
                    string line;
                    while ((line = reader.ReadLine()) != null)
                        try { var data = serializer.Deserialize<Dictionary<string, object>>(line); if (data != null) records.Add(data); } catch { }
                }
                cached = Tuple.Create(stamp, records); journalCache[path] = cached;
            }
            foreach (var data in cached.Item2)
            {
                string id = String(data, "decision_id"); if (id == "") continue;
                DecisionRecord item;
                if (!indexed.TryGetValue(id, out item)) indexed[id] = item = new DecisionRecord { Id = id };
                ApplyHistoryEvent(item, data);
            }
        }
        foreach (var pair in liveRows)
        {
            string id = String(pair.Value, "decision_id");
            DecisionRecord item;
            // Resumed conversations are live state, not new execution history.
            if (id == "" || !indexed.TryGetValue(id, out item)) continue;
            item.Thread = pair.Key; item.Title = String(pair.Value, "name", pair.Key.Substring(0, Math.Min(8, pair.Key.Length)));
            item.Model = Model(Setting(pair.Value, "model", "Sin confirmar"));
            item.Effort = Effort(Setting(pair.Value, "effort", "")); item.Status = String(pair.Value, "status");
            item.ModelReason = String(pair.Value, "model_reason", String(pair.Value, "reason", "Registro anterior sin explicación separada."));
            item.EffortReason = String(pair.Value, "effort_reason", "Registro anterior sin explicación separada del razonamiento.");
            item.Time = Math.Max(item.Time, Number(pair.Value, "updated"));
            CopyPhaseEvidence(item.PhaseEvidence, pair.Value);
            if (pair.Value.ContainsKey("tokens"))
            {
                var tokens = Dict(pair.Value["tokens"]);
                item.InputTokens = Int(tokens, "inputTokens"); item.OutputTokens = Int(tokens, "outputTokens");
                item.CachedTokens = Int(tokens, "cachedInputTokens"); item.ReasoningTokens = Int(tokens, "reasoningOutputTokens");
            }
        }
        var projected = indexed.Values.OrderByDescending(item => item.Time).ToList();
        Action display = delegate {
            decisions.Clear(); decisions.AddRange(projected);
            if (synchronous || selectedMonitorTab == 1) RebuildHistory();
            if (synchronous || selectedMonitorTab == 2) RebuildStatistics();
            analyticsSignature = signature; analyticsBusy = false;
        };
        if (synchronous) display(); else Dispatcher.BeginInvoke(display);
        } catch { Dispatcher.BeginInvoke((Action)delegate { analyticsBusy = false; analyticsSignature = null; }); }
        };
        if (synchronous) load(); else System.Threading.ThreadPool.QueueUserWorkItem(delegate { load(); });
    }

    static void ApplyHistoryEvent(DecisionRecord item, Dictionary<string, object> data)
    {
        string eventName = String(data, "event");
        if (eventName == "phase_checkpoint")
        {
            if (!item.PhaseEvidence.ContainsKey("phase_events")) item.PhaseEvidence["phase_events"] = new List<Dictionary<string, object>>();
            ((List<Dictionary<string, object>>)item.PhaseEvidence["phase_events"]).Add(new Dictionary<string, object>(data));
        }
        if (eventName == "inference_metric" || eventName == "inference_observed" || eventName == "inference_probable")
        {
            if (!item.PhaseEvidence.ContainsKey("inference_samples")) item.PhaseEvidence["inference_samples"] = new Dictionary<string, Dictionary<string, object>>();
            var samples = (Dictionary<string, Dictionary<string, object>>)item.PhaseEvidence["inference_samples"];
            string kind = String(data, "phase_id") + ":" + String(data, "inference_event_name") + ":" + String(data, "inference_event_kind");
            double count = samples.ContainsKey(kind) ? Number(samples[kind], "count") : 0;
            samples[kind] = new Dictionary<string, object>(data); samples[kind]["count"] = count + (data.ContainsKey("inference_sample_count") ? Number(data, "inference_sample_count") : 1);
            if (eventName == "inference_metric") return;
        }
        if (eventName == "native_turn_error")
        {
            if (data.ContainsKey("will_retry") && data["will_retry"] is bool && (bool)data["will_retry"]) item.NativeRetries++;
            return;
        }
        if (eventName == "decision_completed") { item.Error = null; item.ErrorCode = null; item.ErrorHttpStatus = null; }
        CopyPhaseEvidence(item.PhaseEvidence, data);
        // A later user rating must not make an old execution look newly run.
        if (eventName != "decision_quality") item.Time = Math.Max(item.Time, Number(data, "time"));
        if (eventName == "decision_created") item.StartedTime = Number(data, "time");
        if (eventName == "decision_created")
        {
            item.ProductVersion = String(data, "product_version", "Anterior");
            item.BuildId = String(data, "build_id", ""); item.PolicyVersion = String(data, "routing_policy_version", "");
        }
        if (eventName == "decision_accepted" || eventName == "decision_recovered") item.Accepted = true;
        if (eventName == "decision_completed" || eventName == "decision_rejected" || eventName == "decision_error")
            item.FinishedTime = Number(data, "time");
        item.Thread = String(data, "thread", item.Thread); item.Title = String(data, "title", item.Title);
        if (data.ContainsKey("model")) item.Model = Model(String(data, "model"));
        if (data.ContainsKey("effort")) item.Effort = Effort(String(data, "effort"));
        item.ModelReason = String(data, "model_reason", item.ModelReason); item.EffortReason = String(data, "effort_reason", item.EffortReason);
        if (eventName != "engine_comparison") item.ContinuityStrategy = String(data, "continuity_strategy", item.ContinuityStrategy);
        item.Source = String(data, "source", item.Source); item.Status = String(data, "status", item.Status);
        item.Signal = String(data, "signal", item.Signal);
        item.Error = String(data, "error_type", item.Error);
        item.ErrorCode = String(data, "error_code", item.ErrorCode);
        item.ErrorHttpStatus = String(data, "error_http_status", item.ErrorHttpStatus);
        item.Quality = String(data, "quality", item.Quality);
        item.ModelQuality = String(data, "model_quality", item.ModelQuality);
        item.EffortQuality = String(data, "effort_quality", item.EffortQuality);
        if (eventName == "engine_comparison")
        {
            string engine = String(data, "routing_engine", "rules");
            item.Comparisons[engine] = new EngineComparison { Engine = engine, Model = Model(String(data, "proposed_model")),
                Effort = Effort(String(data, "proposed_effort")), Status = String(data, "engine_status"),
                EngineModel = String(data, "engine_model"), Confidence = Number(data, "engine_confidence"),
                LatencyMs = Number(data, "engine_latency_ms"), Failure = String(data, "engine_failure"),
                InputTokens = Int(data, "engine_input_tokens"), OutputTokens = Int(data, "engine_output_tokens"),
                CachedTokens = Int(data, "engine_cached_tokens"),
                Active = data.ContainsKey("engine_active") ? Convert.ToBoolean(data["engine_active"]) : System.String.IsNullOrEmpty(item.RoutingEngine) };
            // Old history had no decision_routed event. Preserve its best-known
            // applied engine while treating malformed/guardrailed choices as local.
            if (!data.ContainsKey("engine_active"))
                item.RoutingEngine = String(data, "engine_status") == "ok" ? engine : "rules";
            return;
        }
        item.RoutingEngine = String(data, "routing_engine", item.RoutingEngine);
        item.EngineModel = String(data, "engine_model", item.EngineModel);
        item.EngineStatus = String(data, "engine_status", item.EngineStatus);
        if (data.ContainsKey("engine_confidence")) item.EngineConfidence = Number(data, "engine_confidence");
        if (data.ContainsKey("engine_latency_ms")) item.EngineLatencyMs = Number(data, "engine_latency_ms");
        if (data.ContainsKey("inputTokens")) item.InputTokens = Int(data, "inputTokens");
        if (data.ContainsKey("outputTokens")) item.OutputTokens = Int(data, "outputTokens");
        if (data.ContainsKey("cachedInputTokens")) item.CachedTokens = Int(data, "cachedInputTokens");
        if (data.ContainsKey("reasoningOutputTokens")) item.ReasoningTokens = Int(data, "reasoningOutputTokens");
    }

    void RebuildHistory()
    {
        historyList.Children.Clear();
        if (requestedHistoryThread != null && !decisions.Any(item => item.Thread == requestedHistoryThread))
        {
            ShowUnrecordedThread(requestedHistoryThread);
            RenderHistoryRows();
            return;
        }
        if (decisions.Count == 0)
        {
            historyDetail.Children.Clear(); historyDetail.Children.Add(Txt("Aún no hay decisiones registradas", 15, Ink, FontWeights.SemiBold));
            var note = Txt("Las nuevas ejecuciones se guardan aquí y se conservan al cerrar Codex. Las conversaciones abiertas sin una nueva ejecución no cuentan como decisiones.", 12, Muted);
            note.TextWrapping = TextWrapping.Wrap; note.Margin = new Thickness(0, 7, 0, 0); historyDetail.Children.Add(note); return;
        }
        historyList.Children.Add(Section("DECISIONES RECIENTES"));
        RenderHistoryRows();
        DecisionRecord selected = decisions.FirstOrDefault(item => item.Id == selectedDecisionId);
        if (requestedHistoryThread != null) selected = decisions.FirstOrDefault(item => item.Thread == requestedHistoryThread);
        ShowDecision(selected ?? decisions[0]); requestedHistoryThread = null;
    }

    void RenderHistoryRows()
    {
        var filtered = decisions.Where(d => (d.Title + " " + d.Model + " " + d.Effort + " " + FriendlyEngine(d.RoutingEngine) + " " + FriendlyStatus(d.Status))
            .IndexOf(historyQuery, StringComparison.OrdinalIgnoreCase) >= 0).ToList();
        historyOffset = Math.Min(historyOffset, Math.Max(0, ((filtered.Count - 1) / 40) * 40));
        foreach (var decision in filtered.Skip(historyOffset).Take(40)) historyList.Children.Add(HistoryRow(decision));
        var pages = new WrapPanel { Margin = new Thickness(18, 8, 18, 10) };
        if (historyOffset > 0) pages.Children.Add(Btn("Anterior", delegate { historyOffset -= 40; RebuildHistory(); }, false));
        pages.Children.Add(Txt(filtered.Count == 0 ? "Sin coincidencias" : (historyOffset + 1) + "–" + Math.Min(historyOffset + 40, filtered.Count) + " de " + filtered.Count, 11, Muted));
        if (historyOffset + 40 < filtered.Count) pages.Children.Add(Btn("Siguiente", delegate { historyOffset += 40; RebuildHistory(); }, false));
        historyList.Children.Add(pages);
    }

    UIElement HistoryRow(DecisionRecord decision)
    {
        var button = new Button { Background = TransparentBrush, BorderThickness = new Thickness(0),
            Foreground = Ink, Template = RowButtonTemplate(), Cursor = Cursors.Hand,
            HorizontalAlignment = HorizontalAlignment.Stretch, HorizontalContentAlignment = HorizontalAlignment.Stretch,
            Margin = new Thickness(12, 3, 12, 3), Padding = new Thickness(8, 7, 8, 7), Tag = decision };
        var row = new Grid(); row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(108) });
        var copy = new StackPanel(); copy.Children.Add(Txt(decision.Title ?? "Sin título", 13, Ink, FontWeights.SemiBold));
        var meta = Txt(HistoryTime(decision.Time) + " · " + FriendlyStatus(decision.Status), 11, decision.Error == null ? Muted : Warning);
        meta.Margin = new Thickness(0, 4, 0, 0); copy.Children.Add(meta); row.Children.Add(copy);
        var tags = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right,
            VerticalAlignment = VerticalAlignment.Center };
        var model = Badge(decision.Model ?? "?", true); model.Padding = new Thickness(7, 0, 7, 0); tags.Children.Add(model);
        if (!System.String.IsNullOrEmpty(decision.Effort)) { var effort = Badge(decision.Effort, false); effort.Margin = new Thickness(4, 0, 0, 0); effort.Padding = new Thickness(7, 0, 7, 0); tags.Children.Add(effort); }
        Grid.SetColumn(tags, 1); row.Children.Add(tags); button.Content = row;
        button.MouseEnter += delegate { button.Background = Panel2; };
        button.MouseLeave += delegate { button.Background = TransparentBrush; };
        button.Click += delegate { ShowDecision(decision); };
        return button;
    }

    static ControlTemplate RowButtonTemplate()
    {
        var border = new FrameworkElementFactory(typeof(Border));
        border.SetValue(Border.CornerRadiusProperty, new CornerRadius(16));
        border.SetBinding(Border.BackgroundProperty, new System.Windows.Data.Binding("Background") { RelativeSource =
            new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        border.SetBinding(Border.PaddingProperty, new System.Windows.Data.Binding("Padding") { RelativeSource =
            new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        var presenter = new FrameworkElementFactory(typeof(ContentPresenter));
        presenter.SetBinding(ContentPresenter.ContentProperty, new System.Windows.Data.Binding("Content") { RelativeSource =
            new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        presenter.SetValue(ContentPresenter.HorizontalAlignmentProperty, HorizontalAlignment.Stretch); border.AppendChild(presenter);
        var template = new ControlTemplate(typeof(Button)) { VisualTree = border };
        var hover = new Trigger { Property = Button.IsMouseOverProperty, Value = true };
        hover.Setters.Add(new Setter(Button.BackgroundProperty, Panel2)); template.Triggers.Add(hover); return template;
    }

    void ShowDecision(DecisionRecord decision)
    {
        if (decision == null) return;
        requestedHistoryThread = null;
        selectedDecisionId = decision.Id;
        historyDetail.Children.Clear();
        var title = Txt(decision.Title ?? "Sin título", 16, Ink, FontWeights.SemiBold); title.TextWrapping = TextWrapping.Wrap;
        historyDetail.Children.Add(title);
        if (!System.String.IsNullOrEmpty(decision.Thread))
            historyDetail.Children.Add(TaskModeControls(decision.Thread, delegate { ShowDecision(decision); }));
        var tags = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 9, 0, 7) };
        tags.Children.Add(Badge(decision.Model ?? "Sin confirmar", true));
        if (!System.String.IsNullOrEmpty(decision.Effort)) { var effort = Badge(decision.Effort, false); effort.Margin = new Thickness(6, 0, 0, 0); tags.Children.Add(effort); }
        historyDetail.Children.Add(tags);
        historyDetail.Children.Add(Txt(FriendlyStatus(decision.Status) + " · " + HistoryTime(decision.Time), 11,
            decision.Error == null ? Muted : Warning, FontWeights.Medium));
        historyDetail.Children.Add(BuildPhasePipeline(decision.PhaseEvidence));
        if (decision.PhaseEvidence.Count > 0)
            AddExplanation(historyDetail, "EVIDENCIA DEL MODELO", ExecutionEvidence(decision.PhaseEvidence, decision.Model, decision.Effort, decision.Source));
        if (decision.Source == "recovered")
        {
            var recovered = Txt("Recuperada de registros anteriores · detalles limitados", 11, Muted);
            recovered.TextWrapping = TextWrapping.Wrap; recovered.Margin = new Thickness(0, 5, 0, 0); historyDetail.Children.Add(recovered);
        }
        AddExplanation(historyDetail, "POR QUÉ EL MODELO", decision.ModelReason);
        AddExplanation(historyDetail, "POR QUÉ EL RAZONAMIENTO", decision.EffortReason);
        if (!System.String.IsNullOrEmpty(decision.ContinuityStrategy))
            AddExplanation(historyDetail, "DECISIÓN DE CONTINUIDAD", FriendlyContinuityStrategy(decision.ContinuityStrategy));
        AddQualityControls(decision);
        if (decision.Comparisons.Count > 0)
        {
            string observed = System.String.Join("\n", decision.Comparisons.Values.OrderBy(item => item.Engine).Select(item =>
                FriendlyEngine(item.Engine) + (item.Active ? (item.Engine == decision.RoutingEngine ? " · aplicado" : " · intento") : " · comparación") + " → " + item.Model + (item.Effort == "" ? "" : " · " + item.Effort) +
                " · " + (item.Status == "ok" ? Math.Round(item.LatencyMs) + " ms" : FriendlyEngineStatus(item.Status)) +
                (System.String.IsNullOrEmpty(item.Failure) ? "" : " · " + FriendlyEngineFailure(item.Failure)) +
                (item.Confidence > 0 ? " · " + Math.Round(item.Confidence * 100) + "%" : "")));
            AddExplanation(historyDetail, "MOTORES OBSERVADOS", observed);
        }
        else if (!System.String.IsNullOrEmpty(decision.RoutingEngine))
        {
            string engine = FriendlyEngine(decision.RoutingEngine);
            string detail = decision.EngineStatus == "ok" ? engine + " decidió en " + Math.Round(decision.EngineLatencyMs) + " ms" :
                engine + " · " + FriendlyEngineStatus(decision.EngineStatus);
            if (decision.EngineConfidence > 0) detail += " · confianza " + Math.Round(decision.EngineConfidence * 100) + "%";
            AddExplanation(historyDetail, "MOTOR DE ENRUTAMIENTO", detail);
        }
        int total = decision.InputTokens + decision.OutputTokens;
        if (total > 0) AddExplanation(historyDetail, "USO OBSERVADO",
            decision.InputTokens + " entrada · " + decision.OutputTokens + " salida · " + decision.CachedTokens + " en caché");
        if (decision.Signal != null) AddExplanation(historyDetail, "SEÑAL DE RESULTADO",
            decision.Signal == "retry" ? "La siguiente petición indicó que el resultado no había resuelto la tarea." :
            "La siguiente petición cambió el modelo explícitamente.");
        if (decision.Error != null) AddExplanation(historyDetail, "INCIDENCIA",
            (decision.Error == "unknown" ? "Causa no proporcionada por Codex" : decision.Error) +
            (decision.ErrorHttpStatus != null ? " · HTTP " + decision.ErrorHttpStatus : "") +
            (decision.ErrorCode != null ? " · RPC " + decision.ErrorCode : ""));
        if (decision.NativeRetries > 0) AddExplanation(historyDetail, "REINTENTOS NATIVOS", decision.NativeRetries.ToString());
    }

    string TaskModeFile(string id)
    {
        using (var hash = SHA256.Create())
            return Path.Combine(StateFolder, "task-modes", BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(id))).Replace("-", "").ToLowerInvariant() + ".json");
    }
    string ReadTaskMode(string id)
    {
        string file = TaskModeFile(id);
        if (!File.Exists(file)) return "automatic";
        try
        {
            var data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(file));
            return String(data, "thread", "") == id && String(data, "mode", "") == "automatic" ? "automatic" : "manual";
        }
        catch { return "manual"; }
    }
    UIElement TaskModeControls(string id, Action changed)
    {
        var panel = new StackPanel { Margin = new Thickness(0, 10, 0, 4) };
        string mode = ReadTaskMode(id);
        var choices = new WrapPanel();
        foreach (var option in new[] { new[] { "automatic", "Automático" }, new[] { "manual", "Manual" } })
        {
            string captured = option[0];
            choices.Children.Add(ChoiceButton(option[1], mode == captured, delegate {
                if (preview) return;
                try
                {
                    string target = TaskModeFile(id), temporary = target + "." + Guid.NewGuid().ToString("N") + ".tmp";
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    File.WriteAllText(temporary, Json.Serialize(new { schema = 1, thread = id, mode = captured }), new UTF8Encoding(false));
                    if (File.Exists(target)) File.Replace(temporary, target, null); else File.Move(temporary, target);
                    changed();
                }
                catch { connection.Text = "No se pudo guardar el modo de esta tarea"; connection.Foreground = Warning; }
            }));
        }
        panel.Children.Add(choices);
        var note = Txt(!ReadEnabled() ? "El selector está pausado para todas las tareas." : mode == "manual" ? "Próximo mensaje: usa el modelo y esfuerzo elegidos en Codex." :
            "Próximo mensaje: el selector decide modelo y esfuerzo.", 11, Muted);
        note.TextWrapping = TextWrapping.Wrap; panel.Children.Add(note);
        return panel;
    }

    void AddQualityControls(DecisionRecord decision)
    {
        var title = Txt("VALORA ESTA ELECCIÓN", 11, Muted, FontWeights.SemiBold);
        title.Margin = new Thickness(0, 12, 0, 7); historyDetail.Children.Add(title);
        AddQualityChoice(decision, "Resultado global", decision.Quality, "quality");
        AddQualityChoice(decision, "Modelo elegido", decision.ModelQuality, "model_quality");
        AddQualityChoice(decision, "Razonamiento elegido", decision.EffortQuality, "effort_quality");
        var note = Txt("Puedes valorar el resultado global, el modelo y el razonamiento por separado. No se guarda el mensaje ni la respuesta.", 11, Muted);
        note.TextWrapping = TextWrapping.Wrap; note.Margin = new Thickness(0, 6, 0, 0); historyDetail.Children.Add(note);
    }

    void AddQualityChoice(DecisionRecord decision, string label, string selectedValue, string field)
    {
        historyDetail.Children.Add(Txt(label, 11, Muted, FontWeights.Medium));
        var choices = new WrapPanel();
        foreach (var option in new[] { new[] { "insufficient", "Insuficiente" }, new[] { "adequate", "Adecuada" }, new[] { "excessive", "Excesiva" } })
        {
            string quality = option[0], optionLabel = option[1]; bool selected = selectedValue == quality;
            var button = ChoiceButton(optionLabel, selected, delegate { WriteDecisionQuality(decision, selected ? "" : quality, field); });
            choices.Children.Add(button);
        }
        historyDetail.Children.Add(choices);
        if (!System.String.IsNullOrEmpty(selectedValue))
        {
            var clear = Btn("Quitar valoración", delegate { WriteDecisionQuality(decision, "", field); }, false);
            clear.HorizontalAlignment = HorizontalAlignment.Left; clear.Foreground = Muted;
            historyDetail.Children.Add(clear);
        }
    }

    void WriteDecisionQuality(DecisionRecord decision, string quality, string field)
    {
        try
        {
            Directory.CreateDirectory(StateFolder);
            var entry = new Dictionary<string, object> {
                { "schema", 2 }, { "time", DateTimeOffset.UtcNow.ToUnixTimeSeconds() }, { "time_iso", DateTime.UtcNow.ToString("o") },
                { "event", "decision_quality" }, { "decision_id", decision.Id }, { "thread", decision.Thread ?? "" }, { field, quality }
            };
            using (var gate = new FileStream(Path.Combine(StateFolder, "history.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.ReadWrite))
            {
                if (gate.Length == 0) { gate.WriteByte(0); gate.Flush(); }
                bool held = false;
                for (int retry = 0; retry < 50 && !held; retry++)
                    try { gate.Lock(0, 1); held = true; } catch (IOException) { System.Threading.Thread.Sleep(20); }
                if (!held) throw new IOException("History is busy");
                try
                {
                    using (var stream = new FileStream(Path.Combine(StateFolder, "history.jsonl"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.ReadWrite))
                    {
                        if (stream.Length > 0) { stream.Position = stream.Length - 1; if (stream.ReadByte() != 10) stream.WriteByte(10); }
                        stream.Position = stream.Length;
                        using (var writer = new StreamWriter(stream, new UTF8Encoding(false))) writer.WriteLine(Json.Serialize(entry));
                    }
                }
                finally { gate.Unlock(0, 1); }
            }
            if (field == "model_quality") decision.ModelQuality = quality;
            else if (field == "effort_quality") decision.EffortQuality = quality;
            else decision.Quality = quality;
            analyticsSignature = null; RefreshData();
        }
        catch { connection.Text = "No se pudo guardar la valoración"; connection.Foreground = Warning; }
    }

    static void AddExplanation(StackPanel panel, string label, string value)
    {
        bool modelChoice = label == "POR QUÉ EL MODELO";
        bool effortChoice = label == "POR QUÉ EL RAZONAMIENTO";
        string title = modelChoice ? "Modelo elegido" : effortChoice ? "Razonamiento elegido" : label;
        var titleText = Txt(title, 11, modelChoice ? Accent : effortChoice ? Good : Muted, FontWeights.SemiBold);
        titleText.TextWrapping = TextWrapping.Wrap;
        var text = Txt(System.String.IsNullOrEmpty(value) ? "No disponible en este registro." : value, 13, Ink, FontWeights.Medium);
        text.TextWrapping = TextWrapping.Wrap; text.Margin = new Thickness(0, 5, 0, 0);
        var stack = new StackPanel(); stack.Children.Add(titleText); stack.Children.Add(text);
        var rail = modelChoice ? Accent : effortChoice ? Good : Line;
        var card = new Border { Background = Panel2, BorderBrush = rail, BorderThickness = new Thickness(3, 0, 0, 0),
            CornerRadius = new CornerRadius(16), Padding = new Thickness(10, 9, 11, 9), Margin = new Thickness(0, 10, 0, 0), Child = stack };
        panel.Children.Add(card);
    }

    static string FriendlyContinuityStrategy(string value)
    {
        return value == "continue" ? "Jev identificó trabajo pendiente y reevaluó el modelo y el razonamiento para continuarlo." :
            value == "reassess" ? "Jev consideró que esta petición debía evaluarse de nuevo antes de elegir modelo y razonamiento." : value;
    }

    void RebuildStatistics()
    {
        statisticsContent.Children.Clear();
        statisticsContent.Children.Add(Txt("Resumen de decisiones", 17, Ink, FontWeights.SemiBold));
        var note = Txt("Historial acumulado · se conserva entre sesiones", 12, Muted);
        statisticsContent.Children.Add(AnalyticsHeading("VERSIONES Y CALIDAD"));
        foreach (var cohort in decisions.GroupBy(d => d.ProductVersion ?? "Anterior"))
        {
            var ratedCohort = cohort.Where(d => !System.String.IsNullOrEmpty(d.Quality)).ToList();
            AddMetric(cohort.Key + " · decisiones", cohort.Count() + " · " + ratedCohort.Count + " valoradas", cohort.Count() * 1.0 / Math.Max(1, decisions.Count), Accent);
            if (ratedCohort.Count > 0) AddMetric(cohort.Key + " · adecuadas", ratedCohort.Count(d => d.Quality == "adequate") + " / " + ratedCohort.Count,
                ratedCohort.Count(d => d.Quality == "adequate") * 1.0 / ratedCohort.Count, Good);
        }
        var caveat = Txt("Valoraciones con su muestra. Disponibilidad y acuerdo entre motores no prueban calidad. Los registros anteriores no confirman una versión.", 11, Muted);
        caveat.TextWrapping = TextWrapping.Wrap; statisticsContent.Children.Add(caveat);
        note.TextWrapping = TextWrapping.Wrap; note.Margin = new Thickness(0, 5, 0, 14); statisticsContent.Children.Add(note);
        statisticsContent.Children.Add(analyticsFreshness);
        int total = decisions.Count, accepted = decisions.Count(item => item.Accepted);
        AddMetric("Decisiones con historial", total.ToString(), total > 0 ? 1 : 0, Accent);
        AddMetric("Envíos aceptados · acumulado", accepted.ToString(), total > 0 ? accepted * 1.0 / total : 0, Accent);
        int errors = decisions.Count(item => item.Error != null || item.Status == "error" || item.Status == "failed");
        int retries = decisions.Count(item => item.Signal == "retry");
        AddMetric("Incidencias registradas", errors.ToString(), total == 0 ? 0 : errors * 1.0 / total, errors == 0 ? Good : Warning);
        AddMetric("Reintentos registrados", retries.ToString(), total == 0 ? 0 : retries * 1.0 / total, Good);
        statisticsContent.Children.Add(AnalyticsHeading("FASES · OBSERVACIÓN"));
        foreach (var group in decisions.Where(item => item.PhaseEvidence.ContainsKey("phase_status"))
            .GroupBy(item => String(item.PhaseEvidence, "phase_status")))
            AddMetric(PhaseStatus(group.Key), group.Count().ToString(), group.Count() * 1.0 / Math.Max(1, total), Accent);
        int published = decisions.Count(item => !System.String.IsNullOrEmpty(String(item.PhaseEvidence, "configured_model")));
        int inferred = decisions.Count(item => !System.String.IsNullOrEmpty(String(item.PhaseEvidence, "observed_model")) && String(item.PhaseEvidence, "evidence_confidence") == "confirmed");
        AddMetric("Configuraciones publicadas", published.ToString(), published * 1.0 / Math.Max(1, total), Good);
        AddMetric("Inferencias confirmadas localmente", inferred.ToString(), inferred * 1.0 / Math.Max(1, total), Muted);
        statisticsContent.Children.Add(AnalyticsHeading("TELEMETRÍA LOCAL"));
        if (!ReadConfigBool("inference_telemetry", false))
            statisticsContent.Children.Add(Txt("Desactivada en Ajustes.", 12, Muted));
        else if (!telemetryReceiverAvailable)
            statisticsContent.Children.Add(Txt("Pendiente de reiniciar Desktop para abrir el receptor local.", 12, Warning));
        else
        {
            bool receiving = Telemetry("requests") > 0;
            AddMetric("Receptor local", receiving ? "Recibiendo" : "Abierto · sin datos", receiving ? 1 : 0, receiving ? Good : Warning);
            AddMetric("Solicitudes procesadas", Telemetry("requests").ToString("N0"), Math.Min(1, Telemetry("requests") / Math.Max(1, total)), Accent);
            AddMetric("Registros con modelo", Telemetry("eligible_records").ToString("N0"), Math.Min(1, Telemetry("eligible_records") / Math.Max(1, Telemetry("records_scanned"))), Accent);
            AddMetric("Finalizaciones exportadas", Telemetry("completion_records").ToString("N0"), Math.Min(1, Telemetry("completion_records") / Math.Max(1, Telemetry("eligible_records"))), Accent);
            AddMetric("Finalizaciones recibidas", Telemetry("telemetry_events").ToString("N0"), Math.Min(1, Telemetry("telemetry_events") / Math.Max(1, Telemetry("eligible_records"))), Accent);
            AddMetric("Inferencias asociadas", Telemetry("telemetry_confirmed").ToString("N0"), Math.Min(1, Telemetry("telemetry_confirmed") / Math.Max(1, Telemetry("telemetry_events"))), Good);
            AddMetric("Coincidencias sin ID de turno", Telemetry("telemetry_probable").ToString("N0"), Math.Min(1, Telemetry("telemetry_probable") / Math.Max(1, Telemetry("telemetry_events"))), Muted);
            double invalidRequests = Telemetry("invalid_requests");
            AddMetric("Conexiones rechazadas por capacidad", Telemetry("rejected_connections").ToString("N0"), Telemetry("rejected_connections") > 0 ? 1 : 0, Warning);
            AddMetric("Incidencias del receptor", invalidRequests.ToString("N0"), invalidRequests > 0 ? 1 : 0, invalidRequests > 0 ? Warning : Good);
            foreach (var stage in new[] { "wire", "decoded" })
            {
                if (new[] { "512k", "1m", "4m", "16m", "over16m" }.Any(bin => Telemetry("size_" + stage + "_" + bin) > 0))
                {
                    var sizes = Txt((stage == "wire" ? "Tamaño recibido" : "Tamaño descomprimido") +
                        " · ≤512 KiB: " + Telemetry("size_" + stage + "_512k").ToString("N0") +
                        " · 512 KiB–1 MiB: " + Telemetry("size_" + stage + "_1m").ToString("N0") +
                        " · 1–4 MiB: " + Telemetry("size_" + stage + "_4m").ToString("N0") +
                        " · 4–16 MiB: " + Telemetry("size_" + stage + "_16m").ToString("N0") +
                        " · >16 MiB: " + Telemetry("size_" + stage + "_over16m").ToString("N0") + ".", 12, Muted);
                    sizes.TextWrapping = TextWrapping.Wrap; statisticsContent.Children.Add(sizes);
                }
            }
            if (Telemetry("invalid_size") + Telemetry("invalid_length") + Telemetry("processing_busy") > 0)
            {
                var rejection = Txt("Captura incompleta. Tamaño recibido: " + Telemetry("invalid_wire_size").ToString("N0") +
                    " · descomprimido: " + Telemetry("invalid_decoded_size").ToString("N0") +
                    " · longitud/formato HTTP: " + Telemetry("invalid_length").ToString("N0") +
                    " · procesamiento ocupado: " + Telemetry("processing_busy").ToString("N0") + ".", 12, Warning);
                rejection.TextWrapping = TextWrapping.Wrap; statisticsContent.Children.Add(rejection);
            }
            string telemetryNote = !receiving ? "El receptor está abierto, pero no recibe eventos. Esto no significa que no haya agentes trabajando." :
                Telemetry("eligible_records") == 0 ? "Se recibieron eventos sin modelo utilizable; no se conserva su contenido." :
                invalidRequests > 0 ? "Incidencias: tamaño " + Telemetry("invalid_size").ToString("N0") + " · codificación " + Telemetry("invalid_encoding").ToString("N0") + " · carga " + Telemetry("invalid_payload").ToString("N0") + " · E/S " + Telemetry("invalid_io").ToString("N0") + "." : null;
            if (telemetryNote != null)
            {
                var notice = Txt(telemetryNote, 12, Warning); notice.TextWrapping = TextWrapping.Wrap;
                statisticsContent.Children.Add(notice);
            }
        }
        statisticsContent.Children.Add(AnalyticsHeading("MODELOS"));
        AddBreakdown(decisions.Where(item => item.Model != null).GroupBy(item => item.Model).ToDictionary(group => group.Key, group => group.Count()), true);
        statisticsContent.Children.Add(AnalyticsHeading("RAZONAMIENTO"));
        AddBreakdown(decisions.Where(item => !System.String.IsNullOrEmpty(item.Effort)).GroupBy(item => item.Effort).ToDictionary(group => group.Key, group => group.Count()), false);
        statisticsContent.Children.Add(AnalyticsHeading("MOTOR DE ENRUTAMIENTO"));
        AddBreakdown(decisions.Where(item => !System.String.IsNullOrEmpty(item.RoutingEngine)).GroupBy(item => FriendlyEngine(item.RoutingEngine)).ToDictionary(group => group.Key, group => group.Count()), false);
        AddEngineTelemetry();
        AddEngineQuality();
        int rated = decisions.Count(item => !System.String.IsNullOrEmpty(item.Quality));
        statisticsContent.Children.Add(AnalyticsHeading("VALORACIÓN DE LA ELECCIÓN"));
        AddMetric("Decisiones valoradas", rated + " / " + total, total == 0 ? 0 : rated * 1.0 / total, Accent);
        AddBreakdown(decisions.Where(item => !System.String.IsNullOrEmpty(item.Quality)).GroupBy(item => FriendlyQuality(item.Quality)).ToDictionary(group => group.Key, group => group.Count()), false);
        long input = decisions.Sum(item => (long)item.InputTokens), output = decisions.Sum(item => (long)item.OutputTokens), cached = decisions.Sum(item => (long)item.CachedTokens);
        if (input + output > 0)
        {
            statisticsContent.Children.Add(AnalyticsHeading("TOKENS · ÚLTIMA LLAMADA OBSERVADA POR REGISTRO"));
            AddMetric("Entrada", input.ToString("N0"), 1, Accent); AddMetric("Salida", output.ToString("N0"), input == 0 ? 0 : Math.Min(1, output * 1.0 / input), Good);
            AddMetric("Entrada en caché", cached.ToString("N0"), input == 0 ? 0 : Math.Min(1, cached * 1.0 / input), Muted);
        }
        var durations = decisions.Where(item => item.StartedTime > 0 && item.FinishedTime >= item.StartedTime)
            .Select(item => item.FinishedTime - item.StartedTime).ToList();
        if (durations.Count > 0) AddMetric("Duración media", FormatDuration(durations.Average()), 1, Accent);
    }

    TextBlock AnalyticsHeading(string text)
    {
        var heading = Label(text); heading.Margin = new Thickness(0, 20, 0, 8); return heading;
    }

    void AddBreakdown(Dictionary<string, int> values, bool models)
    {
        int maximum = values.Count == 0 ? 1 : values.Values.Max();
        foreach (var pair in values.OrderByDescending(pair => pair.Value))
            AddMetric(pair.Key, pair.Value.ToString(), pair.Value * 1.0 / maximum, models ? BadgeColor(pair.Key, true) : BadgeColor(pair.Key, false));
        if (values.Count == 0) statisticsContent.Children.Add(Txt("Sin datos todavía", 12, Muted));
    }

    static Brush BadgeColor(string label, bool model)
    {
        var badge = Badge(label, model); return ((TextBlock)badge.Child).Foreground;
    }

    void AddMetric(string label, string value, double ratio, Brush color)
    {
        var block = new StackPanel { Margin = new Thickness(0, 5, 0, 6) };
        var row = new Grid(); row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto }); row.Children.Add(Txt(label, 12, Ink, FontWeights.Medium));
        var number = Txt(value, 12, color, FontWeights.SemiBold); Grid.SetColumn(number, 1); row.Children.Add(number); block.Children.Add(row);
        var track = new Grid { Height = 4, Background = Panel2, Margin = new Thickness(0, 6, 0, 0) };
        track.Children.Add(new Border { Background = color, CornerRadius = new CornerRadius(2), HorizontalAlignment = HorizontalAlignment.Left,
            Width = Math.Max(2, 350 * Math.Max(0, Math.Min(1, ratio))) }); block.Children.Add(track); statisticsContent.Children.Add(block);
    }

    void RefreshSettings()
    {
        settingsContent.Children.Clear(); settingsContent.Children.Add(Txt("Ajustes", 17, Ink, FontWeights.SemiBold));
        AddSettingsNote("Controla el selector, el motor que decide y cuánto tiempo se conserva su historial local.");
        settingsContent.Children.Add(AnalyticsHeading("CONEXIÓN CON DESKTOP"));
        AddSettingsNote("La instalación se detecta al arrancar. Conecta el inicio habitual una vez y después abre Desktop desde su propio acceso. El monitor se puede cerrar sin detener el selector.");
        settingsContent.Children.Add(SettingsAction("Comprobar conexión", "Distingue instalación, registro y conexión observada.", delegate { ManageConnection("doctor"); }));
        settingsContent.Children.Add(SettingsAction("Conectar al inicio habitual", "Se aplicará al volver a abrir Desktop; conserva las tareas en curso.", delegate { ManageConnection("install"); }));
        settingsContent.Children.Add(SettingsAction("Desconectar integración", "Restaura el inicio habitual sin borrar ajustes ni historial.", delegate { ManageConnection("uninstall"); }));
        if (!System.String.IsNullOrEmpty(connectionMessage)) AddSettingsNote(connectionMessage);
        settingsContent.Children.Add(SettingsAction(ReadEnabled() ? "Ⅱ  Pausar selección automática" : "▶  Activar selección automática",
            ReadEnabled() ? "Codex automático decide en cada nuevo mensaje." : "Se respeta la selección manual de Codex.", delegate { TogglePause(); RefreshSettings(); }));
        settingsContent.Children.Add(SettingsAction(Topmost ? "Desactivar Mantener delante" : "Activar Mantener delante",
            Topmost ? "El monitor permanece sobre otras ventanas." : "El monitor puede quedar detrás de otras ventanas.", delegate { Topmost = !Topmost; SaveUiState(); UpdateTray(); RefreshSettings(); }));
        settingsContent.Children.Add(AnalyticsHeading("CONSERVAR HISTORIAL"));
        var choices = new WrapPanel();
        int current = ReadHistoryDays();
        foreach (var option in new[] { 30, 90, 180, 0 })
        {
            int captured = option; string label = option == 0 ? "Siempre" : option + " días";
            var button = ChoiceButton(label, current == option, delegate { WriteConfigValue("history_days", captured); RefreshSettings(); });
            choices.Children.Add(button);
        }
        settingsContent.Children.Add(choices);
        settingsContent.Children.Add(AnalyticsHeading("FASES Y EVIDENCIA"));
        AddSettingsNote("La pipeline observa la ejecución. Revisión y cierre siguen pendientes de evidencia. El cambio automático de modelo entre fases aún no está activado.");
        bool telemetry = ReadConfigBool("inference_telemetry", false);
        settingsContent.Children.Add(SettingsAction(telemetry ? "Desactivar telemetría local" : "Activar telemetría local",
            telemetry ? "Confirma inferencias mediante un receptor temporal en este equipo. Se aplicará al reiniciar Desktop." :
            "Confirma modelo y razonamiento ejecutados. Solo usa un receptor temporal en este equipo; no guarda mensajes ni respuestas.",
            delegate { WriteConfigValue("inference_telemetry", !telemetry); RefreshSettings(); }));
        BuildRoutingEngineSettings();
        settingsContent.Children.Add(AnalyticsHeading("POLÍTICA ACTUAL"));
        AddPolicy("Luna", "Tareas delimitadas", "Ligero"); AddPolicy("Terra", "Cambios concretos", "Medio");
        AddPolicy("Sol", "Ingeniería compleja", "Alto"); AddPolicy("Astra", "UX, auditorías y gran alcance", "Muy alto");
        settingsContent.Children.Add(AnalyticsHeading("PRIVACIDAD"));
        AddSettingsNote("El historial guarda fecha, tarea, modelo, razonamiento, motores, tiempos, motivos, estado, incidencias y contadores de tokens. No guarda mensajes, respuestas, adjuntos, herramientas ni credenciales.");
    }

    double Telemetry(string key)
    {
        double value; return telemetryHealth.TryGetValue(key, out value) ? value : 0;
    }

    string connectionMessage;
    bool connectionBusy;
    void ManageConnection(string action)
    {
        if (preview || connectionBusy) return;
        connectionBusy = true; connectionMessage = "Comprobando conexión…"; RefreshSettings();
        System.Threading.ThreadPool.QueueUserWorkItem(delegate {
            string message = "No se pudo completar la operación. Tus tareas siguen abiertas.";
            try
            {
                var cfg = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(Root, "config.local.json")));
                bool packaged = cfg.ContainsKey("desktop_runtime");
                var start = new System.Diagnostics.ProcessStartInfo(packaged ? Path.Combine(Root, (string)cfg["desktop_runtime"]) : (string)cfg["python"])
                {
                    Arguments = (packaged ? "" : "\"" + Path.Combine(Root, "desktop.py") + "\" ") + action,
                    UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true,
                    RedirectStandardError = true, StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
                };
                start.EnvironmentVariables["PYTHONUTF8"] = "1";
                start.EnvironmentVariables["PERSONAL_CODEX_ROUTER_ROOT"] = Root;
                start.EnvironmentVariables["PERSONAL_CODEX_ROUTER_CONFIG"] = Path.Combine(Root, "config.local.json");
                using (var process = System.Diagnostics.Process.Start(start))
                {
                    var errors = process.StandardError.ReadToEndAsync();
                    string output = process.StandardOutput.ReadToEnd(); process.WaitForExit();
                    var data = Json.Deserialize<Dictionary<string, object>>(process.ExitCode == 0 ? output : errors.Result);
                    if (data.ContainsKey("error")) message = (string)data["error"];
                    else if (data.ContainsKey("message")) message = (string)data["message"];
                    else message = String(data, "discovery", "") != "ready" ? "No se ha encontrado una instalación compatible." :
                        String(data, "connection", "") == "desktop_connected" ? "Desktop conectado al selector." :
                        String(data, "connection", "") == "bridge_observed" ? "Hay un puente activo; falta confirmar la conexión de Desktop." :
                        data.ContainsKey("registered") && (bool)data["registered"] ? "Conexión instalada. Falta observar el nuevo arranque de Desktop." :
                        "Desktop detectado. El inicio habitual todavía no está conectado.";
                }
            }
            catch { }
            Dispatcher.BeginInvoke((Action)delegate { connectionBusy = false; connectionMessage = message; RefreshSettings(); });
        });
    }

    static bool ValidEngineResponse(EngineComparison item)
    {
        return item.Status == "ok" || item.Status == "guardrail";
    }

    void AddEngineTelemetry()
    {
        var attempts = decisions.SelectMany(item => item.Comparisons.Values).ToList();
        statisticsContent.Children.Add(AnalyticsHeading("FIABILIDAD DE LOS MOTORES"));
        if (attempts.Count == 0) { statisticsContent.Children.Add(Txt("Sin clasificaciones externas registradas todavía", 12, Muted)); return; }
        foreach (var group in attempts.GroupBy(item => FriendlyEngine(item.Engine)).OrderBy(group => group.Key))
        {
            var rows = group.ToList(); int valid = rows.Count(ValidEngineResponse);
            AddMetric(group.Key + " · respuestas válidas", valid + " / " + rows.Count,
                valid * 1.0 / rows.Count, valid == rows.Count ? Good : Warning);
            int fallback = rows.Count(item => item.Active && item.Status != "ok");
            if (fallback > 0) AddMetric(group.Key + " · respaldo local", fallback.ToString(), fallback * 1.0 / rows.Count, Warning);
            var timed = rows.Where(item => item.LatencyMs > 0).ToList();
            if (timed.Count > 0)
            {
                var values = timed.Select(item => item.LatencyMs).OrderBy(value => value).ToList();
                AddMetric(group.Key + " · latencia p50 / p95", Math.Round(values[(int)Math.Ceiling(values.Count * .5) - 1]) + " / " +
                    Math.Round(values[(int)Math.Ceiling(values.Count * .95) - 1]) + " ms · n=" + values.Count, 1, Accent);
            }
            if (timed.Count > 0) AddMetric(group.Key + " · demora media", Math.Round(timed.Average(item => item.LatencyMs)) + " ms",
                Math.Min(1, timed.Average(item => item.LatencyMs) / 6000), Accent);
            long input = rows.Sum(item => (long)item.InputTokens), output = rows.Sum(item => (long)item.OutputTokens);
            if (input + output > 0) AddMetric(group.Key + " · tokens de clasificación", (input + output).ToString("N0"), 1, Muted);
            var failures = rows.Where(item => !System.String.IsNullOrEmpty(item.Failure)).GroupBy(item => FriendlyEngineFailure(item.Failure))
                .OrderByDescending(item => item.Count()).FirstOrDefault();
            if (failures != null) AddMetric(group.Key + " · principal incidencia", failures.Key + " · " + failures.Count(),
                failures.Count() * 1.0 / rows.Count, Warning);
            var confidence = rows.Where(item => item.Confidence > 0).ToList();
            if (confidence.Count > 0) AddMetric(group.Key + " · confianza media", Math.Round(confidence.Average(item => item.Confidence) * 100) + "%",
                confidence.Average(item => item.Confidence), Good);
        }
        var shadows = decisions.SelectMany(decision => decision.Comparisons.Values.Where(item => !item.Active && item.Status == "ok")
            .Select(item => new { Decision = decision, Comparison = item })).ToList();
        if (shadows.Count > 0)
        {
            int agreement = shadows.Count(item => item.Decision.Model == item.Comparison.Model && item.Decision.Effort == item.Comparison.Effort);
            statisticsContent.Children.Add(AnalyticsHeading("COINCIDENCIA DE COMPARACIONES"));
            AddMetric("Propuestas que coinciden con la selección aplicada", agreement + " / " + shadows.Count,
                agreement * 1.0 / shadows.Count, Accent);
        }
    }

    void AddEngineQuality()
    {
        var rated = decisions.Where(item => !System.String.IsNullOrEmpty(item.Quality)).ToList();
        statisticsContent.Children.Add(AnalyticsHeading("VALORACIÓN POR MOTOR APLICADO"));
        if (rated.Count == 0) { statisticsContent.Children.Add(Txt("Valora decisiones para comparar la calidad aplicada", 12, Muted)); return; }
        foreach (var group in rated.GroupBy(item => FriendlyEngine(item.RoutingEngine ?? "rules")).OrderBy(group => group.Key))
        {
            var rows = group.ToList(); int adequate = rows.Count(item => item.Quality == "adequate");
            AddMetric(group.Key + " · adecuadas", adequate + " / " + rows.Count,
                adequate * 1.0 / rows.Count, adequate * 2 >= rows.Count ? Good : Warning);
        }
    }

    void BuildRoutingEngineSettings(string selectedEngine = null)
    {
        settingsContent.Children.Add(AnalyticsHeading("MOTOR DE ENRUTAMIENTO"));
        string current = selectedEngine ?? ReadConfigString("routing_engine", "rules");
        var engines = new WrapPanel();
        foreach (var option in new[] { new[] { "rules", "Reglas" }, new[] { "jev", "Jev" } })
        {
            string key = option[0], label = option[1];
            var button = ChoiceButton(label, current == key, delegate { WriteConfigValue("routing_engine", key); RefreshSettings(); });
            engines.Children.Add(button);
        }
        settingsContent.Children.Add(engines);
        AddSettingsNote(current == "jev" ? "Jev decide con una respuesta estructurada; las reglas mantienen los límites de seguridad y compatibilidad." :
            "Las reglas locales deciden al instante sin enviar el mensaje a otro servicio.");

        settingsContent.Children.Add(AnalyticsHeading("COMPARACIÓN EN PARALELO"));
        var comparisons = ReadConfigStrings("comparison_engines").Where(value => value == "rules" || value == "jev").ToList();
        var compare = new WrapPanel();
        foreach (var option in new[] { new[] { "rules", "Reglas" }, new[] { "jev", "Jev" } })
        {
            string key = option[0], label = option[1]; bool active = current == key;
            var button = ChoiceButton(label, active || comparisons.Contains(key), delegate { ToggleComparison(key); RefreshSettings(); }, true);
            button.IsEnabled = !active;
            button.ToolTip = active ? "Motor activo: su decisión ya se registra" : "Incluir o quitar de la comparación";
            compare.Children.Add(button);
        }
        settingsContent.Children.Add(compare);
        AddSettingsNote("El motor activo ya se registra. Marca otros para comparar sus propuestas. Para configurar uno, selecciónalo arriba.");

        if (current == "jev") BuildJevSettings();
    }

    void BuildJevSettings()
    {
        settingsContent.Children.Add(AnalyticsHeading("JEV"));
        string connection = ReadNestedConfigString("jev", "connection", "typesafe");
        var connections = new WrapPanel();
        foreach (var option in new[] { new[] { "vercel", "Vercel AI Gateway" }, new[] { "typesafe", "TypeSafe directo" } })
        {
            string value = option[0], label = option[1];
            connections.Children.Add(ChoiceButton(label, connection == value, delegate {
                WriteNestedConfigValue("jev", "connection", value); RefreshSettings();
            }));
        }
        settingsContent.Children.Add(connections);
        AddSettingsNote(connection == "vercel" ? "Usa typesafe-ai/jev mediante Vercel AI Gateway; el acceso puede requerir créditos." :
            "Conecta directamente con TypeSafe usando jev-latest.");
        bool keyReady = File.Exists(Path.Combine(StateFolder, "jev-" + connection + ".secret")) ||
            !System.String.IsNullOrEmpty(Environment.GetEnvironmentVariable(connection == "vercel" ? "AI_GATEWAY_API_KEY" : "TYPESAFE_API_KEY"));
        settingsContent.Children.Add(InlineKeySettings("jev-" + connection, connection == "vercel" ? "Vercel AI Gateway" : "TypeSafe", keyReady));
        if (!keyReady && File.Exists(Path.Combine(StateFolder, "jev.secret")))
            AddSettingsNote("La clave anterior no identifica su proveedor. Introduce la clave de esta conexión una vez para vincularla de forma segura.");
    }

    static Button ChoiceButton(string label, bool selected, RoutedEventHandler click, bool multiple = false)
    {
        var button = Btn((multiple ? (selected ? "✓  " : "+  ") : (selected ? "●  " : "○  ")) + label, click, false);
        button.MinWidth = 0; button.Margin = new Thickness(0, 0, 6, 6);
        button.Padding = new Thickness(9, 4, 9, 4);
        button.Background = selected ? Brush("#373343") : Brush("#292A31");
        button.Foreground = selected ? Accent : Ink;
        button.BorderBrush = selected ? Accent : Brush("#51525D");
        button.BorderThickness = new Thickness(1);
        System.Windows.Automation.AutomationProperties.SetName(button, label);
        System.Windows.Automation.AutomationProperties.SetHelpText(button, selected ? "Seleccionado" : "Sin seleccionar");
        return button;
    }

    UIElement InlineKeySettings(string secretId, string name, bool keyReady)
    {
        var stack = new StackPanel();
        var editor = new StackPanel { Visibility = Visibility.Collapsed, Margin = new Thickness(0, 10, 0, 0) };
        string title = keyReady ? "Clave guardada de " + name : "Añadir clave de " + name;
        var toggle = SettingsAction(title, keyReady ? "Pulsa para reemplazar la clave guardada." : "Introduce tu clave aquí mismo, dentro del panel.", delegate {
            editor.Visibility = editor.Visibility == Visibility.Visible ? Visibility.Collapsed : Visibility.Visible;
        });
        stack.Children.Add(toggle);
        var note = Txt("Clave API · se guarda cifrada para tu usuario de Windows", 11, Muted);
        note.TextWrapping = TextWrapping.Wrap; note.Margin = new Thickness(0, 0, 0, 8); editor.Children.Add(note);
        var input = new PasswordBox { Height = 34, Background = TransparentBrush, Foreground = Ink,
            BorderThickness = new Thickness(0), Padding = new Thickness(10, 7, 10, 7), FontSize = 13 };
        System.Windows.Automation.AutomationProperties.SetName(input, "Clave API de " + name);
        var field = new Border { Background = Panel, CornerRadius = new CornerRadius(12), BorderThickness = new Thickness(1), BorderBrush = Line, Child = input };
        input.GotKeyboardFocus += delegate { field.BorderBrush = Accent; };
        input.LostKeyboardFocus += delegate { field.BorderBrush = Line; };
        editor.Children.Add(field);
        var feedback = Txt("", 11, Warning); feedback.TextWrapping = TextWrapping.Wrap;
        var actions = new WrapPanel { Margin = new Thickness(0, 10, 0, 0) };
        var save = ChoiceButton("Guardar clave", false, delegate {
            if (input.Password.Trim().Length == 0) { feedback.Text = "Introduce una clave antes de guardar."; return; }
            try
            {
                Directory.CreateDirectory(StateFolder);
                byte[] cipher = ProtectedData.Protect(Encoding.UTF8.GetBytes(input.Password.Trim()), null, DataProtectionScope.CurrentUser);
                File.WriteAllBytes(Path.Combine(StateFolder, secretId + ".secret"), cipher);
                input.Clear(); RefreshSettings();
            }
            catch { feedback.Text = "No se pudo guardar la clave. Inténtalo de nuevo."; }
        });
        // This is an action, not a selectable value.
        save.Content = "Guardar clave";
        actions.Children.Add(save);
        actions.Children.Add(Btn("Cancelar", delegate { input.Clear(); feedback.Text = ""; editor.Visibility = Visibility.Collapsed; }, false));
        editor.Children.Add(actions); editor.Children.Add(feedback);
        editor.IsVisibleChanged += delegate {
            if (editor.IsVisible) input.Focus(); else input.Clear();
        };
        stack.Children.Add(editor);
        return stack;
    }

    UIElement SettingsAction(string title, string description, Action action)
    {
        var button = new Button { Background = Panel2, BorderBrush = Line, BorderThickness = new Thickness(1),
            Padding = new Thickness(12), Margin = new Thickness(0, 10, 0, 0), Template = RowButtonTemplate(), Cursor = Cursors.Hand };
        var copy = new StackPanel(); copy.Children.Add(Txt(title, 13, Ink, FontWeights.SemiBold));
        var detail = Txt(description, 11, Muted); detail.TextWrapping = TextWrapping.Wrap; detail.Margin = new Thickness(0, 4, 0, 0); copy.Children.Add(detail);
        button.Content = copy; button.Click += delegate { action(); }; return button;
    }

    void AddPolicy(string model, string use, string effort)
    {
        var row = new Grid { Margin = new Thickness(0, 4, 0, 4) };
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(65) });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        row.Children.Add(Badge(model, true)); var text = Txt(use, 12, Muted); text.Margin = new Thickness(8, 0, 8, 0); Grid.SetColumn(text, 1); row.Children.Add(text);
        var level = Badge(effort, false); Grid.SetColumn(level, 2); row.Children.Add(level); settingsContent.Children.Add(row);
    }

    void AddSettingsNote(string value)
    {
        var note = Txt(value, 12, Muted); note.TextWrapping = TextWrapping.Wrap; note.Margin = new Thickness(0, 6, 0, 0); settingsContent.Children.Add(note);
    }

    int ReadHistoryDays()
    {
        try
        {
            var data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(Root, "config.local.json")));
            return data.ContainsKey("history_days") ? Convert.ToInt32(data["history_days"]) : 90;
        }
        catch { return 90; }
    }

    bool ReadConfigBool(string key, bool fallback)
    {
        try
        {
            var data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(Root, "config.local.json")));
            return data.ContainsKey(key) ? Convert.ToBoolean(data[key]) : fallback;
        }
        catch { return fallback; }
    }

    string ReadConfigString(string key, string fallback)
    {
        try
        {
            var data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(Root, "config.local.json")));
            return data.ContainsKey(key) ? Convert.ToString(data[key]) : fallback;
        }
        catch { return fallback; }
    }

    List<string> ReadConfigStrings(string key)
    {
        try
        {
            var data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(Root, "config.local.json")));
            if (!data.ContainsKey(key)) return new List<string>();
            return ((System.Collections.IEnumerable)data[key]).Cast<object>().Select(Convert.ToString).Where(item => item != null).ToList();
        }
        catch { return new List<string>(); }
    }

    string ReadNestedConfigString(string parent, string key, string fallback)
    {
        try
        {
            var data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(Root, "config.local.json")));
            var nested = Dict(data[parent]); return nested.ContainsKey(key) ? Convert.ToString(nested[key]) : fallback;
        }
        catch { return fallback; }
    }

    bool ReadNestedConfigBool(string parent, string key, bool fallback)
    {
        try
        {
            var data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(Root, "config.local.json")));
            return Convert.ToBoolean(Dict(data[parent])[key]);
        }
        catch { return fallback; }
    }

    void WriteConfigValue(string key, object value)
    {
        try
        {
            string path = Path.Combine(Root, "config.local.json");
            var data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(path)); data[key] = value;
            string temp = path + ".monitor.tmp"; File.WriteAllText(temp, Json.Serialize(data), new System.Text.UTF8Encoding(false));
            File.Replace(temp, path, null);
        }
        catch { connection.Text = "No se pudo guardar el ajuste"; connection.Foreground = Warning; }
    }

    void WriteNestedConfigValue(string parent, string key, object value)
    {
        try
        {
            string path = Path.Combine(Root, "config.local.json");
            var data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(path));
            Dictionary<string, object> nested;
            if (data.ContainsKey(parent)) nested = Dict(data[parent]); else data[parent] = nested = new Dictionary<string, object>();
            nested[key] = value;
            string temp = path + ".monitor.tmp"; File.WriteAllText(temp, Json.Serialize(data), new UTF8Encoding(false));
            File.Replace(temp, path, null);
        }
        catch { connection.Text = "No se pudo guardar el ajuste"; connection.Foreground = Warning; }
    }

    void ToggleComparison(string engine)
    {
        var values = ReadConfigStrings("comparison_engines");
        values = values.Where(value => value == "rules" || value == "jev").Distinct().ToList();
        if (values.Contains(engine)) values.Remove(engine); else values.Add(engine);
        WriteConfigValue("comparison_engines", values.Distinct().ToArray());
    }

    static string FriendlyEngine(string engine)
    {
        switch (engine) { case "jev": return "Jev"; case "provider": return "Proveedor retirado"; default: return "Reglas locales"; }
    }

    static string FriendlyEngineStatus(string status)
    {
        switch (status) { case "not_configured": return "sin configurar"; case "unavailable": return "sin conexión";
            case "invalid": return "respuesta no válida"; case "guardrail": return "limitado por la política local"; default: return status ?? "sin datos"; }
    }

    static string FriendlyEngineFailure(string failure)
    {
        switch (failure) { case "invalid_response": return "formato de respuesta"; case "timeout": return "tiempo agotado";
            case "account_access_restricted": return "Vercel restringe el plan gratuito; requiere créditos";
            case "circuit_open": return "En pausa por fallos; se usan reglas locales";
            case "network": return "red local"; case "authentication": return "credenciales"; case "rate_limited": return "límite de uso";
            case "missing_api_key": return "falta clave API"; case "unsupported_provider": return "proveedor no disponible";
            default: return failure ?? "incidencia desconocida"; }
    }

    static string FriendlyQuality(string quality)
    {
        switch (quality) { case "insufficient": return "Insuficiente"; case "adequate": return "Adecuada"; case "excessive": return "Excesiva"; default: return quality ?? "Sin valorar"; }
    }

    static string FriendlyStatus(string value)
    {
        switch (value) { case "completed": case "idle": return "Completada"; case "inProgress": case "active": case "running": return "Trabajando";
            case "finished": return "Finalizada"; case "pending": return "Pendiente"; case "error": case "failed": return "Error"; case "interrupted": return "Interrumpida";
            default: return Status(value ?? "unknown"); }
    }

    static string HistoryTime(double timestamp)
    {
        if (timestamp <= 0) return "Fecha sin confirmar";
        try { return new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc).AddSeconds(timestamp).ToLocalTime().ToString("dd/MM · HH:mm"); }
        catch { return "Fecha sin confirmar"; }
    }

    static string FormatDuration(double seconds)
    {
        if (seconds < 60) return Math.Round(seconds) + " s";
        if (seconds < 3600) return Math.Round(seconds / 60) + " min";
        return Math.Round(seconds / 3600, 1) + " h";
    }

    void PaintAnalyticsFixtures()
    {
        decisions.Clear();
        double now = (DateTime.UtcNow - new DateTime(1970, 1, 1)).TotalSeconds;
        decisions.Add(new DecisionRecord { Id = "fixture-1", Thread = "example", Title = "Revisar el monitor de Codex",
            Model = "Astra", Effort = "Muy alto", ModelReason = "diseño de interfaces, UX o evaluación visual",
            EffortReason = "revisión profunda por amplitud, UX, auditoría o consecuencias", Source = "automatic",
            Status = "completed", Time = now, StartedTime = now - 190, FinishedTime = now,
            InputTokens = 28400, OutputTokens = 2100, CachedTokens = 23700, Quality = "adequate" });
        decisions.Add(new DecisionRecord { Id = "fixture-2", Thread = "translation", Title = "Traducir un mensaje",
            Model = "Luna", Effort = "Ligero", ModelReason = "consulta o transformación delimitada",
            EffortReason = "tarea delimitada: razonamiento ligero", Source = "automatic", Status = "completed", Time = now - 260, Quality = "excessive" });
        decisions.Add(new DecisionRecord { Id = "fixture-3", Thread = "feature", Title = "Ajustar un componente",
            Model = "Terra", Effort = "Medio", ModelReason = "cambio concreto y comprobable",
            EffortReason = "análisis moderado para una tarea concreta", Source = "automatic", Status = "inProgress", Time = now - 520 });
        decisions.Add(new DecisionRecord { Id = "fixture-4", Thread = "failure", Title = "Investigar una migración",
            Model = "Sol", Effort = "Alto", ModelReason = "ingeniería compleja con alcance definido",
            EffortReason = "trabajo complejo que requiere más profundidad", Source = "automatic", Status = "error",
            Error = "turn_rejected", Signal = "retry", Time = now - 830 });
        RebuildHistory(); RebuildStatistics();
    }
}
