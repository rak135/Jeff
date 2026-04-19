# CLI Report

## Audit basis

- Canonical semantic sources used:
  - `v1_doc/CLI_V1_OPERATOR_SURFACE.md`
  - `v1_doc/INTERFACE_OPERATOR_SPEC.md`
  - `v1_doc/ARCHITECTURE.md`
  - `v1_doc/ORCHESTRATOR_SPEC.md`
- Implementation-reality sources used:
  - `pyproject.toml`, `README.md`, `jeff/main.py`, `jeff/bootstrap.py`
  - `jeff/interface/cli.py`, `jeff/interface/commands.py`, `jeff/interface/render.py`, `jeff/interface/json_views.py`, `jeff/interface/session.py`
  - `jeff/interface/HANDOFF.md`
  - `handoffs/system/WORK_STATUS_UPDATE_2026-04-19_0724.md` through `handoffs/system/WORK_STATUS_UPDATE_2026-04-19_1027.md`
- Code areas inspected:
  - CLI facade, command routing, render helpers, JSON views, startup wiring, persisted runtime integration
- Test areas inspected:
  - `tests/smoke/test_cli_entry_smoke.py`
  - `tests/unit/interface/test_cli_scope_and_modes.py`
  - `tests/unit/interface/test_cli_run_resolution.py`
  - `tests/unit/interface/test_cli_truthfulness.py`
  - `tests/unit/interface/test_cli_usability.py`
  - `tests/unit/interface/test_research_commands.py`
  - `tests/unit/interface/test_research_debug_mode.py`
  - `tests/unit/interface/test_research_source_transparency.py`
  - `tests/acceptance/test_acceptance_cli_orchestrator_alignment.py`
  - relevant research CLI integration tests
- Limitations / uncertainty notes:
  - CLI help text and tests prove wiring, not broad human-operator ergonomics under real workloads
  - some commands exist only as conditional request-entry receipts; that does not prove full backend workflows behind them
  - the CLI spec was used as expected design, not as evidence that a command family exists

## What is wired into the CLI today

### Startup / entry path

Status: fully wired for the current bounded surface.

Evidence:
- `pyproject.toml` exposes `jeff = "jeff.main:main"`.
- `jeff/main.py` implements `--help`, `--version`, `--bootstrap-check`, repeated `--command`, scope flags, and `--json`.
- `jeff/bootstrap.py` builds the startup interface context from `.jeff_runtime`, initializes demo runtime state when missing, and attaches runtime services only when `jeff.runtime.toml` exists.
- `tests/smoke/test_cli_entry_smoke.py` proves one-shot help, one-shot project list, truthful `/show` JSON, scope flags, repeated commands, and selection override entry.

### Interactive shell mode

Status: fully wired for bounded slash-command interaction.

Evidence:
- `jeff/main.py` enters `_run_interactive` when a TTY is present.
- The shell prints startup summary, research runtime availability, and slash-command guidance.
- `jeff/interface/cli.py` shares semantics between one-shot and interactive execution.
- `tests/unit/interface/test_cli_scope_and_modes.py` proves interactive and one-shot semantics stay aligned.

What it is not:
- not a free-text assistant shell
- not a full-screen dashboard

### One-shot mode

Status: fully wired.

Evidence:
- `jeff/main.py` supports repeated `--command` arguments inside one temporary CLI session.
- `tests/smoke/test_cli_entry_smoke.py` proves repeated one-shot commands preserve temporary scope across `/inspect` and `/selection show`.

### Session scope handling

Status: fully wired for local CLI scope only.

Evidence:
- `jeff/interface/session.py` defines `SessionScope` and `CliSession` with project/work/run validation.
- `jeff/interface/commands.py` wires `/project use`, `/work use`, `/run use`, `/scope show`, `/scope clear`.
- `tests/unit/interface/test_cli_scope_and_modes.py` proves session changes do not mutate canonical state.
- `tests/integration/test_runtime_workspace_persistence.py` proves CLI session scope is not persisted as canonical truth.

### Project / work / run selection

Status: fully wired for current scope navigation.

Evidence:
- `/project list`, `/project use`, `/work list`, `/work use`, `/run list`, `/run use` are all implemented in `jeff/interface/commands.py`.
- `render_help()` in `jeff/interface/render.py` exposes these commands in the actual help surface.
- `tests/unit/interface/test_cli_usability.py` and `test_cli_run_resolution.py` prove discovery guidance, unknown-ID errors, and scoped run listing.

### Inspect / show / trace / lifecycle surfaces

Status: fully wired.

