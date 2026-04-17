# SELECTION_IMPLEMENTATION_CHECKLIST.md

Status: implementation checklist proposal for Jeff Selection hybrid comparator + operator override  
Authority: subordinate to `PROPOSAL_AND_SELECTION_SPEC.md`, `POLICY_AND_APPROVAL_SPEC.md`, `ORCHESTRATOR_SPEC.md`, `INTERFACE_OPERATOR_SPEC.md`, `ARCHITECTURE.md`, `PROMPT_STANDARD.md`, `WORK_STATUS_UPDATE.md`, and `SELECTION_HYBRID_AND_OPERATOR_OVERRIDE_ARCHITECTURE.md`  
Purpose: define a bounded implementation sequence for upgrading Jeff Selection from the current deterministic stub to a hybrid comparator with explicit operator override support without collapsing selection into governance, interface, or orchestration drift

---

## 1. Why this document exists

Jeff now has:
- a live Proposal vertical that reaches validated `ProposalResult`
- a dedicated `jeff.cognitive.selection` package
- a deterministic `run_selection(...)` entry that performs bounded choice from visible proposal factors only

That is enough for a stub.
It is not enough for a strong Selection layer.

The current Selection behavior is still mostly:
- proposal-type bucketing
- phrase matching over text fields
- rough support / concern / reversibility heuristics

That is acceptable as a temporary bounded implementation.
It is weak as the long-term decision path for real proposal outputs.

This document turns the agreed target design into an execution order:
- model-assisted semantic comparison
- deterministic contract enforcement
- explicit non-selection outcomes
- operator override as a separate downstream lane
- no hidden permissioning drift

---

## 2. Hard architectural target

The target shape is:

`ProposalResult -> Selection comparison -> parsed comparison -> deterministic validation -> SelectionResult -> optional operator override -> action formation -> governance`

The hard law stays:
- Proposal generates bounded options
- Selection chooses or honestly returns non-selection
- Selection does not authorize
- Governance decides whether bounded action may begin now
- Operator override does not rewrite historical Selection truth
- Operator override does not bypass governance

---

## 3. Current reality

### Already true
- Proposal has a bounded end-to-end module-local entry and returns validated `ProposalResult`
- Selection has explicit contracts: `SelectionRequest`, `SelectionResult`, `SelectionDisposition`
- Selection currently supports `selected`, `reject_all`, `defer`, and `escalate`
- The current Selection package is dedicated and no longer a flat module

### Not true yet
- no Selection model/runtime path
- no Selection prompt contract
- no Selection parseable comparison output contract
- no deterministic validator for model comparison output
- no composed Selection API with stage-specific failure surfaces
- no operator override object family
- no CLI review path for Selection override
- no downstream action-resolution path that preserves original Selection truth plus override truth

---

## 4. Non-negotiable guardrails

Every slice below must preserve these rules:

1. **Selection remains bounded**
   - at most one selected proposal
   - or one explicit non-selection outcome

2. **Selection remains non-permissive**
   - no approval language
   - no readiness language
   - no execution permission language

3. **Deterministic shell stays load-bearing**
   - model output is never taken at face value without parsing and validation
   - fail closed on malformed or semantically illegal comparison output

4. **Operator override stays separate**
   - no mutation of historical `SelectionResult`
   - override is a new downstream object / request
   - override may choose only from already-considered proposal ids unless the system explicitly re-enters Proposal

5. **Governance remains downstream**
   - selected or overridden choice still routes into action/governance
   - no direct execution start from Selection or override

---

## 5. Recommended implementation order

---

## Slice 1 - Selection prompt contract surface

### Goal
Create the canonical Selection comparison prompt as a file-backed contract.

### Deliverables
- `PROMPTS/selection/COMPARISON.md`
- optional `PROMPTS/selection/README.md` if useful later
- `jeff/cognitive/selection/prompt_files.py`
- focused tests for prompt loading and placeholder rendering

### Prompt responsibilities
The prompt should:
- compare only the provided proposal options
- consider only visible comparison factors such as:
  - scope fit
  - blocker compatibility
  - support strength
  - assumption burden
  - risk posture
  - reversibility
  - planning-needed impact
