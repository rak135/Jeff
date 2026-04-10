# Purpose

This document defines Jeff's canonical context-assembly law.

It owns:
- context inputs
- context source families
- source priority rules
- filtering rules
- ranking rules
- the high-level context output contract
- truth-first assembly rules
- memory retrieval constraints for context use
- context boundaries
- context failure modes
- the distinction between whole-Jeff context, the v1 enforced context model, and deferred expansion

It does not own:
- proposal logic
- selection logic
- evaluation logic
- transition lifecycle or commit law
- interface display contracts
- telemetry schemas
- test matrices
- roadmap sequencing

This is the canonical truth-first context-assembly document for Jeff as a whole.
It is not an implementation-status note, not a vague essay about why context matters, and not a hidden replacement for research, proposal, planning, governance, or interface specs.

# Canonical Role in Jeff

Context is how Jeff assembles the bounded information package needed for one current reasoning or action-preparation purpose.

Jeff cannot tolerate:
- dump-based context
- memory-first context
- trace-first context
- interface/session context pretending to be canonical focus
- support layers silently replacing current truth

If context becomes a raw archive, downstream cognition stops being trustworthy.
If memory or artifacts frame reality before current truth is read, Jeff starts reasoning from drift.
If context quietly absorbs decision, evaluation, or workflow logic, Jeff stops having inspectable stage boundaries.
This document exists to keep context assembly disciplined so the rest of Jeff reasons from the right truth, the right scope, and only the support material that actually matters now.

# Core Principle

Context is selected, not collected.

Context must be:
- truth-first
- bounded
- scoped
- purpose-built
- source-labeled

Planning is conditional, not universal.
Context assembly may support planning when the work shape needs it.
It does not assume that every bounded task passes through planning.

Context is not:
- a raw archive
- a hidden reasoning stage
- a covert decision engine
- a workflow dump
- a session cache

# Context Inputs

Context assembly takes a bounded request.
At the conceptual level, the main input classes are:

- current trigger or operator input
  The live request, objective, question, or bounded task frame.
- current assembly purpose
  The immediate reason Jeff is assembling context, such as research support, proposal support, planning support, selection support, evaluation support, or operator explanation.
- current scope
  `project_id`, `work_unit_id`, and `run_id` where relevant.
  These are Jeff's foundational scope containers inside one global canonical state with nested projects.
- current canonical truth
  Current state in the relevant global, project, work-unit, and run scopes.
- governance-relevant current truth when needed
  Current blockers, integrity conditions, approval dependencies, readiness-relevant constraints, and policy-relevant bindings when they materially affect the current bounded task.
- relevant committed memory
  Selective durable support knowledge that may improve current judgment.
- relevant artifacts, source refs, and evidence
  Existing support objects with provenance when they materially matter to the current bounded task.
- relevant existing research results
  Existing research artifacts, findings, or source-aware summaries when they already exist and are still materially useful.
- canonical active context truth when present
  Narrow committed operating-focus truth from canonical state, never UI/session attention state.

These inputs define what context assembly may consider.
They do not grant context ownership over downstream reasoning semantics.

# Context Sources

Context uses source families, not one blended pool.

## Canonical truth sources

These are the authoritative current-truth sources:
- the one global canonical state where system-level truth is relevant
- project truth
- work-unit truth
- run truth
- canonical active-context truth when present in state
- authoritative direction, bindings, and scoped integrity/blocker truth that live in or are lawfully referenced by canonical state

Project is the hard isolation boundary inside global state.
Context assembly must respect that isolation boundary directly.

## Governance-relevant truth sources

These are current truth inputs that matter because they constrain safe next reasoning or action preparation:
- current blocker truth
- current degraded-trust or truth-mismatch truth
- current approval dependency or escalation dependency when canonically material
- current readiness-relevant state and current policy-relevant bindings where those facts are already authoritative

Governance meaning is still owned by `POLICY_AND_APPROVAL_SPEC.md`.
This document only governs how those current facts may enter context.
Approval and readiness remain governance objects, not truth objects.
Selection remains distinct from execution permission and therefore is not a permission source inside context assembly.

## Committed memory sources

These are durable support sources owned by the Memory layer:
- committed memory entries
- committed memory links referenced from canonical state
- memory-linked source or artifact refs when available

Memory is support knowledge, not current truth.

## Artifact, source, and evidence sources

These are bounded support sources with provenance:
- artifacts
- source refs
- evidence items
- source-aware research artifacts
- code or document sources when relevant
- external sources when the current task requires them

