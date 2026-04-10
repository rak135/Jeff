# CLI_V1_OPERATOR_SURFACE.md

Status: v1 implementation proposal for Jeff CLI operator surface  
Authority: subordinate to `INTERFACE_OPERATOR_SPEC.md`, `ARCHITECTURE.md`, `ORCHESTRATOR_SPEC.md`, `STATE_MODEL_SPEC.md`, `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md`, `CORE_SCHEMAS_SPEC.md`, and `ROADMAP_V1.md`  
Purpose: define a concrete, buildable v1 CLI operator surface for Jeff without changing canonical interface, truth, scope, or orchestration law

---

## 1. Why this document exists

Jeff already has canonical operator-surface law:
- the CLI is the v1 primary operator surface
- interfaces render and invoke; they do not redefine backend meaning
- operator surfaces must remain truthful about authority, uncertainty, and state class
- `project + work_unit + run` remain foundational scope containers
- project is a hard isolation boundary
- interface or session state must not become rival canonical truth
- lifecycle and trace surfaces must remain inspectable

This document does not change those rules.
It turns them into a concrete v1 CLI design:
- shell model
- prompt model
- operator scope model
- slash command family
- live output model
- rationale, trace, and telemetry views
- stall and loop visibility
- JSON and automation boundaries
- acceptance slice for v1

---

## 2. Design goals

### 2.1 Hard goals
1. Make Jeff usable as a real interactive operator shell in v1.
2. Keep scope explicit without forcing `project_id` and `work_unit_id` on every command.
3. Let the operator see which Jeff stage and module is running right now.
4. Provide enough runtime visibility to detect stalls, loops, degraded progress, and boundary failures.
5. Preserve truthful distinctions between truth, support artifacts, derived views, and telemetry.
6. Keep the CLI inspectable and automation-friendly.
7. Avoid turning the CLI into a second control plane or a shadow truth layer.

### 2.2 Non-goals
1. Showing raw chain-of-thought or full hidden model reasoning.
2. Building a giant terminal dashboard for v1.
3. Replacing lifecycle, trace, or backend truth with clever shell-only state.
4. Hiding approval, readiness, blocked, degraded, or inconclusive states behind polished UX.
5. Building the full future GUI inside the terminal.
6. Making the CLI own orchestration, governance, or transition semantics.

---

## 3. Core v1 principles

### 3.1 CLI-first, not CLI-owned semantics
The CLI is the primary v1 operator surface, but it remains downstream of backend truth.
It may:
- render backend truth and support objects
- issue lawful operator requests
- maintain local session convenience state
- expose lifecycle, trace, rationale, and telemetry surfaces

It must not:
- redefine status meaning
- infer permission from selection or review convenience
- imply apply from approval
- imply completion from execution alone
- create hidden truth through session state

### 3.2 Session scope is convenience, not truth by default
The shell may maintain current working scope for operator convenience.
That session scope is not canonical truth by default.
It is:
- local shell navigation state
- a convenience binding for default command targeting
- replaceable without mutating canonical state

If Jeff later uses committed `active_context` in canonical state, that must be explicit and separate from shell-local focus.

### 3.3 Visibility over raw reasoning
The CLI should expose:
- active stage
- active module
- stage/substep progress
- structured rationale
- stage trace
- observability hooks
- telemetry
- stall/loop suspicion

The CLI should not expose raw hidden chain-of-thought.
The operator needs inspectability and operational awareness, not a dump of internal scratchpad text.

### 3.4 Truth labels matter
When relevant, the CLI must distinguish:
- canonical truth
- support artifact
- derived view
- telemetry
- session-local state

The operator should not have to guess which class of object is being shown.

---

## 4. v1 shell model

### 4.1 Interactive shell
Jeff v1 should support an interactive shell mode:

```text
jeff:/<project_slug>/<work_unit_slug>>
```

This is the default human operator surface for day-to-day use.
It should feel closer to a bounded project shell than a one-shot command runner.

### 4.2 Prompt contents
The prompt should show human-meaningful scope aliases, not raw opaque IDs.
Recommended prompt shape:

```text
jeff:/project_slug/work_unit_slug>
```

Optional extended prompt in debug mode:

```text
jeff:/project_slug/work_unit_slug [run=run_1842 flow=proposal_selection_action stage=memory/retrieval]>
```

