# Purpose

This document defines Jeff's canonical execution-outcome-evaluation law.

It owns:
- the execution model
- the outcome model
- the evaluation model
- stage boundaries between execution, outcome, and evaluation
- evidence rules for the action/judgment layer
- deterministic override rules for the action/judgment layer
- bounded recommended next-step outputs
- the bounded verdict model used by outcome and evaluation
- failure, degradation, and inconclusive handling at the action/judgment layer
- recovery and revalidation recommendation boundaries
- execution/outcome/evaluation invariants and failure modes

It does not own:
- governance semantics
- approval or readiness meaning
- transition lifecycle or truth-mutation law
- interface display contracts
- telemetry schemas
- test matrices
- roadmap sequencing

This is the canonical post-governance action / observed-result / judgment document for Jeff as a whole.
It is not an implementation-status note.
It is not a vague essay about acting and judging.
It is not a rival authority for governance, recovery orchestration, or transition law.

# Canonical Role in Jeff

This layer starts only after lawful action entry.
Execution begins only when governance allows the bounded `action`.
From there, Jeff must keep doing, observed result, and judgment separate.

Jeff still operates inside:
- one global canonical state with nested projects
- project as a hard isolation boundary inside that state
- `project + work_unit + run` as the foundational scope containers for this layer

Upstream of this layer:
- planning is conditional, not universal
- workflow is not first-class canonical truth in v1
- `action` remains the narrow transient operational object family between selection/planning and governance
- approval and readiness remain governance objects

Jeff cannot tolerate:
- execution claiming truth
- execution claiming success it cannot know
- outcome claiming judgment
- evaluation claiming permission
- evaluation claiming mutation
- artifacts or traces pretending to be truth
- degraded or inconclusive results being smoothed into clean success

This document keeps the post-governance chain hard:
- execution performs bounded governed action
- outcome states what was observed in normalized form
- evaluation judges what that observed result means against goals, constraints, evidence, and direction

# Core Principle

The binding law is:
- execution performs bounded governed action
- outcome states the normalized observed result of that action
- evaluation judges that result against objective, direction, constraints, and evidence
- none of these stages mutate canonical truth by themselves
- none of these stages replace governance
- only transitions mutate canonical truth

Execution acts.
Outcome records what happened in bounded normalized form.
Evaluation judges what that means.
That separation is not optional.

# Execution Model

Execution is the bounded performance of a governed `action`.

`action` is the narrow transient operational object family between selection/planning and governance.
Execution does not create rival action authority.

Execution begins only after governance allows the action.
Execution consumes governed action, not raw proposal and not raw plan.
Proposal and planning may shape action formation upstream.
They are not execution authority.

Execution may use:
- tools
- model assistance
- external systems
- bounded operational adapters
- bounded research or verification mechanisms when the governed action requires them

Execution should produce bounded operational residue such as:
- raw outputs
- artifact refs
- trace refs
- observed side-effect residue
- timing and environment facts that matter to interpretation
- local execution errors, warnings, interruption markers, and execution-local status

Execution-local status is operational only.
It may distinguish states such as:
- `pending_start`
- `running`
- `completed`
- `completed_with_degradation`
- `failed`
- `interrupted`
- `aborted`

Execution does not claim:
- that the objective was achieved
- that the result is acceptable
- that the result became truth
- that permission still exists for future action

Execution may fail, partially complete, degrade, or terminate early.
It must surface that honestly rather than smoothing it into eventual-looking success.

Execution is not:
- governance
- truth mutation
- outcome normalization
- evaluation
- workflow truth in v1

# Outcome Model

Outcome is the normalized observed result of execution.

Outcome exists because raw execution residue is too low-level and execution-local status is too narrow to support honest judgment.
Outcome sits strictly between execution result and evaluation.

Outcome turns raw execution residue into a bounded observed-result representation that may include:
- observed completion posture
- target effect posture
- artifact posture
- observed side effects
- uncertainty markers
- contradiction markers
- mismatch markers where relevant
- evidence bundle pointers
- restoration or consistency posture where relevant

Outcome should preserve operational meaning without claiming normative adequacy.
Examples of outcome-layer content include:
- target unchanged
- target changed partially
- required artifact missing
- side effects widened beyond intended surface
- verification evidence incomplete
- result affected by truth mismatch

Outcome is not:
- evaluation
- governance
- transition
- current truth

Outcome may legitimately be:
- `complete`
- `partial`
- `degraded`
- `blocked`
- `failed`
- `inconclusive`
- `mismatch_affected`

Outcome may also carry interruption or recovery-relevant notes when that operational fact matters, but it must remain a normalized observed-result object rather than a trace dump or verdict essay.

