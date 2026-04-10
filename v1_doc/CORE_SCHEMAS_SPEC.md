# Purpose

This document defines Jeff's shared machine-facing schema primitives.

It owns:
- shared envelope discipline for internal module I/O
- shared scope, ID, and reference rules
- shared naming discipline for typed schema fields
- shared validation expectations
- shared schema versioning and compatibility rules

It does not own:
- architecture law
- state topology
- transition lifecycle semantics
- governance semantics
- module-local business logic
- interface-specific JSON contracts
- test matrices
- roadmap sequencing

This is the canonical shared-primitives document for Jeff as a whole.
It is not a loose set of examples, not an interface-only JSON note, and not a place to restate downstream module schemas.

# Canonical Role in Jeff

Jeff depends on many bounded modules, but they must still exchange data through one coherent machine-facing contract layer.

This document exists to stop:
- ad hoc payload drift
- generic `status` flattening
- inconsistent ID and reference naming
- envelope sprawl between modules, orchestrator, and interfaces
- business logic being smuggled into "schema" convenience fields

Its role is to keep contracts interoperable without turning schemas into business logic.
The owning canonical documents still define what their objects mean.
This document defines how shared machine contracts stay explicit, typed, and stable across those documents.

# Schema System Principles

- Explicit shape beats dict chaos.
- Shared schemas are closed by default. Hidden shared fields are forbidden.
- Module inputs are treated as immutable facts for that module invocation.
- Shared surface must stay minimal. If a field is not reused across modules, it does not belong here.
- Extension is allowed only through documented ownership and versioning, never through silent drift.
- Typed semantics must not be flattened into one generic `status` field.
- Architecture beats convenience naming. Shared field names must follow canonical meaning, not local habit.
- Direct typed IDs are the default linkage mechanism. Rich reference objects are exceptions, not the baseline.
- Invocation envelopes, persisted truth objects, and interface responses are different schema layers and must not be collapsed into one shape.
- Canonical state may reference only committed memory IDs.

# Shared Envelope Rules

Jeff uses one internal shared envelope family for inter-module communication.
That family is separate from:
- persisted canonical truth objects
- interface/API/CLI response contracts
- artifact storage formats

Shared envelope rules:
- Top-level envelope fields are fixed and closed.
- Module-specific content lives inside `payload` on requests and `result` on results.
- Scope is explicit through a shared `scope` block, not implied by nesting or prompt context.
- Envelope-level call health is separate from domain semantics.
- Validation failures and warnings live in shared carrier fields, not mixed into domain payloads.
- Telemetry is allowed, but telemetry is not domain truth.

Universal shared envelope content:
- `module`
- `scope`
- `metadata`

Conditionally required shared envelope content:
- `payload` for requests
- `result` for successful result envelopes
- `validation_errors` when schema or reference validation fails
- `warnings` when non-fatal contract cautions must remain visible
- `telemetry` when the caller or orchestrator records execution metrics

What belongs only in module-local payloads:
- proposal content
- selection reasoning
- readiness checks
- execution traces
- outcome evidence content
- evaluation criteria
- memory-writing judgments
- any owner-specific enum set

# ID and Reference Rules

## ID Rules

- Shared entity identifiers use typed field names: `<entity>_id`.
- Shared ID list fields use `<entity>_ids`.
- Bare shared `id` is forbidden.
- ID values are opaque strings. Correctness must not depend on parsing string prefixes.
- One entity keeps one stable ID for its lifetime. A materially different entity gets a new ID.

The shared typed IDs frozen by this document are:
- `project_id`
- `work_unit_id`
- `run_id`
- `transition_id`
- `memory_id`
- `proposal_id`
- `selection_id`
- `action_id` when an action descriptor is materialized
- `approval_id` when approval linkage is materialized
- `readiness_id` when readiness linkage is materialized
- `artifact_id`
- `trace_id` when a trace is treated as a distinct linked object

