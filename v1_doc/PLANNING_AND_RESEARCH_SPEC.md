# Purpose

This document defines Jeff's canonical planning-and-research law.

It owns:
- the research model
- research artifact rules
- research quality rules
- research-to-proposal handoff law
- the planning model
- plan artifact rules
- plan review and update rules
- workflow composition rules for planning/research support
- evidence and provenance requirements for planning/research outputs
- planning/research invariants, boundaries, and anti-patterns

It does not own:
- governance semantics
- selection semantics
- execution semantics
- transition lifecycle or commit law
- interface display contracts
- telemetry schemas
- test matrices
- roadmap sequencing

This is the canonical bounded planning-and-research document for Jeff as a whole.
It is not a vague essay about why research or planning matter.
It is not an implementation-status note.
It is not a rival authority for governance, execution, orchestration, or truth mutation.

# Canonical Role in Jeff

Research reduces uncertainty through bounded, source-aware inquiry.
Planning structures multi-step, review-heavy, high-risk, or time-spanning work only when that structure is actually needed.

Research and planning operate inside one global canonical state with nested projects.
Project remains the hard isolation boundary.
`project + work_unit + run` remain the foundational containers that bound planning/research scope.

Jeff cannot tolerate:
- browsing sludge instead of bounded research
- provenance loss during synthesis
- findings, inference, and recommendation collapsing into one blob
- universal planning bureaucracy
- plan-as-authority drift
- workflow or plan artifacts quietly becoming a rival orchestrator or truth layer

Research and planning exist to improve later reasoning and later action shape.
They do not become current truth, permission, or execution by themselves.

# Core Principle

The binding law is:
- research must be bounded, source-aware, and evidence-disciplined
- planning is conditional and structural, not universal and not self-authorizing
- neither research nor planning mutates canonical truth
- neither research nor planning grants permission
- approval and readiness remain governance objects, not planning or research outputs
- both must stay inspectable, subordinate, and consumable by downstream modules without guesswork

Research informs.
Planning structures.
Selection chooses.
Governance permits.
Execution acts.
Transitions mutate truth.

# Research Model

Research is bounded inquiry performed to answer a bounded question or satisfy a bounded uncertainty-reduction objective.

Research exists to:
- answer a specific question
- compare bounded alternatives
- test or narrow assumptions
- identify contradictions, missing information, and limitations
- produce evidence-backed direct outputs
- supply proposal, planning, evaluation, or operator review with stronger support

Research must begin from:
- a bounded question or bounded objective
- explicit scope
- current truth and current constraints read first

Research should then proceed through a disciplined flow:
- define what evidence would matter
- gather sources appropriate to the question
- compare sources where comparison matters
- extract evidence rather than just collect material
- synthesize findings in source-aware form
- separate findings from inference
- surface contradiction and uncertainty explicitly
- produce a bounded output or bounded handoff

Source gathering law:
- use source classes explicitly rather than one blended bucket
- prefer authoritative internal truth for current-state questions
- use external sources when the question actually requires them
- treat memory as support or clue context, not as primary evidence
- stay within the smallest sufficient scope and budget

Source comparison law:
- comparison is required when multiple sources, options, or conflicting claims matter to the question
- comparison must preserve which source supports which point
- comparison must keep contradiction visible rather than smoothing it away
- comparison may legitimately conclude that no strong winner exists

Source-aware synthesis law:
- synthesis must stay tied to the original question or objective
- synthesis must preserve provenance
- synthesis must show what is supported, what is inferred, and what remains uncertain
- synthesis must not turn citation volume into fake certainty

Findings, inference, and recommendation are distinct:
- findings are direct evidence-backed statements
- inference is interpretation drawn from findings
- recommendation is a suggested next step derived from findings and inference

Research supports two legitimate output shapes:
- direct-output research
  A bounded research brief, comparison, or memo may be the final deliverable for the work unit, including non-Jeff project work.
- research-for-decision support
  Research may feed proposal, planning, evaluation, or operator review through explicit artifacts and explicit uncertainty handling.

Research is not:
- truth mutation
- selection
- governance
- generic browsing
- a substitute for context
- a substitute for execution or evaluation

