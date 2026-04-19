# 3step_transition.md

Status: implementation transition plan for Jeff typed-LLM runtime and Research 3-step pipeline  
Authority: subordinate to `ARCHITECTURE.md`, `PLANNING_AND_RESEARCH_SPEC.md`, `ORCHESTRATOR_SPEC.md`, `INTERFACE_OPERATOR_SPEC.md`, `MEMORY_SPEC.md`, `CORE_SCHEMAS_SPEC.md`, `2step_reseach_transition.md`, and current implementation reality  
Purpose: define the concrete target shape for Jeff's 3-step Research pipeline and the reusable Infrastructure runtime that will later support Research, Proposal, Evaluation, and other typed LLM stages

---

## 1. Why this document exists

Jeff Research already has a usable base:
- bounded source acquisition
- evidence-pack construction
- citation-key remap (`S1..Sn`)
- fail-closed provenance validation
- truthful debug boundaries
- downstream persistence / projection linkage
- Infrastructure-owned runtime/config routing

That base should not be thrown away.

The weakness is the middle of the pipeline.
One-shot strict JSON is too brittle across models and providers.
We want a cheaper and more provider-agnostic path:
- cheap bounded generation first
- deterministic normalization second
- LLM formatting only when needed

At the same time, we do **not** want Research to invent its own one-off infrastructure that Proposal, Evaluation, and future typed LLM stages cannot reuse.

So this document does two things together:
1. defines the **Research 3-step pipeline**
2. defines the **reusable Infrastructure runtime shape** that can serve Research now and other typed LLM stages later

---

## 2. Core decision

Jeff Research will move to this target flow:

`source acquisition -> evidence pack -> Step 1 bounded text artifact -> Step 2 deterministic transformer -> Step 3 formatter fallback only if needed -> remap -> provenance -> persistence/render -> optional memory handoff`

Interpretation:
- Step 2 deterministic transformation is the **primary** normalization path
- Step 3 formatter is **fallback-only**, not the normal success path
- Step 3 uses the **already-produced bounded text artifact**, not the original evidence pack again
- downstream remap / provenance / persistence / render remain unchanged

Infrastructure must support this as one reusable strategy called:
- `bounded_text_then_parse`

and optionally its fallback variant:
- `bounded_text_then_formatter`

This same Infrastructure must later be able to support:
- `plain_text`
- `native_json_schema`
- `baml_contract`
- and other typed-output strategies when justified

---

## 3. Non-negotiable boundaries

The following must remain true:
- Research is support, not truth
- evidence-first research remains
- citation-key remap remains
- remap to internal `source_id` remains downstream
- fail-closed provenance remains downstream
- persistence / projection / render remain downstream
- memory handoff semantics remain downstream
- Interface remains downstream only
- Orchestrator sequences stages but does not own parsing or research semantics
- Infrastructure owns runtime/config and routing, but does not own Jeff semantics

If a proposal violates any of the above, it is wrong.

---

## 4. Why this is better than one-shot JSON

One-shot strict JSON looks tidy but is fragile.
Across providers and local models it causes:
- malformed JSON
- fenced JSON
- schema-incomplete JSON
- wrong field names
- wrong nested types
- repeated retries and repair calls

That is bad not only for reliability but also for token cost.

The 3-step model is usually cheaper because:
- Step 1 uses a smaller, cheaper bounded syntax instead of exact JSON
- Step 2 is pure local deterministic code
- Step 3 runs only on the failure tail
- Step 3 works on the already-created bounded artifact, not the original full evidence pack

So the expected cost is usually lower than:
- always forcing exact JSON in Step 1, or
- always doing two LLM passes

---

## 5. Open-source decisions

We are building this as a hybrid system.
We will use open-source parts for generic plumbing only.
Jeff keeps ownership of its semantics.

### 5.1 Use now

#### Instructor
Decision: **USE NOW**  
Role: multi-provider typed LLM call layer  
Where: Step 3 formatter fallback; later other typed LLM contracts  
Why:
- practical provider-swappable structured output layer
- works well as a thin typed wrapper
- useful for future Proposal / Evaluation typed outputs too

