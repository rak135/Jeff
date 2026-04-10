# Purpose

This document defines Jeff's canonical proposal-and-selection law.

It owns:
- the proposal model
- the selection model
- proposal cardinality law
- proposal quality and scarcity rules
- selection choice rules
- reject-all, defer, and escalate rules at the decision layer
- proposal-to-selection handoff law
- rationale requirements for proposal and selection
- risk, assumption, and feasibility handling at the decision layer
- proposal/selection invariants
- proposal/selection failure modes
- the distinction between whole-Jeff decision law, the v1 enforced decision layer, and deferred expansion

It does not own:
- governance semantics
- approval or readiness meaning
- execution semantics
- transition lifecycle or truth-mutation law
- interface display contracts
- telemetry schemas
- test matrices
- roadmap sequencing

This is Jeff's canonical bounded option-generation and bounded choice document.
It is not an implementation-status note, not a vague essay about decision-making, and not a hidden replacement for planning, governance, execution, or workflow specs.

# Canonical Role in Jeff

Proposal explores bounded possibilities from truth-first context.
Selection chooses among those possibilities, or honestly declines to advance any of them, under current truth, scope, constraints, and known uncertainty.

Proposal and selection operate inside one global canonical state with nested projects.
`project`, `work_unit`, and `run` are the foundational scope containers this decision law reasons within.
Project is the hard isolation boundary for proposal and selection scope.

Jeff cannot tolerate:
- fake alternatives invented to satisfy process
- hidden decisions smuggled into context or proposal wording
- selection results that quietly mean approval, readiness, or execution permission
- workflow or planning momentum pretending to be choice

If proposal inflates options, selection becomes theater.
If context does hidden proposal work, Jeff loses inspectable cognition boundaries.
If selection absorbs approval or readiness, governance disappears before execution starts.
This document exists to keep Jeff's pre-governance cognition disciplined, bounded, and reviewable.

# Core Principle

The binding law is:
- proposal generates possibilities, not authority
- selection chooses, but does not authorize execution
- both stages stay bounded, honest, and inspectable
- fake option inflation is worse than honest scarcity

If Jeff has no honest option, it must say so.
If Jeff has only one serious option, it must say so.
If Jeff reaches a real judgment boundary, it must reject all, defer, or escalate honestly instead of laundering that boundary into fake decisiveness.

# Proposal Model

Proposal is the bounded candidate-option stage.
It turns truth-first context, relevant support, visible constraints, and current scope into a small set of serious possibilities for decision.

Proposal is upstream of decision.
It is not:
- action
- action permission
- planning authority
- governance
- execution
- truth mutation

Proposal may produce bounded options such as:
- direct action
- investigation or research
- clarification when missing facts or scope ambiguity block stronger action
- planning insertion when the chosen path would need structured multi-step work
- recovery or reconciliation
- defer or pause
- escalation

These are option shapes, not a mandatory large taxonomy.
Jeff should type options only as far as needed to preserve real differences between them.

## Allowed Cardinality

Proposal may honestly return 0 to 3 serious options.

0 serious options is legitimate when:
- no honest option can be supported from current truth and available support
- scope is too unclear for serious option framing
- contradiction or blocker state makes every apparent option dishonest
- the candidate pool collapses under duplicate suppression or quality filtering

1 serious option is legitimate when:
- only one option survives boundedness, support, and scope discipline
- one path is genuinely the only serious candidate
- the only honest candidate is a bounded investigate, clarify, defer, or escalate path

2 serious options are useful when:
- Jeff has a real tradeoff to compare
- one option favors progress while another favors caution
- direct action and investigation are both serious

3 serious options are useful when:
- there are three materially distinct bounded paths with meaningful comparative value
- adding the third option reveals a real tradeoff Jeff would otherwise hide

Proposal must not return more than 3 serious options in canonical form.
If more possibilities exist, Jeff must cluster them, suppress duplicates, or keep only the serious representatives.

When proposal returns 0 or 1, the scarcity reason must be explicit.

## Quality Rules

Every serious proposal must be:
- bounded enough to compare
- grounded in current truth and relevant support
- scope-honest
- explicit about material assumptions
- explicit about material risks
- explicit about decisive blockers or constraints when they matter
- distinct from other retained options
- usable by downstream selection without narrative guesswork

Proposal quality is not measured by:
- how bold the option sounds
- how polished the wording sounds
- how many options exist
- how likely the option is to win

A high-quality investigation, clarification, defer, or escalation option is better than a polished but weak action option.

## Scarcity Rules

Proposal scarcity is a law, not an exception.

The rules are:
- do not invent fake alternatives to satisfy a quota
- do not pad the set with near-duplicates
- do not hide the need for investigation, clarification, defer, or escalation just because they sound less exciting
- do not turn one preferred path into fake diversity through wording variants
- do not suppress honest scarcity to make the system look smarter

If the honest set is weak, incomplete, or empty, proposal must say so directly.

# Selection Model

Selection is the bounded choice stage.
It evaluates the current proposal set under current truth, current scope, visible constraints, available support, and known uncertainty, then either chooses one option or returns an honest non-selection outcome.

