# Module Name

- `jeff.orchestrator`

# Module Purpose

- Coordinate bounded stage sequencing across the existing semantic layers without owning their business logic.

# Current Role in Jeff

- Defines flow families and stage order, validates stage handoffs, routes blocked/defer/retry/escalate outcomes, and records lifecycle and trace events.

# Boundaries / Non-Ownership

- Does not own truth semantics, governance semantics, proposal logic, evaluation logic, memory rules, transition law, or interface semantics.
- Does not synthesize missing semantic outputs.

# Owned Files / Areas

- `jeff/orchestrator/flows.py`
- `jeff/orchestrator/validation.py`
- `jeff/orchestrator/routing.py`
- `jeff/orchestrator/runner.py`
- `jeff/orchestrator/continuations/`
- `jeff/orchestrator/lifecycle.py`
- `jeff/orchestrator/trace.py`

# Dependencies In / Out

- In: depends on public contracts from Core, Governance, Cognitive, Action, and Memory.
- Out: provides deterministic flow results and traceable lifecycle/output bundles to the interface layer.

# Canonical Docs to Read First

- `v1_doc/ARCHITECTURE.md`
- `v1_doc/ORCHESTRATOR_SPEC.md`
- `v1_doc/TESTS_PLAN.md`

# Current Implementation Reality

- The current orchestrator is deterministic and bounded.
- It validates stage order and semantic handoffs rather than generating business meaning itself.
- `runner.py` is again mainly the explicit stage loop, stage invocation, generic handoff/output validation, lifecycle updates, and event/finish helpers.
- Orchestration-local continuation glue now lives in `jeff/orchestrator/continuations/` as small helper modules rather than one inline runner blob.
- No new semantic layer was added: the extracted helpers remain orchestration-local glue that calls existing public contracts and reuses existing downstream law.
- It can now enter the existing planning stage for planning-routed selections, preserve the produced `PlanArtifact`, and either stop truthfully at the planning boundary or bridge one explicit bounded planned step into `Action` before governance.
- It can now also enter the existing research stage for research-followup-routed selections, preserve the produced `ResearchArtifact`, evaluate that artifact through an explicit research-output sufficiency bridge, build an explicit research decision-support handoff when that sufficiency result is lawful, consume that handoff into an explicit proposal-support package, consume that package into an explicit proposal-input package, pass that package through the explicit proposal-generation bridge when the bounded repo-local generation inputs are present, pass preserved lawful proposal output through the explicit Selection-local proposal-output-to-selection bridge, and then continue that preserved `SelectionResult` through the existing downstream post-selection chain as far as current repo-local stages lawfully allow.
- Acceptance and anti-drift tests already cover several cross-layer failure cases and truthfulness expectations.

# Important Invariants

- Orchestrator does not absorb business logic.
- Orchestrator does not synthesize missing outputs.
- Orchestrator does not treat a plan as permission and only bridges planning into `Action` through the explicit fail-closed bridge contract.
- Orchestrator does not treat research output as truth or permission and does not invent a hidden research-to-downstream bridge.
- Research sufficiency evaluation is structural only: insufficient research must preserve explicit unresolved items.
- Research decision-support handoff building is structural only: sufficient research may produce a handoff for later downstream consumption, but that still does not authorize proposal choice, selection, action, governance, or execution.
- Research proposal-support consumption is structural only: sufficient research may also produce a proposal-support package for later proposal consumption, but that still does not authorize proposal generation, selection, action, governance, or execution.
- Proposal-input consumption is structural only: sufficient research may also produce a proposal-input package for later proposal generation, but that still does not authorize proposal output, selection, action, governance, or execution.
- Proposal-generation bridge use is structural only: sufficient research may also produce preserved proposal output, but that still does not authorize action, governance, or execution.
- Selection bridge use is structural only: sufficient research may also produce preserved Selection output, and any further downstream continuation must reuse the existing post-selection chain without making Selection itself authorizing.
- Extracted continuation helpers must not fork a second downstream interpretation path or duplicate downstream semantic law.
- If continued post-research next-stage resolution points back to `research_followup`, orchestrator stops truthfully at an explicit anti-loop boundary rather than auto-recursing.
- Missing proposal-to-selection bridge inputs must hold truthfully at the proposal-output boundary instead of guessing downstream semantics.
- Blocked or approval-gated flows stop honestly.
- Routing decisions stay distinct from semantic stage outputs.

# Active Risks / Unresolved Issues

- Richer workflow engines remain deferred.
- Autonomous continuation remains deferred.
- Any future convenience abstraction that hides stage boundaries or permissions inside the runner would be drift.

# Next Continuation Steps

- If future work extends flows, add handoff validation and acceptance coverage first so sequencing remains downstream of semantic owners.

# Submodule Map

- `flows.py`: flow families and stage ordering; no separate handoff.
- `validation.py`: handoff and stage-output validation; no separate handoff.
- `routing.py`: bounded follow-up routing; no separate handoff.
- `runner.py`: deterministic flow runner and generic lifecycle/event/result coordination; no separate handoff.
- `continuations/post_research.py`: orchestration-local research-followup continuation glue; no separate handoff.
- `continuations/post_selection.py`: orchestration-local preserved-selection continuation glue; no separate handoff.
- `continuations/planning.py`: orchestration-local plan-to-action bridge glue; no separate handoff.
- `continuations/boundary_routes.py`: orchestration-local routing summaries for continuation boundaries; no separate handoff.
- `lifecycle.py`: orchestration-local lifecycle state; no separate handoff.
- `trace.py`: compact ordered trace events; no separate handoff.

# Related Handoffs

- `handoffs/system/REPO_HANDOFF.md`
- `jeff/core/HANDOFF.md`
- `jeff/governance/HANDOFF.md`
- `jeff/cognitive/HANDOFF.md`
- `jeff/action/HANDOFF.md`
- `jeff/memory/HANDOFF.md`
- `jeff/interface/HANDOFF.md`
