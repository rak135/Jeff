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
- the demo workspace contains one project, one work unit, one run, and one bounded flow trace
- no persistence, daemon, GUI, or background continuation is started
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
/run list
/run use run-1
/inspect
/show
/trace
/lifecycle
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

## Current Caveats

- startup currently uses explicit demo bootstrap only; there is no persisted runtime state
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