Selection may choose only from:
- the bounded serious options handed forward by proposal
- the explicit constraints and uncertainty carried with them
- current truth and context needed to judge them

Selection may not choose from hidden context residue, workflow momentum, interface pressure, or untracked operator assumptions.

## Choice Rules

Selection may choose at most one proposal option.
It may also honestly choose not to advance to action.

Selection should compare options using criteria such as:
- scope fit
- direction fit
- blocker compatibility
- evidence strength
- assumption burden
- risk posture
- reversibility or recovery friendliness when relevant
- whether planning insertion is needed before operationalization

Selection may use feasibility signals, but only as decision support.
Feasibility is not readiness.
Risk acceptability is not approval.

If a selected option remains the best bounded path, selection may hand forward intent that later becomes or informs `action`.
If the selected option is a planning-insertion path, planning may later structure it.
If no option should move forward, selection must say so explicitly.

## Reject-All / Defer / Escalate Rules

Whole-Jeff non-selection outcomes are intentionally small and explicit:
- `reject_all`
- `defer`
- `escalate`

`reject_all` is appropriate when:
- the available proposal set is not acceptable as a serious decision basis
- all options are out of scope, badly supported, blocked, structurally weak, or otherwise not honest to choose
- proposal scarcity resulted in no viable candidate to select

`defer` is appropriate when:
- choice should not be made now, but the situation does not yet require operator judgment
- a bounded prior condition must be satisfied first
- more research, clarification, reconciliation, or time-dependent change is needed before honest choice
- one or more options remain potentially viable later

`escalate` is appropriate when:
- autonomous choice would cross a judgment boundary
- direction, strategy, or risk tradeoff requires operator judgment
- contradiction or uncertainty is too meaningful to resolve inside the decision layer
- Jeff can frame the decision but should not make it alone

Selection does not emit permission law.
Selection does not decide approval.
Selection does not decide readiness.
Selection does not mutate truth.
Selection is not execution.
Selection is not workflow advancement by momentum.

Legacy `no_selection` language is treated here as archival drift.
Canonical whole-Jeff non-selection is `reject_all`, `defer`, or `escalate`.
Legacy investigate-first behavior belongs in proposal as an investigation or clarification option, not as a rival selection outcome.

# Proposal-to-Selection Handoff

What passes from proposal to selection is bounded decision input, not authority.

The handoff must preserve:
- the serious option set, including an honestly empty set when that is the truth
- option summaries and bounded scope framing
- material assumptions
- material risks
- coarse feasibility and reversibility signals when relevant
- planning-needed markers when the option would require structured multi-step work
- relevant visible constraints already surfaced in context
- proposal scarcity reasons, suppression reasons, or incompleteness markers when they matter

What does not pass:
- permission
- action-entry clearance
- approval
- readiness
- execution authority
- truth mutation authority

Proposal rationale may pass as inspectable input.
It must not arrive as hidden decision authority.
Selection must judge the handoff under current truth rather than inheriting proposal confidence or proposal phrasing as a verdict.

# Rationale Requirements

Rationale must be inspectable and bounded.
It must not become essay spam.

Every serious proposal must make explicit:
- why the option exists
- why it matters now
- the main assumptions it relies on
- the main risks or blockers that shape it
- the reason it is included instead of suppressed
- the reason for scarcity when the set contains fewer than two serious options

Every selection result must make explicit:
- what was selected or which non-selection outcome occurred
- the strongest reasons behind that disposition
- the most important alternative or alternatives and why they did not win
- the decisive constraints, uncertainty, or conflict that materially shaped the result
- any downstream caution that still matters

`reject_all`, `defer`, and `escalate` each require explicit rationale.
Non-selection outcomes are not vague fallback labels.

# Risk / Assumption Handling

Proposal must surface material assumptions and material risks.
Selection must account for them honestly.

The decision-layer law is:
- assumptions must stay visible enough to challenge
- risk must stay visible enough to shape choice
- hidden assumptions and hidden risks invalidate disciplined decision-making
- coarse feasibility matters, but it must not silently become readiness
- risk handling in selection is comparative judgment, not governance permission

High-risk, blocker-heavy, or under-specified options may legitimately lead to:
- reject all
- defer
- escalate
- planning insertion instead of immediate operationalization
- investigation or clarification being selected over direct action

Selection must not force an action-shaped choice just because action looks like progress.

# Forbidden Collapses

The following collapses are forbidden:
- `proposal = decision`
- `proposal = plan authority`
- `proposal = governance`
- `selection = permission`
- `selection = readiness`
- `selection = approval`
- `selected option = action permission`
- `selection = execution`
- `selection = workflow progression`
- `selection rationale = approval rationale`
- `planning = mandatory stage`
- `plan existence = choice authority`
- `plan review = permission`
- `workflow progression = permission`
- `proposal count quota = quality`
- fake alternative generation to satisfy process
- context doing hidden proposal work
- context doing hidden selection work
- proposal laundering blocked or weak options into apparently clean choices
- selection doing hidden governance work
- governance doing hidden selection work
- feasibility judgment secretly becoming readiness
- risk judgment secretly becoming approval law
- proposal or selection mutating truth