- allow only these dispositions:
  - `selected`
  - `reject_all`
  - `defer`
  - `escalate`
- forbid:
  - approval language
  - readiness language
  - execution authority language
  - fake second winners
  - hidden option invention

### Output shape
Use one strict bounded text contract first.
Do **not** start with freeform prose.
Example fields:
- `DISPOSITION:`
- `SELECTED_PROPOSAL_ID:`
- `PRIMARY_BASIS:`
- `MAIN_LOSING_ALTERNATIVE_ID:`
- `MAIN_LOSING_REASON:`
- `PLANNING_INSERTION_RECOMMENDED:`
- `CAUTIONS:`

### Done when
- prompt file loads and renders through a Selection-local helper
- missing placeholders fail closed
- tests prove required markers and forbidden looseness are enforced

---

## Slice 2 - Comparison request and prompt-bundle surface

### Goal
Add a Selection-local request builder above the prompt contract.

### Deliverables
- `jeff/cognitive/selection/comparison.py`
- `SelectionComparisonRequest`
- `SelectionComparisonPromptBundle`
- `build_selection_comparison_prompt_bundle(...)`

### Responsibilities
- accept `SelectionRequest`
- render bounded visible comparison inputs only
- include considered proposal ids explicitly
- include enough option fields for semantic comparison
- keep hidden runtime/config logic out of the module surface

### Explicit non-goals
- no runtime call yet
- no parsing yet
- no validation yet
- no operator override logic yet

### Done when
- Selection has a generation-ready comparison bundle analogous to the Proposal vertical
- tests prove correct bundle rendering from real `ProposalResult` inputs

---

## Slice 3 - Selection runtime handoff

### Goal
Let Selection perform one bounded model comparison call through existing infrastructure.

### Deliverables
- runtime handoff in `comparison.py` or a dedicated `runtime.py`
- `RawSelectionComparisonResult`
- fail-closed runtime failure surfaces

### Responsibilities
- call `services.contract_runtime.invoke(...)`
- use a dedicated Selection purpose route
- preserve raw text and minimal runtime metadata only
- no parsing or semantic interpretation in this slice

### Important rule
Do not leak Selection semantics into Infrastructure.
Infrastructure routes and executes model calls.
Selection owns the meaning of the comparison output.

### Done when
- Selection can make one bounded model call and return raw comparison output or explicit runtime failure

---

## Slice 4 - Deterministic parsing of comparison output

### Goal
Turn raw Selection comparison text into a strict parsed object.

### Deliverables
- `jeff/cognitive/selection/parsing.py`
- `ParsedSelectionComparisonResult`
- deterministic parser with fail-closed malformed-shape errors

### Responsibilities
- parse only the exact expected shape
- reject missing required fields
- reject duplicate fields when ambiguous
- normalize sentinel values such as `NONE`
- keep parsing separate from semantic judgment

### Done when
- malformed model output cannot silently slide downstream
- tests cover missing fields, malformed ids, duplicate disposition fields, and empty rationale-like fields

---

## Slice 5 - Deterministic semantic validation and guardrails

### Goal
Make the deterministic shell truly load-bearing.

### Deliverables
- `jeff/cognitive/selection/validation.py`
- `ValidatedSelectionComparisonResult` or equivalent internal surface
- explicit validation issue types

### Required checks
At minimum:
- disposition must be one of the allowed four
- selected vs non-selection must be mutually exclusive
- selected proposal id must be in `considered_proposal_ids`
- `reject_all`, `defer`, `escalate` must not carry a fake selected winner
- rationale / basis fields must be non-empty where required
- forbidden authority language must be rejected
- planning recommendation must not become plan authority
- no hidden second winner language
- no invented proposal ids

### Important rule
Validation must be deterministic and fail closed.
Do not ask the model to validate itself.

### Done when
- Selection model output can be lawful or rejected, but never “kind of accepted”

---

## Slice 6 - Composed hybrid Selection API

