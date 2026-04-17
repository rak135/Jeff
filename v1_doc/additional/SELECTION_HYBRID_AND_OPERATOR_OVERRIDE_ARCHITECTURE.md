# SELECTION_HYBRID_AND_OPERATOR_OVERRIDE_ARCHITECTURE.md

Status: proposed implementation architecture for Jeff Selection  
Authority: subordinate to `PROPOSAL_AND_SELECTION_SPEC.md`, `POLICY_AND_APPROVAL_SPEC.md`, `ARCHITECTURE.md`, `INTERFACE_OPERATOR_SPEC.md`, `ROADMAP_V1.md`, `WORK_STATUS_UPDATE.md`, and current Selection/Proposal handoffs  
Purpose: define a concrete, buildable architecture for hybrid Selection comparison and explicit operator override without weakening Jeff's decision law, governance boundaries, or audit truth

---

## 1. Why this document exists

Jeff now has:
- Proposal as a real bounded runtime-backed vertical with prompt -> runtime -> parse -> validate -> `ProposalResult`
- Selection as a dedicated package with explicit contracts and one deterministic bounded choice entry
- Governance already separated from Selection and already enforcing the `selection -> action -> governance -> execution` boundary

That is enough for a first lawful backbone.
It is not enough for a strong final decision layer.

Current Selection is still a bounded deterministic comparator over visible proposal fields.
That is useful as a fail-closed baseline, but weak as the long-term comparator when much of proposal meaning still lives in short natural-language fields such as summary, risks, blockers, constraints, assumptions, and reversibility notes.

This document exists to define the next strong form:
- model-assisted semantic comparison
- deterministic contract enforcement
- explicit operator override support
- zero leakage of permission semantics into Selection
- zero rewriting of historical Selection truth

The goal is not to make Selection “smarter” by blurring it with Governance.
The goal is to make Selection more semantically reliable while keeping boundaries hard.

---

## 2. Core design principle

The binding design law is:
- Proposal generates bounded serious options
- Selection compares those options and returns one bounded disposition
- Selection never grants permission
- Governance still decides whether bounded action may start now
- Operator override may redirect downstream choice, but it must not falsify what Selection originally returned

In compact form:

`ProposalResult -> hybrid comparison -> validated SelectionResult -> optional operator override -> action formation -> governance -> execution`

This preserves Jeff's canonical law:
- selection chooses
- governance permits
- execution acts

Selection stays a pre-governance choice layer.
Operator override stays a downstream human-control lane.
Governance remains load-bearing.

---

## 3. Non-goals

This architecture does **not** do the following:
- make Selection a permission layer
- let the model decide approval or readiness
- let operator override rewrite `SelectionResult`
- let the interface become a hidden governance shortcut
- let Selection choose from options that Proposal did not actually hand forward
- introduce workflow-first decision authority
- turn prompts into parsers, validators, or policy engines
- replace deterministic fail-closed checks with “LLM confidence”

If any of those happen, the architecture is broken.

---

## 4. Current reality

Current project reality:
- Proposal is already the more advanced model-backed vertical and ends in validated `ProposalResult`
- Selection is a dedicated package with `SelectionRequest`, `SelectionResult`, and a deterministic `run_selection(...)`
- current Selection behavior is deterministic and local, with no runtime/model comparison or package-local validation engine yet

This means the right next step is **not** a broad rewrite.
The right next step is a bounded Selection-local upgrade path that keeps the current deterministic path as a lawful fallback while adding hybrid comparison above it.

---

## 5. Decision-layer target shape

The target Selection stack should be:

```text
SelectionRequest
  -> comparison bundle builder
  -> hybrid comparator runtime call
  -> deterministic parse
  -> deterministic validation / guardrails
  -> SelectionResult
```

And then, separately:

```text
SelectionResult
  -> optional OperatorSelectionOverride
  -> effective decision resolution
  -> action formation
  -> governance
  -> execution
```

This separation is the whole point.
Do not collapse these two stacks.

---

## 6. Why pure deterministic selection is not enough