# Evaluation Model

Evaluation is the bounded judgment of what the outcome means.

Evaluation judges outcome against:
- the bounded objective
- direction
- constraints
- evidence quality and provenance
- blockers where relevant
- degraded conditions where relevant
- mismatch conditions where relevant

Evaluation should answer:
- was the result acceptable for its bounded purpose
- what prevented a stronger judgment
- what uncertainty remains
- what bounded next step should be recommended

Evaluation may produce:
- an `evaluation_verdict`
- bounded rationale
- bounded recommended next-step output
- decisive negatives and cautions

Evaluation does not:
- mutate canonical truth
- grant permission
- replace governance
- replace transitions
- replace recovery semantics

Evaluation recommendations are downstream support only.
If a new action is needed, governance still owns permission for that action.
Evaluation may later inform memory work, but only Memory creates memory candidates and canonical state may reference only committed memory IDs.

# Stage Boundaries

The stage boundary law is:
- execution performs
- outcome normalizes what was observed
- evaluation judges what that means

Execution -> Outcome handoff must preserve:
- raw outputs
- artifacts
- trace refs
- observed effects
- execution-local failure, degradation, interruption, and warning facts

Outcome -> Evaluation handoff must preserve:
- normalized observed result
- evidence linkage
- artifact posture
- unresolved or contradictory observations
- uncertainty and mismatch markers

Evaluation -> downstream handoff may include:
- verdict
- rationale
- recommended next step

It must not include:
- permission
- truth mutation authority
- hidden governance decision

Traces and artifacts are support outputs, not truth.
Outcome is not evaluation.
Evaluation is not transition.
Evaluation recommendation is not permission or mutation.

# Evidence Rules

Execution may produce evidence-bearing residue.
That includes artifacts, traces, logs, raw outputs, and observed side-effect facts.

Outcome must preserve enough evidence linkage that evaluation does not have to reconstruct meaning from raw logs alone.
At minimum, outcome should preserve:
- origin linkage to action and execution
- scope linkage to `project`, `work_unit`, and `run`
- artifact refs
- trace refs where needed
- observed facts tied to those refs
- unresolved and contradictory evidence markers where relevant

Evaluation must remain evidence-backed.
It must not:
- invent support
- infer success from artifact presence alone
- treat trace volume as progress
- use unsupported optimism to override missing or contradictory evidence

Evidence quality matters.
Provenance matters.
Missing evidence must remain visible.

Source, evidence, observation, outcome, verdict, and recommendation must remain distinct.
This law applies to Jeff-project work and non-Jeff project work alike.

# Deterministic Override Rules

Deterministic checks belong in the action/judgment layer as hard constraints on judgment.
They do not become transition validation law.

Their role is simple:
- hard failures cap or override softer evaluative optimism
- missing required evidence remains disqualifying where the bounded task depends on it
- explicit constraint violations cannot be rebranded as acceptable
- unresolved mismatch conditions cannot be smoothed into clean completion

Examples of deterministic overrides include:
- required artifact missing
- required verification missing
- explicit constraint violation observed
- bounded target not reached where that target is mandatory
- outcome marked `mismatch_affected` with unresolved critical mismatch
- evidence bundle insufficient for the specific claim being judged

Deterministic checks may force or cap disposition such that:
- `acceptable` or `acceptable_with_cautions` are unavailable
- `accept_as_complete` is unavailable
- only `partial`, `degraded`, `blocked`, `inconclusive`, `unacceptable`, or stronger downstream caution is honest

Deterministic override law does not mean:
- evaluation becomes transition validation
- evaluation decides what mutates truth
- every judgment becomes binary

It means Jeff may not talk itself past hard evidence.

# Recommended Next-Step Outputs

Evaluation may emit one bounded `recommended_next_step`.

The canonical whole-Jeff recommendation set is:
- `accept_as_complete`
- `continue`
- `retry`
- `revalidate`
- `recover`
- `escalate`
- `terminate_and_replan`
- `request_clarification`

These recommendations mean:
- `accept_as_complete`: the bounded objective is judged complete enough for closure or downstream transition consideration
- `continue`: the current bounded lineage may continue, subject to normal governance for any new action
- `retry`: repeat the bounded action or a tightened equivalent because the basis still stands but the observed result did not land cleanly
- `revalidate`: re-check prior basis, readiness, assumptions, or current-truth fit before more doing
- `recover`: initiate bounded recovery or containment because degraded or unsafe conditions remain
- `escalate`: operator or higher governance judgment is needed
- `terminate_and_replan`: current lineage should stop and a new bounded path should be formed
- `request_clarification`: missing objective, constraint, or judgment basis prevents honest continuation