### Goal
Expose one bounded Selection-local API that composes:
- prompt build
- runtime handoff
- parse
- validate
- canonical `SelectionResult` construction

### Deliverables
- `jeff/cognitive/selection/api.py`
- stage-distinct success/failure surfaces
- one public package entry for hybrid Selection

### Result behavior
On success:
- produce canonical `SelectionResult`
- preserve useful stage metadata for trace/debug visibility

On failure:
- preserve whether the failure was runtime, parsing, or validation
- fail closed rather than falling back to permissive heuristics silently

### Transitional recommendation
Keep the current deterministic `run_selection(...)` entry available temporarily as a compatibility path while the hybrid path is being integrated.
But do **not** let the temporary fallback hide hybrid failures in production-facing semantics.

### Done when
- there is one Selection-local hybrid entry that returns either lawful `SelectionResult` or explicit stage-specific failure

---

## Slice 7 - Orchestrator integration for Selection hybrid path

### Goal
Allow orchestrator / flow code to consume the hybrid Selection entry without changing Selection meaning.

### Deliverables
- bounded orchestrator-stage wiring
- handoff validation updates if needed
- trace/lifecycle visibility for comparison stage

### Responsibilities
- route Proposal output into hybrid Selection input
- preserve stage-order law
- surface comparison failure honestly
- avoid turning orchestrator into Selection fallback policy owner

### Explicit non-goals
- no operator override yet
- no governance shortcut
- no orchestration-owned semantic reinterpretation

### Done when
- one real flow can lawfully consume hybrid Selection output
- trace shows Selection comparison as a real stage with explicit failure class when relevant

---

## Slice 8 - Operator override contract family

### Goal
Add explicit human override without falsifying Selection history.

### Deliverables
- `jeff/governance/` is **not** the place to define this if the object means “operator decision over selection output” rather than permission
- recommended package: `jeff/cognitive/selection/override.py` or a neutral downstream review package if one already exists later
- `OperatorSelectionOverrideRequest`
- `OperatorSelectionOverride`
- deterministic validation rules

### Recommended fields
- `override_id`
- `selection_id`
- `project_id`
- `work_unit_id`
- `run_id`
- `original_selection_disposition`
- `chosen_proposal_id`
- `operator_rationale`
- `created_at`

Optional:
- `requested_by`
- `requires_reproposal`
- `notes`

### Hard rules
- override never mutates the original `SelectionResult`
- override may choose only from the original `considered_proposal_ids`
- if the operator wants something outside that set, do not fake it as override; route to re-proposal / re-framing
- override does not imply permission
- override does not skip governance

### Done when
- the system can represent “Selection chose X, operator explicitly chose Y from the same bounded set” without semantic lying

---

## Slice 9 - Action-resolution surface after Selection and override

### Goal
Define what downstream consumers actually use when both Selection and operator override exist.

### Deliverables
- `SelectionResolution` or equivalent downstream object
- action-formation input rules
- deterministic precedence rules

### Recommended law
- if no override exists, downstream uses `SelectionResult`
- if lawful override exists, downstream uses override choice for action formation
- original `SelectionResult` remains inspectable and unchanged
- downstream resolution object must preserve both facts:
  - original Selection outcome
  - actual operator-directed chosen option

### Important rule
This is not governance.
It is downstream decision resolution before action formation.
Governance still evaluates whether the resulting bounded action may begin now.

### Done when
- action creation can consume either original selection or lawful operator override without semantic ambiguity

---

## Slice 10 - CLI/operator review surface for Selection override

### Goal
Expose override power to the operator without making the interface lie.

### Deliverables
- new CLI surface, for example:
  - `/selection show [run_id]`
  - `/selection override <proposal_id>`
  - `/selection clear-override` only if later justified
- interface JSON/read views that preserve authority labels

### Interface truthfulness requirements
The operator surface must distinguish:
- original Selection result
- override existence
- resolved downstream choice
- governance status after override if later present

The interface must not present:
- override as if Selection itself originally chose that option
- override as approval
- override as execution start