Constraint:
- Instructor does **not** define Jeff research semantics
- Instructor does **not** own fallback policy
- Instructor does **not** replace Infrastructure routing

#### Guardrails
Decision: **OPTIONAL NOW / LIMITED USE**  
Role: extra validation helpers where useful  
Where: post-Step-3 checks or selected validator composition  
Why:
- can help with custom validator packaging
- can be useful where a validator is clearer there than in ad hoc code

Constraint:
- core Jeff fail-closed validation still remains Jeff-owned
- do not let Guardrails become hidden semantic repair

### 5.2 Optional later

#### Outlines
Decision: **OPTIONAL LATER**  
Role: constrained generation for controlled backends  
Where: possible future optimization of Step 1 on selected local backends  
Why:
- useful only if we control the inference backend well enough
- useful only if it actually reduces failure rate materially

Constraint:
- not required for the first implementation
- not a reason to redesign Step 1 around backend-specific grammar machinery

#### BAML
Decision: **OPTIONAL LATER**  
Role: contract layer for selected typed LLM flows  
Where: likely Step 3 formatter later; possibly Proposal / Evaluation later  
Why:
- can become useful once provider fallback trees and typed contracts get richer
- can help with contract testing and provider fallback orchestration

Constraint:
- do not adopt BAML as the primary Jeff runtime backbone now
- do not make Jeff Infrastructure subordinate to BAML
- do not use BAML for Step 2 deterministic transformation

### 5.3 Jeff-owned only

These remain fully Jeff-owned:
- Step 1 syntax contract
- Step 1 prompt builder
- Step 2 deterministic transformer
- all research semantics
- finding / inference / uncertainty / recommendation separation
- citation-key discipline
- fallback eligibility policy
- fail-closed downstream rules
- provider/capability routing policy
- purpose routing policy

---

## 6. Research target architecture

### 6.1 Final flow

```text
source acquisition
  -> evidence pack
  -> Step 1 bounded text generation
  -> Step 1 syntax precheck
  -> Step 2 deterministic transformer
      -> success -> validated canonical research JSON
      -> structural failure -> Step 3 formatter fallback eligibility check
  -> Step 3 formatter fallback
  -> strict output validation
  -> citation remap
  -> provenance validation
  -> persistence
  -> projection/render
  -> optional memory handoff
```

### 6.2 Key interpretation

- Step 1 owns semantic synthesis from evidence
- Step 2 owns mechanical normalization only
- Step 3 owns formatting fallback only
- Step 3 does **not** analyze the original evidence pack again
- Step 3 receives the already-created bounded artifact plus the exact target schema

### 6.3 Cost posture

Research default strategy should be:
- `bounded_text_then_parse`

Research fallback path should be:
- `bounded_text_then_formatter`

Research should **not** default to:
- `native_json_schema`
- `baml_contract`

Those may become useful for selected models later, but they are not the cheap default.

---

## 7. Research step definitions

## Step 1 — bounded text artifact generation

### Responsibility
Generate a bounded text artifact from the evidence pack in a very hard syntax.

### Input
- research question
- evidence pack
- citation keys only (`S1..Sn`)
- no internal `source_id`

### Output class
A text artifact in strict syntax.
Not JSON.
Not persisted artifact shape.
Not backend-coupled.

### Initial syntax contract

```text
SUMMARY:
<one bounded paragraph>

FINDINGS:
- text: <finding 1>
  cites: S1,S2
- text: <finding 2>
  cites: S3

INFERENCES:
- <inference 1>
- <inference 2>

UNCERTAINTIES:
- <uncertainty 1>
- <uncertainty 2>

RECOMMENDATION:
<text or NONE>
```

### Step 1 rules
Must:
- answer only from evidence
- use citation keys only
- keep findings separate from inference
- keep uncertainties explicit
- keep recommendation bounded
- return bounded text in the declared syntax

Must not:
- return JSON
- return fenced code
- emit internal `source_id`
- invent findings
- invent citations
- drift into essay format

### Ownership
Jeff-owned.
No open-source tool owns this contract.

---

## Step 2 — deterministic transformer

