# 3step_research_transition.md

Status: implementation transition plan for Jeff Research  
Authority: subordinate to `2step_reseach_transition.md`, `PLANNING_AND_RESEARCH_SPEC.md`, `ARCHITECTURE.md`, `ORCHESTRATOR_SPEC.md`, `INTERFACE_OPERATOR_SPEC.md`, `MEMORY_SPEC.md`, and current Jeff research implementation reality  
Purpose: define the concrete hybrid 3-step research architecture for Jeff using a mix of selected open-source components and Jeff-owned logic

---

## 1. Why this document exists

The current Jeff research pipeline already has important pieces working:
- evidence-first research
- citation-key remap (`S1..Sn`)
- fail-closed provenance validation
- bounded repair behavior
- truthful debug boundaries
- downstream persistence / projection linkage
- Infrastructure-owned runtime/config routing

That base should not be thrown away.

However, the current one-shot JSON-oriented synthesis shape remains too brittle across models and providers. The system needs a more provider-agnostic and more failure-tolerant middle section.

This document defines the target hybrid architecture:

1. **Step 1 — bounded syntax artifact generation**
2. **Step 2 — deterministic transformer**
3. **Step 3 — LLM formatter fallback**

Then Jeff continues through the existing downstream path:
- citation remap
- provenance validation
- persistence
- projection/render
- optional memory handoff

This is not a broad rewrite.
This is a bounded restructuring of the middle of the research pipeline.

---

## 2. Core decision

Jeff Research will move to this target flow:

`source acquisition -> evidence pack -> Step 1 bounded syntax artifact -> Step 2 deterministic transformer -> Step 3 LLM formatter fallback only if needed -> remap -> provenance -> persistence/render`

Important interpretation:
- **deterministic transformation is the primary normalization path**
- **LLM formatting is fallback, not the default success path**
- **formatter is formatting-only and must not become a second reasoner**

This is the key architectural change.

---

## 3. What stays unchanged

The following Jeff behaviors remain unchanged:
- evidence-first research model
- existing source acquisition and evidence-pack construction
- citation-key remap (`S1..Sn`)
- remap from citation keys back to internal `source_id`
- fail-closed provenance validation
- persistence rules
- projection/render rules
- memory handoff semantics
- Interface as downstream only
- Infrastructure ownership of runtime and provider configuration
- research artifacts remain support artifacts, not truth

If a migration step threatens any of the above, the migration is wrong.

---

## 4. Why 3 steps instead of the earlier 2-step idea

The earlier 2-step idea was:
- Step 1 content synthesis
- Step 2 LLM formatter

That is better than one-shot strict JSON, but it still has a weakness:
if Step 2 is always an LLM, then the fallback layer remains semantic-risky and provider-dependent.

The hybrid 3-step model is stronger because it inserts a mechanical stage first:

- Step 1 produces a bounded artifact in a very hard syntax
- Step 2 tries to convert that artifact deterministically
- Step 3 uses a small formatter model only when the deterministic path fails

This reduces cost, reduces model dependence, improves auditability, and makes cross-provider behavior less fragile.

---

## 5. Open-source parts we will use

We will not try to outsource Jeff semantics.
We will only take open-source parts that solve generic plumbing problems.

### 5.1 Use now

#### A. Instructor
**Use:** yes  
**Role:** main multi-provider structured LLM I/O layer  
**Why:** gives a practical typed/validated output layer over many providers and local/remote backends  
**Where used:** Step 3 formatter fallback, and possibly future typed research helper calls

We use Instructor as a thin provider-swappable structured-output layer.
We do **not** let it define Jeff research semantics.

#### B. Guardrails
**Use:** yes  
**Role:** validation and guard layer  
**Why:** useful for custom validators and fail-closed post-generation checks  
**Where used:** after Step 2 deterministic transformation and after Step 3 formatter fallback

We will mainly use it for custom validation patterns where useful.
If a Jeff-specific validator is simpler in native Python, we keep it native.

### 5.2 Use later / optional

