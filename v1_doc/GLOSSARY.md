# Purpose of This Document

This document fixes the canonical meaning of Jeff terms for the whole Jeff system.

It owns the language layer.
It resolves conflicting legacy wording.
It freezes which words mean what across canonical Jeff documents.

It does not own:
- architecture law
- schema details
- lifecycle enums
- roadmap sequencing
- implementation status

This is not a v1-only glossary.
It defines whole-Jeff language and uses v1 notes only to mark the first enforced subset where needed.

# Terminology Rules

- One canonical term gets one canonical meaning.
- Canonical docs must not carry parallel meanings for the same term.
- Terminology follows architecture, not habit.
- Legacy wording is subordinate once this glossary defines the term.
- Casual synonym sprawl is forbidden unless this glossary explicitly allows it.
- Container terms are strict: use `project`, `work_unit`, and `run` for the canonical containers, not ad hoc substitutes such as `task`, `job`, `thread`, or `workflow`.
- Mutation terms are strict: use `transition` for canonical truth mutation. Do not smuggle mutation authority back in through `Change`, `patch`, `diff`, or interface wording.
- Action-entry terms are strict: `selection` chooses, `action` operationalizes intended work, `approval` grants permission where required, `readiness` answers whether action may begin now, and `execution` performs action if lawfully allowed.
- `action` is strict: use it only for the bounded transient operational object family between decision structure and execution entry.
- Interface wording must preserve backend semantics. Convenience labels must not flatten truth classes or lifecycle boundaries.
- If a whole-Jeff term has a narrower v1 role, note the v1 limit explicitly. Do not create a second definition.

# Core Terms

### truth
Authoritative Jeff fact.
In Jeff, current truth is carried by canonical truth objects, not by memory, artifacts, logs, chat, or interface state.

### canonical truth
Truth that Jeff recognizes as authoritative under its architecture.
For current system reality, canonical truth is what the Core layer exposes through canonical truth objects.

### canonical state
The authoritative current-state representation of Jeff truth.
In Jeff this means the global canonical state and the canonical truth objects nested within it.

### global canonical state
The one root canonical truth object for the system.
It contains system-level truth and nested projects.
It is not one state among many.

### project
The canonical bounded container for one line of work inside the global canonical state.
Project is a hard isolation boundary inside global truth, not a separate truth store.

### work_unit
The canonical bounded effort inside a project.
It is the primary persistent work container in v1.
It is not a workflow, run, or chat thread.

### run
One bounded attempt or flow instance inside a work_unit.
Run is a canonical truth object.
It is not the work_unit and not the workflow.

### workflow
A higher-level bounded coordination structure across flows, decision points, and review points.
Workflow may coordinate actions and other bounded flow units.
Whole-Jeff meaning: valid coordination concept.
v1 note: not first-class canonical truth.

### action
A bounded transient operational object family representing concrete intended work after selection or after a plan boundary and before or at execution entry.
Action is what approval and readiness evaluate and what execution may perform if lawfully allowed.
Action is not a canonical truth object, governance object, support/review object, plan, execution, transition, or a generic synonym for any thing to do.

### transition
The only canonical truth mutation contract.
A transition constructs, validates, and commits authoritative state change.
It is not a patch, diff, execution side effect, or interface write.

### Change
A support/apply/review object for bounded real-world mutation intent when that flow exists.
It may support apply, rollback, recovery, or review.
It may inform later action for governed mutation work.
It is never action itself and never a rival canonical mutation primitive.

### governance
The Jeff control domain that decides whether bounded action may proceed.
It owns permissioning, gating, freshness-sensitive rechecks, and action-entry results.

### policy
The explicit rule system for what is allowed, blocked, approval-gated, or autonomy-gated.
Policy is enforceable system law, not prompt habit.

### approval
A governance object that records a permission decision for action where operator or policy-controlled approval is required.
Approval gates action.
Approval is not readiness, action, execution, or apply.

### readiness
A governance object that answers whether a bounded action may begin now under current truth, current scope, and current constraints.
Readiness evaluates action at start time.
Readiness is not approval, action, execution, and not mere workflow momentum.