### Responsibility
Parse the Step 1 artifact and convert it into the exact canonical research JSON shape expected by downstream Research.

### Input
- Step 1 bounded text artifact

### Output
- exact canonical research JSON object
- still citation-key based
- no semantic widening

### Allowed operations
May:
- split named sections
- verify section presence
- parse finding entries and citation lists
- normalize arrays and nulls
- trim whitespace
- map `RECOMMENDATION: NONE` to `null`
- fail closed when syntax is materially broken

### Forbidden operations
Must not:
- infer missing findings
- invent summary text
- transform uncertainty into finding
- transform finding into inference
- create recommendation from nearby text
- guess missing citations
- merge semantic families to make output pass

### Failure classes
Step 2 should fail when:
- required headers are missing
- findings entries are malformed
- required citations are absent
- citation pattern is invalid
- ordering/shape is too broken for safe parse
- ambiguity would require semantic interpretation

### Ownership
Jeff-owned pure deterministic code.
This is not the place for BAML, Instructor, or a second LLM call.

---

## Step 3 — formatter fallback

### Responsibility
Convert the existing Step 1 bounded artifact into the exact canonical research JSON shape only when Step 2 could not safely do so.

### Input
- original Step 1 bounded text artifact
- exact target JSON schema
- strict formatting-only instructions
- optionally a minimal metadata hint set such as allowed citation-key family

### Output
- exactly one canonical research JSON object

### Important cost rule
Step 3 receives:
- the already-created bounded artifact
- not the original evidence pack
- not the full raw source set again

This is what keeps Step 3 cheap.

### Allowed behavior
May:
- place already-present content into exact fields
- normalize arrays / nulls / field layout
- preserve citation keys

Must not:
- invent claims
- invent citations
- add content not materially present
- become a second research reasoner
- reinterpret evidence freely

### When Step 3 may run
Only when:
- Step 1 completed successfully
- Step 1 passed syntax precheck
- Step 2 failed
- Step 2 failure is structural, not substantive
- the artifact still appears materially complete enough to format without guessing

### When Step 3 must not run
Must fail closed when:
- Step 1 omitted essential content
- findings lack required citations
- artifact is too broken to know what content exists
- Step 3 would need to guess missing substance

### Ownership
- Step 3 orchestration policy: Jeff-owned
- Step 3 typed LLM call wrapper: Instructor now
- BAML: optional later replacement or companion contract layer, not required in the first version

---

## 8. Research validation stack

### 8.1 Step 1 syntax precheck
Jeff-owned.

Checks:
- no fenced code block wrapper
- required top-level headers exist
- artifact is text, not JSON
- findings section exists
- citation tokens match `S<number>` where present

### 8.2 Step 2 output validation
Jeff-owned.

Checks:
- exact canonical schema shape
- required fields present
- findings array valid
- each finding has text and citation keys
- no forbidden backend fields (`source_id`, `source_ref`, etc.)
- citation keys remain keys, not remapped ids

### 8.3 Step 3 formatter output validation
Jeff-owned, with optional Guardrails assistance.

Checks:
- same canonical schema validation
- no extra fields
- no fabricated citation forms
- content-preserving relative to Step 1 artifact

### 8.4 Downstream validation
Unchanged Jeff-owned.

Checks:
- citation remap
- provenance validation
- persistence assumptions
- projection/render assumptions

---

## 9. Research package target structure

```text
jeff/cognitive/research/
├── __init__.py
├── contracts.py
├── bounded_syntax.py
├── synthesis.py
├── deterministic_transformer.py
├── formatter.py
├── validators.py
├── fallback_policy.py
├── debug.py
├── documents.py
├── web.py
├── persistence.py
├── memory_handoff.py
├── errors.py
└── legacy.py
```

### File-by-file intent

#### `contracts.py`
Keep and extend.
Owns:
- EvidencePack / source-side contracts
- final canonical Research artifact schema
- any new intermediate contract models that are truly schema-level

#### `bounded_syntax.py`
New.
Owns:
- Step 1 syntax contract
- prompt builder for Step 1
- cheap syntax precheck helpers