These are recommendations only.
They do not authorize action.
They do not mutate truth.
They do not bypass governance.

# Verdict Model

Jeff uses expanded but bounded verdict posture.
It does not collapse result meaning into simple success/fail.
It also does not explode into taxonomy soup.

Outcome and evaluation use related but not identical fields:
- `outcome_state`
- `evaluation_verdict`

The canonical outcome-state family is:
- `complete`
- `partial`
- `degraded`
- `blocked`
- `failed`
- `inconclusive`
- `mismatch_affected`

Use them as follows:
- `complete`: observed execution result reached bounded operational completion with no material outcome-layer defect known
- `partial`: meaningful observed effect occurred, but full intended operational effect did not
- `degraded`: operational result exists, but meaningful degraded conditions remain
- `blocked`: observed result cannot honestly support forward use because an explicit blocker, missing required element, or unavailable condition remains decisive
- `failed`: bounded operational result did not achieve acceptable operational completion
- `inconclusive`: observed result exists, but evidence or observations are too weak or contradictory for a cleaner outcome state
- `mismatch_affected`: the observed result is materially affected by unresolved truth mismatch or equivalent trust degradation

The canonical evaluation-verdict family is:
- `acceptable`
- `acceptable_with_cautions`
- `partial`
- `degraded`
- `blocked`
- `inconclusive`
- `unacceptable`
- `mismatch_affected`

Use them as follows:
- `acceptable`: judged sufficient for the bounded objective without material unresolved defect
- `acceptable_with_cautions`: judged sufficient, but bounded cautions must remain visible
- `partial`: judged as meaningful but incomplete progress
- `degraded`: judged as real result with material degradation that matters to continuation or reuse
- `blocked`: judged unable to support honest continuation because a decisive blocker, missing basis, or hard condition remains
- `inconclusive`: judged too uncertain for a stronger verdict
- `unacceptable`: judged not acceptable for the bounded objective or downstream use
- `mismatch_affected`: judged under active truth-mismatch or equivalent trust degradation such that normal clean verdicting would be dishonest

Alignment rules:
- outcome uses descriptive observed-result language, not acceptability language
- evaluation uses judgment language, not execution-completion language
- `complete` is not an evaluation verdict
- `acceptable` is not an outcome state

# Failure / Degradation / Inconclusive Handling

Jeff must surface degraded, partial, interrupted, contradictory, and inconclusive results honestly.

This layer must handle:
- partial completion
- degraded results
- interrupted execution
- evidence gaps
- contradictory observations
- mismatch-affected results
- inconclusive judgment

Handling law:
- partial does not become acceptable by default
- degraded does not become silently usable
- inconclusive is not pass
- mismatch-affected result must remain visibly trust-degraded
- contradictory evidence reduces confidence and may force `inconclusive`, `blocked`, `degraded`, or `mismatch_affected`

This layer may recommend:
- `retry`
- `revalidate`
- `recover`
- `escalate`
- `terminate_and_replan`

It does not authorize any of them.
It does not commit recovery.
It does not commit truth.

# Recovery / Revalidation Boundaries

Evaluation may recommend:
- recovery
- revalidation
- escalation
- retry
- terminate-and-replan

Those are downstream recommendations.
They do not become self-executing workflow authority.

Boundary law:
- governance still owns permission for any new action entry
- transitions still own truth mutation
- recovery and revalidation recommendations do not bypass governance
- recovery activity does not self-certify restored truth
- revalidation does not become implicit because the system wants momentum

If recovery or revalidation is needed, Jeff must say so explicitly.
If governance is needed afterward, Jeff must still go through governance.

# Forbidden Collapses

The following collapses are forbidden:
- `execution = truth`
- `execution = success judgment`
- `outcome = evaluation`
- `outcome = truth`
- `evaluation = transition`
- `evaluation = governance`
- `evaluation recommendation = permission`
- `artifact existence = success`
- `trace volume = progress`
- `partial result = acceptable by default`
- `degraded result = silently usable`
- `execution residue = canonical truth`
- `execution_status = outcome_state`
- `outcome_state = evaluation_verdict`
- `completed_with_degradation = clean success`
- `inconclusive = pass`
- `recovery activity = restored or acceptable by default`
- `rolled_back = restored_verified`

# Invariants

