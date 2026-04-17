# Module Name

- `jeff.cognitive.proposal`

# Module Purpose

- Own the bounded Proposal contract surface for candidate-option generation without owning selection, governance, action entry, execution, or truth mutation.

# Current Role in Jeff

- Exposes the canonical Proposal contract types used by current callers and tests.
- Keeps Proposal as a Cognitive-owned stage with honest scarcity and `0..3` serious-option law.
- Owns the bounded Proposal Step 1 pipeline from prompt contract through validated proposal handoff without owning selection semantics.

# Boundaries / Non-Ownership

- Does not own selection, approval, readiness, action, execution, memory, transition commit, or orchestrator flow control.
- Does not grant authority, permission, or action-entry semantics.
- Does not add repair/formatter behavior, retry/fallback logic, selection wiring, orchestrator integration, or truth mutation.

# Owned Files / Areas

- `jeff/cognitive/proposal/__init__.py`
- `jeff/cognitive/proposal/contracts.py`
- `jeff/cognitive/proposal/api.py`
- `jeff/cognitive/proposal/generation.py`
- `jeff/cognitive/proposal/parsing.py`
- `jeff/cognitive/proposal/validation.py`
- `jeff/cognitive/proposal/prompt_files.py`
- `PROMPTS/proposal/STEP1_GENERATION.md`

# Current Implementation Reality

- Proposal is now a dedicated package rather than a flat module.
- `ProposalResult` is now the primary current Proposal-local success and downstream handoff contract for the composed runtime pipeline.
- Selection, Planning, and orchestrator stage validation now consume `ProposalResult` directly.
- `ProposalOption` and `ProposalSet` remain only as a carried compatibility subset inside `ProposalResult` plus narrow contracts-only scaffolding in bootstrap, fixtures, and explicit compatibility tests.
- Proposal now also has a file-backed Step 1 generation prompt contract plus a minimal local prompt loader/renderer.
- Proposal now also has a bounded generation-entry surface that builds a render-ready prompt bundle from context plus optional research support.
- Proposal now also has a bounded runtime handoff that sends the Step 1 prompt bundle through the existing infrastructure runtime pattern and returns raw text plus minimal runtime metadata.
- Proposal now also has a deterministic Step 1 parser that turns raw bounded text into structured parsed data without semantic judgment.
- Proposal now also has a deterministic semantic validator that turns parsed Step 1 output into a lawful `ProposalResult` or explicit validation issues.
- Proposal now also has a thin end-to-end API entry that composes build, runtime, parse, and validation into either `ProposalPipelineSuccess` with a `ProposalResult` or explicit stage-specific failure.
- Public Proposal exports now center on `ProposalResult`, `ProposalResultOption`, the pipeline entry, and stage-specific failure surfaces.
- `ProposalOption` and `ProposalSet` are no longer exported from `jeff.cognitive.proposal` or `jeff.cognitive`; they remain only in `jeff.cognitive.proposal.contracts` for explicit compatibility-only construction.
- Older `ValidatedProposalGenerationResult`, `ValidatedProposalOption`, and `ProposalDownstreamHandoff` shapes are removed as public primary surfaces.

# Important Invariants

- Proposal stays distinct from selection, governance, approval, readiness, action, and execution.
- Proposal may return `0..3` serious options only.
- Honest scarcity is required when fewer than two serious options exist.
- Near-duplicate padding remains forbidden.

# Active Risks / Unresolved Issues

- Legacy scaffold prompt files still exist under `PROMPTS/proposal/` beside the new canonical Step 1 contract.
- Research artifacts currently do not carry their own scope fields, so Proposal generation cannot independently verify research-support scope beyond trusted caller discipline.
- Proposal runtime currently returns raw text only before parsing; no normalization or repair layer exists yet.
- The primary downstream handoff currently stays Proposal-local and intentionally does not shape Selection semantics yet.
- Proposal validation currently uses proposal-local authority-language checks because the repo does not yet have a shared bounded cognition validation utility.
- `ProposalResult` still carries `proposal_set` and per-option `proposal` compatibility objects internally, so fully removing `ProposalOption` / `ProposalSet` requires a separate contract-removal pass rather than another downstream migration.

# Next Continuation Steps

- Add Proposal runtime calling only in later bounded slices.
- Keep generation-entry work separate from later parsing, normalization, and runtime invocation.
- Keep runtime handoff separate from later parsing, normalization, validation, and any formatter/repair behavior.
- Keep validation separate from any later repair, retry, normalization, or selection handoff behavior.
- Keep the thin API entry compositional only; do not let it absorb selection, repair, or orchestration behavior.
- Keep contract ownership in this package even if runtime surfaces are added later.

# Related Handoffs

- `jeff/cognitive/HANDOFF.md`
- `handoffs/system/REPO_HANDOFF.md`