#### `synthesis.py`
Modify.
Owns:
- orchestration of Step 1 -> Step 2 -> Step 3 within Research
- no longer a one-shot JSON-first file
- should coordinate, not hide old repair-only semantics

#### `deterministic_transformer.py`
New.
Owns:
- Step 2 parse and normalization logic
- explicit structured failure reasons

#### `formatter.py`
New.
Owns:
- Step 3 formatter request builder
- formatter-specific typed call wrapper usage
- no research semantics beyond formatting contract

#### `validators.py`
New.
Owns:
- Step 1 syntax checks
- Step 2 / Step 3 schema checks
- citation-key checks
- forbidden-field checks
- content-preservation checks where feasible

#### `fallback_policy.py`
New.
Owns:
- classification of Step 2 failure types
- decision whether Step 3 is allowed
- fail-closed policy when content is missing

#### `debug.py`
Keep and extend.
Owns:
- truthful debug checkpoint helpers
- stage names aligned to real 3-step boundaries

#### `documents.py`
Keep.
Still owns local document acquisition.

#### `web.py`
Keep.
Still owns web acquisition.

#### `persistence.py`
Keep.
Still owns local research artifact persistence.

#### `memory_handoff.py`
Keep.
Still owns selective research-to-memory distillation handoff.

#### `errors.py`
Keep.
Still owns research-specific exception classes.

#### `legacy.py`
Keep temporarily, retire later.
Use only as bounded compatibility shim while the old compatibility surface still exists.
Do not let it own new semantics.

---

## 10. Infrastructure target architecture

Research should not create bespoke runtime hacks.
Infrastructure must expose reusable typed-LLM runtime decisions.

### 10.1 Infrastructure responsibilities
Infrastructure must own:
- adapter abstraction
- provider registry
- runtime config loading
- purpose routing
- capability profiles
- fallback policies
- output strategy selection
- retry / timeout posture
- typed LLM call wrappers
- observability/telemetry hooks

Infrastructure must not own:
- research semantics
- proposal semantics
- evaluation semantics
- deterministic parsing semantics
- Jeff canonical truth semantics

---

## 11. LLM contract runtime

Add a reusable Infrastructure layer above adapters.

### 11.1 Core concepts

#### `purpose_router`
Given a purpose such as:
- `research_step1`
- `research_formatter`
- `proposal_generation`
- `evaluation_summary`

select the configured capability profile and output strategy.

#### `capability_profiles`
For each model/provider pair, capture things such as:
- strong at plain text
- good at bounded syntax
- reliable at native structured output
- good cheap formatter
- good long-context reasoner
- high-latency / low-latency posture
- cost posture

These profiles are Jeff-owned policy data, not provider dogma.

#### `fallback_policies`
Define:
- when retry is allowed
- when fallback to another model is allowed
- when failure is structural vs substantive
- when fail-closed is required

#### `output_strategies`
Infrastructure must support multiple strategies, not one hardcoded path.

Required strategy families:
- `plain_text`
- `bounded_text_then_parse`
- `bounded_text_then_formatter`
- `native_json_schema`
- `baml_contract`

Research uses mainly:
- `bounded_text_then_parse`
- `bounded_text_then_formatter`

Proposal later may use:
- `plain_text`
- `native_json_schema`
- `baml_contract`

Evaluation later may use:
- `native_json_schema`
- `baml_contract`
- or plain text depending on size and value

---

## 12. Infrastructure package target structure

```text
jeff/infrastructure/
├── __init__.py
├── runtime.py
├── config.py
├── purposes.py
├── capability_profiles.py
├── fallback_policies.py
├── output_strategies.py
├── contract_runtime.py
├── typed_calls/
│   ├── __init__.py
│   ├── instructor_runtime.py
│   ├── guardrails_runtime.py
│   └── baml_runtime.py
├── model_adapters/
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   ├── factory.py
│   └── providers/
│       └── ...
└── telemetry/
    ├── __init__.py
    └── llm_events.py
```

### File-by-file intent

#### `runtime.py`
Modify.
Assemble the Infrastructure services object.
Wire together:
- adapter registry
- purpose router
- output strategy runtime
- fallback policy runtime