`project_id + work_unit_id + run_id` are the foundational shared container identifiers.
Their existence reflects the canonical whole-Jeff backbone, while the state model still owns exact truth placement.
Jeff has one global canonical state with nested projects; these shared identifiers assume that topology without redefining it here.

## Scope Rules

Shared machine scope uses one reusable block:

```json
{
  "project_id": "string",
  "work_unit_id": "string | null",
  "run_id": "string | null"
}
```

Scope rules:
- `project_id` is required for project-scoped work.
- `work_unit_id` is required when the work belongs to a work unit.
- `run_id` is required for orchestrated module I/O that occurs inside a run.
- Any system-scoped exception must be explicit in the owning spec; it must not be implied by missing fields.

## Reference Rules

- Direct typed IDs are the default reference form.
- Structured `*_ref` objects are used only when identity alone is insufficient.
- Structured `*_refs` arrays must contain reference objects, not plain strings.
- Locator data is not identity. Paths, URIs, and storage locations may describe where something lives, but they do not replace typed IDs.

Minimal structured shared references:

```json
{
  "artifact_ref": {
    "artifact_id": "string",
    "artifact_type": "string",
    "locator": "string | null",
    "produced_by_run_id": "string | null"
  }
}
```

```json
{
  "source_ref": {
    "source_type": "string",
    "source_id": "string | null",
    "locator": "string | null",
    "project_id": "string | null",
    "work_unit_id": "string | null",
    "run_id": "string | null"
  }
}
```

Reference discipline:
- Use `memory_id` or `memory_ids` for committed memory links.
- Use `artifact_id` or `artifact_ids` for direct artifact identity links.
- Use `artifact_ref` only when artifact metadata beyond identity is required.
- Use `source_ref` when provenance must survive across internal and external source classes.
- Use `selected_proposal_id`, not `selected_id`.
- Use `proposal_id`, not bare `id`, in proposal-linked payloads.

Committed memory rule:
- Canonical state may reference committed `memory_id` values only.
- Uncommitted memory candidates, failed writes, or speculative memory links must not appear as canonical references.

Thin action-linkage rule:
- Shared schemas may carry `action_id`, `approval_id`, and `readiness_id` as linkage fields where needed.
- v1 does not require a heavy durable action object in shared schema law.
- A thin action descriptor or action reference is sufficient when action must cross module boundaries.

# Core Object Families

This document defines object-family classes, not full downstream object models.

## Canonical Truth Objects

- global canonical state
- project
- work_unit
- run
- transition

These are the current-truth object families.
`STATE_MODEL_SPEC` and `TRANSITION_MODEL_SPEC` own their detailed schemas and rules.
There is one global canonical state with nested projects, and project remains the hard isolation boundary inside that state.

## Governance Objects

- policy outputs
- approval objects
- readiness objects

These govern whether bounded action may proceed.
They are not execution results and not truth-mutation objects.

## Transient Processing Objects

- context package
- proposal set and proposal objects
- selection result
- execution result
- outcome object
- evaluation result

These are stage-bounded working objects.
They may be durable as artifacts or records, but they are not current canonical truth by default.

## Transient Operational Objects

- action descriptor
- action reference

`action` is a narrow canonical transient operational object family.
It bridges selected or plan-refined intent into governance and execution without becoming workflow truth, governance authority, or transition law.

## Support / Review Objects

- memory candidate
- memory entry
- `Change`
- apply/review/reconciliation support records

These may be important and durable, but they do not rival canonical truth mutation.
`Change` is never a rival mutation primitive.

## Artifacts / Evidence / References

- artifact objects
- artifact references
- source references
- evidence-bearing support objects
- trace references

These preserve provenance, reviewability, and linkage.
They are not canonical truth by default.

# Cross-Document Schema Ownership Boundaries