### Done when
- an operator can lawfully inspect and override a Selection decision from the considered set with honest UI semantics

---

## Slice 11 - Governance handoff after override-aware action formation

### Goal
Ensure the override path still respects action-entry law.

### Deliverables
- action-formation wiring from resolved choice
- governance tests for override-aware action entry

### Required rules
- selected choice or override choice becomes bounded action input
- governance still evaluates approval/readiness on that bounded action
- prior governance results do not automatically transfer if the chosen proposal changes materially

### Done when
- override-aware action formation still routes through normal `selection -> action -> governance -> execution` discipline

---

## Slice 12 - Tests, anti-drift, and acceptance hardening

### Goal
Make the new design enforceable rather than aspirational.

### Required test families

#### Unit tests
- prompt loading
- prompt bundle construction
- runtime handoff contracts
- parsing failures
- validation failures
- canonical `SelectionResult` construction
- override contract validation
- selection-resolution precedence rules

#### Integration tests
- proposal result into hybrid Selection
- hybrid Selection into orchestrator handoff
- override into action formation
- override into governance entry

#### Anti-drift tests
- selection output cannot imply permission
- operator override cannot rewrite `SelectionResult`
- override cannot select out-of-set proposal ids
- override cannot bypass governance
- interface cannot flatten original result and override result into one false history

#### Acceptance tests
- lawful selected case
- lawful defer case
- lawful escalate case
- malformed model output fail-closed case
- override to different considered option then governance stop case
- override to different considered option then governed action-entry case

### Done when
- the new Selection path is stronger because boundaries are tested, not because the prompt sounds smarter

---

## 6. Suggested file layout

A reasonable target layout is:

```text
jeff/cognitive/selection/
  __init__.py
  contracts.py
  decision.py                  # temporary deterministic legacy/stub path
  prompt_files.py
  comparison.py
  parsing.py
  validation.py
  api.py
  override.py                  # if kept Selection-local
  HANDOFF.md

PROMPTS/
  selection/
    COMPARISON.md
```

Possible downstream consumer placement later:

```text
jeff/cognitive/selection_resolution.py
```

or

```text
jeff/cognitive/decision_resolution.py
```

Keep this separate from Governance unless the object truly becomes a permission object.

---

## 7. Explicitly not in scope

Do **not** do these during the Selection slices:
- broad orchestrator rewrite
- governance redesign
- interface redesign beyond the minimum truthful Selection review surface
- letting override select non-considered options
- collapsing Selection and Evaluation into one “decision engine”
- moving permission semantics into Selection prompts
- hiding hybrid failure behind silent permissive fallback

---

## 8. Practical recommended sequence

Shortest sane order:

1. Selection prompt contract
2. comparison request + prompt bundle
3. runtime handoff
4. deterministic parsing
5. deterministic validation
6. composed hybrid Selection API
7. orchestrator integration
8. operator override contracts
9. action-resolution surface
10. CLI/operator override surface
11. governance handoff checks
12. hardening and acceptance coverage

---

## 9. Acceptance gate for “Selection hybrid complete enough to build on”

Do not treat the hybrid Selection slice as done until all of the following are true:

- Selection can consume real `ProposalResult` objects through one composed hybrid entry
- malformed or semantically illegal model output fails closed
- canonical `SelectionResult` still preserves the original bounded Selection law
- operator override exists as a separate explicit object / request
- override cannot falsify history
- override cannot choose outside the considered proposal set
- override-aware downstream action formation is explicit
- governance still gates actual action start
- CLI/operator surfaces distinguish original selection, override, and downstream resolved choice truthfully
- tests prove anti-drift boundaries, not just happy paths

---

## 10. Final recommendation

The right next move is **not** to keep polishing the current phrase engine.
That is lipstick on a weak core.

The right move is:
- add the hybrid path in bounded slices
- keep deterministic validation load-bearing
- keep operator override explicit and separate
- preserve the hard line that Selection chooses but Governance permits

That gives Jeff a stronger decision layer without turning it into hidden governance, prompt theater, or interface-owned semantics.