#### `config.py`
New or expand current config loading.
Owns runtime config structures for:
- model choices by purpose
- fallback chains
- strategy defaults
- timeout/cost posture

#### `purposes.py`
New.
Owns stable purpose names and purpose families.
Examples:
- `research_step1`
- `research_formatter`
- `proposal_generation`
- `evaluation_structured`

#### `capability_profiles.py`
New.
Owns capability metadata and selection helpers.

#### `fallback_policies.py`
New.
Owns provider/model fallback decisions.
This is Infrastructure-level fallback logic.
Research-level semantic fallback eligibility still remains in Research.

#### `output_strategies.py`
New.
Owns strategy definitions and selection helpers.
This is where `bounded_text_then_parse`, `native_json_schema`, etc. become first-class runtime options.

#### `contract_runtime.py`
New.
Owns the reusable “LLM contract runtime” above raw adapters.
Given a purpose and strategy, it dispatches to the correct typed call helper.

#### `typed_calls/instructor_runtime.py`
New.
Thin wrapper for Instructor-backed typed calls.
Used first by Research Step 3.
Later reusable for Proposal / Evaluation.

#### `typed_calls/guardrails_runtime.py`
Optional now.
Used only where it adds real value for validation composition.
Do not let it become core semantic logic.

#### `typed_calls/baml_runtime.py`
Optional later.
Keep the slot in the design, but do not implement first unless there is a real need.

#### `model_adapters/*`
Keep and extend.
Still own low-level provider-neutral adapter interfaces and provider implementations.

#### `telemetry/llm_events.py`
New.
Owns low-level LLM runtime event emission so debug and operator surfaces remain truthful without polluting module semantics.

---

## 13. How Research should use Infrastructure

Research must not manually pick models in scattered files.
Research should say something like:
- purpose: `research_step1`
- strategy: `bounded_text_then_parse`

or for fallback:
- purpose: `research_formatter`
- strategy: `bounded_text_then_formatter`

Infrastructure then decides:
- which model/provider profile to use
- whether the configured path uses plain adapter calls or Instructor
- timeout/retry posture
- optional provider fallback if transport/runtime failure occurs

Important:
- Research owns semantic fallback eligibility
- Infrastructure owns technical model/provider routing

That split must stay hard.

---

## 14. Proposal and Evaluation implications

This document is mainly for Research, but Infrastructure should be shaped for reuse.

### Proposal
Proposal may later benefit from:
- `plain_text` for cheap option generation
- `native_json_schema` for tighter typed candidate sets
- `baml_contract` if candidate contract testing and provider fallback become important

Proposal should not need its own private provider-routing code.

### Evaluation
Evaluation may later benefit from:
- `native_json_schema` when a tight verdict schema is useful
- `baml_contract` for testable evaluation contracts if the layer grows more structured
- plain text when output is naturally small and typed rigidity adds no value

Evaluation should reuse the same Infrastructure runtime instead of inventing a custom structured-output path.

---

## 15. Debug and observability

The 3-step pipeline needs truthful stage visibility.

### Research debug checkpoints should become:
- `content_generation_started`
- `content_generation_succeeded`
- `content_generation_failed`
- `syntax_precheck_failed`
- `deterministic_transform_started`
- `deterministic_transform_succeeded`
- `deterministic_transform_failed`
- `formatter_fallback_started`
- `formatter_fallback_succeeded`
- `formatter_fallback_failed`
- `citation_remap_started`
- `citation_remap_succeeded`
- `provenance_validation_started`
- `provenance_validation_succeeded`
- `provenance_validation_failed`

These must correspond to real steps, not optimistic labels.

Infrastructure telemetry should expose:
- selected purpose
- selected strategy
- selected capability profile
- adapter/provider used
- retry/fallback events
- token usage if available

But telemetry must remain telemetry, not semantic truth.

---

## 16. Migration plan

## Slice 1 — Introduce Infrastructure strategy vocabulary

Goal:
- add reusable Infrastructure concepts without changing live Research behavior yet

Files:
- `jeff/infrastructure/purposes.py`
- `jeff/infrastructure/output_strategies.py`
- `jeff/infrastructure/capability_profiles.py`
- `jeff/infrastructure/contract_runtime.py` (minimal shell)
- small updates to `runtime.py`