#### C. Outlines
**Use:** optional later  
**Role:** constrained generation / grammar-backed structured generation for selected local backends  
**Why:** useful when we fully control inference backend and want a stricter Step 1 generation path  
**Where used:** optional optimization path for Step 1 or future backend-specific strict modes

Outlines is **not** required for the first build of this 3-step architecture.
It is a future optimization or alternate backend strategy.

#### D. BAML
**Use:** not in the first implementation  
**Role:** possible future provider/fallback orchestration layer  
**Why not now:** it overlaps too much with what Instructor plus Jeff-owned routing can already do; adding both immediately would create unnecessary abstraction sprawl

BAML may be revisited later if provider routing, retries, and fallback trees become much more complex.

### 5.3 Jeff-owned only

The following stays fully Jeff-owned:
- Step 1 syntax contract
- Step 2 deterministic transformer
- all research semantics
- finding / inference / uncertainty / recommendation separation
- citation-key discipline
- fail-closed provenance rules
- downstream remap and persistence semantics
- routing policy for when to invoke Step 3 fallback

No open-source tool should own those rules.

---

## 6. High-level architecture

```text
source acquisition
    -> evidence pack
    -> Step 1 bounded syntax generation
    -> syntax precheck
    -> Step 2 deterministic transformer
        -> if success: validated canonical JSON
        -> if fail: Step 3 formatter fallback
    -> Step 3 LLM formatter fallback
    -> strict validation
    -> citation remap
    -> provenance validation
    -> persistence
    -> projection/render
    -> optional memory handoff
```

### Architectural interpretation
- Step 1 produces a **text artifact**, not final canonical JSON
- Step 2 attempts a **mechanical conversion**, not semantic repair
- Step 3 is a **bounded formatting fallback**, not a second reasoning stage
- remap/provenance/persistence remain downstream and unchanged

---

## 7. Step-by-step ownership map

## Step 1 — bounded syntax artifact generation

### Responsibility
Generate a bounded text artifact from evidence using a very hard syntax.

### Shape class
This is a **research-local text artifact**, not a persisted artifact and not final canonical JSON.

### Input
- research question
- evidence pack
- citation keys only (`S1..Sn`)
- no backend `source_id`

### Output
A text artifact in a strict syntax such as:

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

### Hard rules
Step 1 must:
- answer only from evidence
- use citation keys only
- keep findings separate from inference
- keep uncertainties explicit
- keep recommendation bounded
- avoid fenced code blocks
- avoid JSON output
- avoid backend source IDs

Step 1 must not:
- return final persisted artifact schema
- embed internal `source_id`
- invent citations
- invent findings
- use freeform essay format

### Open-source or custom?
**Primary implementation:** Jeff-owned  
**Why:** this syntax contract is Jeff-specific and tied to Jeff semantics  
**Open-source help:** optional future use of Outlines for stricter backend-specific generation, but not required initially

### First implementation choice
Implement with Jeff-owned prompt builder and Jeff-owned syntax precheck.
Do not wait for Outlines.

---

## Step 2 — deterministic transformer

### Responsibility
Parse the Step 1 text artifact and convert it into the exact Jeff canonical research JSON shape expected by downstream validation and persistence.

### Input
- Step 1 bounded syntax text artifact

### Output
- exact canonical research JSON object
- still citation-key based
- no semantic widening

### Allowed operations
Step 2 may:
- split the artifact into named sections
- validate section presence
- parse findings entries and citation lists
- normalize list shapes
- trim whitespace
- map `RECOMMENDATION: NONE` to `null`
- insert empty arrays for missing but semantically empty optional sections when this is explicitly allowed by the syntax contract
- fail closed when the syntax is materially broken

### Forbidden operations
Step 2 must not:
- infer missing findings
n- create summary text
- reinterpret a finding as an inference
- reinterpret an uncertainty as a finding
- create recommendation text from other sections
- repair broken citations by guessing
- move content between semantic families just to make output pass

### Failure classes
Step 2 should fail when:
- required section headers are missing
- findings block is malformed
- finding entries are missing text or citations
- citation keys do not match the allowed pattern
- section ordering or structure is too broken for a safe parse
- there is ambiguity requiring semantic interpretation

