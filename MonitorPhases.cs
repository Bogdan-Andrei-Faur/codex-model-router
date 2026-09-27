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
        if (String(source, "phase_status") == "applied" ||
            (source.ContainsKey("phase_id") && String(source, "phase_id") != String(target, "phase_id") && String(source, "phase_status") == "accepted"))
        {
            if (target.ContainsKey("observed_model"))
            {
                if (!target.ContainsKey("prior_inferences")) target["prior_inferences"] = new List<string>();
                ((List<string>)target["prior_inferences"]).Add(Model(String(target, "observed_model")) + " · " + Effort(String(target, "observed_effort")) + " · " + String(target, "evidence_confidence"));
            }
            foreach (string key in new[] { "observed_model", "observed_effort", "observed_candidate_model", "observed_candidate_effort", "evidence_confidence" }) target.Remove(key);
            if (source.ContainsKey("phase_model")) target["accepted_model"] = source["phase_model"];
            if (source.ContainsKey("phase_effort")) target["accepted_effort"] = source["phase_effort"];
        }
        foreach (string key in new[] { "status", "phase_id", "phase_name", "phase_model", "phase_effort", "phase_status", "phase_transition", "pipeline_mode", "phase_pipeline",
            "accepted_model", "accepted_effort", "configured_model", "configured_effort", "observed_model", "observed_effort", "observed_candidate_model", "observed_candidate_effort", "evidence_confidence" })
            if (source.ContainsKey(key) && !(key == "phase_id" && String(source, "event") == "phase_checkpoint" && String(source, "phase_status") != "applied")) target[key] = source[key];
    }

    static string PhaseStatus(string value)
    {
        switch (value)
        {
            case "proposed": return "Propuesta";
            case "requested": return "Cambio solicitado";
            case "applied": return "Cambio aceptado";
            case "rejected": return "Cambio rechazado";
            case "preserved": return "Selección conservada";
            case "unchanged": return "Sin cambio";
            case "requires_new_turn": return "Requiere otro turno";
            case "unknown_after_timeout": return "Cambio sin confirmar";
            case "checkpoint_limit": return "Límite de fases";
            case "cancelled": return "Cancelado";
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
        if (String(data, "status") == "interrupted") lines.Add("Turno interrumpido; no acredita la terminación de todos los procesos de sus herramientas.");
        lines.Add((source == "manual" || source == "preserved" || source == "agent" ? "Solicitado" : "Propuesto") + " · " + model + " · " + effort);
        foreach (var entry in new[] { new[] { "accepted", "Aceptado por Codex" }, new[] { "configured", "Configuración publicada" },
            new[] { "observed", String(data, "evidence_confidence") == "confirmed" ? "Inferencia confirmada localmente" : "Observación anterior sin correlación" } })
        {
            string selected = String(data, entry[0] + "_model");
            if (selected != "") lines.Add(entry[1] + " · " + Model(selected) + " · " + Effort(String(data, entry[0] + "_effort")));
        }
        if (String(data, "observed_model") == "") lines.Add("Inferencia real · sin confirmación disponible");
        if (String(data, "observed_candidate_model") != "") lines.Add("Coincidencia probable · " + Model(String(data, "observed_candidate_model")) + " · " + Effort(String(data, "observed_candidate_effort")));
        if (data.ContainsKey("prior_inferences")) foreach (string prior in (List<string>)data["prior_inferences"]) lines.Add("Inferencia de una fase anterior · " + prior);
        if (data.ContainsKey("phase_events"))
            foreach (var entry in (List<Dictionary<string, object>>)data["phase_events"])
                lines.Add("Fase " + String(entry, "phase_name") + " · " + PhaseStatus(String(entry, "phase_status")) + " · " + Model(String(entry, "phase_model")));
        if (data.ContainsKey("inference_samples"))
        {
            foreach (var sample in ((Dictionary<string, Dictionary<string, object>>)data["inference_samples"]).Values)
            {
                lines.Add(String(sample, "inference_event_name") + " / " + String(sample, "inference_event_kind") + " · " + String(sample, "evidence_confidence") + " · registros " + Number(sample, "count"));
                foreach (string key in new[] { "inference_input_tokens", "inference_output_tokens", "inference_ttft_ms", "inference_duration_ms", "inference_http_status" })
                    if (sample.ContainsKey(key)) lines.Add(key + " · " + Number(sample, key));
            }
            lines.Add("Último registro por clase; duración del evento no equivale a latencia total de inferencia.");
        }
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
