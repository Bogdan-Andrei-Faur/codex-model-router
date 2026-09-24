# Phase routing feasibility — 2026-09-23

## Scope and decision

This is a bounded native-protocol experiment, not an enabled orchestration
feature. Keep production routing at `turn/start`. Prefer broad phases and few
transitions. No user task, prompt, credentials, approval policy or installed
Desktop configuration was modified by the probe.

Desktop build tested: **26.917.8451.0**, Windows. The protocol schema was generated
from its staged native backend with `app-server generate-json-schema --experimental`.
The current public [App Server documentation](https://learn.chatgpt.com/docs/app-server)
documents per-turn model overrides and says `turn/steer` does not accept them.
The installed experimental schema additionally exposes `turn/settings/update`.

## Verified protocol behavior

- `turn/settings/update` accepts model/effort for a running turn only when
  `features.step_model_switching` is enabled. The flag was passed only to the
  isolated test process, never written to the user's configuration.
- Its schema explicitly says publication applies to subsequent captures.
  Already captured steps and child sessions do not change; `applied` does not
  guarantee a subsequent inference. Pending approvals retain their reviewer.
- While a synthetic tool call waited, changing effort from Medium to High
  returned `applied` and the turn finished normally.
- Terra → Astra in the same running turn was rejected with:
  `the destination changes the admitted node REPL review requirement`.
  This is a compatibility restriction for the tested setup, not proof that every
  model pair or tool setup is incompatible. Do not bypass it by relaxing review.
- Starting a subsequent completed-boundary turn with Astra/Medium retained both
  a synthetic checkpoint and an unpredictable receipt returned by the tool.
  The tool ran exactly once across both turns. No manual context summary was needed.
- Updating an already completed turn returned `targetUnavailable`.
- The isolated backend shut down cleanly.

The initial two-turn probe did **not** independently observe which model
performed each inference. The compatibility follow-up below adds native runtime
telemetry for same-turn changes; neither experiment attests server-side model
identity independently of Codex's own telemetry.

## Compatibility follow-up (same build, Windows)

Backend: **codex-cli 0.155.0-alpha.16.3**. Seven isolated turns tested all twelve
directed model pairs, and exercised all six accepted transitions through another
completed inference step. Each turn started at Medium, waited at an in-memory
tool, tested destinations serially (restoring the admitted source after each
accepted probe), then selected its final destination at High before returning
the unpredictable receipt. Nothing was interrupted or replayed.

| Admitted source → next model | Luna | Terra | Sol | Astra |
| --- | --- | --- | --- | --- |
| Luna | — | Accepted + observed | Accepted + observed | Rejected |
| Terra | Accepted + observed | — | Accepted + observed | Rejected |
| Sol | Accepted + observed | Accepted + observed | — | Rejected |
| Astra | Rejected | Rejected | Rejected | Effort change observed |

“Observed” means the native OTLP `codex.sse_event` / `response.completed`
telemetry identified the source/Medium and destination/High steps. It is stronger
than a settings acknowledgement or asking the model its name. It is still
client-runtime evidence, not independent server attestation. All seven turns
returned their checkpoint and unpredictable tool receipt, executed the receipt
tool exactly once, and shut down with exit 0; telemetry parsing reported no errors.

All six Astra transitions failed with the same admitted node REPL review error.
The cached catalog dated 2026-09-21 marks
`node_repl_auto_review_required=true` for Astra and false for the other three.
The live rejections, not that cache alone, establish today's restriction.
The official implementation's
[step activation checks](https://github.com/openai/codex/blob/main/codex-rs/core/src/session/step_activation.rs)
compare the destination against both the original admitted model and the current
model. Other checks cover approval authority, Guardian coverage/policy and tool
availability. Consequently, routing through an intermediate model does not
solve the Astra boundary. Do not change safety metadata to force compatibility.
Public `main` is explanatory evidence, not a version-pinned match to this binary.

### Product implication

Broad automatic phases are **technically feasible for the compatible group**
within a single native turn. Effort can also change while remaining on Astra.
Unrestricted switching across all four models inside one native turn is **not
supported by the tested build**. Re-check compatibility on application/catalog
updates; do not hard-code the current matrix as a permanent guarantee.

The useful first implementation would use explicit broad phase checkpoints,
with the current model held until the router decides and receives native
acknowledgement. The synthetic tool proves this controlled boundary works.
Reacting to an ordinary tool-completed notification alone is insufficient:
the backend may already have captured the next step by the time a change arrives.
Checkpoint integration with Desktop remains untested and is not implemented.

If a request clearly requires Astra, start with Astra and vary effort when useful.
If an unexpected later phase needs Astra, do not silently continue on a weaker
model or repeatedly retry a rejected switch. Report the blocked transition and
retain the existing execution until a validated completed-turn handoff is available.
The earlier Terra → Astra completed-turn test preserved context, but seamless
Desktop continuation, cancellation and user input still need product validation.

For the monitor, distinguish a proposed model, an accepted setting and a
model/effort observed on a completed inference. Child agents do not inherit
updates automatically and need separate handling. These probes disabled
multi-agent delegation; no conclusions about child-session compatibility follow.

## Reproduction

`python tests/smoke_phases.py --live` consumes a small amount of the existing
ChatGPT subscription. It discovers the installed backend and starts a separate
ephemeral thread in an empty temporary directory. It disables configured MCP
servers, apps, shell and web tools; the only external tool handler is an in-memory
synthetic receipt. Unknown requests are rejected. No phases are delegated to
agents and no filesystem/deployment work is performed by the model.

The receipt cannot be guessed from the prompt: the probe checks actual tool
execution and preservation of its output, not an answer the model could invent.
Current builds require the code-mode host for the dynamic tool. Disabling that
host caused early exploratory tests to finish without executing the tool; their
assertions correctly failed. The finalized probe enables code mode only in its
own process and explicitly prints the tool result into model-visible context.

Result: `state/phase-probe.json` (ignored by Git). It records no user messages,
credentials or tool arguments/results. It records two real native turns, rather
than pretending they are one turn from Desktop's perspective.

Compatibility matrix and completion evidence:

```text
python tests/probe_model_compatibility.py --live
python tests/probe_model_compatibility.py --live --reverse
```

These consume four and three short subscription turns respectively. Reports:
`state/model-compatibility-probe.json` and
`state/model-compatibility-reverse-probe.json`. The probe temporarily configures
its own native subprocess to export logs to a random loopback-only HTTP port.
It disables prompt logging and retains only allowlisted model/effort/event fields;
raw logs, resource identity, credentials, prompts and tool results are discarded.
No production telemetry configuration is changed. A missing telemetry event is
a failed verification, never interpreted as a successful model switch.

## Remaining product validation

1. Integrate an explicit broad-phase checkpoint with Desktop and test realistic
   tool/approval configurations. The synthetic compatibility matrix is established,
   but it is not a guarantee for every permission profile or child agent.
2. The production bridge now records conservative phase lifecycle metadata
   (`proposed`, `accepted`, `active`, `settings_published`, `completed`,
   `blocked`/`failed`) and the monitor displays it. It deliberately does not
   label a selector/settings notification as an observed inference; connect a
   verified inference telemetry source before adding that label.
3. Validate Desktop's presentation, cancellation, approvals and new user input
   when phases use successive native turns. This probe does not establish a
   seamless single-response experience in Desktop.
4. Validate restart recovery and macOS against that platform's installed backend.

Until these are established, expose no automatic phase-switching toggle and no
pipeline of invented phases. A future pipeline should distinguish planned,
active, completed, interrupted and blocked stages, with model/effort provenance.