### Open-source or custom?
**Primary implementation:** Jeff-owned  
**Why:** this is Jeff’s semantic boundary; generic parsers do not know which transformations are lawful vs forbidden  
**Open-source help:** none required; plain Python is enough

### Implementation note
This transformer should be simple, explicit, and heavily unit-tested.
Do not make it “smart.”
A dumb honest parser is better than a clever liar.

---

## Step 3 — LLM formatter fallback

### Responsibility
Convert the Step 1 text artifact into the exact canonical research JSON shape only when Step 2 deterministic transformation cannot safely do so.

### Input
- original Step 1 bounded syntax artifact
- exact target canonical JSON schema
- strict formatter prompt forbidding semantic widening

### Output
- exactly one JSON object matching the canonical research schema

### Hard rules
Step 3 may:
- normalize shape
- place content into the expected fields
- preserve citation keys
- output required arrays and nulls correctly

Step 3 must not:
- invent findings
- invent citations
- add new claims
- derive recommendation from “general understanding”
- reinterpret evidence beyond what is already materially present in the syntax artifact
- become a second reasoner

### When Step 3 may run
Step 3 runs only when:
- Step 1 completed
- Step 1 syntax artifact still looks materially recoverable
- Step 2 failed for structural/formatting reasons
- failure reason does not imply missing substantive content

### When Step 3 must not run
Step 3 must not run when:
- Step 1 artifact is substantively incomplete
- citations are absent for findings that require them
- the syntax artifact is too broken to know what content exists
- the model would need to guess missing content

In those cases, the flow fails closed.

### Open-source or custom?
**Primary implementation:** use **Instructor**  
**Why:** it gives provider-swappable structured output over typed Pydantic models and is a good fit for formatter fallback calls  
**Validation help:** use **Guardrails** where useful and Jeff-native validation everywhere else needed

### First implementation choice
Use Instructor as the single LLM fallback wrapper.
Do not bring in BAML here in the first implementation.

---

## 8. Validation stack

Validation is not one thing.
This architecture needs several checks.

### 8.1 Step 1 syntax precheck
Jeff-owned.

Checks:
- no fenced code block wrapper
- required top-level section headers exist
- artifact is text, not JSON
- citation tokens match `S<number>` where present
- findings section is present

Purpose:
- cheap rejection before the deterministic transformer

### 8.2 Step 2 output validation
Jeff-owned, optionally supplemented by Guardrails.

Checks:
- exact canonical schema shape
- required fields present
- findings array valid
- each finding has text plus citation keys
- no forbidden fields such as `source_id`, `source_ref`, `description`, `finding`
- citation keys preserved as keys, not remapped ids

### 8.3 Step 3 formatter output validation
Jeff-owned, optionally supplemented by Guardrails.

Checks are the same as Step 2 output validation, plus:
- verify formatter did not introduce fields not in the schema
- verify formatter did not fabricate citation formats
- verify output still appears content-preserving relative to the Step 1 artifact

### 8.4 Downstream validation
Unchanged Jeff-owned.

Checks:
- citation remap
- provenance validation
- persistence validation
- projection/render assumptions

---

## 9. Canonical decision policy

This section defines exactly when each step is allowed.

### 9.1 Step 1 always runs
The system always starts with Step 1 bounded syntax generation.

### 9.2 Step 2 runs by default after Step 1
The deterministic transformer is always attempted first after Step 1 syntax precheck passes.

### 9.3 Step 3 is fallback-only
Step 3 runs only if all of the following are true:
- Step 1 completed successfully
- Step 1 output passed syntax precheck
- Step 2 failed
- Step 2 failure is structural rather than substantive
- the artifact still appears bounded and materially complete enough to format without guessing

### 9.4 Immediate fail-closed cases
The pipeline must fail closed immediately when any of the following occurs:
- Step 1 omitted findings required by the question
- Step 1 omitted citation keys for findings that claim support
- Step 1 returned unusable freeform prose rather than the required syntax
- Step 2 detects ambiguity that would require semantic interpretation
- Step 3 output is schema-invalid
- Step 3 output appears to have invented content
- downstream provenance validation fails

