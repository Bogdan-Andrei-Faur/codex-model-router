using System;
using System.Collections;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

internal sealed partial class ModernRouterMonitor
{
    readonly Border phaseHost = new Border();
    string phaseSignature;

    static void CopyPhaseEvidence(Dictionary<string, object> target, Dictionary<string, object> source)
    {
        foreach (string key in new[] { "phase_status", "phase_transition", "pipeline_mode", "phase_pipeline",
            "accepted_model", "accepted_effort", "configured_model", "configured_effort", "observed_model", "observed_effort", "evidence_confidence" })
            if (source.ContainsKey(key)) target[key] = source[key];
    }

    static string PhaseStatus(string value)
    {
        switch (value)
        {
            case "proposed": return "Propuesta";
            case "accepted": return "Aceptada por Codex";
            case "active": return "En curso";
            case "completed": return "Completada";
            case "blocked": return "Solicitud rechazada";
            case "failed": return "Con incidencia";
            case "interrupted": return "Interrumpida";
            default: return "Sin confirmar";
        }
    }

    static UIElement BuildPhasePipeline(Dictionary<string, object> data)
    {
        var content = new StackPanel();
        bool dynamic = String(data, "pipeline_mode") == "plan_and_observation";
        content.Children.Add(Txt(dynamic ? "PLAN DE TRABAJO · OBSERVACIÓN" : "PIPELINE · OBSERVACIÓN", 11, Accent, FontWeights.SemiBold));
        string status = String(data, "phase_status");
        var steps = new List<Dictionary<string, object>>();
        if (data.ContainsKey("phase_pipeline"))
            foreach (var item in (IEnumerable)data["phase_pipeline"]) steps.Add(Dict(item));
        if (steps.Count == 0)
        {
            steps.Add(new Dictionary<string, object> { { "label", "Ejecución en Codex" }, { "state", status } });
        }
        foreach (var step in steps)
        {
            string labelValue = String(step, "label", "Fase");
            string state = String(step, "state");
            bool observed = String(step, "evidence") == "observed" || labelValue == "Ejecución en Codex";
            var row = new Grid { Margin = new Thickness(0, 8, 0, 0) };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(16) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.45, GridUnitType.Star) });
            Brush color = state == "completed" ? Good : state == "active" ? Accent :
                observed && state != "" ? Accent : state == "selected" ? Good : Muted;
            row.Children.Add(new Border { Width = 7, Height = 7, CornerRadius = new CornerRadius(4),
                BorderThickness = new Thickness(1), BorderBrush = color, Background = observed || state == "selected" ? color : TransparentBrush,
                HorizontalAlignment = HorizontalAlignment.Left, VerticalAlignment = VerticalAlignment.Center });
            var label = Txt(labelValue, 12, observed || state == "selected" ? Ink : Muted, FontWeights.Medium);
            Grid.SetColumn(label, 1); row.Children.Add(label);
            string stateText = state == "planned" ? "Planificada" : state == "selected" ? "Seleccionada" : PhaseStatus(state);
            var text = Txt(stateText, 11, color); text.TextWrapping = TextWrapping.Wrap;
            text.TextAlignment = TextAlignment.Right; Grid.SetColumn(text, 2); row.Children.Add(text);
            content.Children.Add(row);
        }
        var note = Txt(dynamic ? "Las etapas son un plan; solo la ejecución en Codex se confirma por eventos reales." :
            status == "" ? "Esta ejecución no tiene estados de fase registrados." : "La evidencia interna de esta ejecución es limitada.", 11, Muted);
        note.TextWrapping = TextWrapping.Wrap; note.Margin = new Thickness(0, 9, 0, 0); content.Children.Add(note);
        return new Border { Background = Panel2, CornerRadius = new CornerRadius(16), Padding = new Thickness(12),
            Margin = new Thickness(0, 10, 0, 0), Child = content };
    }

    static string ExecutionEvidence(Dictionary<string, object> data, string model, string effort, string source)
    {
        var lines = new List<string>();
        lines.Add((source == "manual" || source == "preserved" || source == "agent" ? "Solicitado" : "Propuesto") + " · " + model + " · " + effort);
        foreach (var entry in new[] { new[] { "accepted", "Aceptado por Codex" }, new[] { "configured", "Configuración publicada" },
            new[] { "observed", String(data, "evidence_confidence") == "confirmed" ? "Inferencia confirmada localmente" : "Observación anterior sin correlación" } })
        {
            string selected = String(data, entry[0] + "_model");
            if (selected != "") lines.Add(entry[1] + " · " + Model(selected) + " · " + Effort(String(data, entry[0] + "_effort")));
        }
        if (String(data, "observed_model") == "") lines.Add("Inferencia real · sin confirmación disponible");
        return System.String.Join("\n", lines);
    }

    void RefreshPhasePipeline(string id, Dictionary<string, object> row)
    {
        var evidence = new Dictionary<string, object>(); CopyPhaseEvidence(evidence, row);
        string signature = id + ":" + Json.Serialize(evidence);
        if (phaseSignature == signature) return;
        phaseSignature = signature; phaseHost.Child = BuildPhasePipeline(evidence);
    }
}