Rules:
- prompt aliases may be human-readable
- canonical backend IDs remain opaque typed IDs internally
- prompt display must not become the authoritative identity representation

### 4.3 Modes of use
Jeff CLI v1 should support two operator modes:

1. **interactive shell mode**
   The operator enters Jeff and works inside a sticky session scope.

2. **one-shot command mode**
   For scripts, automation, or quick inspection.

These modes should share the same command semantics where possible.

---

## 5. Scope model

### 5.1 Foundational scope containers
Jeff CLI v1 is built around:
- `project`
- `work_unit`
- `run`

These remain the foundational containers.
The shell does not replace them.

### 5.2 Session scope
The shell maintains a local current scope:
- current project
- current work unit
- optionally current run when a run is active or explicitly selected

This scope is used as the default target for commands.

Example:
- operator enters project `energy-upgrade`
- operator enters work unit `heat-pump-research`
- subsequent `/run`, `/inspect`, `/trace`, `/review` use that scope by default

### 5.3 Changing scope
Scope changes must be explicit commands.
No hidden scope switching based on last viewed item, trace item, or output click.

Recommended commands:
- `/project use <project_slug>`
- `/work use <work_unit_slug>`
- `/run use <run_id>`
- `/scope show`
- `/scope clear`

### 5.4 Session scope vs committed focus
Jeff v1 CLI must distinguish:

**Session scope**
- local shell convenience state
- not canonical truth by default

**Committed focus**
- future or optional explicit canonical `active_context`
- only when backend law treats current operating focus as authoritative
- not automatically updated by shell navigation

V1 does not require committed focus support in the CLI.
If added, it must be explicit, not silent.

---

## 6. Slash command model

### 6.1 Why slash commands
Jeff v1 should use slash commands for discoverable operator actions.
This matches operator expectations from modern coding/research CLIs and keeps command families easy to scan.

### 6.2 v1 command families
The v1 command set should stay small and disciplined.

#### Scope commands
- `/project list`
- `/project use <project_slug>`
- `/work list`
- `/work use <work_unit_slug>`
- `/run use <run_id>`
- `/scope show`
- `/scope clear`

#### Flow and execution commands
- `/run <prompt or objective>`
- `/abort`
- `/resume` if lawful and implemented

#### Inspect/read commands
- `/inspect`
- `/show <run_id>`
- `/trace [run_id]`
- `/lifecycle [run_id]`
- `/change <change_id>` when relevant

#### Reasoning-support visibility commands
- `/rationale [stage]`
- `/telemetry [run_id]`
- `/health`

#### Output/view control commands
- `/mode compact`
- `/mode debug`
- `/json on`
- `/json off`
- `/help`

#### Review/action-request commands
Only when backend support exists and conditions are lawful:
- `/approve <change_id>`
- `/reject <change_id>`
- `/retry <run_id>`
- `/revalidate <target>`
- `/recover <target>`

### 6.3 Command rules
Slash commands must:
- preserve authoritative backend distinctions
- fail clearly on missing or ambiguous scope
- report request acceptance vs downstream completion honestly
- remain scriptable where JSON surfaces are claimed

Slash commands must not:
- imply that a command request means the underlying effect already happened
- infer approval or readiness from review visibility
- flatten multiple backend states into a single friendly `done`

---

## 7. Live output model

### 7.1 Goal
The operator needs to know:
- what Jeff is doing now
- which module and stage is active
- whether progress is happening
- whether the system is blocked, slow, degraded, or stalled

The operator does not need raw hidden model thoughts.

### 7.2 Default live display
During an active run, the CLI should show a compact live status block.

Recommended header:

```text
RUN run_1842  flow=proposal_selection_action
SCOPE project=energy-upgrade work_unit=heat-pump-research
ACTIVE stage=memory/retrieval module=memory elapsed=13s health=ok
```

Recommended live panel fields:
- `flow`
- `project`
- `work_unit`
- `run`
- `stage`
- `substep`
- `module`
- `elapsed`
- `last_progress`
- `health`
- `tokens in/out` when available
- `t/s` when available

### 7.3 Event stream under the live panel
Below the live status block, Jeff should print compact event lines.

Example:

```text
[12:41:03] stage_entry(context)
[12:41:04] truth_read(ok)
[12:41:04] stage_exit(context)
[12:41:04] stage_entry(memory)
[12:41:05] retrieval_started
[12:41:06] rerank_started
[12:41:06] budget_trim_applied
[12:41:06] stage_exit(memory)
```