Pure deterministic selection is only strong when proposal outputs are already normalized into explicit machine-judgment signals.
That is not today's reality.

Today, Proposal carries enough structure to be bounded and parseable, but much of the real meaning still lives in natural-language fields.
That creates specific weaknesses for deterministic-only comparison:
- synonyms and paraphrases fragment the same meaning across different wording
- blockers vs cautions are not always cleanly detectable by phrase matching
- assumption burden is often comparative, not binary
- defer vs escalate often depends on judgment context, not one keyword
- two serious options can be close enough that phrase heuristics become theater

So deterministic-only Selection is good as:
- baseline behavior
- fallback
- guardrail shell
- testable fail-closed path

It is not good enough as the final comparator over semantically rich proposal text.

---

## 7. Why pure model selection is also wrong

Pure model selection is trash architecture here.

Why:
- it risks hidden governance inside Selection
- it weakens inspectability
- it increases prompt-owned semantics
- it makes permission drift more likely
- it makes failures softer and less testable
- it tempts people to treat the model's prose as authority

Jeff should not let the model own law.
Jeff should let the model do only the part that is actually model work:
semantic comparison between already-bounded options.

Everything else must stay deterministic.

---

## 8. Hybrid Selection model

### 8.1 Definition

Hybrid Selection means:
- the model performs bounded semantic comparison of already-validated proposal options
- deterministic code parses and validates the comparison output
- deterministic code emits the canonical `SelectionResult`
- invalid model output fails closed

### 8.2 Allowed model task

The model may do only this:
- compare the provided serious options
- weigh visible factors such as scope fit, evidence/support strength, blocker compatibility, assumption burden, risk posture, reversibility, and planning-needed impact
- determine whether the most honest disposition is `selected`, `reject_all`, `defer`, or `escalate`
- explain strongest reasons and strongest losing alternative in bounded form

The model may **not** do any of the following:
- approve
- declare readiness
n- authorize execution
- invent new options
- use hidden context residue
- choose from outside the considered proposal set
- mutate truth
- write policy
- perform action formation

---

## 9. Selection-local ownership boundaries

The Selection package should own:
- comparison request shaping for Selection
- comparison prompt contract for Selection
- hybrid comparator result parsing
- Selection-local validation / guardrails
- canonical `SelectionResult` emission
- deterministic fallback selection path
- Selection-local rationale structure

The Selection package should **not** own:
- Proposal generation
- Proposal validation
- Governance semantics
- Approval or readiness
- Action object formation
- Operator UI decisions
- Transition commits
- Interface-local review state
- Orchestrator business logic

Operator override should not live inside Selection package semantic ownership.
It is a downstream review/control lane.

---

## 10. Comparison input model

Hybrid Selection input should remain narrow and explicit.
The comparator should consume only a Selection-local comparison bundle built from:
- `SelectionRequest`
- the `ProposalResult`
- explicit considered option ids
- visible option fields needed for bounded comparison
- narrow truth/context cues only when they are already lawful selection input

The comparison bundle should **not** include:
- hidden operator wishes not reflected in current scope/request
- approval state
- readiness state
- execution history as hidden pressure
- interface-local “preferred option” residue
- speculative memory summaries not already in lawful context

### 10.1 ComparisonBundle draft shape

```json
{
  "request_id": "...",
  "project_id": "...",
  "work_unit_id": "... | null",
  "run_id": "... | null",
  "considered_proposal_ids": ["prop_1", "prop_2"],
  "scarcity_reason": "... | null",
  "options": [
    {
      "proposal_id": "prop_1",
      "proposal_type": "direct_action | planning_insertion | investigate | clarify | defer | escalate | ...",
      "summary": "...",
      "why_now": "...",
      "main_risks": ["..."],
      "assumptions": ["..."],
      "blockers": ["..."],
      "constraints": ["..."],
      "support_refs": ["..."],
      "planning_needed": true,
      "reversibility": "... | null"
    }
  ]
}
```

This bundle is for comparison only.
It is not a public replacement for `ProposalResult`.

