# Module Name

- `jeff.cognitive`

# Module Purpose

- Own bounded reasoning-layer contracts for context, research, proposal, selection, conditional planning, and evaluation without taking over truth, governance, execution, or memory ownership.

# Current Role in Jeff

- Assembles truth-first context from current canonical state and bounded support inputs.
- Owns the active research package for prepared-evidence synthesis, document and web source acquisition, research artifact persistence, and selective research-to-memory handoff.
- Produces bounded proposal, selection, planning, and evaluation outputs for downstream layers without implying permission or mutating truth.

# Boundaries / Non-Ownership

- Does not own canonical truth, transition commit, governance policy/approval/readiness, execution, outcome normalization, memory retrieval rules, memory commit decisions, or interface semantics.
- Does not let research artifacts become truth.
- Does not let proposal, selection, planning, or evaluation imply permission.
- Does not own provider implementations; cognitive research uses only provider-neutral infrastructure surfaces.

# Owned Files / Areas

- `jeff/cognitive/context.py`
- `jeff/cognitive/research/`
- `jeff/cognitive/proposal/`
- `jeff/cognitive/selection/`
- `jeff/cognitive/planning.py`
- `jeff/cognitive/evaluation.py`
- `jeff/cognitive/types.py`
- `jeff/cognitive/__init__.py`

# Dependencies In / Out

- In: reads canonical truth from Core first, consumes bounded support inputs, uses provider-neutral infrastructure model-adapter/runtime surfaces through the research package, and uses the current Memory pipeline only for selective downstream handoff.
- Out: provides bounded research, proposal, selection, planning, and evaluation outputs to downstream orchestration or operator-facing layers; may hand off selected research artifacts into the current Memory write pipeline without owning the final write decision.

# Canonical Docs to Read First

- `v1_doc/ARCHITECTURE.md`
- `v1_doc/CONTEXT_SPEC.md`
- `v1_doc/PLANNING_AND_RESEARCH_SPEC.md`
- `v1_doc/PROPOSAL_AND_SELECTION_SPEC.md`
- `v1_doc/EXECUTION_OUTCOME_EVALUATION_SPEC.md`
- `v1_doc/additional/RESEARCH_ARCHITECTURE.md`

# Current Implementation Reality

- Context remains truth-first and bounded.
- Research is now a real submodule package rather than a flat file.
- Proposal is now a real submodule package rather than a flat file.
- Research currently supports prepared-evidence synthesis, bounded local-document acquisition, bounded web acquisition, durable research-artifact persistence, and selective research-to-memory handoff.
- Research still carries a bounded legacy surface because current callers/tests still use `ResearchResult` and compatibility request behavior.
- Proposal now has a file-backed Step 1 prompt contract and a Proposal-local prompt loader/renderer, but still no model/runtime caller.
- Proposal, selection, planning, and evaluation remain separate bounded contracts with unchanged semantics.
- Selection is now a real submodule package rather than a flat file.
- Selection now also has a deterministic package-local choice entry built on its local contracts.

# Important Invariants

- Context starts from current canonical truth before memory or artifacts.
- Research artifacts are support records, not truth.
- Research persistence stays separate from memory.
- Research-to-memory handoff is selective and must go through the current Memory write pipeline.
- Proposal padding is forbidden.
- Selection does not imply permission.
- Evaluation remains distinct from outcome and transition.

# Active Risks / Unresolved Issues

- Research now has meaningful local complexity; future work must stay inside `jeff/cognitive/research/` instead of recreating blob modules.
- Proposal now has its own package boundary; future work should stay inside `jeff/cognitive/proposal/` instead of rebuilding a flat module.
- Selection now has its own package boundary; future work should stay inside `jeff/cognitive/selection/` instead of rebuilding a flat module.
- The web acquisition path is intentionally bounded and basic rather than a general crawler or autonomy loop.
- Legacy research compatibility still exists; removing it later will require checking real callers/tests first.
- Future changes must not let research persistence or memory handoff collapse support artifacts into truth or into a memory dump.

# Next Continuation Steps

- If work is about research, continue from `jeff/cognitive/research/HANDOFF.md` first.
- If work is about proposal, continue from `jeff/cognitive/proposal/HANDOFF.md` first.
- If work is about selection, continue from `jeff/cognitive/selection/HANDOFF.md` first.
- Keep future research slices inside the research package and preserve the separation between evidence acquisition, synthesis, persistence, and memory handoff.
- Keep future proposal slices inside the proposal package and preserve the separation between proposal contracts and later runtime/model work.
- Keep future selection slices inside the selection package and preserve the separation between selection contracts and later comparison/runtime work.
- If the legacy research surface stops having real callers/tests, isolate or remove it locally instead of letting it spread back across the module.

# Submodule Map

- `context.py`: truth-first context assembly; no separate handoff.
- `research/`: bounded research package for contracts, synthesis, documents, web, persistence, and memory handoff; has its own handoff at `jeff/cognitive/research/HANDOFF.md`.
- `proposal/`: bounded proposal package for option-generation contracts; has its own handoff at `jeff/cognitive/proposal/HANDOFF.md`.
- `selection/`: bounded choice package with local contracts and deterministic choice behavior; has its own handoff at `jeff/cognitive/selection/HANDOFF.md`.
- `planning.py`: conditional planning only; no separate handoff.
- `evaluation.py`: outcome judgment contracts; no separate handoff.
- `types.py`: shared cognitive helper types; no separate handoff.

# Related Handoffs

- `handoffs/system/REPO_HANDOFF.md`
- `jeff/cognitive/proposal/HANDOFF.md`
- `jeff/cognitive/research/HANDOFF.md`
- `jeff/cognitive/selection/HANDOFF.md`
- `jeff/core/HANDOFF.md`
- `jeff/governance/HANDOFF.md`
- `jeff/action/HANDOFF.md`
- `jeff/memory/HANDOFF.md`
- `jeff/orchestrator/HANDOFF.md`
- `jeff/interface/HANDOFF.md`