---

## 10. Exact ownership by layer

### Cognitive / Research owns
- Step 1 request building
- Step 1 syntax contract
- Step 2 deterministic transformer
- Step 3 formatter prompt contract
- research-specific validation rules

### Infrastructure owns
- provider configuration
- model selection
- model purpose routing
- Instructor integration wrapper
- optional future Outlines integration

### Interface owns
- downstream rendering only
- debug visibility only
- no research semantic ownership

### Orchestrator owns
- stage sequencing only
- not parsing rules
- not semantic rescue logic

---

## 11. Concrete component plan

## 11.1 Components we will build ourselves

### A. `bounded_syntax.py`
Purpose:
- define Step 1 syntax contract
- build Step 1 prompts
- provide syntax precheck helpers

### B. `deterministic_transformer.py`
Purpose:
- parse Step 1 artifact
- emit canonical research JSON
- return structured failure reasons

### C. `validators.py`
Purpose:
- Step 1 syntax checks
- Step 2/3 schema checks
- forbidden-field checks
- citation-key checks
- content-preservation checks where feasible

### D. `fallback_policy.py`
Purpose:
- classify deterministic transformer failures
- decide whether Step 3 fallback is allowed
- fail closed on substantive incompleteness

## 11.2 Components we will use from open source

### A. Instructor integration wrapper
Purpose:
- make Step 3 formatter fallback provider-swappable
- validate response into Pydantic target schema

### B. Guardrails hooks
Purpose:
- support custom validator composition if useful
- provide additional fail-closed confidence around formatter output

## 11.3 Components we will not build in the first version
- BAML provider orchestration
- Outlines-constrained Step 1 generation
- advanced semantic diffing between Step 1 and Step 3
- generalized agent framework integration

---

## 12. Canonical Step 1 syntax contract

The initial syntax contract should be as small as possible.

### Required sections
- `SUMMARY:`
- `FINDINGS:`
- `INFERENCES:`
- `UNCERTAINTIES:`
- `RECOMMENDATION:`

### Section rules

#### `SUMMARY:`
- one bounded paragraph
- required

#### `FINDINGS:`
- zero or more bullet-style entries only in the approved syntax
- each entry must contain:
  - `text:`
  - `cites:`
- `cites:` must be comma-separated `S<number>` keys

#### `INFERENCES:`
- zero or more bullet lines
- no citation requirement at this layer unless later canon changes it

#### `UNCERTAINTIES:`
- zero or more bullet lines
- must remain uncertainty-shaped, not rebranded findings

#### `RECOMMENDATION:`
- either bounded text
- or exact literal `NONE`

### Example

```text
SUMMARY:
The evidence suggests X is the strongest current explanation, but there is still uncertainty around Y.

FINDINGS:
- text: Source S1 states that A increased by 12% in 2024.
  cites: S1
- text: Sources S2 and S3 both describe a supply constraint affecting deliveries.
  cites: S2,S3

INFERENCES:
- The increase in A likely reflects the same supply pressure described by S2 and S3.

UNCERTAINTIES:
- The sources do not establish whether the pressure is temporary or structural.

RECOMMENDATION:
Investigate whether the 2025 data confirms the same pattern.
```

---

## 13. Deterministic transformer behavior contract

The deterministic transformer should produce one of these result families:

### `transform_success`
Contains:
- canonical JSON payload
- parse metadata
- warnings if minor but non-semantic cleanup occurred

### `transform_recoverable_failure`
Contains:
- explicit reason code
- exact failure location if known
- classification indicating formatter fallback is allowed

Examples:
- malformed findings entry shape
- section text present but indentation not parseable
- recommendation block present but not in exact expected line shape

### `transform_terminal_failure`
Contains:
- explicit reason code
- exact failure location if known
- classification indicating fallback is **not** allowed

Examples:
- missing findings section
- citation keys absent for evidence-backed findings
- sections collapsed into freeform prose
- ambiguity requiring semantic interpretation

---

## 14. Formatter fallback prompt contract

Step 3 prompt contract must be brutally narrow.