These sources may inform context.
They do not silently replace canonical truth.

## Operator-provided inputs

These include:
- direct instructions
- constraints
- provided materials
- clarified objectives
- explicit operator judgments delivered through lawful channels

Operator input is authoritative for the request frame and operator-owned constraints.
It is not a silent rewrite path for current system truth.

## Trigger-derived inputs

These include:
- system triggers
- scheduled triggers
- run-entry triggers
- bounded continuation triggers

Trigger-derived input defines why context is being assembled now.
It does not outrank canonical truth on questions of current reality.

## Non-default sources

The following are not default context sources:
- raw traces
- raw logs
- event history
- full chat history
- full artifact archives
- interface/session state

They may enter only as bounded support in explicitly justified cases such as debugging, reconciliation support, or audit support.

# Source Priority Rules

Context assembly has two anchors:
- request framing
- truth authority

The request frame comes from the current trigger or operator input.
The truth anchor comes from current canonical truth.
These must not be confused.

The binding authority rules are:

1. Current canonical truth wins for current-state questions.
   State is authoritative over memory, artifacts, traces, logs, and prior summaries.

2. Current governance-relevant truth is part of current truth for context purposes when the bounded task materially depends on it.
   Current blockers, integrity issues, approval dependencies, and similar current constraints must be surfaced before support layers.

3. Canonical active context may narrow scope only when that focus is committed in canonical state.
   UI/session focus, recently viewed items, tabs, filters, and similar attention residue do not define canonical context scope.

4. Operator input may define objectives, constraints, and priorities.
   It does not silently rewrite current truth without lawful mutation through transitions.

5. Committed memory may enrich, remind, and accelerate.
   It may not override state, direction, current bindings, or current blocker truth.

6. Evidence, artifacts, and existing research may inform.
   They remain support unless and until a lawful transition updates canonical truth.

7. Direct source-backed support outranks remembered summaries and derived summaries.
   When support is needed, better provenance and better scope fit beat more volume.

8. Stale, contradictory, or weak support must remain labeled as support, conflict, uncertainty, or mismatch.
   It must not be harmonized into fake current truth.

9. Traces, logs, and event history are lowest-priority support layers and are excluded by default.
   They are not normal anchors for reasoning context.

10. Only transitions mutate canonical truth.
    No support source, operator note, artifact, or memory entry silently becomes truth during context assembly.

This same truth-first law applies to Jeff-project work and non-Jeff project research.
The project domain changes.
The source-authority law does not.

# Filtering Rules

Context stays bounded through hard filters before any support ranking.

The binding filtering rules are:

- filter by scope first
  Stay inside the smallest sufficient scope. Wrong-project and wrong-work-unit material stays out.
- filter by purpose first
  Include only what materially affects the current bounded task.
- read truth before support
  Do not admit support layers until the current truth anchor is fixed.
- exclude support noise
  If a support item does not change the current bounded reasoning frame, omit it.
- exclude duplicate and near-duplicate support
  Prefer one strong representative over many redundant items.
- prefer thin refs and summaries over whole archives
  Include full bodies only when the current purpose genuinely requires them.
- exclude raw history by default
  Traces, logs, event streams, and chat history are out unless explicitly needed.
- exclude interface and session residue
  UI focus, tabs, filters, view-model state, and local cache state never belong in canonical reasoning context.
- exclude hidden downstream work
  Proposal content, selection rationale, evaluation judgments, and workflow progression do not get smuggled into context as if they were neutral inputs.
- exclude non-committed memory
  Only committed memory is eligible for context use.
- exclude stale or invalidated support when current use would be misleading
  Superseded, invalidated, stale, or clearly mismatched support stays out unless historical comparison is the explicit purpose.
- treat artifact posture as a filtering or ranking signal only where canonically available
  Existing quality, freshness, or review posture may help filter or rank support.
  v1 does not require a universal hard research-artifact-status gate in this document.

# Ranking Rules

Ranking applies only after truth anchoring and hard filtering.
Ranking does not allow support layers to outrank authoritative truth.

After the truth layer is fixed, support candidates are ranked by:

- exact scope fit
  Exact run scope, then exact work-unit scope, then exact project scope.
- current-task relevance
  Material fit to the immediate bounded objective or question.
- direction and constraint relevance
  Support that materially bears on current direction, scope boundaries, blockers, or key constraints ranks higher.
- evidence strength and source quality
  Better-grounded support outranks weaker support.
- memory confidence, stability, and source linkage
  Stronger, better-grounded memory outranks weak or poorly grounded memory.
