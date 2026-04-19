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
- `jeff/cognitive/proposal/proposal_generation_bridge.py`
- `jeff/cognitive/proposal/proposal_support_package_consumer.py`
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
- Proposal now also has a proposal-local fail-closed consumer that turns a preserved proposal-support package into an explicit proposal-input package for later proposal generation without auto-running generation.
- Proposal now also has a proposal-local fail-closed proposal-generation bridge that turns a lawful preserved `ProposalInputPackage` plus the bounded repo-local generation inputs into a lawful `ProposalGenerationRequest`, runs the real proposal pipeline, preserves proposal output when generation succeeds, and otherwise preserves a truthful non-generation boundary.
- When orchestration explicitly chooses to continue after lawful preserved proposal output exists, that downstream continuation now happens through a separate Selection-local proposal-output-to-selection bridge and then, when lawful, through the existing downstream post-selection chain rather than by collapsing Proposal into Selection inside this package.
- Public Proposal exports now center on `ProposalResult`, `ProposalResultOption`, the pipeline entry, and stage-specific failure surfaces.
- `ProposalOption` and `ProposalSet` are no longer exported from `jeff.cognitive.proposal` or `jeff.cognitive`; they remain only in `jeff.cognitive.proposal.contracts` for explicit compatibility-only construction.
- Older `ValidatedProposalGenerationResult`, `ValidatedProposalOption`, and `ProposalDownstreamHandoff` shapes are removed as public primary surfaces.
- Post-selection research continuation may now also preserve a proposal-support package, a proposal-input package, and when the required bounded runtime/context inputs exist a preserved proposal output through the explicit proposal-generation bridge.

# Important Invariants

- Proposal stays distinct from selection, governance, approval, readiness, action, and execution.
- Proposal may return `0..3` serious options only.
- Honest scarcity is required when fewer than two serious options exist.
- Near-duplicate padding remains forbidden.
- Upstream proposal-support packages remain support-only and do not count as proposal output, selection, permission, or execution authority.
- Proposal-input packages remain support-only and do not count as proposal output, selection, permission, or execution authority.
- Proposal-input packages must preserve decomposed support, visible uncertainty, visible contradiction notes, and missing-information markers rather than collapsing them into hidden choices.
- Proposal-generation bridge results remain structural and non-authorizing whether they preserve proposal output or a truthful non-generation boundary.
- Proposal output remains proposal output only; it does not become selection, permission, action, governance, or execution authority.
- Any downstream Selection continuation remains separate from Proposal ownership even when orchestration preserves Selection output after Proposal output.

# Active Risks / Unresolved Issues

- Legacy scaffold prompt files still exist under `PROMPTS/proposal/` beside the new canonical Step 1 contract.
- Research artifacts currently do not carry their own scope fields, so Proposal generation cannot independently verify research-support scope beyond trusted caller discipline.
- Proposal runtime currently returns raw text only before parsing; no normalization or repair layer exists yet.
- The primary downstream handoff currently stays Proposal-local and intentionally does not shape Selection semantics yet.
- Proposal validation currently uses proposal-local authority-language checks because the repo does not yet have a shared bounded cognition validation utility.
- Post-selection proposal generation now depends on explicit runtime services being provided by the calling boundary; missing runtime/context inputs truthfully hold at the proposal-input boundary instead of guessing.
- `ProposalResult` still carries `proposal_set` and per-option `proposal` compatibility objects internally, so fully removing `ProposalOption` / `ProposalSet` requires a separate contract-removal pass rather than another downstream migration.

# Next Continuation Steps

- Keep generation-entry work separate from later parsing, normalization, and runtime invocation.
- Keep runtime handoff separate from later parsing, normalization, validation, and any formatter/repair behavior.
- Keep validation separate from any later repair, retry, normalization, or selection handoff behavior.
- Keep the thin API entry and proposal-generation bridge compositional only; do not let them absorb selection, repair, or orchestration behavior.
- Keep contract ownership in this package even if runtime surfaces are added later.

# Related Handoffs

- `jeff/cognitive/HANDOFF.md`
- `handoffs/system/REPO_HANDOFF.md`