This gives the operator a heartbeat without noisy raw internals.

---

## 8. Stage model shown in CLI

### 8.1 Canonical stage families to surface
The CLI should surface whichever of these stages are actually present in the current flow:
- `context`
- `research`
- `proposal`
- `selection`
- `planning`
- `governance`
- `execution`
- `outcome`
- `evaluation`
- `memory`
- `transition`

### 8.2 Stage and substep display
Each visible stage may also expose a lighter-weight substep for operator understanding.

Examples:
- `memory/retrieval`
- `memory/reranking`
- `proposal/generate_options`
- `selection/compare_options`
- `governance/readiness_check`
- `execution/tool_run`
- `evaluation/deterministic_checks`

Substeps are observability aids.
They are not new canonical workflow truth.

---

## 9. Structured rationale

### 9.1 Purpose
Structured rationale is the operator-facing summary of why a stage produced its result.
It is bounded, inspectable, and intentionally smaller than raw model thought.

### 9.2 Where rationale is most useful
Highest value stages for rationale in v1:
- `proposal`
- `selection`
- `planning` when used
- `governance`
- `evaluation`
- `memory` for retrieval or write-decision summary

### 9.3 Rationale content rules
A stage rationale should answer only the useful operator questions:
- what the stage was trying to do
- what inputs mattered most
- what decisive factors shaped the result
- what output or disposition the stage produced
- what caution or uncertainty still matters

It must not:
- dump long chain-of-thought text
- impersonate permission or truth mutation
- become essay spam

### 9.4 Example rationale shapes

#### Proposal rationale example
```json
{
  "stage": "proposal",
  "serious_option_count": 2,
  "scarcity_reason": "no third serious option survived support and scope filtering",
  "options": [
    "direct comparison brief",
    "narrow incentive-focused follow-up"
  ]
}
```

#### Selection rationale example
```json
{
  "stage": "selection",
  "selected_option_id": "option_1",
  "decision": "selected",
  "strongest_reasons": [
    "better scope fit",
    "lower assumption burden",
    "stronger evidence support"
  ],
  "important_alternatives": [
    {
      "option_id": "option_2",
      "why_not_selected": "narrower immediate value"
    }
  ],
  "cautions": [
    "fresh incentive verification still needed later"
  ]
}
```

#### Memory retrieval rationale example
```json
{
  "stage": "memory",
  "operation": "retrieval",
  "purpose": "context_for_proposal",
  "retrieved_count": 6,
  "excluded_due_to_budget": 11,
  "top_memory_types": ["semantic", "operational"],
  "conflict_labeled": 1
}
```

---

## 10. Stage trace and observability hooks

### 10.1 Purpose
Stage trace gives the operator an audit-friendly timeline of what happened during a run.
This is not raw reasoning.
It is orchestration and module progress visibility.

### 10.2 Minimum v1 observability hooks
Jeff v1 CLI should surface the following hook families when available:
- `flow_start`
- `scope_binding`
- `stage_entry`
- `stage_exit`
- `handoff_validation_pass`
- `handoff_validation_fail`
- `routing_decision`
- `hold_reason`
- `stop_reason`
- `escalation_point`
- `flow_completion`

Additional module-local hooks are allowed when useful and truthful.

### 10.3 Example trace output
```text
TRACE run_1842
1. flow_start
2. scope_binding
3. stage_entry(context)
4. stage_exit(context)
5. stage_entry(memory)
6. handoff_validation_pass(memory->proposal)
7. stage_exit(memory)
8. stage_entry(proposal)
9. stage_exit(proposal)
10. stage_entry(selection)
11. routing_decision(direct_output_research)
12. stage_exit(selection)
13. flow_completion
```

### 10.4 Hook display rules
Hooks should be compact by default.
Detailed payloads belong behind `/trace` or `/inspect` in debug mode.

---

## 11. Telemetry model

### 11.1 Goal
Telemetry should help the operator answer:
- how long is this taking
- is it making progress
- how many tokens is it using
- how fast is it moving
- how full is context if that data exists

### 11.2 Required honesty rule
Telemetry certainty must be labeled.
Values may be:
- `measured`
- `estimated`
- `partial`
- `unavailable`

The CLI must not pretend exactness where the backend does not have it.