### context
The bounded truth-first input package assembled for reasoning.
It may include current truth, committed memory, operator input, and relevant evidence.
It is not a raw dump.

### research
Bounded, source-grounded inquiry used to reduce uncertainty.
Research produces decision support, not truth mutation or permission.

### proposal
The bounded candidate-option stage.
Proposal generation may honestly return 0 to 3 serious options.
A proposal is not a decision and not permission.

### selection
The bounded choice stage that selects one proposal or rejects, defers, or escalates honestly.
Selection is not execution permission.
Selection does not itself become action.

### planning
Structured intended work used when the work shape needs it.
Whole-Jeff meaning: plan formation for multi-step or review-heavy work.
v1 note: conditional, not universal.
Planning may structure or refine later action, but it is not action.

### selection result
The transient processing object produced by selection.
It carries the chosen option or explicit non-selection outcome.
It is upstream of action formation.
It does not carry permission and is not action itself.

### execution
The governed stage that performs bounded work.
Execution performs action in the world or through tools when governance allows it.
Execution is not action, truth, or evaluation.

### execution result
The direct transient result produced by execution before outcome normalizes what happened.
It is stage-local operational output produced from execution of action, not current truth.

### outcome
The normalized observed result of execution.
Outcome states what happened in bounded form.
Outcome uses an expanded but bounded verdict model rather than a coarse binary.
It is not evaluation.

### evaluation
The stage that judges outcome against goals, constraints, evidence, and direction.
Evaluation produces verdicts and recommendations.
Evaluation also uses an expanded but bounded verdict model rather than a coarse binary.
It does not mutate truth by itself.

### evaluation result
The transient processing object produced by evaluation.
It can inform memory and transition construction, but does not commit truth.

### memory
Durable non-truth continuity.
Memory exists for retrieval and reuse across time.
It does not define current truth.

### memory candidate
A pre-commit memory write candidate created by the Memory module.
Only Memory creates memory candidates in v1.

### memory entry
A committed durable memory record.
It is support knowledge, not current truth.

### committed memory ID
The identifier of a memory entry that completed the memory write pipeline.
Canonical state may reference committed memory IDs only.

### artifact
A durable output of a flow or stage.
Artifacts may support later reasoning, review, or evidence use.
Artifacts are not current truth by default.

### source
The origin container from which information comes.
A source may be a truth object, artifact, document, code file, operator material, or external material.
A source is not automatically evidence.

### evidence
Bounded support extracted from one or more sources for a specific question or claim.
Evidence must preserve provenance.
Evidence is not the same thing as a source list.

### finding
A direct evidence-backed statement.
Finding is stronger than raw source content and narrower than inference.

### inference
An interpretation drawn from findings.
Inference must remain labeled as inference.
It is not a finding and not current truth.

### recommendation
A suggested next action or decision input derived from research, evaluation, or review.
Recommendation is not selection, approval, execution, or truth.

### operator
The human authority above Jeff.
The operator sets direction, resolves escalations, and grants approvals that policy requires.

### orchestrator
The sequencing layer that coordinates bounded flows through public contracts.
It does not absorb module reasoning, policy semantics, or transition law.

### interface
The human- and client-facing surface into Jeff.
It must present backend semantics truthfully and must not own hidden write paths.

### derived view
A presentation-oriented representation produced from authoritative backend/domain data.
A derived view may reshape data for usability.
It must not invent semantics or replace canonical truth.

### interface state
Frontend-local or session-local presentation state.
It may support interaction.
It is never canonical state.

### assistant
The higher-level interaction layer above backend law.
Whole-Jeff meaning: conversational continuity and future initiative behavior.
v1 note: richer assistant behavior is deferred.

### infrastructure
The non-semantic technical support layer.
It provides storage, adapters, observability, and plumbing.
It does not define Jeff meaning.

### direction
Durable project strategic truth that states what the project is trying to become and what it must not quietly become.
Direction is canonical project truth, not memory and not roadmap.

### truth mismatch
A structured condition where sources that should align do not align in a way that matters to truth or safe operation.
Truth mismatch is a degraded-trust condition, not the repair itself.