The same research law applies to Jeff-project work and non-Jeff project work.
The project domain changes.
The boundedness, provenance, and evidence rules do not.

# Research Artifact Rules

Research artifacts are durable support objects that preserve bounded research results without pretending to be truth.

Canonical research artifact families may include:
- source list or source refs
- findings set
- comparison note
- bounded research brief
- recommendation memo
- uncertainty register
- bounded source-aware synthesis artifact

Every meaningful research artifact should make explicit:
- question or objective
- scope
- relevant source refs
- findings
- inference
- contradiction or uncertainty
- freshness or current-truth fit where relevant
- recommendation or next-step implication only if justified
- unresolved items

Research artifact rules:
- provenance must survive from source to evidence to finding to synthesis
- raw source bodies should usually be linked, not dumped
- artifacts are support, not current truth by default
- artifacts must not silently become plans, decisions, governance objects, or canonical truth
- artifacts must not hide whether a statement is evidence, finding, inference, or recommendation
- artifacts may support approval or plan review conversations, but do not become approval or plan authority
- research artifacts may later inform memory writing, but only Memory creates memory candidates and canonical state may reference only committed memory IDs

# Research Quality Rules

Research quality is about epistemic cleanliness and downstream safety, not polish.

Quality requirements:
- bounded scope
- question quality good enough to avoid topic drift
- relevant source coverage rather than source count inflation
- authoritative sources used for the kind of question asked
- provenance preserved
- evidence extracted and claim-bounded
- findings distinguished from inference
- contradictions surfaced honestly
- uncertainty preserved
- recommendations proportional to support
- freshness and current-truth fit checked where relevant
- output usable by downstream modules without uncertainty laundering

Research must reject:
- fake certainty
- source laundering
- source dumping as substitute for synthesis
- citation theater
- memory-as-primary-evidence
- inference-as-finding
- contradiction suppression
- recommendation inflation
- endless research with no sufficiency rule

High-quality inconclusive research is valid.
Low-quality confident research is not.

# Research-to-Proposal Handoff

Research may hand bounded support into proposal generation and later decision support.

What may pass:
- findings
- inference
- uncertainty
- contradiction notes
- comparison results
- bounded recommendation candidates
- provenance-aware support
- missing-information markers
- freshness or current-truth-fit cautions

What must not pass:
- truth mutation authority
- governance permission
- hidden decision authority
- silent scope expansion
- fake closure

Handoff rules:
- proposal must consume research as decomposed support, not as one blended blob
- proposal generation may still honestly return 0 to 3 serious options after consuming research
- research quality and freshness constrain what proposal may honestly generate
- weak or stale research may justify only investigation, defer, or escalate paths
- research may suppress options as well as support them
- research may narrow proposal shape, but does not replace proposal generation

# Planning Model

Planning is the conditional construction of bounded intended work structure after a selected path or other already-fixed bounded objective needs multi-step coordination.

Selection chooses the path.
Selection does not grant execution permission.
Planning may structure the selected or already-fixed path, but it does not turn that path into lawful execution by itself.

Planning is legitimate when:
- work is multi-step
- work is review-heavy
- work is high-risk
- work spans time and needs bounded continuation support
- dependencies, checkpoints, or decomposition need to be made explicit
- operator explicitly asks for a plan

Planning is not legitimate when:
- no serious path exists yet
- uncertainty still requires research first
- blockers make sequencing premature
- the work is obviously bounded enough to proceed without plan overhead

Planning should express:
- bounded objective
- intended ordered steps or phases
- assumptions
- dependencies
- risks
- checkpoints or review points
- blockers where relevant
- stop conditions
- invalidation conditions

Planning is support structure, not authority.
It may refine later action shape.
It does not replace selection, governance, execution, or transition law.
`action` remains the narrow transient operational object family between selection or planning and governance, not a synonym for plan or workflow.

Planning is not:
- mandatory
- governance
- orchestration
- workflow truth in v1
- a hidden execution queue
- a roadmap for everything

A plan does not authorize action.

# Plan Artifact Rules

Plan artifacts are inspectable support objects representing intended bounded work.

