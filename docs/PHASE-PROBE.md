# Phase routing feasibility — updated 2026-09-25

> Current visual pipeline: Agents consumes validated native `turn/plan/updated`
> states for the current turn, or observed lifecycle fields when no plan exists.
> This visual projection does not trigger model switches or independently verify
> completed work. See [NOTCH-MONITOR.md](NOTCH-MONITOR.md#live-pipeline).
> The phase-switch boundaries and protocol experiments below remain separate.

## Scope and decision

The native experiments below established compatibility. The bridge now has an
opt-in checkpoint controller, disabled by default; see the integration section.
Prefer broad phases and few transitions. No existing user task, credentials or
approval policy was modified by the probes.

Initial Desktop build tested: **26.917.8451.0**, Windows. The protocol schema was generated
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
The isolated bridge integration is now implemented and tested below. Real
Desktop presentation, approvals and restart/resume remain separate acceptance gates.

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

## macOS verification — 2026-09-25

Reproduced on Apple Silicon with ChatGPT Desktop **26.917.71314** and
**codex-cli 0.155.0-alpha.16.4**, using Python **3.11.16**. The owner authorized
isolated subscription probes. The existing production Desktop connection was
left running; no automatic phase switching was enabled in its configuration.

All three commands passed, using nine synthetic turns in total:

```sh
python3.11 tests/smoke_phases.py --live
python3.11 tests/probe_model_compatibility.py --live
python3.11 tests/probe_model_compatibility.py --live --reverse
```

- The two-turn continuity probe accepted an effort update during the first
  turn, rejected Terra → Astra with the admitted node REPL review error, then
  completed a separate Astra turn retaining the checkpoint and unpredictable
  tool receipt. The tool executed once across both turns. Updating the completed
  turn returned `targetUnavailable`; the process exited with code 0.
- The seven compatibility turns reproduced the Windows matrix above: all six
  directed transitions among Luna, Terra and Sol were accepted and followed by
  a completed destination inference at High. Astra stayed on Astra and changed
  from Medium to High; all six transitions crossing its boundary were rejected
  with the same review-requirement error. No review requirements were relaxed.
- Each compatibility turn returned its checkpoint and receipt, executed the
  synthetic tool exactly once, and exited with code 0. Every run recorded native
  `response.completed` evidence for the source/Medium and destination/High,
  with zero telemetry parsing errors. This is native runtime evidence, not
  independent server-side identity attestation.
- Reports remain local and ignored by Git: `state/phase-probe.json`,
  `state/model-compatibility-probe.json` and
  `state/model-compatibility-reverse-probe.json`. The latter two identify the
  exact Desktop and backend versions and timestamp of this Mac validation.

This establishes the controlled native boundary on Mac as well as Windows.
It does **not** establish automatic phase detection, a Desktop checkpoint tool,
safe behavior across cancellation/steering/approvals or child-agent switching.
The subsequent implementation below adds an explicit checkpoint that holds continuation
until the native setting is acknowledged, with bounded waits, preserved control
messages and visible blocked transitions. Ordinary tool-completed notifications
alone still cannot guarantee that the next inference has not already started.

## Reproduction

These live probes require Python 3.11+ (`tomllib`); the router itself still
supports Python 3.9. `python tests/smoke_phases.py --live` consumes a small amount of the existing
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
bounded correlation and numeric performance fields may also be retained. Raw
logs, resource identity, credentials, prompts, free-form errors and tool results
are discarded.
No production telemetry configuration is changed. A missing telemetry event is
a failed verification, never interpreted as a successful model switch.

Production prompt collection is a separate explicit path. When
`prompt_logging: true`, the router records the exact user text it already receives
in `turn/start` to the private ignored file `state/prompts.jsonl` and correlates it
with the routing `decision_id`. The OTel collector still discards its raw body:
that body can mix the useful inference fields with resource attributes, tool data,
headers and other content that is unrelated to routing.

A 2026-09-27 isolated schema probe enabled native prompt telemetry for one
synthetic ephemeral turn and kept the payload only in process memory. The batch
contained the synthetic prompt plus account email/id, host name, endpoint and
free-form error fields. Its only correlation candidate was `conversation.id`;
there was no turn or response identifier. It also exposed useful bounded metrics:
input/output/cache/reasoning/tool tokens, duration, first-token latency, attempt,
success and HTTP status. Those metrics are now allowlisted; the raw batch is not.

## Remaining product validation

### Implemented bridge integration (macOS, 2026-09-25)

`phase_control.py` registers `router_phase_checkpoint` on new durable
`thread/start` requests when `phase_routing: true` was present at bridge startup
and the client negotiated the experimental API. Existing dynamic tools and
instructions are preserved. Internal ephemeral roots, forks, existing tasks
without enrollment, colliding tool names and non-OpenAI providers are excluded
from enrollment. The accepted thread ID is stored in a content-free ownership
marker, allowing the tool handler to recognize enrolled tasks after restart.

The tool asks the model to identify a broad next phase and remaining complexity.
Local policy selects the route; it does not invoke Jev again. This is a model
declared checkpoint, not independent proof that a semantic phase finished.
The controller preserves the initial quality/effort floors, catalog constraints,
manual mode, explicit user choices and the Astra compatibility boundary. It
does not select Max/Ultra automatically. If later work requires Astra from a
different model, the tool explicitly asks Codex to stop that phase and explain
the need for a new turn. It does not automatically interrupt or replay work.

Each task has at most one pending update, one checkpoint per phase and four
checkpoints per turn. The tool result is held until the native settings reply;
unrelated protocol traffic remains responsive. Rejection disables further
phase updates for that turn. A missing reply reaches a ten-second deadline
(checked by the existing heartbeat), reports an uncertain result and disables
further changes; an already sent native update cannot be revoked. Late replies
are consumed internally. Completion/closure retires pending calls. Interrupt,
steer and client settings changes disable subsequent phase selection. None of
this changes approval requirements or already captured inference steps.

Activation for a controlled Desktop test: use **Ajustes → Activar cambios
automáticos por fases** (or set `phase_routing` to `true` in
`config.local.json`), fully restart Desktop, and create a new task. Existing
tasks without the tool continue using between-turn routing. Setting the flag
back to `false` prevents new phase changes; a restart also removes the native
feature override. An inherited tool on a known child/fork returns `preserved`;
it is not a child-routing mechanism.

```text
python3.11 tests/smoke_phase_bridge.py --live
```

This end-to-end probe creates a separate synthetic durable task because the
production controller deliberately excludes ephemeral helpers, then archives
it. It uses an empty temporary directory, disables shell/web/apps/MCP and
multi-agent tools, preserves the existing subscription, and changes no live
Desktop configuration. Its final passing run on Desktop **26.917.71314** showed:

- One native turn, initial **Terra/medium**, checkpoint **requested → applied**,
  subsequent **Sol/high** in native `response.completed` telemetry.
- The final synthetic answer preserved its checkpoint and the returned status.
  The owned dynamic-tool request stayed inside the bridge.
- Zero telemetry parse errors; synthetic task archived; subprocess exited 0.

Report: `state/phase-bridge-probe.json` (ignored). Telemetry is scoped to this
isolated subprocess; it does not guarantee native turn identifiers or constitute
independent server attestation. Early runs accepted and executed the checkpoint
but correctly failed telemetry assertions because of probe configuration and
flush timing; they are not counted as passing model-switch evidence.

### Natural checkpoint acceptance (macOS, 2026-09-26)

Version 0.4.3 makes the dynamic-tool contract imperative at substantive phase
boundaries. It does not inject or replace `baseInstructions` or
`developerInstructions`. The installed experimental schema exposes
`dynamicTools` on `thread/start` and `turn/settings/update`; existing tasks still
cannot be enrolled retroactively through the supported resume request.

`python3.11 tests/smoke_phase_bridge.py --live --natural` creates the same
isolated archived task, but neither its thread instructions nor its prompt order
the model to call `router_phase_checkpoint`. The prompt describes two phases and
marks the remaining verification as complex. On ChatGPT Desktop
**26.924.22138**, the final run passed:

- Initial route **Terra/medium**.
- The model invoked the checkpoint from the registered tool contract.
- Lifecycle **requested → applied**.
- Later native `response.completed` telemetry identified **Sol/high**.
- Non-empty final response, zero telemetry errors, archived synthetic task and
  subprocess exit code 0.

Two calibration runs invoked the checkpoint but declared the remaining phase
normal, so the controller correctly retained Terra/medium. A third run produced
the verified transition but failed an unrelated exact-output assertion. The
final probe checks the controlled boundary and continuation rather than requiring
the model to echo a test marker. This evidence establishes natural invocation
and one compatible same-turn transition in isolation. It does not prove that
every real task will need or select a different model at every boundary.

### Real Desktop task enrollment (macOS, 2026-09-26)

After restarting Desktop with product 0.4.3 and policy 7, a newly created project
chat exposed `router_phase_checkpoint` in its active tool contract. During ordinary
repository work, the agent reached a genuine investigate-to-implement boundary and
invoked the checkpoint from that contract. The initial routing decision was
complex, Sol/high. Checkpoints before implementation and verification both returned
`unchanged` with `same_model`, Sol/high, so this real turn did not contain a
`requested → applied` cycle. The live status retained Sol/high as configured and
accepted. Inference telemetry was disabled and recorded zero observed events, so
the accepted settings cannot be presented as evidence of a subsequent inference.
This establishes real enrollment and invocation while preserving that distinction.

### Real Desktop transition and native control boundaries (macOS, 2026-09-27)

A follow-up in the same post-restart Desktop chat began at **Terra/high**. At
the explicitly complex verification boundary the owned checkpoint completed
`requested → applied`, with transition `compatible_group`, and the live bridge
retained **Sol/high** as the accepted phase settings. A later
`response.completed` record was associated with that decision as probable
inference evidence. Native OTLP still supplies no turn or response identifier,
so this is intentionally not described as independently confirmed model identity.

`python3.11 tests/smoke_control_boundaries.py --live` then exercised the current
router source against Desktop backend **26.924.22138** in two isolated ephemeral
threads. The first received a native command-approval request under `on-request`,
accepted only the expected temporary marker command, completed it, and removed
the marker. The second sent `turn/interrupt` after a reasoning item started and
ended with native status `interrupted`. The isolated bridge exited 0; its private
OTLP collector received 12 requests with zero errors. This validates real native
approval and cancellation callbacks without mutating Desktop conversations or
configuration. It does not claim visual review of Desktop's approval surface.

A later bridge correction records the opaque `processId` published by each
`commandExecution` and, on the matching `turn/interrupt`, sends the native
`thread/backgroundTerminals/terminate` RPC for that exact thread and process.
The strengthened live probe observed both the synthetic parent and child stop,
with final state `interrupted`, bridge exit 0, 28 OTLP requests and zero receiver
errors. The direct-backend baseline remains evidence that this bridge RPC, rather
than the original `turn/interrupt` alone, provides process termination.

### Before general activation

1. Continue sampling the implemented broad-phase checkpoint across additional
   permission profiles and child agents. One real Desktop Terra→Sol transition
   and isolated native approval/cancellation callbacks are established, but they
   are not a guarantee for every profile or child agent.
2. The production bridge now records conservative phase lifecycle metadata
   (`proposed`, `accepted`, `active`, `settings_published`, `completed`,
   `blocked`/`failed`) and the monitor displays it. Its opt-in loopback OTel
   collector now records `response.completed` model/effort evidence only when
   it can associate exactly one active task. It deliberately does not label a
   selector/settings notification as an observed inference. The current visual
   pipeline uses native plan states or observed lifecycle fields; the historical
   inferred semantic pipeline is no longer shown. These names do not trigger
   automatic model/effort changes.
3. Visually review Desktop's presentation when phases use successive native
   turns. Native approval and cancellation callbacks are verified above; this
   protocol probe does not judge the UI surface.
4. Continue regression coverage for restart/resume. The post-restart Desktop
   chat retained checkpoint ownership and completed a later Terra→Sol transition;
   local ownership recovery remains unit-tested as well.

Keep these follow-up checks as regression coverage. The observation pipeline must
show review and closure as pending evidence, rather
than invented internal activity. A future pipeline should distinguish planned,
active, completed, interrupted and blocked stages, with model/effort provenance.