### integrity
The structural correctness and lawful alignment of truth objects, references, and related authoritative surfaces.
Integrity problems may exist without immediate mutation.
Serious integrity failure can block unsafe continuation.

### drift
Meaningful movement away from stated direction, scope, truth discipline, or other intended system boundaries.
Drift is not any difference.
It is deviation that matters.

### revalidation
A renewed check because prior basis may be stale, conditions changed, or risk now requires a fresh determination.
Revalidation is not optional cleanup.

### rollback
A governed attempt to restore an earlier real-world state after failed or unsafe mutation-related work.
Rollback is not a transition and not automatic truth repair.

### reconciliation
A governed repair flow that restores alignment after mismatch, partial apply, or other degraded-truth conditions.
Reconciliation may recommend or support transitions.
It does not bypass them.

# Object-Class Terms

### canonical truth object
An object that carries current authoritative Jeff truth.
Only canonical truth objects define current truth directly.

### governance object
An object that records or determines permission, gating, or action-entry status.
Governance objects constrain action but do not become current truth of the world.

### transient processing object
A stage-bounded working object used during reasoning, action, or judgment.
It may be durable as an artifact or loggable result, but it is not current canonical truth.

### transient operational object family
A specialized transient processing family for concrete intended work between decision structure and execution entry.
`action` is the canonical transient operational object family.

### support/review object
A durable or semi-durable object that supports review, apply, memory, recovery, or operator understanding without owning current truth mutation law.

Classification:
- `global state`: canonical truth object
- `project`: canonical truth object
- `work_unit`: canonical truth object
- `run`: canonical truth object
- `transition`: canonical truth object
- `approval`: governance object
- `readiness`: governance object
- `proposal`: transient processing object
- `selection result`: transient processing object
- `action`: transient operational object family
- `execution result`: transient processing object
- `outcome`: transient processing object
- `evaluation result`: transient processing object
- `memory entry`: support/review object
- `Change`: support/review object

# Layer Terms

### Core
Owns canonical truth, canonical containers, transition law, and shared truth contracts.

### Governance
Owns policy, approval, readiness, and other action-entry permissioning semantics.

### Cognitive
Owns context, research, proposal, selection, conditional planning, and evaluation.

### Action
Owns execution and outcome, plus supporting real-world mutation flows such as apply or rollback support where they exist.

### Memory
Owns memory candidate creation, memory storage, retrieval, and linking.

### Orchestration
Owns sequencing, lifecycle coordination, handoff validation, and routing.

### Interface
Owns truthful operator and client access surfaces such as CLI, GUI, and API bridge.

### Infrastructure
Owns replaceable technical support such as storage, adapters, connectors, and observability.

### Assistant
Owns higher-level personal interaction behavior above the rest of the system.
It stays subordinate to backend law.

# Flow and Lifecycle Terms

### trigger
The event or condition that starts a Jeff flow.
A trigger begins work.
It does not authorize unsafe continuation by itself.

### bounded action flow
A finite, scoped Jeff flow that moves through named stages toward one bounded objective under policy and truth constraints.
Canonical whole-Jeff path: `proposal -> selection -> optional planning -> action -> governance -> execution -> outcome -> evaluation -> memory -> transition`.

### pre-execution governance
The governance step between action and execution.
In v1 it minimally includes approval and readiness.

### blocked flow
A flow that cannot continue because a blocker, policy rule, truth mismatch, missing approval, failed readiness, or other decisive constraint is active.

### escalation
A structured request for operator judgment when Jeff reaches a boundary it must not cross alone.
Escalation is not approval itself and not generic uncertainty.

### conditional planning
Planning invoked only when the work is multi-step, high-risk, review-heavy, or time-spanning.
Conditional planning is the canonical v1 rule.

### long-running bounded continuation
Future whole-Jeff capability for continuing bounded work across many runs under persistent scope, policy, and checkpoint rules.
It is not a v1 default runtime promise.

# Research and Evidence Terms

### internet research
Research that gathers external sources from the internet to answer a bounded question.
It must remain source-aware, scoped, and evidence-disciplined.

### project-scoped research
Research explicitly anchored to one project, work_unit, or bounded project question.
It must not quietly widen into unscoped browsing.