---

## 11. Hybrid comparator output contract

The comparator must not return essay sludge.
It must return a strict bounded contract.

### 11.1 Output goals

The output must preserve:
- one disposition only
- selected proposal id when selected
- strongest reasons
- strongest losing alternative
- decisive cautions
- zero permission language

### 11.2 Canonical comparison output shape

Recommended contract:

```text
DISPOSITION: selected | reject_all | defer | escalate
SELECTED_PROPOSAL_ID: <proposal_id | NONE>
PRIMARY_BASIS: <one bounded sentence>
STRONGEST_REASONS:
- <reason>
- <reason>
MAIN_LOSING_ALTERNATIVE_ID: <proposal_id | NONE>
MAIN_LOSING_REASON: <one bounded sentence>
DECISIVE_FACTORS:
- <factor>
- <factor>
CAUTIONS:
- <caution>
- <caution>
PLANNING_INSERTION_RECOMMENDED: yes | no
```

### 11.3 Output rules

- `DISPOSITION` is mandatory
- `SELECTED_PROPOSAL_ID` is mandatory and must be `NONE` for non-selection outcomes
- `PRIMARY_BASIS` is mandatory
- `STRONGEST_REASONS` must contain at least one item
- `MAIN_LOSING_ALTERNATIVE_ID` may be `NONE` only when no serious losing alternative exists
- `MAIN_LOSING_REASON` is still required when there was a losing alternative
- `CAUTIONS` may contain exactly `- None.` if empty
- `PLANNING_INSERTION_RECOMMENDED` is advisory only and never becomes plan authority

---

## 12. Deterministic parse and validation layer

This is where the architecture either stays clean or collapses.

The model output must pass a deterministic parser and a deterministic validator before any canonical `SelectionResult` exists.

### 12.1 Parser responsibilities

The parser owns:
- field extraction
- exact sentinel handling
- bounded structural validation
- malformed-output rejection

The parser does not own:
- permission-language policy
- proposal id membership checks beyond simple extraction
- semantic law

### 12.2 Validator responsibilities

The validator owns:
- lawful disposition check
- exactly-one-disposition enforcement
- `selected_proposal_id` membership in `considered_proposal_ids`
- no hidden second winner
- non-selection outcomes requiring rationale
- rejection of forbidden authority words such as `approved`, `ready`, `safe to execute`, `can proceed now`
- ensuring `PLANNING_INSERTION_RECOMMENDED` remains advisory
- ensuring losing-alternative references are lawful

### 12.3 Fail-closed behavior

If validation fails:
- do not silently reinterpret
- do not “best effort” patch into a selection verdict
- return an explicit Selection-local invalid result or error surface
- optionally fall back to deterministic comparator if policy for that slice explicitly allows it

The correct default posture is fail-closed.

---

## 13. Canonical SelectionResult remains unchanged

The architecture should preserve the current canonical Selection contract shape:
- one selected proposal max
- or one explicit non-selection outcome
- bounded rationale

That is good law.
Do not bloat it.

Recommended rule:
- hybrid comparator produces richer intermediate structured output
- final `SelectionResult` remains the public canonical downstream choice object

### 13.1 Rationale construction

`SelectionResult.rationale` should remain concise and inspectable.
It should be built deterministically from the validated hybrid output, not passed through as raw model essay text.

Recommended rationale shape:
- disposition summary
- strongest reason(s)
- strongest losing alternative + why not selected
- decisive caution when relevant

This keeps public Selection truth compact while preserving richer observability separately.

---

## 14. Observability and rationale artifacts

Jeff should not lose inspection just because the public contract stays compact.

Selection should additionally expose a Selection-local support record for operator visibility, for example:
- `SelectionComparisonRecord`
- `SelectionComparisonTrace`
- `SelectionRationaleRecord`

This support record may include:
- comparison input summary
- raw comparison output
- parsed comparison output
- validation issues
- strongest reasons
- losing alternative analysis
- fallback-used flag
- runtime metadata

This record is **not** canonical truth.
It is a support artifact for CLI/debug/review surfaces.