- `STATE_MODEL_SPEC` owns canonical truth topology, root placement, and what canonical state may contain.
- `TRANSITION_MODEL_SPEC` owns the transition object model, mutation validation layers, commit results, and audit/commit law.
- `POLICY_AND_APPROVAL_SPEC` owns policy outputs, approval meaning, readiness meaning, and governance-stage semantics.
- `PROJECT_AND_WORK_UNIT_MODEL_SPEC` owns project and work-unit identities, lifecycles, linking rules, and isolation semantics.
- `CONTEXT_SPEC` owns context package content, source priority, filtering, and assembly rules.
- `PROPOSAL_AND_SELECTION_SPEC` owns proposal and selection object meanings, scarcity rules, rationale rules, and decision semantics.
- `EXECUTION_OUTCOME_EVALUATION_SPEC` owns execution, outcome, and evaluation object meanings, stage boundaries, and verdict semantics.
- `MEMORY_SPEC` owns memory candidate authorship, memory record schemas, write policy, retrieval, and linking semantics.
- `ORCHESTRATOR_SPEC` owns sequencing, orchestration-time validation routing, and lifecycle coordination.
- `INTERFACE_OPERATOR_SPEC` owns CLI/API/GUI contracts, operator-facing JSON, and view-model rules.

This document owns only the shared schema primitives reused across those documents.
If a rule cannot be stated without deciding business semantics for one of those documents, it does not belong here.

# Base Envelope Definitions

## Shared Metadata Block

Shared metadata is small and mechanical.
It is not a junk drawer for domain semantics.

```json
{
  "metadata": {
    "schema_version": "1.0",
    "produced_at": "iso8601",
    "correlation_id": "string | null",
    "trace_id": "string | null",
    "producer": "string | null"
  }
}
```

Metadata rules:
- `schema_version` is required.
- `produced_at` is required on emitted envelopes.
- `correlation_id` is optional and may be used to bridge interface/request correlation.
- `trace_id` is optional shared linkage, not a substitute for run scope.
- `producer` is optional when the top-level `module` field is already sufficient.

## Base Request Envelope

```json
{
  "module": "string",
  "scope": {
    "project_id": "string",
    "work_unit_id": "string | null",
    "run_id": "string | null"
  },
  "payload": {},
  "metadata": {
    "schema_version": "1.0",
    "produced_at": "iso8601",
    "correlation_id": "string | null",
    "trace_id": "string | null",
    "producer": "string | null"
  }
}
```

## Base Result Envelope

```json
{
  "module": "string",
  "scope": {
    "project_id": "string",
    "work_unit_id": "string | null",
    "run_id": "string | null"
  },
  "module_call_status": "succeeded | rejected_input | failed",
  "result": {},
  "validation_errors": [],
  "warnings": [],
  "telemetry": {},
  "metadata": {
    "schema_version": "1.0",
    "produced_at": "iso8601",
    "correlation_id": "string | null",
    "trace_id": "string | null",
    "producer": "string | null"
  }
}
```

## Error / Warning Carrier Conventions

Validation errors and shared warnings use one small carrier shape:

```json
{
  "code": "string",
  "message": "string",
  "field_path": "string | null",
  "related_id": "string | null"
}
```

Carrier rules:
- `code` is stable and machine-usable.
- `message` is human-readable.
- `field_path` points to the invalid shared field when applicable.
- `related_id` is optional typed linkage to the offending object.
- Domain-specific issue lists still belong to the owning payload schema.

# Module I/O Envelope Rules

- `module` identifies the producing or receiving module at the envelope top level.
- `payload` holds module-specific request content.
- `result` holds module-specific successful output content.
- `telemetry` holds timing and execution metrics only.
- `validation_errors` holds pre-execution or post-output contract failures.
- `warnings` holds non-fatal contract cautions that must survive handoff.

Rules:
- A module must not place domain payload fields beside envelope control fields.
- A module must not hide validation failures inside `result`.
- A module must not overload `warnings` as evaluation judgment, blocker truth, or policy result.
- A failed or rejected envelope may omit `result`, but it must still preserve `module`, `scope`, `module_call_status`, and `metadata`.
- Interface-layer envelopes may adapt this shape later, but they are subordinate to this internal law and owned by `INTERFACE_OPERATOR_SPEC`.