### source-aware synthesis
Synthesis that preserves which sources were used, what each source supports, and where contradiction or limitation remains.

### evidence-backed output
An output whose key claims, comparisons, or recommendations are grounded in explicit evidence with visible scope and limits.

### provenance
The origin and transformation lineage of a claim, evidence item, or derived view.
Provenance explains where something came from and how it was derived.

### finding
A directly supported statement extracted from evidence.
Findings should be narrow, reviewable, and claim-bounded.

### inference
An interpretation drawn from findings.
Inference may guide later work, but it must not be mislabeled as direct support.

### recommendation
A bounded suggested next step derived from findings, inference, judgment, or review.
It must stay proportional to the support behind it.

# Terms That Must Not Drift

- `state`: the authoritative current truth model, not memory, logs, or interface cache.
- `transition`: the only canonical truth mutation contract.
- `action`: bounded transient operational object after selection and before governance/execution; never a catch-all synonym for work.
- `Change`: a support/apply object only, never rival mutation law.
- `workflow`: higher-level coordination structure; not first-class canonical truth in v1.
- `selection`: bounded choice only; never permission by itself.
- `approval`: permission decision; not readiness, execution, or apply.
- `readiness`: start-time governance result; not approval and not mere workflow progression.
- `outcome`: normalized observed result; not evaluation.
- `evaluation`: judgment of outcome; not execution and not transition.
- `memory`: durable non-truth continuity; not current truth.
- `truth`: authoritative Jeff fact rooted in canonical truth objects.
- `project`: isolation boundary inside one global canonical state; not a separate canonical state.
- `run`: one bounded attempt inside a work_unit; not the work_unit and not the workflow.
- `source`: information origin; not evidence by default.

# Forbidden Terminology Collapses

- `memory = truth`: forbidden. Memory is support continuity, not current authority.
- `action = selection`: forbidden. Selection chooses; action operationalizes concrete intended work afterward.
- `action = approval`: forbidden. Approval governs action; it is not the action.
- `action = readiness`: forbidden. Readiness judges whether action may start now; it is not the action.
- `action = execution`: forbidden. Execution performs action; it does not replace it.
- `action = planning`: forbidden. Planning structures intended work; it does not become action by default.
- `action = transition`: forbidden. Action may lead to execution and later transitions; it is not mutation law.
- `action = generic thing to do`: forbidden. `action` is a bounded canonical operational term, not loose prose.
- `selection = permission`: forbidden. Selection chooses; governance permits.
- `execution = truth`: forbidden. Execution does work; it does not define what became true.
- `outcome = evaluation`: forbidden. Outcome states what happened; evaluation judges it.
- `workflow = work_unit`: forbidden. Workflow is coordination structure; work_unit is the bounded work container.
- `Change = transition`: forbidden. `Change` may support apply or review; `transition` alone mutates canonical truth.
- `interface state = canonical state`: forbidden. Interface state is local presentation state only.
- `assistant memory = canonical memory`: forbidden. Assistant continuity or session memory is not canonical Jeff memory by default.
- `planning = mandatory stage`: forbidden. Planning is conditional, not universal.
- `research = unscoped browsing`: forbidden. Research must stay bounded, source-grounded, and question-shaped.
- `project = separate canonical state`: forbidden. Projects live inside one global canonical state.
- `run = work_unit`: forbidden. A run is one bounded attempt inside a work_unit.
- `source = evidence`: forbidden. A source is origin; evidence is support extracted for a claim or question.
- `approved = applied`: forbidden. Approval grants permission; apply or execution still must happen and be verified.

# Questions

No unresolved terminology questions were found in this pass.

# Final Note

The remaining open edges are about future richness, not about current meanings:
- `action` may gain richer typed families or more durable runtime materialization later, but it remains a narrow transient operational object family rather than a new truth or governance layer.
- `workflow` may become a first-class truth object later, but that future does not weaken its current canonical meaning or its non-first-class v1 status.
- `long-running bounded continuation` is a future system capability built from the same backbone, not a different backbone.
- `assistant` may grow richer initiative behavior later, but it remains downstream of truth, governance, and transition law.