A plan artifact should express:
- bounded objective
- scope
- origin basis such as selected path, operator instruction, or relevant research support
- ordered intended steps or phases
- assumptions
- risks
- dependencies or blockers where relevant
- checkpoints or review points
- stop conditions
- invalidation conditions
- revision or supersession possibility

Plan artifact rules:
- plan artifacts are support objects, not current truth
- current truth always outranks plan intent
- plan artifacts may inform later action formation, but do not become action by default
- plan artifacts may recommend decomposition into work units, but do not mutate work-unit truth by themselves
- materially new plans should supersede old plans rather than silently overwrite them
- plan artifacts must stay bounded enough that downstream consumers do not have to guess what is meant

Jeff v1 does not require a heavy universal plan object bureaucracy.
It does require that any real plan remain structured, bounded, and inspectable.

# Plan Review / Update Rules

Plans may be reviewed or updated whenever bounded work structure needs fitness checking against current truth.

Plan review should check at least:
- structural completeness
- boundedness
- scope fit
- current-truth fit
- direction fit
- blocker awareness
- assumption burden
- dependency realism
- checkpoint sufficiency
- stop and invalidation sufficiency

Plan review rules:
- plan review is not approval
- plan review is not readiness
- plan review is not re-selection
- a positively reviewed plan may still fail later governance or readiness

Plan update rules:
- non-semantic fixes may be recorded in place
- meaningful same-plan changes must stay inspectable and may require re-review or revalidation
- material change requires supersession or invalidation rather than silent rewrite
- stale, blocked, or truth-misaligned plans require re-review, revalidation, supersession, or invalidation
- plans must remain revisable when reality changes

Plan revision must never silently rewrite:
- current truth
- permission
- review history
- strategic basis

If the objective, scope, or governing assumptions change materially, Jeff must not pretend it is still the same plan.

# Workflow Composition Rules

Planning and research may compose bounded work, but they must not become hidden orchestration.

Binding rules:
- workflow may remain a supporting coordination concept
- workflow is not first-class canonical truth in v1
- research artifacts may feed later proposal, planning, evaluation, or operator review
- plan artifacts may structure intended steps, checkpoints, and dependencies
- orchestration still owns sequencing
- governance still owns permission
- transitions still own truth mutation

Composition rules:
- research may lead to direct output, proposal input, or planning input
- planning may shape later action candidates, checkpoints, or decomposition suggestions
- review points and revalidation points may be explicit planning support concepts
- bounded work may terminate, defer, re-research, replan, or escalate honestly

Forbidden composition drift:
- plan artifacts acting like workflow truth in v1
- research artifacts directly selecting or authorizing work
- plan review being treated as approval
- workflow progression being treated as readiness or permission
- planning/research artifacts carrying hidden orchestration logic

# Boundaries Against Universal Planning

Planning is conditional, not universal.

Jeff must explicitly forbid:
- planning every task by default
- forcing plan creation for obviously bounded simple work
- equating plan existence with seriousness or quality
- using planning to hide indecision
- using planning to postpone necessary research
- using planning to smuggle workflow truth back into v1
- using plan artifacts as permission or mutation authority

Simple bounded work may go:
- selection -> action -> governance -> execution

Planning belongs only where structure materially improves safety, continuity, or clarity.
No plan should exist just to satisfy process vanity.

# Evidence and Provenance Requirements

Source, evidence, finding, inference, recommendation, and provenance must remain distinct.

Binding requirements:
- source is the origin container
- evidence is claim-bounded support extracted from source(s)
- finding is a direct evidence-backed statement
- inference is interpretation drawn from findings
- recommendation is a suggested next step downstream of findings and inference
- provenance records where support came from and how it was transformed

Additional rules:
- provenance must survive synthesis
- contradiction must remain visible
- evidence must stay bounded to a question or claim
- recommendation must remain proportional to support
- source authority and freshness must be considered where relevant
- plan or research artifacts may cite sources and support, but do not become truth by citation alone

Planning-specific provenance:
- if a plan depends on research, that dependency should remain visible
- if a plan rests on assumptions rather than findings, that distinction must remain visible
- if a plan inherits stale or contradicted support, review or revalidation is required