---

## 15. Deterministic fallback path

The current deterministic comparator should not be deleted immediately.
That would be dumb.

It should be retained as one of:
- fallback path when hybrid output is malformed or unavailable
- test baseline for comparison slices
- explicit low-capability mode for constrained runtimes

### 15.1 Recommended fallback policy

Initial safe policy:
- if hybrid comparator is disabled, use deterministic comparator
- if hybrid comparator returns malformed output, fail closed first
- enable deterministic fallback only if explicitly configured for the slice
- when fallback is used, expose that fact in Selection support artifacts and operator surfaces

This prevents silent quality regression hiding inside fallback.

---

## 16. Operator override problem

The operator must be allowed to intervene when Selection rejects, defers, escalates, or chooses a different considered option than the operator wants.

But the operator must **not** be allowed to rewrite history.

That means:
- the original `SelectionResult` must remain exactly what Selection returned
- operator override must exist as a separate downstream object or request
- downstream action formation may choose to respect the override instead of the raw Selection result
- governance still decides whether the resulting action may begin now

If you overwrite `SelectionResult`, you destroy inspectability and lie about what happened.

---

## 17. Operator override design law

The binding law is:
- operator override is a review/control action downstream of Selection
- operator override is not Selection truth
- operator override is not Governance permission
- operator override is not Transition truth mutation
- operator override may redirect downstream effective choice only within lawful bounds

### 17.1 Allowed operator override scope

Operator override may:
- choose one different proposal from the already-considered set
- convert a non-selection result into a chosen considered option
- preserve an existing selected option while adding operator note
- explicitly confirm an escalate path
- explicitly request reproposal instead of selecting from current options

Operator override may **not**:
- invent a new proposal not present in `considered_proposal_ids`
- silently widen scope
- bypass governance
- claim approval
- claim readiness
- claim execution effect
- mutate canonical truth directly

---

## 18. Override classes

There should be only a small bounded set of operator override classes.

Recommended v1 set:
- `choose_considered_option`
- `confirm_non_selection`
- `request_reproposal`
- `cancel_decision_path`

### 18.1 `choose_considered_option`
Use when the operator wants a different option from the ones already proposed.

### 18.2 `confirm_non_selection`
Use when the operator explicitly agrees with `reject_all`, `defer`, or `escalate` and wants that confirmation recorded.

### 18.3 `request_reproposal`
Use when none of the current considered options are acceptable but the operator wants a new proposal pass rather than accepting the current non-selection outcome.
This is **not** an override to a non-considered option.
It is a new upstream request.

### 18.4 `cancel_decision_path`
Use when the operator wants to stop here without forwarding anything to action formation.

---

## 19. OperatorSelectionOverride object

Recommended support/review object:

```json
{
  "override_id": "ovr_...",
  "selection_id": "sel_...",
  "scope": {
    "project_id": "proj_...",
    "work_unit_id": "wu_... | null",
    "run_id": "run_... | null"
  },
  "override_type": "choose_considered_option | confirm_non_selection | request_reproposal | cancel_decision_path",
  "chosen_proposal_id": "prop_... | null",
  "original_disposition": "selected | reject_all | defer | escalate",
  "operator_rationale": "...",
  "created_at": "iso8601",
  "created_by": "operator"
}
```

### 19.1 Hard validation rules

- `selection_id` must resolve to an actual Selection result
- `original_disposition` must match the referenced Selection result
- `chosen_proposal_id` is required for `choose_considered_option`
- `chosen_proposal_id` must be one of `considered_proposal_ids`
- `chosen_proposal_id` must be null for `confirm_non_selection`, `request_reproposal`, and `cancel_decision_path`
- `operator_rationale` is required

This object is a support/review object, not canonical truth and not governance.

---

## 20. Effective decision resolution

Because both Selection and operator override may exist, Jeff needs one downstream resolver.

Recommended object:
- `EffectiveDecisionResolution`

Purpose:
- compute what should actually be forwarded to action formation
- preserve whether the source was raw Selection or operator override
- keep this resolution explicit and inspectable

