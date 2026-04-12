# Module Name

- `jeff.interface`

# Module Purpose

- Provide the current truthful operator surface for Jeff through the CLI and bounded read/command projections.

# Current Role in Jeff

- Exposes the CLI facade, command execution layer, JSON/readable renderers, and local session scope used by `python -m jeff`.
- Presents startup/bootstrap reality, inspect surfaces, trace surfaces, lifecycle surfaces, and a thin research command family without mutating canonical truth from reads.

# Boundaries / Non-Ownership

- Does not own canonical truth, governance shortcuts, hidden write paths, private lifecycle semantics, research semantics, or backend meaning.
- Does not flatten selected vs permitted, approved vs applied, or outcome vs evaluation.

# Owned Files / Areas

- `jeff/interface/cli.py`
- `jeff/interface/commands.py`
- `jeff/interface/render.py`
- `jeff/interface/json_views.py`
- `jeff/interface/session.py`

# Dependencies In / Out

- In: consumes bootstrapped interface context, orchestrator outputs, and approved read-only backend projections.
- Out: provides the current operator-facing entry surface only; there is no GUI or broad API bridge yet.

# Canonical Docs to Read First

- `v1_doc/ARCHITECTURE.md`
- `v1_doc/INTERFACE_OPERATOR_SPEC.md`
- `v1_doc/CLI_V1_OPERATOR_SURFACE.md`

# Current Implementation Reality

- The stable operator start path is `python -m jeff`.
- Startup bootstraps an explicit in-memory demo workspace and supports help, bootstrap checks, one-shot commands, and an interactive shell in a real terminal.
- Startup can now also load an explicit local `jeff.runtime.toml` file and attach research runtime dependencies when present.
- Session scope is local CLI state, not canonical truth mutation.
- The CLI now includes `/research docs` and `/research web` as a thin operator surface over the existing research backend.
- `/mode debug` now emits bounded live research-debug checkpoints during research runs so operators can see synthesis, repair, remap, and provenance stages without changing backend semantics.
- Ad-hoc research is not projectless: when no project scope is selected, the interface anchors the request into the built-in `general_research` project plus a bounded derived work unit and lawful run.
- When runtime config is absent, non-research CLI surfaces still work and research remains explicitly unavailable rather than silently fabricated.

# Important Invariants

- Interface surfaces remain downstream of backend semantics.
- Read and inspect surfaces do not mutate truth.
- Support artifacts are not rendered as canonical truth.
- CLI projections keep evaluation under Cognitive, execution/outcome under Action, and governance meanings distinct.
- Research persistence and optional research-to-memory handoff remain owned by backend helpers; the CLI only resolves scope, calls them, and renders results.
- Runtime config parsing, provider construction, purpose-based adapter selection, and provider options remain owned by Infrastructure; the interface only receives assembled dependencies.

# Active Risks / Unresolved Issues

- GUI is deferred.
- Broad API bridge is deferred.
- Startup still uses explicit demo bootstrap only; there is no persisted operator runtime.
- There is still no scheduling, orchestrator-integrated research workflow, autonomous continuation, or cross-project retrieval exception in the interface layer.

# Next Continuation Steps

- Keep future interface work truthful and bounded: startup, docs, and CLI refinements are acceptable; semantic flattening or hidden control paths are not.

# Submodule Map

- `cli.py`: CLI facade for one-shot and interactive command execution; no separate handoff.
- `commands.py`: command parsing and operator actions over backend contracts; no separate handoff.
- `render.py`: human-readable output surfaces; no separate handoff.
- `json_views.py`: machine-readable truthful projections; no separate handoff.
- `session.py`: local session scope only; no separate handoff.

# Related Handoffs

- `handoffs/system/REPO_HANDOFF.md`
- `jeff/orchestrator/HANDOFF.md`
- `jeff/core/HANDOFF.md`
- `jeff/governance/HANDOFF.md`
- `README.md`
