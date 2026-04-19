# Jeff

Jeff currently ships as a CLI-first, in-memory v1 backbone. It is useful for operator inspection, contract validation, orchestration tracing, and truthful surface testing. It is not yet a GUI product, a broad API product, an autonomous continuation system, or an advanced memory platform.

## What It Is Now

- One global canonical state with nested projects
- Governance with explicit approval and readiness boundaries
- Cognitive context, proposal, selection, conditional planning, and evaluation contracts
- Governed execution, outcome normalization, and bounded memory discipline
- Deterministic orchestrator sequencing over public contracts
- Truthful CLI-first operator surfaces with anti-drift and acceptance coverage

## Current Startup Path

The stable operator entrypoint is:

```text
python -m jeff
```

Important current behavior:

- startup bootstraps an explicit in-memory demo workspace
- startup can also load explicit local runtime config from `jeff.runtime.toml` when present
- the demo workspace contains one project, one work unit, one run, and one bounded flow trace
- no daemon, GUI, or background continuation is started
- one-shot mode is available for deterministic smoke and automation-safe checks

## Quickstart

Use Python 3.11+.

Optional editable install:

```text
python -m pip install -e .
```

Show startup help:

```text
python -m jeff --help
```

Run deterministic bootstrap checks:

```text
python -m jeff --bootstrap-check
```

Run one command against the bootstrapped demo context:

```text
python -m jeff --command "/help"
python -m jeff --command "/project list"
python -m jeff --command "/show run-1" --json
```

Start the interactive shell in a real terminal:

```text
python -m jeff
```

## Primary Operator Surface

The primary implemented operator surface is the CLI under `jeff.interface`.

Useful demo commands after startup:

```text
/help
/project list
/project use project-1
/work use wu-1
/inspect
/trace
/lifecycle

# Manual history/debug when needed:
/run list
/run use run-1
/show
```

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

Memory v1 PostgreSQL validation is Windows-native only in this repo. Do not use Docker or WSL for this path.

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

Notes:

- `.venv` is only for Python packages such as `pytest` and `psycopg2-binary`
- PostgreSQL server and `pgvector` are native Windows installs outside `.venv`
- the target database must already accept the DSN and have `CREATE EXTENSION vector` available to the PostgreSQL integration path
- on PostgreSQL 18+, if `pgvector` is staged outside the default PostgreSQL tree, `extension_control_path` must point at the custom prefix and `dynamic_library_path` must include both the custom `lib` directory and PostgreSQL's own `$libdir`

## Current Caveats

- startup always uses explicit demo truth state; research runtime becomes available only when local `jeff.runtime.toml` is present
- the canonical semantics still live in `v1_doc/`, not in this README

## Explicitly Deferred

- GUI
- broad API bridge
- advanced memory backend
- autonomous continuation
- richer workflow engines

## Canonical Docs

Read these first for canon:

- `v1_doc/ARCHITECTURE.md`
- `v1_doc/ROADMAP_V1.md`
- `v1_doc/TESTS_PLAN.md`
- `v1_doc/HANDOFF_STRUCTURE.md`
- `v1_doc/DOCS_GOVERNANCE.md`