### 20.1 Resolution rules

1. If there is no operator override, forward raw Selection result.
2. If there is `choose_considered_option`, forward that proposal as effective selected path.
3. If there is `confirm_non_selection`, forward the non-selection outcome as confirmed.
4. If there is `request_reproposal`, stop current decision path and reopen proposal.
5. If there is `cancel_decision_path`, terminate current downstream flow.

### 20.2 Resolution record draft

```json
{
  "resolution_id": "res_...",
  "selection_id": "sel_...",
  "override_id": "ovr_... | null",
  "effective_disposition": "selected | reject_all | defer | escalate | reproposal_requested | cancelled",
  "effective_selected_proposal_id": "prop_... | null",
  "decision_source": "selection | operator_override",
  "resolution_rationale": "..."
}
```

This makes the downstream source explicit.
That matters for audit and CLI truthfulness.

---

## 21. Action formation boundary

Action formation should consume `EffectiveDecisionResolution`, not raw Selection if override is supported.

Why:
- it keeps override outside Selection semantics
- it gives action formation one resolved source of intent
- it keeps audit truth explicit

But action formation still must not turn decision into permission.
It just materializes bounded operational intent.
Governance still owns the start decision.

---

## 22. Governance remains unchanged and load-bearing

Even when the operator overrides Selection, Governance remains in charge of whether the resulting action may start now.

That means:
- override does not imply approval
- override does not imply readiness
- override does not imply lowered risk posture
- override does not bypass stale-basis checks
- override does not bypass blocker checks

The clean law remains:

`effective decision -> action -> governance -> execution`

Any architecture that lets operator override jump straight to execution is garbage.

---

## 23. Interface and CLI implications

The CLI and future GUI must display these distinctions clearly:
- raw Selection result
- operator override presence
- effective decision resolution
- governance result

They must not flatten them into one friendly “chosen path”.

### 23.1 Recommended CLI detail view

Selection detail should show:
- `selection_id`
- disposition
- selected option or non-selection outcome
- strongest reasons
- strongest losing alternative
- whether hybrid comparator or deterministic fallback was used

Operator override detail should show:
- whether an override exists
- override type
- chosen considered option if applicable
- operator rationale

Resolution detail should show:
- effective downstream choice
- source = `selection` or `operator_override`

Governance detail should show separately:
- approval verdict
- readiness state
- blocked / approval-required / allowed / invalidated / escalated posture

This is mandatory to preserve truthfulness.

---

## 24. Memory implications

Memory may later store bounded decision-support memories such as:
- repeated reasons why certain options tend to be rejected
- operator preference patterns that are safe and durable
- durable strategic anti-drift lessons

But memory must not become a hidden chooser.

That means:
- memory may inform Proposal and Selection through lawful context
- memory may not silently override current Selection outcome
- memory may not turn operator preference into untracked default choice
- any operator preference strong enough to guide future selection should be stored as explicit durable support, not hidden behavior

---

## 25. Recommended package/module layout

### 25.1 Selection package

```text
jeff/cognitive/selection/
  __init__.py
  contracts.py
  decision.py                  # current deterministic comparator
  comparison.py                # comparison bundle + result models
  prompt_files.py              # selection prompt loader
  runtime.py                   # runtime handoff for hybrid comparator
  parsing.py                   # parse hybrid comparator output
  validation.py                # deterministic selection-local guardrails
  api.py                       # composed Selection-local entry
  HANDOFF.md
```

### 25.2 Interface / review lane

Recommended new area:

```text
jeff/interface/review/
  selection_override.py
```

Or equivalent downstream review package if you prefer broader review ownership.

### 25.3 Resolution / action handoff

Possible placement:

```text
jeff/cognitive/decision_resolution.py
```

or

```text
jeff/contracts/decision_resolution.py
```

Pick one and keep ownership explicit.
Do not bury this in interface glue.

---

## 26. Suggested implementation slices

