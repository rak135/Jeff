# Repo Scope / Purpose

- Jeff currently ships as a CLI-first persisted-runtime v1 backbone.
- This handoff is a continuation guide for the current repo reality. Canonical meaning still lives in `v1_doc/`.

# How to Start

- Use Python 3.11+.
- Stable entrypoint: `python -m jeff`
- Help: `python -m jeff --help`
- Bootstrap sanity check: `python -m jeff --bootstrap-check`
- One-shot operator path: `python -m jeff --command "/help"`

# Canonical Docs to Read First

- `v1_doc/ARCHITECTURE.md`
- `v1_doc/ROADMAP_V1.md`
- `v1_doc/DOCS_GOVERNANCE.md`
- `v1_doc/HANDOFF_STRUCTURE.md`
- `v1_doc/TESTS_PLAN.md`

# Module Map / Handoff Index

- Core: `jeff/core/HANDOFF.md`
- Governance: `jeff/governance/HANDOFF.md`
- Cognitive: `jeff/cognitive/HANDOFF.md`
- Action: `jeff/action/HANDOFF.md`
- Memory: `jeff/memory/HANDOFF.md`
- Orchestrator: `jeff/orchestrator/HANDOFF.md`
- Interface: `jeff/interface/HANDOFF.md`

# Current Repo-Level Reality

- Implemented now:
  - one global canonical state with nested projects
  - governance with explicit approval and readiness boundaries
  - cognitive context, research, proposal, selection, planning, and evaluation contracts
  - bounded action execution and outcome contracts
  - runtime-selected research memory handoff through `MemoryStoreProtocol`
  - deterministic orchestrator sequencing, validation, routing, lifecycle, and trace
  - CLI-first truthful operator surface
  - explicit bootstrap/start path through `python -m jeff`
- Startup loads or initializes `.jeff_runtime`, reuses persisted canonical state and support records across restarts, and exposes one explicit clean-room path through `--reset-runtime`.
- A local `jeff.runtime.toml` enables the bounded `/run <objective>` path and research commands.
- `/run <objective>` currently executes one repo-local validation slice with captured execution evidence and transition-backed run truth.
- `approve` records bound approval, `revalidate` continues or fails closed, and `reject` terminally blocks that continuation for the current bounded run.
- Session scope remains process-local; `/project use`, `/work use`, and `/run use` do not mutate canonical truth.
- The repo is intentionally not a GUI product, broad API product, advanced memory platform, autonomous continuation system, or richer workflow engine.

# Cross-Module Risks / Unresolved Issues

- Jeff still has only one bounded `/run` action family; it is not a broad command runner.
- Research memory remains intentionally narrow operator value; there is still no broad `/memory` CLI.
- Handoffs must stay subordinate to `v1_doc/`; if canon and implementation diverge, the gap needs to be named rather than smoothed over.
- Orchestrator and interface are intentionally narrow; future work must not let them absorb business logic or hidden control flow.

# Next Recommended Continuation Work

- Start with `README.md`, then this file, then the module handoff nearest the task.
- Keep follow-up work bounded to the current v1 backbone and current deferrals.
- Update the most local handoff first if module reality changes materially.

# Related Repo-Level Handoffs

- `handoffs/system/WORK_STATUS_UPDATE.md`
- `handoffs/system/STATUS_UPDATE_RULES.md`