# Failure Modes / Anti-Patterns

The planning/research layer is failing if any of the following happens:
- research-as-browsing-sludge
- provenance loss
- source dumping instead of synthesis
- citation theater
- findings, inference, and recommendation collapse
- memory or summary acting as primary evidence
- contradiction erasure
- fake certainty
- recommendation inflation
- research artifacts treated as truth
- research artifacts treated as hidden decisions
- plan inflation
- universal planning bureaucracy
- plan-as-authority drift
- plan-as-truth drift
- silent plan rewrite
- stale plan reuse without review
- workflow inflation through plan artifacts
- planning or research becoming hidden orchestrator logic
- plan review treated as governance
- workflow progression treated as permission
- planning replacing selection
- planning replacing work-unit or run semantics

# v1 Initial / Conditional Scope

v1 enforces enough planning/research law to stop drift without overbuilding.

v1 enforces:
- bounded research question or objective
- truth-first framing before wider evidence gathering
- explicit source-aware support rather than generic browsing output
- distinction between source, evidence, finding, inference, recommendation, and provenance
- bounded research artifacts that preserve uncertainty and contradiction
- research support usable by proposal without uncertainty laundering
- planning as conditional rather than universal
- plan artifacts as bounded support objects when plans are actually used
- explicit assumptions, dependencies, review points, and invalidation conditions for real plans
- explicit re-review or revalidation when plans go stale or materially change
- workflow remaining support-only rather than first-class canonical truth
- no permission or truth mutation from research or planning artifacts

v1 does not require:
- a first-class workflow truth object
- a universal plan for every selected path
- giant planning or research taxonomies
- heavy artifact-status bureaucracies
- hidden orchestration semantics inside planning support

# Deferred / Future Expansion

Deferred expansion may later add:
- richer source-comparison frameworks
- stronger research artifact families
- stronger research quality grading or review outputs
- richer long-running continuation planning
- richer plan revision and supersession lineage
- more expressive checkpoint and revalidation support
- more advanced workflow support only if workflow is later explicitly promoted

Deferred expansion does not weaken current law.
Future richness must still preserve boundedness, provenance, conditional planning, and separation from governance, orchestration, and truth mutation.

# Questions

No unresolved planning/research questions were found in this pass.

# Relationship to Other Canonical Docs

- `ARCHITECTURE.md` owns the structural backbone that places research and planning in the Cognitive layer, keeps planning conditional, and keeps workflow non-first-class in v1.
- `GLOSSARY.md` owns the canonical meanings of research, source, evidence, finding, inference, recommendation, planning, workflow, action, approval, and readiness.
- `CONTEXT_SPEC.md` owns truth-first input assembly and source priority before research begins.
- `PROPOSAL_AND_SELECTION_SPEC.md` owns option generation and choice; this document governs how research feeds proposal and how planning may legitimately follow selection.
- `POLICY_AND_APPROVAL_SPEC.md` owns approval, readiness, and permission boundaries; this document makes explicit that planning and research do not grant permission.
- `STATE_MODEL_SPEC.md` owns truth placement; this document keeps research and planning subordinate to current truth.
- `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` owns the persistent container model; this document allows planning and research to support both Jeff and non-Jeff project work within that container law.
- `CORE_SCHEMAS_SPEC.md` owns shared schema primitives; this document does not redefine low-level machine contracts.
- `TRANSITION_MODEL_SPEC.md` owns truth mutation law; this document forbids research and plan artifacts from becoming mutation authority.
- `VISION.md` owns the product-level need for bounded research, source-aware outputs, and conditional planning.

# Final Statement

Jeff research is bounded, source-aware uncertainty reduction.
Jeff planning is conditional, structural support for bounded work that genuinely needs it.

Neither becomes truth.
Neither becomes permission.
Neither becomes hidden orchestration.

If these laws stay hard, Jeff can support evidence-backed research and disciplined multi-step work for both Jeff projects and non-Jeff projects without collapsing into browsing sludge, workflow bureaucracy, or plan-driven pseudo-authority.
If they soften, the system will start confusing support with truth and structure with permission.