# Status / Verdict / Typed Field Naming Rules

This section is binding.
It exists to stop generic naming collapse.

## `status`

Use `status` only for lifecycle or operational state inside one object's own state machine.

Allowed examples:
- `module_call_status`
- `execution_status`
- `action_status`

Preferred stronger forms:
- `readiness_state`
- `run_lifecycle_state`
- `outcome_state`

Rules:
- Bare shared `status` is forbidden in semantic payloads.
- `status` must not simultaneously mean call health, choice outcome, evaluation judgment, and mutation result.

## `verdict`

Use `verdict` for judgment or gating conclusions.

Examples:
- `policy_verdict`
- `approval_verdict`
- `evaluation_verdict`

`verdict` answers: how should this be judged?

## `decision`

Use `decision` for an explicit choice among alternatives or a recorded choice event.

Examples:
- selection decision
- operator decision

`decision` answers: what route or option was chosen?

`decision` must not be the default name for evaluation or policy outputs.

## `result`

Use `result` for the output object of an operation or for an operation-level result classification.

Examples:
- `execution_result`
- `validation_result`
- `transition_result`

`result` must not replace `verdict` where the real meaning is judgment.

## `type`

Use `type` for the primary discriminator or taxonomy field of an object family.

Examples:
- `artifact_type`
- `source_type`
- `memory_type`

## `kind`

Do not use `kind` as a casual synonym for `type`.
Use it only when a second taxonomy layer is genuinely necessary and owned by the relevant document.

## Required Distinctions

The following must remain distinct in naming and schema:
- selection outcome is not execution permission
- approval is not readiness
- readiness is not execution
- execution status is not outcome state
- outcome state is not evaluation verdict
- approval verdict is not transition result
- action status is not readiness state
- `approved` is not `applied`

Recommended typed names across Jeff:
- `selection_outcome`
- `policy_verdict`
- `approval_verdict`
- `readiness_state`
- `execution_status`
- `outcome_state`
- `evaluation_verdict`
- `transition_result`

# Validation Rules

- Validate shared request envelopes before module execution.
- Validate shared result envelopes after module output and before downstream consumption.
- Fail fast on malformed shared fields, missing required scope, invalid schema version, or illegal reference shape.
- Shared validation must reject undocumented top-level envelope fields.
- Reference integrity must be checked whenever a referenced object is required to already exist.
- A module must not continue from invalid input by "best effort."
- A downstream module must not treat an invalid upstream result as usable domain truth.
- Canonical truth mutation paths must additionally satisfy the owning transition/state validation rules; this document does not replace them.

# Versioning Rules

Jeff uses two different version concepts and they must not be conflated.

## Shared Schema Version

- Shared envelopes use `metadata.schema_version`.
- `schema_version` is a string in `major.minor` form.
- `schema_version` tracks contract shape, not truth state.

## Canonical State Version

- `state_version` is the version of canonical truth state.
- `state_version` is an integer monotonic counter.
- `state_version` is not interchangeable with `schema_version`.

## Document-Level Discipline

- Any change to shared schema law must update this document explicitly.
- Any consuming canonical doc that depends on the changed primitive must be updated in the same change set.
- No legacy schema document retains equal authority once this document defines the shared rule.

# Compatibility Rules

Shared schema evolution is conservative.

Breaking changes include:
- renaming or removing a shared field
- changing a shared field's meaning
- changing a shared field's type or cardinality
- changing a shared field from optional to required
- reusing one field name for conflicting meanings
- converting an ID field into a locator field
- adding new top-level shared envelope fields without a versioned contract change

Compatible changes may include:
- adding an optional field inside an owning module payload block
- adding a new structured reference object under an owning doc
- adding new typed domain enums in an owning doc when naming law remains intact

Compatibility rules:
- Shared envelope top level is closed and changes rarely.
- Module-local payload interiors may evolve under their owner docs.
- New optional shared fields require documented ownership, version change, and consuming-doc alignment.
- Canonical docs must remain aligned; no document may quietly fork shared primitive meaning.