Must remain unchanged:
- current research behavior
- persistence
- provenance
- memory handoff

Acceptance:
- Infrastructure can describe `research_step1` and `research_formatter`
- no behavior switch yet

## Slice 2 — Add Step 1 syntax contract and Step 2 transformer

Goal:
- build the cheap primary path

Files:
- `jeff/cognitive/research/bounded_syntax.py`
- `jeff/cognitive/research/deterministic_transformer.py`
- `jeff/cognitive/research/validators.py`
- `jeff/cognitive/research/synthesis.py`

Must remain unchanged:
- Step 3 formatter fallback not yet live
- downstream remap/provenance/persistence behavior

Acceptance:
- Research can produce bounded text artifact
- deterministic transformer can parse valid artifacts
- invalid artifacts fail closed

## Slice 3 — Add formatter fallback through Instructor

Goal:
- add the cheap-on-failure formatter rescue path

Files:
- `jeff/cognitive/research/formatter.py`
- `jeff/cognitive/research/fallback_policy.py`
- `jeff/infrastructure/typed_calls/instructor_runtime.py`
- `jeff/infrastructure/runtime.py`
- `jeff/infrastructure/purposes.py`

Must remain unchanged:
- downstream remap/provenance/persistence semantics
- Interface and Orchestrator ownership boundaries

Acceptance:
- Step 3 runs only after Step 2 structural failure
- Step 3 uses Step 1 artifact, not original evidence pack
- formatter output is revalidated strictly

## Slice 4 — Align debug and telemetry

Goal:
- make stage visibility truthful

Files:
- `jeff/cognitive/research/debug.py`
- `jeff/infrastructure/telemetry/llm_events.py`
- any CLI/operator rendering glue needed later

Acceptance:
- debug labels correspond to real 3-step stages
- runtime strategy selection is inspectable

## Slice 5 — Optional Guardrails use

Goal:
- add selected validator composition only where it truly improves clarity

Files:
- `jeff/infrastructure/typed_calls/guardrails_runtime.py`
- optional `validators.py` integration points

Acceptance:
- no semantic repair hidden inside Guardrails

## Slice 6 — Optional BAML adoption later

Goal:
- add BAML only if formatter/proposal/evaluation contract complexity actually justifies it

Files:
- `jeff/infrastructure/typed_calls/baml_runtime.py`
- selected contract wrappers only

Acceptance:
- Jeff Infrastructure remains the owner of routing and semantics
- BAML remains a plugin-like contract backend, not the architecture owner

---

## 17. First recommended build slice

The smallest correct first slice is:

### First slice
Introduce the reusable Infrastructure strategy vocabulary.

Why first:
- it strengthens Infrastructure for Research now and Proposal/Evaluation later
- it does not risk breaking the already-working Research pipeline
- it prevents the 3-step Research refactor from becoming a one-off hardcoded hack

### Exact first-slice outputs
- stable purpose names for `research_step1` and `research_formatter`
- stable output strategy names
- capability profile concept introduced
- minimal contract runtime shell introduced
- no live behavioral change yet

This is the right first move because it creates the reusable backbone before touching the Research middle path.

---

## 18. Final recommendation

The target shape should be:

- Research default path:
  - `bounded_text_then_parse`
- Research fallback path:
  - `bounded_text_then_formatter`
- Infrastructure reusable runtime:
  - `purpose_router`
  - `capability_profiles`
  - `fallback_policies`
  - `output_strategies`
  - `contract_runtime`

Open-source parts should be adopted narrowly:
- use Instructor now for Step 3 typed fallback calls
- use Guardrails only where it clearly helps validation composition
- keep Outlines optional later
- keep BAML optional later

Hard rule:
- Jeff owns semantics
- Infrastructure owns routing/runtime
- open-source tools remain replaceable helpers

That gives Jeff a Research pipeline that is:
- cheaper than one-shot strict JSON on average
- more provider-agnostic
- easier to debug
- easier to extend later into Proposal and Evaluation without inventing new per-module hacks