The following invariants are binding:
- Jeff has one global canonical state with nested projects
- project is the hard isolation boundary inside that state
- `project + work_unit + run` remain the foundational scope containers for this layer
- planning is conditional, not universal
- workflow is not first-class canonical truth in v1
- execution starts only after governance allows the relevant action
- execution does not self-authorize
- execution does not mutate truth
- outcome remains distinct from execution and evaluation
- evaluation remains distinct from governance and transition
- recommendations remain recommendations
- evidence matters
- provenance matters
- deterministic hard failures cannot be softened away
- artifacts and traces remain support layers rather than truth layers
- transitions remain the only canonical truth mutation contract
- `action` remains the narrow transient operational object family between selection/planning and governance
- approval and readiness remain governance objects, not execution or evaluation outputs
- only Memory creates memory candidates
- canonical state may reference only committed memory IDs
- Jeff-project and non-Jeff project work use the same action/judgment law

# Failure Modes

The execution/outcome/evaluation layer is failing if any of the following happens:
- execution claims success it cannot know
- execution, outcome, and evaluation collapse into one blob
- generic status flattening hides important distinctions
- artifact presence is mistaken for task success
- evaluation optimism overrides hard failure
- recommendation blurs into permission
- degraded or inconclusive results are hidden behind clean summaries
- traces, raw outputs, or artifacts are treated as truth
- recovery or rollback is presented as clean restoration without verification
- post-hoc rationalization replaces evidence-backed judgment
- workflow momentum quietly overrides evaluation or revalidation need

# v1 Enforced Action/Judgment Model

v1 enforces enough of the whole-Jeff model to stop fake clarity and stage drift.

v1 enforces:
- one global canonical state with nested projects as the truth backdrop for all execution, outcome, and evaluation scope
- project as the hard isolation boundary for this layer's work
- `project + work_unit + run` as the foundational scope containers
- execution begins only from governed action entry
- execution emits explicit operational residue rather than verdict theater
- execution keeps `execution_status` distinct from `outcome_state`
- outcome produces explicit normalized observed result with evidence linkage
- evaluation produces explicit `evaluation_verdict`, rationale, and one bounded `recommended_next_step`
- outcome and evaluation use expanded but bounded verdict families rather than binary success/fail only
- deterministic hard failures cap what evaluation may honestly conclude
- artifacts, traces, and raw outputs remain support objects, not truth
- recovery and revalidation may be recommended but are not self-authorizing
- planning remains conditional rather than universal
- workflow remains non-first-class canonical truth in v1 and cannot smuggle authority into this layer
- transitions remain the only truth mutation path

v1 does not require:
- a giant execution routing taxonomy
- deep historical evaluation scoring
- a heavy universal recovery engine in this document
- interface-specific rendering contracts

# Deferred / Future Expansion

Deferred expansion may later add:
- richer execution routing families and environment classes
- stronger outcome normalization families for different action types
- richer evaluation comparison across historical runs
- better recovery recommendation models
- more expressive artifact and evidence support structures
- stronger evaluation lineage and rationale families

Deferred expansion does not weaken current law.
Execution still does not become truth.
Outcome still does not become evaluation.
Evaluation still does not become governance or transition law.

# Questions

No unresolved execution/outcome/evaluation questions were found in this pass.

# Relationship to Other Canonical Docs

- `ARCHITECTURE.md` owns the system backbone that places action, governance, execution, outcome, evaluation, memory, and transition in order.
- `GLOSSARY.md` owns the canonical meanings of `action`, `execution`, `outcome`, `evaluation`, `evidence`, `recommendation`, `approval`, and `readiness`.
- `POLICY_AND_APPROVAL_SPEC.md` owns approval, readiness, and permission semantics. This document assumes governance has already allowed action entry.
- `TRANSITION_MODEL_SPEC.md` owns truth mutation law. This document keeps execution, outcome, and evaluation non-mutating.
- `CORE_SCHEMAS_SPEC.md` owns shared schema naming law, including `execution_status`, `outcome_state`, and `evaluation_verdict`.
- `PROPOSAL_AND_SELECTION_SPEC.md` owns option generation and choice. This document begins after governed action entry, not at decision time.
- `PLANNING_AND_RESEARCH_SPEC.md` owns bounded research and conditional planning. This document only governs the post-governance action / observed-result / judgment chain.
- `CONTEXT_SPEC.md` owns truth-first context assembly and evidence input preparation for later stages.
- `STATE_MODEL_SPEC.md` and `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` own truth placement and work-container scope that this layer must respect.

# Final Statement

Jeff's post-governance action/judgment chain is hard by design:
execution performs bounded governed action, outcome states what was observed in normalized form, and evaluation judges what that means.

None of those stages grant permission.
None of those stages mutate truth.
None of those stages may smooth degraded, partial, inconclusive, or mismatch-affected reality into clean success.

If this law stays hard, Jeff can act, observe, and judge honestly in both Jeff-project and non-Jeff project work.
If it softens, Jeff will collapse into execution theater, artifact-as-success drift, and fake post-hoc certainty.