### 11.3 Recommended v1 telemetry fields
At minimum, when available:
- `tokens_in`
- `tokens_out`
- `context_usage`
- `latency_ms`
- `elapsed_ms`
- `tokens_per_second`
- `last_progress_at`
- `events_seen`

### 11.4 Example telemetry panel
```text
TELEMETRY
- tokens_in: 1820        [measured]
- tokens_out: 96         [measured]
- context_usage: 41%     [estimated]
- t/s: 14.2              [estimated]
- elapsed: 13.1s         [measured]
- last_progress: 4.0s ago
```

---

## 12. Stall and loop visibility

### 12.1 Why this matters
The operator must be able to detect when:
- a small model is stuck
- a retrieval pass is spinning without improvement
- a stage is repeating the same substep
- apparent activity is happening without actual progress

This is especially important for:
- memory retrieval
- memory write candidate handling
- proposal generation with weaker models
- review or comparison loops

### 12.2 v1 stage health model
Each active stage should expose a coarse health state:
- `ok`
- `slow`
- `stalled`
- `loop_risk`
- `blocked`
- `degraded`

These are operator-facing visibility values.
They do not replace backend domain meaning.

### 12.3 Minimum signals for stall detection
The live runner should track at least:
- `started_at`
- `last_progress_at`
- `current_substep`
- `substep_repeat_count`
- `same_result_count`
- `tokens_in`
- `tokens_out`
- `event_count`
- `health`

### 12.4 Example live status when healthy
```text
ACTIVE STAGE: memory
SUBSTEP: reranking
ELAPSED: 00:00:13
LAST PROGRESS: 00:00:04 ago
TOKENS: in=1820 out=96
RATE: 14.2 tok/s
PROGRESS: 21 candidates -> 8
HEALTH: ok
```

### 12.5 Example live status when stalled
```text
ACTIVE STAGE: memory
SUBSTEP: reranking
ELAPSED: 00:00:31
LAST PROGRESS: 00:00:17 ago
TOKENS: in=4410 out=117
RATE: 2.1 tok/s
PROGRESS: no change
HEALTH: stalled
```

### 12.6 Loop suspicion example
```text
WARNING loop_risk=true
reason: repeated substep without cardinality or decision change
stage: proposal/generate_options
repeat_count: 4
```

### 12.7 Operator actions
When health is not `ok`, the operator should be able to:
- inspect `/trace`
- inspect `/telemetry`
- inspect `/rationale`
- `/abort` the current run

Future richer recovery commands are allowed later.

---

## 13. Output modes

### 13.1 Purpose
Operators do not always want the same level of detail.
Jeff v1 should provide output modes rather than one permanently noisy surface.

### 13.2 Recommended v1 modes
#### `compact`
Default mode.
Shows:
- prompt scope
- current run header
- active stage/module/substep
- compact event lines
- warnings and terminal result

#### `debug`
Shows everything from compact mode plus:
- expanded trace hooks
- structured rationale blocks
- telemetry panels
- handoff validation visibility
- more explicit truth/support/telemetry labels where relevant

### 13.3 Mode rules
Changing mode changes presentation density.
It does not change backend meaning.

---

## 14. JSON and automation boundary

### 14.1 Why this matters
Jeff CLI must remain machine-readable where JSON is claimed.
The interactive shell serves humans.
One-shot commands must remain safe for automation.

### 14.2 JSON rule
Commands that claim JSON output must produce stable machine-readable output and avoid mixing human chatter into the same response surface.

### 14.3 Recommended approach
- interactive shell: human-oriented output by default
- one-shot mode or explicit `/json on`: machine-readable output for supported commands

### 14.4 Suggested JSON-support commands
At minimum for v1, keep JSON support aligned with stable inspect surfaces:
- `show`
- `trace`
- `lifecycle`
- `change`
- approval/reject results where implemented
- telemetry snapshot if exposed in a stable way

---

## 15. Truth labeling in the CLI

### 15.1 Why labels are needed
The CLI must avoid letting support objects masquerade as canonical truth.

### 15.2 Minimum truth classes to expose where relevant
- `[truth]`
- `[support]`
- `[derived]`
- `[telemetry]`
- `[session]`

### 15.3 Example
```text
[truth] run_status = active
[support] review_artifact = patch_preview_12
[derived] stage_health = slow
[telemetry] tokens_in = 1820 [measured]
[session] current_scope = energy-upgrade / heat-pump-research
```