### Slice 1 — Selection comparison contract surface
Add:
- comparison bundle model
- hybrid comparator parsed-output model
- package-local handoff updates

Do not add runtime yet.

### Slice 2 — Selection prompt contract
Add:
- `PROMPTS/selection/COMPARISON.md`
- Selection-local prompt loader
- focused tests for markers/placeholders

### Slice 3 — runtime handoff
Add:
- Selection-local runtime call through `ContractRuntime`
- raw comparison result surface
- fail-closed behavior only

### Slice 4 — deterministic parse
Add:
- strict parser for comparison output
- malformed-shape errors

### Slice 5 — deterministic validation / guardrails
Add:
- membership validation
- forbidden authority-language rejection
- lawful disposition enforcement
- SelectionResult emission from validated intermediate output

### Slice 6 — deterministic fallback integration
Add:
- explicit config-controlled fallback mode
- support artifact visibility when fallback is used

### Slice 7 — operator override support
Add:
- `OperatorSelectionOverride`
- validation rules
- CLI/API action request surface for override creation

### Slice 8 — effective decision resolution
Add:
- resolution object
- downstream action formation update to consume resolution
- CLI visibility for raw selection vs override vs effective path

### Slice 9 — hardening and acceptance
Add:
- anti-drift tests
- interface truthfulness tests
- governance boundary tests
- regression tests for override abuse cases

---

## 27. Test obligations

This architecture is useless unless the test suite enforces it.

### 27.1 Selection hybrid tests
Must cover:
- one selected option only
- lawful `reject_all`, `defer`, `escalate`
- selected proposal id must come from considered set
- malformed comparator output fails closed
- forbidden permission language is rejected
- losing-alternative reporting remains bounded
- deterministic fallback path is explicit when used

### 27.2 Override tests
Must cover:
- override cannot change historical `SelectionResult`
- override may only choose from considered set
- override cannot invent proposal ids
- request_reproposal does not masquerade as considered-option choice
- override does not imply governance pass
- override cannot bypass approval-required conditions

### 27.3 Interface truthfulness tests
Must cover:
- raw selection vs override vs effective resolution remain visibly distinct
- selected vs permitted remain visibly distinct
- confirmed non-selection is not shown as selected
- governance outputs remain separate from decision outputs

### 27.4 Orchestrator / downstream tests
Must cover:
- action formation consumes effective decision resolution correctly
- governance still evaluates resulting action normally
- blocked and approval-required outcomes remain intact after override

---

## 28. Main failure modes to defend against

This architecture is failing if any of the following happens:
- hybrid comparator invents a proposal id and code quietly accepts it
- Selection output contains approval/readiness language and code lets it through
- deterministic fallback runs silently with no visibility
- operator override rewrites or replaces the original `SelectionResult`
- interface displays override choice as if Selection originally chose it
- operator override can pick an option that Proposal never produced
- action formation consumes override directly with no explicit resolution step
- governance is skipped because “the human already chose”
- memory becomes a hidden preference override layer
- Selection package expands until it starts owning governance or interface semantics

Any one of those is a real architecture defect, not a cosmetic issue.

---

## 29. Recommended immediate build order

Given current project state, the sane order is:

1. finish Selection comparison contract and prompt surface
2. add hybrid runtime call and parse/validate shell
3. keep deterministic comparator as explicit fallback
4. only then add operator override lane
5. only after override exists, add effective decision resolution and downstream action-formation consumption
6. then harden CLI truthfulness and anti-drift coverage

Do **not** start with override first.
Without hybrid comparison, override becomes a band-aid over a weak comparator instead of a proper human-control lane over a strong comparator.

---

## 30. Final statement

The correct Selection upgrade is not:
- regexes forever
- or model authority everywhere

The correct upgrade is:
- model-assisted semantic comparison
- deterministic contract enforcement
- explicit operator override as a separate downstream lane
- preserved audit truth
- unchanged governance load-bearing boundary

In one sentence:

**Selection may become hybrid, but it must stay non-permissive; operator override may redirect downstream choice, but it must never rewrite Selection history or bypass Governance.**