Evidence:
- `/inspect`, `/show`, `/trace`, and `/lifecycle` are implemented and routed through `run_show_json`, `trace_json`, and `lifecycle_json`.
- `tests/acceptance/test_acceptance_cli_orchestrator_alignment.py` proves inspect/trace/lifecycle stay aligned on flow ID, active stage, active module, and support separation.
- `tests/smoke/test_cli_entry_smoke.py` proves truthful `/show run-1 --json` output.

### JSON views

Status: fully wired for the implemented read surfaces.

Evidence:
- `jeff/interface/json_views.py` defines projections for scope, project/work/run lists, run show, selection review, selection override receipts, lifecycle, trace, request receipts, and research results/errors.
- `jeff/interface/commands.py` applies JSON mode through `_apply_json_mode`.
- multiple tests assert support/derived/truth separation, especially `tests/unit/interface/test_cli_truthfulness.py` and `tests/unit/interface/test_research_commands.py`.

### Render layer

Status: fully wired.

Evidence:
- `jeff/interface/render.py` contains operator-facing renderers for scope, run show, selection review, request receipts, research results, debug events, and help text.
- `tests/unit/interface/test_cli_usability.py` covers help text and prompt/error formatting behavior.

### Run handling

Status: partial, and intentionally narrower than the CLI spec.

What is wired:
- `/run list` and `/run use <run_id>` are wired.
- `/show`, `/trace`, `/lifecycle`, and `/selection show` can resolve historical runs.
- `/inspect` is the primary current-run surface.

What is not wired:
- the CLI spec discusses `/run <prompt or objective>` as a launch surface; actual code does not implement that meaning.
- `tests/unit/interface/test_cli_run_resolution.py` explicitly proves `/run compare heat pump options` is rejected.

Conclusion:
- run history/debug is wired
- run launching is not

### Auto-run resolution behavior

Status: fully wired for current inspect/history semantics.

Evidence:
- `jeff/interface/commands.py` implements `_resolve_or_create_active_run`, `_resolve_historical_run`, `_select_existing_run`, and `_create_run_for_work_unit`.
- `/inspect` auto-selects the current/latest run or creates a new one through a real core transition.
- `/show`, `/trace`, and `/lifecycle` can auto-bind an existing run but do not create one.
- `tests/unit/interface/test_cli_run_resolution.py` proves both behaviors.

### Research commands

Status: fully wired for the current bounded research surface.

Evidence:
- `/research docs` and `/research web` are parsed and executed in `jeff/interface/commands.py`.
- Research commands resolve scope, auto-anchor ad-hoc research into `general_research`, call real research backend helpers, persist artifacts, optionally hand off to memory, and render debug or JSON outputs.
- `tests/unit/interface/test_research_commands.py` proves parsing, scope anchoring, memory-handoff flag behavior, JSON behavior, missing-path error surfaces, and help exposure.
- `tests/unit/interface/test_research_debug_mode.py` proves live debug streaming and structured debug JSON.
- `tests/integration/test_research_live_context_proposal_followup.py` proves research command output can include live context and real proposal follow-up support projections.

### Help / prompt / usability behavior

Status: fully wired for current command surface.

Evidence:
- `render_help()` in `jeff/interface/render.py` is the actual operator command inventory.
- `tests/unit/interface/test_cli_usability.py` proves unsupported-command guidance, scope-step hints, help text wording, and readability helpers.
- `jeff/main.py` startup messaging clearly tells the operator this is a slash-command shell, not plain text.

### Operator-facing truthfulness protections

Status: strong and explicitly wired.

Evidence:
- `json_views.py` keeps `truth`, `derived`, `support`, and `telemetry` distinct.
- `tests/unit/interface/test_cli_truthfulness.py` proves selected is not rendered as permitted, execution completion is not rendered as objective completion, blocked/inconclusive states remain visible, and request commands distinguish acceptance from effect.
- `tests/unit/interface/test_research_source_transparency.py` proves research render/projection does not fabricate provenance and keeps support separate from truth.

### Debug / telemetry / rationale / health surfaces if present

Status: partial.

What is present:
- `/mode debug` exists and emits research debug checkpoints.
- `/show`, `/trace`, and `/lifecycle` include telemetry blocks such as elapsed seconds, event count, and derived health posture in projections.
- selection rationale and evaluation rationale summaries are surfaced inside existing views.

What is not present as standalone surfaces:
- no `/telemetry` command
- no `/health` command
- no `/rationale` command family

Conclusion:
- debug and telemetry information exist inside current views
- debug/telemetry/rationale/health are not first-class command families

### Review / approval / retry / revalidate / recover / change surfaces only if truly wired

Status: partially wired and thin.

What is truly wired:
- `/selection show` is a real deep review surface.
- `/selection override <proposal_id> --why ...` is a real operator action that recomputes downstream resolved basis, materialized proposal, action formation, and governance handoff in-memory/current context.
- `/approve`, `/reject`, `/retry`, `/revalidate`, and `/recover` are implemented in `jeff/interface/commands.py`.