- freshness where the question is freshness-sensitive
  Recent support matters more when the subject is time-sensitive.
- blocker or mismatch relevance
  Support that materially explains active risk, blockage, or contradiction outranks background material.
- novelty over redundancy
  New signal outranks repeated versions of the same point.
- contradiction salience
  Material contradiction may outrank redundant confirming support because it changes reasoning quality more than repetition does.

Ranking must not become:
- hidden evaluation
- hidden selection
- hidden policy interpretation

# Context Output Contract

The output of context assembly is a bounded, source-labeled context package.

At a high level, every context package should make the following explicit:
- purpose and trigger frame
  What bounded question, task, or preparation goal this package serves.
- scope frame
  `project_id`, `work_unit_id`, and `run_id` where relevant, plus any canonical active-context anchor if one exists.
- scoped truth snapshot
  The current authoritative facts that matter now.
- direction and current constraints
  Relevant direction, scope boundaries, bindings, blockers, integrity conditions, or governance-visible facts when materially needed.
- bounded memory support
  Selective committed memory, clearly labeled as memory.
- bounded evidence or source-aware support
  Existing artifacts, evidence, or research summaries with provenance.
- uncertainty, mismatch, or contradiction markers
  Explicit unresolved issues that downstream reasoning must not ignore.

The package must keep these source classes separate enough that downstream modules can tell:
- what is current truth
- what is support
- what is uncertain

The package must not dump unlabeled low-level JSON or raw archives by default.

# Truth-First Assembly Rules

The binding assembly order is:

1. Fix the bounded purpose.
   Jeff must know what this context package is for before gathering inputs.

2. Fix the bounded scope.
   Determine `project_id`, `work_unit_id`, and `run_id` from the request and canonical state, not from UI/session residue.

3. Read current canonical truth first.
   Read the relevant current global, project, work-unit, run, direction, and binding truth before support retrieval.

4. Read current governance-relevant truth when materially needed.
   Include blockers, integrity issues, approval dependencies, readiness-relevant constraints, and similar current facts before support layers.

5. Anchor the current request frame explicitly.
   Include the trigger or operator ask as the current objective frame, separate from current truth.

6. Add support layers only after the truth anchor is fixed.
   Memory, artifacts, evidence, and existing research enter only after steps 1 through 5.

7. Preserve source distinctions.
   Authoritative truth, memory, evidence, and uncertainty must remain visibly distinct.

8. Surface mismatch honestly.
   If support conflicts with current truth, surface the conflict instead of forcing a fake-clean packet.

9. Stop before context becomes reasoning.
   Context assembly prepares bounded inputs.
   It does not decide, select, evaluate, or mutate.

# Memory Retrieval Constraints for Context Use

Memory retrieval for context use is constrained by hard rules:

- only committed memory is eligible
- any state-carried memory linkage is by committed `memory_id` only
- only the Memory module creates memory candidates
- context retrieval consumes memory; it does not author memory
- memory is support knowledge, not current truth
- memory retrieval starts only after current truth is read
- scope filtering comes before similarity or relevance scoring
- same run, same work unit, and same project memory dominate local reasoning
- cross-project memory is excluded by default in v1
- retrieved memory must stay selective and budgeted
- near-duplicate memory should be deduplicated or suppressed
- source-grounded memory outranks ungrounded memory
- low-confidence or low-stability memory must remain labeled if included
- memory that conflicts with state stays labeled as stale support, contradiction, or mismatch support, not truth
- retrieval must not become "dump top-k and pray"

When a direct current-truth answer exists in state, memory does not get to repair or replace it.

# Context Boundaries

Context must not become any of the following:

- a hidden reasoning stage
- a proposal engine
- a selection engine
- an evaluation engine
- a transition path
- a policy override layer
- a workflow engine
- a plan archive
- a raw trace/log/event dump
- a memory dump
- an interface/session cache
- a second truth layer

Specific boundary rules:

- context may frame downstream reasoning; it does not perform it
- context may carry current constraints; it does not own governance meaning
- context may include existing research results; it does not own research methodology
- context may include plan or workflow support only as bounded support when later canon allows it; it does not absorb planning or workflow law
- context may include run truth; it does not become run history
- context may include operator framing; it does not turn chat/session residue into canonical focus
- context may carry action-preparation inputs; it does not turn `action`, approval, readiness, or selection results into current truth

# Failure Modes

Context assembly is failing if any of the following happens:

