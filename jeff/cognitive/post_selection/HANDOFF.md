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
- `jeff/cognitive/post_selection/research_to_decision_support_bridge.py`
- `jeff/cognitive/post_selection/research_to_proposal_consumer.py`
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
- When research is sufficient, post-selection research output may now also pass through the explicit fail-closed `research_to_decision_support_bridge` step and preserve a bounded decision-support handoff object.
- When a lawful research decision-support handoff exists, post-selection may now also pass through the explicit fail-closed `research_to_proposal_consumer` step and preserve a bounded proposal-support package for later proposal consumption.
- When a lawful proposal-support package exists, orchestrator may now also hand it into the proposal-local fail-closed consumer and preserve a bounded proposal-input package for later proposal generation.
- When a lawful proposal-input package exists and the bounded repo-local generation inputs are explicitly present, orchestration may now also pass it through the proposal-local fail-closed proposal-generation bridge and preserve bounded proposal output.
- Only one explicit non-review intended step with plan linkage may form `Action`; non-bridgeable plans still stop truthfully at the planning boundary.
- Governance remains the next authority after a formed planned action; planning still does not grant permission.
- Research sufficiency evaluation is structural and non-authorizing: insufficient output must preserve explicit unresolved items.
- Research decision-support handoff building is structural and non-authorizing: it preserves decomposed support for later downstream consumption only and does not auto-return into proposal, selection, action, governance, or execution.
- Research-to-proposal consumption is structural and non-authorizing: it preserves decomposed support as a proposal-support package and does not auto-run proposal generation or continue into selection, action, governance, or execution.
- Proposal-input package building is proposal-local and non-authorizing: it preserves decomposed support for later proposal generation only and does not auto-run proposal generation or continue into selection, action, governance, or execution.
- Proposal-generation bridge execution remains structural and non-authorizing: it may preserve proposal output, but it does not choose an option by itself and does not auto-continue into action, governance, or execution.
- When lawful preserved proposal output exists after research follow-up, orchestrator may now hand it into the explicit Selection-local proposal-output-to-selection bridge and preserve bounded Selection output.
- When that preserved post-research `SelectionResult` exists, orchestrator may now reuse this same downstream post-selection chain to continue truthfully into terminal non-selection, escalation, planning, or governance boundaries without creating a parallel second interpretation layer.
- If that continued downstream chain would point back to `research_followup`, orchestration now stops truthfully at an explicit anti-loop boundary instead of silently recursing.
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
- Decision-support-ready research output, decision-support handoff output, and proposal-support package output are still not proposal output, not proposal choice, not selection, not permission, not governance, and not execution authority.
- Proposal-input package output is still not proposal output, not proposal choice, not selection, not permission, not governance, and not execution authority.
- Proposal output preserved after research is still only proposal output; it is not proposal choice, not selection, not permission, not governance, and not execution authority.
- Selection output preserved after that explicit downstream bridge is still only Selection output; it is not action, not permission, not governance, and not execution authority.
- Continued downstream use of preserved post-research Selection output must reuse this package's existing bridge law rather than forking a second downstream workflow.
- Research decision-support handoff must preserve uncertainty and contradiction visibility rather than compressing everything into one prose decision blob.
- Research proposal-support packages must preserve decomposed support, visible uncertainty, visible contradiction notes, and missing-information markers rather than collapsing them into hidden proposal decisions.
- Missing runtime/context inputs for post-selection proposal generation must hold truthfully at the proposal-input boundary instead of guessing or silently skipping the missing requirement.
- Governance handoff stays separate from governance policy semantics and from execution.
- The package does not own planning semantics, research-followup semantics, governance semantics, or execution semantics.
- No bridge step implies approval or execution start.
- Research-followup re-entry from continued post-research Selection output must fail closed at an explicit anti-loop boundary unless a later dedicated slice lawfully adds that recursion.

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