# Invariants

The following invariants are binding:
- proposal may honestly return 0 to 3 serious options
- fake alternatives are forbidden
- proposal scarcity is preferable to fake diversity
- selection may choose one option or honestly choose none through `reject_all`, `defer`, or `escalate`
- selection never implies permission
- proposal and selection remain distinct
- proposal and selection never mutate truth
- proposal and selection do not own governance
- proposal and selection do not own execution
- proposal and selection reason within one global canonical state with nested projects
- `project`, `work_unit`, and `run` remain the foundational scope containers for decision work
- project remains the hard isolation boundary for proposal and selection scope
- planning is conditional, not universal
- selection may inform later `action`, but it is not `action`
- workflow is not first-class canonical truth in v1
- transitions remain the only canonical truth mutation contract
- proposal and selection may consume committed memory support, but only Memory creates memory candidates
- Jeff-project work and non-Jeff project work use the same proposal-and-selection law

# Failure Modes

Proposal/selection is failing if any of the following happens:
- proposal inflation
- fake diversity
- one-option bias disguised as reasoning
- forced two-option padding
- selection-as-permission collapse
- selection flattening into "pick the first plausible thing"
- forced choice where reject-all, defer, or escalate was more honest
- planning inflation back into every task
- selection secretly becoming a proto-planner
- context secretly doing proposal or selection work
- hidden governance inside selection
- rationale theater with no real basis
- underexplained non-selection outcomes
- major alternatives disappearing with no why-not basis
- proposal confidence laundering itself into decision confidence
- feasibility quietly becoming readiness
- plan or workflow momentum overriding honest choice
- support polish overpowering actual truth and constraints

# v1 Enforced Decision Layer

Whole-Jeff law is broader than v1 implementation detail, but v1 must enforce enough to stop fake-option drift, decision blur, and permission leakage.

v1 enforces:
- an explicit `context -> proposal -> selection` decision path
- honest proposal cardinality of 0 to 3 serious options
- no minimum-two-options quota
- bounded option shapes sufficient to distinguish at least direct action, bounded research or clarification, planning insertion, defer, and escalate when relevant
- visible assumptions, risks, and current constraint markers on serious options
- a selection result that either chooses one option or returns a typed non-selection outcome
- `reject_all`, `defer`, and `escalate` as real outcomes rather than vague failure text
- concise but inspectable rationale for proposals and selection results
- explicit separation between selection and governance
- no approval or readiness output from selection
- no truth mutation by proposal or selection
- the default downstream law that a selected path informs `action`, then governance determines approval and readiness before execution
- conditional planning insertion only when work shape actually needs multi-step or high-risk structuring
- workflow is not a first-class canonical truth driver at the decision layer in v1

v1 does not require:
- a giant option taxonomy
- a heavy scoring engine
- a universal planning stage
- a universal action framework at decision time
- decision traces beyond what is needed for honest rationale

# Deferred / Future Expansion

Deferred expansion may later include:
- richer option typing if real implementation pressure justifies it
- stronger historical feedback into proposal quality without turning memory into a hidden chooser
- richer comparison support for close tradeoffs
- better planning-insertion heuristics for multi-step or review-heavy work
- more explicit decision-support artifacts when they improve inspection without duplicating governance or interface ownership

These are future refinements.
They do not change the current law that proposal stays scarce and selection stays non-permissive.

# Questions

No unresolved proposal/selection questions were found in this pass.

# Relationship to Other Canonical Docs

This document depends on other canonical docs without duplicating their ownership:

- `ARCHITECTURE.md` defines the whole-Jeff backbone and the placement of proposal, selection, `action`, governance, and execution
- `GLOSSARY.md` defines the hard meanings of proposal, selection, planning, governance, approval, readiness, and `action`
- `CONTEXT_SPEC.md` owns truth-first input assembly for proposal and selection
- `POLICY_AND_APPROVAL_SPEC.md` owns permission, approval, readiness, and action-entry governance
- `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` owns the scope containers across which the same decision law applies
- `STATE_MODEL_SPEC.md` and `TRANSITION_MODEL_SPEC.md` keep proposal/selection non-mutating and downstream of truth discipline
- `CORE_SCHEMAS_SPEC.md` owns shared envelopes, typed naming, and schema discipline
- `MEMORY_SPEC.md` owns memory-candidate creation and canonical memory-link discipline; proposal and selection may consume committed memory support through context but do not create memory candidates or canonical memory truth
- `PLANNING_AND_RESEARCH_SPEC.md` owns plan artifacts, review/update law, workflow composition, and research discipline; this document owns only when planning insertion is a legitimate decision outcome
- `EXECUTION_OUTCOME_EVALUATION_SPEC.md` owns the post-selection action, execution, outcome, and evaluation chain

# Final Statement

Jeff's decision layer is only trustworthy if it can do two things honestly:
- generate only the serious options that actually exist
- choose one, or choose none, without smuggling in permission or fake certainty

That is the law established here.
Proposal stays scarce, selection stays explicit, planning stays conditional, governance stays separate, and truth changes only later through transitions.