It should explicitly tell the formatter model:
- you are a formatter, not a researcher
- use only the provided text artifact
- preserve existing content only
- preserve citation keys exactly
- do not invent findings
- do not invent citations
- do not add missing recommendations
- if content is absent, reflect absence lawfully in the JSON
- return exactly one JSON object matching the schema

This prompt should be versioned and treated as a contract, not as casual prompt text.

---

## 15. Suggested build order

## Slice A — define Step 1 syntax contract
Build ourselves:
- syntax contract
- prompt builder
- syntax precheck

Open-source use:
- none required

## Slice B — build deterministic transformer
Build ourselves:
- parser
- result families
- validator hooks

Open-source use:
- none required

## Slice C — add Instructor-based formatter fallback
Build using open source:
- Instructor integration

Build ourselves:
- formatter prompt
- fallback policy
- validation wiring

Optional open-source help:
- Guardrails integration where it simplifies validation

## Slice D — wire the 3-step flow into current synthesis orchestration
Build ourselves:
- stage orchestration changes
- debug checkpoints
- error families

Keep unchanged:
- remap
- provenance
- persistence
- projection/render

## Slice E — optional later tightening
Optional open-source use:
- Outlines for stricter Step 1 generation on selected backends
- BAML only if provider-routing complexity later justifies it

---

## 16. Debug and observability requirements

The debug stream should reflect real stages.

Required checkpoints:
- `content_syntax_generation_started`
- `content_syntax_generation_succeeded`
- `content_syntax_generation_failed`
- `deterministic_transform_started`
- `deterministic_transform_succeeded`
- `deterministic_transform_failed_recoverable`
- `deterministic_transform_failed_terminal`
- `formatter_fallback_started`
- `formatter_fallback_succeeded`
- `formatter_fallback_failed`
- existing remap/provenance/persistence checkpoints remain

This matters because we want truthful operator visibility, not another blurred middle stage.

---

## 17. Testing plan

## 17.1 Unit tests

### Step 1 syntax tests
- valid artifact passes
- missing required header fails
- fenced output fails
- invalid citation key fails

### Step 2 deterministic transformer tests
- perfect syntax transforms successfully
- recoverable malformed findings produce recoverable failure
- missing substantive section produces terminal failure
- forbidden semantic rescue never occurs

### Step 3 formatter tests
- formatter output accepted only when schema-valid
- formatter cannot introduce forbidden fields
- formatter fallback is blocked on terminal Step 2 failures

## 17.2 Integration tests
- evidence pack -> Step 1 -> Step 2 success path
- evidence pack -> Step 1 -> Step 2 recoverable fail -> Step 3 success path
- evidence pack -> Step 1 -> Step 2 terminal fail -> fail closed
- remap/provenance downstream still behaves unchanged

## 17.3 Anti-drift tests
- Step 3 never runs as the default path when Step 2 succeeds
- deterministic transformer never synthesizes missing content
- formatter never becomes a second reasoner by policy

---

## 18. Final design choices

### Choice 1
**Primary normalization path:** deterministic transformer  
**Decision:** yes

### Choice 2
**LLM formatter as default path:** no  
**Decision:** reject

### Choice 3
**LLM formatter as fallback path only:** yes  
**Decision:** accept

### Choice 4
**Use Instructor now:** yes  
**Decision:** accept

### Choice 5
**Use Guardrails now:** yes, selectively  
**Decision:** accept

### Choice 6
**Use Outlines now:** no, later if useful  
**Decision:** defer

### Choice 7
**Use BAML now:** no  
**Decision:** defer

---

## 19. Brutally simple summary

We are building this:

1. a model produces a bounded text artifact in a hard syntax
2. Jeff tries to convert it mechanically
3. only if that mechanical conversion fails for recoverable structural reasons, Jeff uses a small formatter model to produce exact canonical JSON
4. then Jeff continues through the existing downstream validated pipeline unchanged

Open source solves:
- provider-swappable structured LLM calls
- optional validator composition
- optional future constrained generation

Jeff solves:
- syntax contract
- semantics
- deterministic transformation
- fallback policy
- provenance discipline
- downstream truth-safe behavior

That split is the correct split.
