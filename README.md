# Jeff

Jeff is a CLI-first persisted-runtime v1 backbone. It is strongest today at truthful inspection, bounded `/run`, approval-gated continuation, research support, and anti-drift coverage. It is not a GUI, a broad API surface, an autonomous continuation system, or a broad memory product.

## Start

The stable operator entrypoint is:

```text
python -m jeff
```

After `pip install -e .` the `jeff` console script is also available as a bare command; without the install, use `python -m jeff`.

Startup loads or initializes a persisted local runtime workspace under `.jeff_runtime`. On a fresh or reset runtime, Jeff initializes `project-1` / `wu-1` with no seeded run history; later startups reload the persisted canonical state and support records already present in that workspace. No daemon, GUI, or background continuation is started.

A local `jeff.runtime.toml` enables the bounded repo-local validation `/run <repo-local-validation-objective>` path and the research commands. Without it, the read-oriented CLI still works, but `/run <repo-local-validation-objective>` and `/research ...` remain unavailable.

`/run` is not a general command runner. In the current v1 slice it creates one bounded repo-local validation run, drives proposal and selection under the configured model/runtime, and only executes the fixed smoke pytest validation plan when that bounded chain reaches lawful execution.

## Quickstart

Use Python 3.11+.

Optional editable install:

```text
python -m pip install -e .
```

Core startup checks:

```text
python -m jeff --help
python -m jeff --bootstrap-check
python -m jeff --reset-runtime --bootstrap-check
```

One-shot examples:

```text
python -m jeff --command "/help"
python -m jeff --command "/project list"
python -m jeff --project project-1 --work wu-1 --command "/run list" --json
```

PowerShell quoting: inner quotes in `--command` values need backtick escaping:

```powershell
python -m jeff --command "/research docs `"`"summary`"`" README.md"
```

Interactive shell:

```text
python -m jeff
```

## Operator Contract

The primary implemented operator surface is the CLI under `jeff.interface`.

Primary flow:

```text
/project list
/project use <project_id>
/work list
/work use <work_unit_id>
/run <repo-local-validation-objective>
/inspect
/show [run_id]
/selection show [run_id]
/selection override <proposal_id> --why "<operator rationale>" [run_id]
```

History/debug:

```text
/run list
/run use <run_id>
/trace [run_id]
/lifecycle [run_id]
/scope show
/scope clear
/mode <compact|debug>
/json <on|off>
```

Conditionally available request-entry:

```text
/approve [run_id]    (only when routed_outcome=approval_required)
/reject [run_id]     (only when routed_outcome=approval_required or revalidate)
/revalidate [run_id] (only when routed_outcome=revalidate and approval is already granted)
```

Bounded receipt-only request-entry:

```text
/retry [run_id]   (only when routed_outcome=retry)
/recover [run_id] (only when routed_outcome=recover)
```

Research:

```text
/research docs "<question>" <path1> [<path2> ...] [--handoff-memory]
/research web "<question>" <query1> [<query2> ...] [--handoff-memory]
```

Current operator rules:

- `/run <repo-local-validation-objective>` is the current bounded repo-local validation entry when `jeff.runtime.toml` is loaded. It drives one fixed smoke pytest validation plan with captured command evidence; it is not a general command runner.
- `approve` records a bound approval, `revalidate` continues or fails closed, and `reject` terminally blocks that continuation for the current bounded run.
- `retry` and `recover` remain bounded receipt-only commands when surfaced.
- `/project use`, `/work use`, and `/run use` update session-local/process-local scope only. Scope does not persist across processes.
- In one-shot usage, pass `--project`, `--work`, and `--run`, or repeat `--command` flags in one process.
- `--json` affects one-shot output only; `/json on` affects the current interactive or repeated-command session only. Text-only commands like `/help` remain text even under `--json`.
- When multiple runs exist in one work unit, use `/run list` and `/run use <run_id>` or pass an explicit run id instead of relying on implicit historical binding.

### What `/run` does

`/run` runs one bounded repo-local pytest validation plan under the current model configuration. It is not a general command runner. A `/run` invocation drives proposal generation and selection under the configured model/runtime. If the bounded chain reaches lawful execution, it runs the fixed smoke pytest validation plan with captured command evidence. Runs that stop at proposal or selection (e.g. defer, reject_all) are terminal non-execution paths and are reported as such.

## Memory

Runtime config can select the research memory backend through `MemoryStoreProtocol`. The current operator-visible value is intentionally small: research handoff and live context can report whether memory was configured and what happened. Memory handoff is bounded to runs that reach terminal postures; not every run produces a memory entry. There is no broad `/memory` command family in v1.

## Tests

Run the bounded bootstrap and smoke path:

```text
python -m pytest -q tests/smoke/test_bootstrap_smoke.py tests/smoke/test_cli_entry_smoke.py tests/smoke/test_quickstart_paths.py
```

Run the full suite:

```text
python -m pytest -q
```

## Native Windows PostgreSQL Memory Tests

Memory PostgreSQL validation is Windows-native only in this repo. Do not use Docker or WSL for this path.

Preflight a real PostgreSQL-backed test database:

```text
powershell -ExecutionPolicy Bypass -File .\scripts\windows-postgres-memory-preflight.ps1 -Dsn "postgresql://user:pass@localhost:5432/jeff_test"
```

Run the real PostgreSQL integration file:

```text
$env:JEFF_TEST_POSTGRES_DSN="postgresql://user:pass@localhost:5432/jeff_test"
.\.venv\Scripts\python.exe -m pytest tests\integration\memory\test_postgres_memory.py -v
```

Run the broader memory suite against the same database:

```text
$env:JEFF_TEST_POSTGRES_DSN="postgresql://user:pass@localhost:5432/jeff_test"
.\.venv\Scripts\python.exe -m pytest tests\unit\memory tests\integration\memory -q
```

## Explicitly Deferred

- GUI
- broad API bridge
- broader `/run` action families
- broad memory CLI or UX
- autonomous continuation

## Canonical Docs

Read these first for canon:

- `v1_doc/ARCHITECTURE.md`
- `v1_doc/ROADMAP_V1.md`
- `v1_doc/TESTS_PLAN.md`
- `v1_doc/HANDOFF_STRUCTURE.md`
- `v1_doc/DOCS_GOVERNANCE.md`
