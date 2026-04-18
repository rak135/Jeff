# Module Name

- `jeff.cognitive.post_selection`

# Module Purpose

- Own the downstream bridge after Selection without taking over Selection semantics, Governance semantics, execution, or outcome ownership.

# Current Role in Jeff

- Groups the bounded post-Selection bridge into one dedicated package.
- Carries the deterministic bridge objects and transformations from `SelectionResult` plus optional override through resolved basis, materialized effective proposal, explicit next-stage resolution, formed `Action`, and governance handoff.

# Boundaries / Non-Ownership

- Does not own Selection semantics, Selection-local decision behavior, or proposal generation.
- Does not own Governance semantics, approval policy, or governance decision rules.
- Does not own execution, outcome normalization, truth mutation, or interface rendering semantics.
- Does not imply permission, readiness, approval, or execution authority.

# Owned Files / Areas

- `jeff/cognitive/post_selection/__init__.py`
- `jeff/cognitive/post_selection/override.py`
- `jeff/cognitive/post_selection/action_resolution.py`
- `jeff/cognitive/post_selection/effective_proposal.py`
- `jeff/cognitive/post_selection/action_formation.py`
- `jeff/cognitive/post_selection/plan_action_bridge.py`
- `jeff/cognitive/post_selection/research_output_sufficiency_bridge.py`
- `jeff/cognitive/post_selection/governance_handoff.py`
- `jeff/cognitive/post_selection/next_stage_resolution.py`
- `jeff/cognitive/post_selection/HANDOFF.md`

# Current Implementation Reality

- This package was extracted from the flat `jeff/cognitive/` layout for package hygiene and clearer ownership.
- The bridge remains deterministic and structural: Selection output stays separate from override choice, resolved basis, effective proposal materialization, explicit next-stage routing, Action formation, and governance handoff.
- Orchestrator now consumes the explicit next-stage routing result after effective proposal materialization.
- The `governance` route continues into `action_formation` and `governance_handoff`.
- The `planning` route is no longer only a structural routing label: orchestrator may now enter the existing planning stage and preserve a bounded `PlanArtifact`.
- Planning may now also bridge into `Action`, but only through the explicit fail-closed `plan_action_bridge` step.
- The `research_followup` route is no longer only a structural routing label: orchestrator may now enter the existing research stage and preserve a bounded `ResearchArtifact`.
- Post-selection research output now also passes through the explicit fail-closed `research_output_sufficiency_bridge` step before orchestration stops at the research boundary.
- Only one explicit non-review intended step with plan linkage may form `Action`; non-bridgeable plans still stop truthfully at the planning boundary.
- Governance remains the next authority after a formed planned action; planning still does not grant permission.
- Research sufficiency evaluation is structural and non-authorizing: sufficient output means bounded decision-support-ready only, and insufficient output must preserve explicit unresolved items.
- Downstream after research remains bounded by current repo reality: there is still no repo-owned research-to-proposal, research-to-selection, research-to-action, governance, or execution bridge inside this package.
- Other routed targets remain structural downstream results surfaced truthfully to orchestration; they are not hidden execution branches.

# Important Invariants

- The package starts from `SelectionResult` and optional operator override; it does not redefine Selection truth.
- Resolved basis stays separate from effective proposal materialization.
- Explicit next-stage resolution stays separate from Action formation.
- Effective proposal materialization stays separate from Action formation.
- Planning remains support-only and non-authorizing even when orchestration enters the planning stage.
- Planned Action formation remains structural and fail-closed; it must not guess from vague or multi-step plan prose.
- Research follow-up remains support-only and non-authorizing even when orchestration enters the research stage.
- Research sufficiency evaluation must not hide contradictions, missing evidence, or unresolved items behind vague closure language.
- Decision-support-ready research output is still not permission, not governance, and not execution authority.
- Governance handoff stays separate from governance policy semantics and from execution.
- The package does not own planning semantics, research-followup semantics, governance semantics, or execution semantics.
- No bridge step implies approval or execution start.

# Next Continuation Steps

- Keep future downstream-bridge slices inside this package instead of recreating flat `jeff/cognitive/` modules.
- Preserve the separation between Selection semantics, bridge transformations, governance semantics, and execution semantics.

# Related Handoffs

- `jeff/cognitive/HANDOFF.md`
- `jeff/cognitive/selection/HANDOFF.md`
- `jeff/governance/HANDOFF.md`
- `jeff/action/HANDOFF.md`
- `jeff/interface/HANDOFF.md`
- `handoffs/system/REPO_HANDOFF.md`