- memory overrides truth
- memory is retrieved before truth and frames the task incorrectly
- stale support is treated as current truth
- wrong-project leakage occurs
- wrong-work-unit leakage occurs
- run-local context is reconstructed from traces instead of run truth
- operator input silently rewrites truth
- support noise drowns current truth
- archive-dump context replaces bounded assembly
- duplicate support crowds out signal
- evidence enters without provenance
- research artifacts are treated as current truth or as decisions
- contradictory memory or evidence is silently harmonized into a fake-clean story
- context quietly performs proposal, selection, or evaluation work
- workflow, plan, or orchestration state is imported as if it were current truth
- UI/session focus masquerades as canonical active context
- raw traces, logs, or event history become default context sources
- non-Jeff project research gets weaker truth discipline than Jeff-project work

These are not cosmetic defects.
They are cognition and truth-drift failures.

# v1 Enforced Context Model

v1 enforces the following context model:

- every context package is purpose-bounded and scope-bounded
- `project_id` is required for project-scoped work
- `work_unit_id` and `run_id` are included when the bounded task actually depends on them
- one global canonical state with nested projects remains the truth anchor for context reads
- project remains the hard isolation boundary for context scope
- current canonical state is read first
- project direction and relevant current constraints are included when materially needed
- governance-relevant current truth is included when the bounded task touches action preparation, blocked conditions, or current risk posture
- canonical active context is used only when it exists as committed state truth
- only committed memory is eligible for retrieval
- memory retrieval is selective, local-scope-first, and support-only
- existing evidence, artifacts, and research summaries may be included only as bounded, source-aware support
- traces, logs, raw event history, and chat history are not default context sources
- workflow is not first-class canonical truth in v1 and must not be treated as a default context anchor
- planning remains conditional rather than universal
- context packages keep truth, memory, evidence, and uncertainty visibly separate
- context assembly never grants permission, never selects, never evaluates, and never mutates truth

This is enough to stop the main legacy drift:
- context-as-dump
- memory-first framing
- support layers silently replacing truth
- UI/session context masquerading as canonical focus
- context absorbing downstream reasoning logic

# Deferred / Future Expansion

Deferred expansion may add:

- richer context profiles for different reasoning purposes
- stronger conflict-aware assembly and contradiction handling
- richer evidence bundling and provenance structures
- better ranking of support inputs inside strict truth-first limits
- more advanced long-running continuation context models
- more explicit support for bounded cross-project or system-global context only if later canonized
- richer use of workflow or plan support only if later canonical docs promote them without weakening current boundaries

Deferred expansion does not relax the current law:
context remains truth-first, bounded, source-labeled, and non-decisional.

# Questions

No unresolved context-model questions were found in this pass.

# Relationship to Other Canonical Docs

- `ARCHITECTURE.md` owns the structural placement of context inside the Cognitive layer and the backbone that context feeds.
- `GLOSSARY.md` owns the meanings of `context`, `truth`, `memory`, `evidence`, `source`, `project`, `work_unit`, `run`, and related terms used here.
- `STATE_MODEL_SPEC.md` owns where current truth lives, the one-global-state topology, and what canonical active context means.
- `POLICY_AND_APPROVAL_SPEC.md` owns governance semantics; this document only defines how governance-relevant current facts may enter context.
- `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` owns container semantics and scope boundaries that context must respect.
- `CORE_SCHEMAS_SPEC.md` owns shared IDs, scope blocks, and reference primitives used by context I/O.
- `TRANSITION_MODEL_SPEC.md` owns truth mutation law; this document only defines how truth is read and prepared for downstream reasoning.
- `VISION.md` owns the product-level purpose for truth-first, bounded cognition.
- future `MEMORY_SPEC.md` owns memory model and retrieval law in full; this document only constrains memory use inside context assembly.
- future `PLANNING_AND_RESEARCH_SPEC.md` owns research and planning semantics; this document only defines how existing research support may enter context and how context may frame later research.
- future `PROPOSAL_AND_SELECTION_SPEC.md` and `EXECUTION_OUTCOME_EVALUATION_SPEC.md` own the downstream reasoning and judgment stages that context must not absorb.

# Final Statement

Jeff context is a bounded truth-first assembly, not a collection habit.

Jeff reads current truth first, fixes scope first, and only then adds selective support from memory, evidence, artifacts, and existing research.
Memory never becomes truth.
Support never outranks state.
UI/session residue never becomes canonical focus.
Context never becomes hidden reasoning.

If these laws stay hard, Jeff can reason from the right bounded reality in both Jeff-project work and non-Jeff project work.
If they soften, Jeff collapses into context sludge, truth drift, and memory-shaped hallucinated certainty.
