# Module Name

- `jeff.cognitive.selection`

# Module Purpose

- Own the Selection-local contract and deterministic bounded-choice behavior without owning proposal generation, planning, governance, action permission, execution, or truth mutation.

# Current Role in Jeff

- Exposes the dedicated Selection package public surface.
- Defines one Selection input path centered on `ProposalResult`.
- Defines bounded Selection output with at most one selected proposal or one explicit non-selection outcome.

# Boundaries / Non-Ownership

- Does not own model/runtime behavior, validation pipelines, orchestrator sequencing, governance, approval, readiness, action formation, or execution.
- Does not imply permission, readiness, approval, workflow momentum, or execution authority.

# Owned Files / Areas

- `jeff/cognitive/selection/__init__.py`
- `jeff/cognitive/selection/contracts.py`
- `jeff/cognitive/selection/decision.py`
- `jeff/cognitive/selection/proposal_output_to_selection_bridge.py`

# Current Implementation Reality

- Selection is now a dedicated package instead of a flat module.
- The package now exposes contracts plus one deterministic Selection-local choice entry.
- `SelectionRequest` is centered on `ProposalResult`.
- `SelectionResult` still carries explicit non-selection outcomes as `reject_all`, `defer`, or `escalate`.
- `run_selection(...)` now compares current proposal options deterministically using only visible Selection-local factors.
- Selection now also owns a deterministic fail-closed bridge that turns preserved lawful proposal output into a bounded `SelectionRequest`, runs Selection, and preserves Selection output without implying action, governance, or execution.
- Orchestrator now uses that explicit Selection-local bridge after lawful post-research proposal output exists, and may then hand the preserved `SelectionResult` into the existing downstream post-selection chain.

# Important Invariants

- Selection may choose at most one proposal option.
- Honest non-selection remains explicit and limited to `reject_all`, `defer`, or `escalate`.
- Selection does not grant permission.
- Planning-needed information may influence comparison, but it does not become plan authority.
- Proposal output stays proposal output until the explicit Selection bridge runs; the bridge preserves Selection output only and does not collapse Selection into action or permission.
- Any continued downstream use of preserved Selection output remains outside Selection ownership and remains non-authorizing until later lawful downstream stages say otherwise.

# Next Continuation Steps

- Add later Selection refinement inside this package instead of recreating a flat module.
- Keep future Selection slices separate from governance, action, and execution semantics.

# Related Handoffs

- `jeff/cognitive/HANDOFF.md`
- `handoffs/system/REPO_HANDOFF.md`