These labels should appear where the distinction matters.
They do not need to clutter every line.

---

## 16. Review and action semantics in CLI

### 16.1 Requests vs effect
When the operator issues a command like `/approve` or `/reject`, the CLI must present that as a request/result boundary honestly.

Correct pattern:
- command accepted
- backend processed the request
- request result returned
- downstream effects remain distinct if not yet complete

Incorrect pattern:
- operator typed `/approve`
- CLI prints `done` as if apply or transition already happened

### 16.2 Visible distinctions that must remain visible
Where relevant, the CLI must not flatten:
- selected vs permitted
- approved vs applied
- execution complete vs objective complete
- outcome state vs evaluation verdict
- canonical truth vs support artifact
- degraded vs failed vs inconclusive

---

## 17. Recommended v1 command behavior examples

### 17.1 Scope selection
```text
jeff:/> /project use energy-upgrade
session scope updated: project=energy-upgrade

jeff:/energy-upgrade> /work use heat-pump-research
session scope updated: project=energy-upgrade work_unit=heat-pump-research
```

### 17.2 Running work
```text
jeff:/energy-upgrade/heat-pump-research> /run compare heat pump options and incentives
RUN run_1842 created
flow=research_to_decision_support
```

### 17.3 Inspecting trace
```text
jeff:/energy-upgrade/heat-pump-research> /trace run_1842
TRACE run_1842
...
```

### 17.4 Showing rationale
```text
jeff:/energy-upgrade/heat-pump-research> /rationale selection
stage=selection
selected_option=option_1
strongest_reasons:
- better evidence coverage
- lower assumption burden
```

### 17.5 Telemetry snapshot
```text
jeff:/energy-upgrade/heat-pump-research> /telemetry
TELEMETRY
...
```

---

## 18. Minimal implementation shape for v1

Recommended interface package layout:

```text
src/jeff/interface/cli/
  __init__.py
  shell.py
  prompt.py
  commands.py
  session_scope.py
  renderer.py
  event_stream.py
  rationale_view.py
  trace_view.py
  telemetry_view.py
  health_monitor.py
  json_mode.py
```

Module roles:
- `shell.py`: interactive loop and command dispatch
- `prompt.py`: prompt rendering from session scope and optional live status
- `commands.py`: slash command registry and handlers
- `session_scope.py`: local scope state and validation
- `renderer.py`: human-oriented rendering of live and inspect views
- `event_stream.py`: compact hook/event display
- `rationale_view.py`: bounded stage rationale rendering
- `trace_view.py`: stage trace and hook timeline rendering
- `telemetry_view.py`: telemetry labels and display
- `health_monitor.py`: stage health, stall, and loop suspicion visibility
- `json_mode.py`: stable machine-readable output path for supported commands

---

## 19. Acceptance criteria for v1

Jeff CLI v1 is ready when all of the following are true:

1. The operator can enter an interactive Jeff shell.
2. The operator can set project and work unit once and then issue commands inside sticky session scope.
3. The shell clearly shows active flow, stage, and module during a run.
4. The shell prints compact lifecycle/event progress during execution.
5. The operator can inspect trace, rationale, and telemetry on demand.
6. The shell can expose slow, stalled, blocked, degraded, or loop-risk conditions visibly.
7. JSON-capable commands remain machine-readable where claimed.
8. Session scope remains convenience state and does not silently mutate canonical truth.
9. The CLI preserves critical backend distinctions instead of flattening them.
10. The CLI does not expose raw chain-of-thought.

---

## 20. Explicit out-of-scope items for v1

The following are deliberately deferred:
- full GUI-like terminal dashboards
- raw hidden model reasoning display
- rich inline graphs and heavy TUI widgets
- automatic canonical active-context mutation from shell navigation
- complex continuation/session restoration logic across many terminals
- advanced multi-pane trace browsers
- complete future API bridge semantics in this document

These may be added later if they remain subordinate to canonical interface and truth law.

---

## 21. Final recommendation

Jeff v1 should ship a CLI that feels like a focused operator shell, not a bag of one-shot scripts and not a fake agent theater surface.

The right v1 slice is:
- sticky shell scope
- slash commands
- active stage/module visibility
- compact event stream
- bounded rationale
- stage trace
- telemetry with honesty labels
- stall and loop detection

That gives the operator real oversight without polluting the system with shell-owned semantics or raw reasoning sludge.