# Forbidden Schema Anti-Patterns

- raw dict chaos
- hidden fields
- undocumented extras
- generic `status` flattening
- generic bare `id` in shared contracts
- interface-specific schema becoming backend authority
- invocation envelopes, module payloads, and persisted records collapsed into one schema layer
- scope implied by nesting or prompt context
- mutation semantics smuggled into support objects
- `Change` or apply treated as rival mutation primitives
- memory references without committed IDs
- field reuse with conflicting meanings
- action / governance / execution blur through loose naming
- plan / workflow / approval treated as automatic readiness
- locator or path treated as identity
- string-array `*_refs` used where typed IDs or structured refs are required

# v1 Enforced Schema Surface

v1 enforces the following shared schema surface:

- one internal module I/O envelope family with fixed top-level fields
- explicit `scope` block using `project_id`, `work_unit_id`, and `run_id`
- typed shared IDs instead of bare `id`
- direct typed IDs as the default linkage mechanism
- minimal structured `artifact_ref` and `source_ref`
- `metadata.schema_version` as shared contract version
- integer `state_version` for canonical truth versioning
- validation before module execution and after module output
- `module_call_status` for envelope-level call health
- typed naming discipline that preserves:
  - `selection_outcome`
  - `policy_verdict`
  - `approval_verdict`
  - `readiness_state`
  - `execution_status`
  - `outcome_state`
  - `evaluation_verdict`
  - `transition_result`
- thin action linkage through `action_id` and related refs where needed
- planning-related payloads and refs are conditional, not universal
- no requirement for first-class workflow truth objects in shared schema v1
- canonical state references only to committed `memory_id` values

v1 does not require:
- a heavy universal action record
- a universal workflow object
- rich interface transport contracts
- full artifact-lineage governance fields
- broad globally named IDs for every transient module object

# Deferred / Future Schema Expansion

The following areas are deferred until later canonical pressure justifies them:

- richer durable action records beyond thin action descriptors and refs
- richer workflow schemas if workflow is promoted beyond supporting coordination
- long-running continuation, checkpoint, and resumption metadata
- richer artifact/source/evidence lineage contracts
- broader external API and GUI envelope contracts
- broader cross-project memory or source-link models if whole-Jeff canon later requires them

# Questions

No unresolved schema questions were found in this pass.

# Relationship to Other Canonical Docs

- `VISION.md` explains what Jeff is for and why the contract discipline exists.
- `ARCHITECTURE.md` defines the structural laws these shared schemas must obey.
- `GLOSSARY.md` defines the canonical meanings of terms such as `action`, `transition`, `approval`, `readiness`, `outcome`, and `evaluation`.
- `STATE_MODEL_SPEC.md` uses these primitives to define truth topology and canonical state contents.
- `TRANSITION_MODEL_SPEC.md` uses these primitives to define mutation law and transition structure.
- `POLICY_AND_APPROVAL_SPEC.md` uses these primitives to define governance outputs and gating objects.
- `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` uses these primitives to define container identities and linking rules.
- `CONTEXT_SPEC`, `PROPOSAL_AND_SELECTION_SPEC`, `EXECUTION_OUTCOME_EVALUATION_SPEC`, and `MEMORY_SPEC` own their respective payload meanings.
- `ORCHESTRATOR_SPEC` owns sequencing and boundary enforcement, not schema meaning.
- `INTERFACE_OPERATOR_SPEC` owns downstream operator/client contracts, not internal shared schema law.

# Final Statement

Jeff needs one hard shared schema layer.

That layer is small on purpose:
- one internal envelope family
- one typed ID and reference discipline
- one naming law for status, verdict, decision, result, and type
- one validation and versioning posture

If this layer stays narrow and explicit, Jeff's modules can interoperate without losing architectural meaning.
If it expands into business logic or collapses into generic payload sludge, the rest of the canon will drift with it.