What those request commands actually do:
- they only validate that the current routed outcome makes the request lawful
- they return a request receipt saying the request was accepted
- they explicitly do not imply apply, completion, or truth mutation

Evidence:
- `_request_command()` in `jeff/interface/commands.py`
- `tests/unit/interface/test_cli_truthfulness.py`

What is not wired:
- no `/change <change_id>` surface
- no real approval workflow state machine behind `/approve` and `/reject`
- no recovery executor behind `/recover`

## What still remains to be wired into the CLI

### Command families present in spec but not in code

- `/run <prompt or objective>` is spec-level, not implemented.
- `/abort` is not present.
- `/resume` is not present.
- `/rationale [stage]` is not present.
- `/telemetry [run_id]` is not present.
- `/health` is not present.
- `/change <change_id>` is not present.

### Thin placeholders

- `/approve`, `/reject`, `/retry`, `/revalidate`, and `/recover` are thin request-entry surfaces, not strong operator workflows.
- They are truthful about this thinness, but they are still thin.

### Missing action-request surfaces

- There is no true CLI surface for launching a fresh bounded work objective through the orchestrator.
- There is no CLI-managed approval lifecycle with persisted operator decision state beyond request receipts.

### Missing runtime visibility

- Telemetry and health are embedded in existing projections, but there is no dedicated operator command family for them.
- There is no broader live progress dashboard beyond trace/lifecycle/show and research debug checkpoints.

### Missing rationale / telemetry / health surfaces

- Rationale is only available indirectly inside selection/evaluation summaries.
- No first-class rationale or health inspection command is wired.

### Missing review / change / recovery surfaces

- Review is strongest around selection review, not around execution/change control.
- Change surfaces from the CLI spec do not exist.
- Recovery surfaces do not go beyond request-entry receipts.

### Partial operator ergonomics

- The command shell is truthful and reasonably usable, but still narrow.
- The help surface is disciplined, yet it exposes conditional request commands that sound larger than their backend effect unless the user reads the receipt carefully.
- Research usability is stronger than action/governance usability.

### Anything deferred to future GUI/API work

- GUI is absent.
- Broad API bridge is absent.
- The current CLI remains the sole operator surface.

### Important distinction: absent vs not yet honest to expose

- Some spec-level command families are absent because the backend is not ready enough to support them honestly. `/telemetry`, `/health`, `/change`, and richer recovery/approval flows would currently risk overstating backend maturity.
- By contrast, `/run <objective>` is a more meaningful missing CLI gap because the backend backbone exists but is not exposed as a primary operator action.

## CLI design vs implementation reality

### What the CLI docs/specs expect

- a project-shell style operator surface
- explicit scope handling
- run launch and inspection
- trace, lifecycle, rationale, telemetry, and health visibility
- truthful review and action-request commands
- JSON-friendly automation support

### What the repo actually delivers

- a real slash-command shell with explicit scope, project/work/run navigation, inspect/show/trace/lifecycle views, JSON output, research commands, selection review, and truthful request-entry commands
- research is the most developed live CLI capability
- selection review/override is the deepest non-research operator review surface
- run launch, health, telemetry, rationale, change review, and broad recovery remain materially behind the spec

### Which gaps are acceptable for now

- not having GUI/API surfaces is acceptable because they are explicitly deferred
- not having standalone telemetry/health commands is acceptable for now because basic visibility is already embedded in current views
- keeping request commands thin is acceptable if they remain explicit about their thinness

### Which gaps are real problems

- the lack of a primary operator launch path for new bounded work is a real CLI gap
- approval/recovery commands being only receipts means the CLI is still weaker than it may first appear from help text
- the CLI spec is materially ahead of current implementation on runtime control and observability command families

## CLI bottom line

- Is the CLI already a real operator surface?
  - Yes, in bounded form. It is a real operator surface for startup, scope control, inspection, trace/lifecycle review, selection review/override, research commands, and truthful JSON automation. It is not yet a complete control surface for the whole v1 backbone.

- Which CLI pieces are strongest today?
  - Startup and one-shot entry, inspect/show/trace/lifecycle, research commands, selection review/override, and truthfulness-preserving JSON projections.

- Which missing CLI piece matters most?
  - A truthful primary run-launch surface for new bounded work. Without that, the CLI remains stronger at inspection and research than at actually driving the backbone.

- What should not be built yet because backend semantics are still too thin?
  - Do not build polished health/change/recovery/approval control panels that imply a richer backend workflow than exists. Those surfaces should stay narrow until the underlying execution and governance lifecycle are stronger than request receipts.