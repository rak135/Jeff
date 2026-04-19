# research_fix.md

Status: bounded repair/design note for current Jeff research synthesis robustness  
Authority: subordinate to `RESEARCH_V2_ROADMAP.md`, `PLANNING_AND_RESEARCH_SPEC.md`, `INTERFACE_OPERATOR_SPEC.md`, `ARCHITECTURE.md`, and current Cognitive/Research handoffs  
Purpose: describe the concrete fixes needed to make Jeff research less fragile across different models and less dependent on one-shot strict JSON + raw source-id behavior

---

## 1. Why this document exists

Current Jeff research already has:
- bounded source acquisition
- evidence packaging
- synthesis
- artifact persistence
- operator-facing rendering
- provenance validation

That is enough to reveal the current weakness clearly:

the synthesis contract is still too fragile and too model-dependent.

The observed failure modes already show the pattern:
- one model can produce structurally valid output but drift on source identifiers
- another model can fail strict JSON output entirely
- the backend then fails closed, which is good, but this still means the synthesis contract is too brittle

This document defines the concrete fix direction.

The goal is not to weaken validation.
The goal is to make the synthesis path more robust **before** validation has to reject it.

---

## 2. Core principle

Jeff research must remain:
- evidence-first
- source-aware
- provenance-preserving
- bounded
- model-assisted, not model-owned

The key rule is:

**the model should not own fragile structural responsibilities that Jeff can own deterministically.**

That means:
- Jeff should own source identity
- Jeff should own final citation mapping
- Jeff should own schema enforcement
- Jeff should own bounded repair logic
- the model should mainly contribute reasoning, synthesis, comparison, and wording

---

## 3. Current weakness

The current one-shot synthesis contract asks the model to do too many fragile things at once:

1. read bounded evidence
2. produce a structured JSON object
3. keep the exact required schema
4. preserve source linkage
5. cite using internal source identifiers
6. return all of this cleanly in one pass

That is the wrong place to put all the fragility.

Even a strong model can fail in one of these ways:
- produce almost-correct JSON
- drift one source identifier
- hallucinate a source reference pattern
- wrap valid content in extra prose
- output valid reasoning but invalid structure

So the fix is not “find one perfect model”.
The fix is “change the contract so weaker and different models can still succeed more often”.

---

## 4. Fix 1 — stop exposing raw internal source IDs to the model

## Problem
Current internal source identifiers such as:
- `web-359eb9e7c0c0`
- `web-a98eb9b78b78`

are hostile to model reliability.

They are:
- long
- opaque
- visually similar
- easy to mutate accidentally
- semantically meaningless to the model

This makes citation drift much more likely.

## Fix
Do not give the model raw internal source IDs.

Instead, create a deterministic short citation key map per synthesis request, such as:
- `S1`
- `S2`
- `S3`
- `S4`

Then map them internally:

- `S1 -> actual SourceItem(source_id="web-359eb9e7c0c0", ...)`
- `S2 -> actual SourceItem(...)`

The model sees only:
- the finding text
- the bounded source summary
- the citation key `S1`, `S2`, etc.

The model never sees the backend hash-like source IDs.

## How to apply it
At synthesis-request construction time:
1. build a deterministic ordered list of source items
2. assign stable per-request citation keys `S1..Sn`
3. include only those keys in the model prompt/schema
4. keep the real mapping in Jeff-owned runtime state
5. after model output, remap `S1..Sn` back to actual source IDs

## Expected benefit
- lower citation drift
- less model confusion
- easier schema validation
- easier multi-model support

---

## 5. Fix 2 — use a dynamic citation enum in the synthesis contract

## Problem
Even if you shorten source identifiers, the model can still invent invalid ones unless the output contract constrains it tightly.

## Fix
Generate the synthesis schema dynamically per request.

If the available citation keys are:
- `S1`
- `S2`
- `S3`

then any citation-bearing field should only accept that exact set.

For example:
- `source_refs: ["S1", "S2"]`
- not arbitrary strings
- not free-form `source_id`
- not `web-*` patterns

This means the model is not being asked to remember open-ended identifiers.
It is being asked to choose from a small bounded set.

## How to apply it
When building the synthesis request:
1. inspect the actual source set
2. create deterministic citation keys
3. inject the allowed key set into the JSON schema
4. mirror the same allowed set in the natural-language formatting instructions
5. reject anything outside that set before remapping

## Expected benefit
- source references become easier for the model
- invalid references are reduced earlier
- citation space becomes bounded and model-friendly

---

## 6. Fix 3 — deterministic remap after synthesis

## Problem
The model should not be trusted with final backend identity handling.

Even if the model returns valid citation keys, Jeff still has to restore real provenance.

## Fix
After synthesis output is parsed and validated:
1. validate that all cited keys belong to the allowed key set
2. remap each key back to the real internal `source_id`
3. attach real `SourceItem` linkage only after deterministic remap
4. then run normal provenance validation

This means the model outputs citation tokens, not final source identities.

## How to apply it
Introduce a bounded post-synthesis remap step:

- model output:
  - `finding.text`
  - `finding.source_refs = ["S1", "S3"]`

- Jeff remap:
  - `S1 -> web-359eb9e7c0c0`
  - `S3 -> web-7e000b5818a1`

- final artifact:
  - `finding.source_refs = ["web-359eb9e7c0c0", "web-7e000b5818a1"]`

Then provenance validation runs against the real source set.

## Expected benefit
- keeps backend identity deterministic
- reduces model responsibility
- keeps current persistence model intact
- preserves existing provenance discipline

---

## 7. Fix 4 — add one explicit bounded repair pass for malformed structured output

## Problem
Some models are good at reasoning but unreliable at exact one-shot JSON output.
That does not always mean the reasoning is bad.
It often means the formatting step is too brittle.

## Fix
Add one explicit bounded repair pass.

If the primary synthesis pass fails because:
- JSON is malformed
- schema structure is almost correct but not exact
- the model wrapped the result in extra prose

Jeff may run one additional repair step:
- “convert this content into the exact required schema”
- same bounded input
- no open-ended retry loop
- one repair pass only

If that repair fails too:
- fail closed

## How to apply it
Suggested policy:
1. primary synthesis call
2. if failure class is `malformed_output` only:
   - run one repair call
3. repair call must be narrow:
   - no new source discovery
   - no new reasoning
   - format repair only
4. if repair succeeds:
   - continue normally
5. if repair fails:
   - return classified failure

## Important rule
This must stay bounded.
Do not create:
- infinite retries
- self-healing loops
- hidden autonomy
- silent post-hoc invention

## Expected benefit
- better compatibility with models like Gemma
- fewer unnecessary hard failures
- preserves fail-closed posture after one explicit extra chance

---

## 8. Fix 5 — separate reasoning task from formatting task

## Problem
The current one-shot synthesis contract mixes:
- reasoning
- summarization
- citation binding
- exact formatting

in one output event.

That is too much pressure on one call, especially for local or smaller models.

## Fix
Split synthesis into two bounded logical stages.

### Stage A — reasoning synthesis
The model focuses on:
- summary
- findings
- uncertainties
- recommendation
- citation keys only, not backend source IDs

This stage is allowed to optimize for reasoning quality.

### Stage B — formatting/structuring
A narrower formatter step converts Stage A output into:
- exact required JSON
- strict schema
- exact citation-key structure

This can be:
- the same model in a narrower second pass
- or a different model better at strict structure
- or a deterministic formatter where feasible

## How to apply it
Possible v1.5-friendly shape:
1. build evidence pack + citation key map
2. run synthesis step for bounded content
3. run formatting step for exact schema
4. remap citation keys
5. run provenance validation
6. persist/render

## Important rule
Do not let Stage B become hidden reasoning.
It is a structure pass, not a new research pass.

## Expected benefit
- weaker models can still help on reasoning
- stricter models or bounded formatters can handle exact schema
- fewer one-shot failures

---

## 9. Fix 6 — capability profiles instead of vendor dependence

## Problem
The wrong mental model is:
- “Gemma is bad”
- “Qwen is good”
- “find one model that does everything”

That is trash thinking for a modular system.

Different models are better at different roles:
- reasoning
- strict JSON
- reranking
- critique
- rewrite/repair
- extraction support

## Fix
Introduce capability profiles at the runtime/routing layer.

Example profiles:
- `research_reasoning`
- `research_formatter`
- `research_repair`
- `evidence_rerank`
- `proposal_reasoning`
- `evaluation_reasoning`

Then map available models to those roles.

One model may fill multiple roles in small setups.
Better setups may split them.

## How to apply it
1. keep current adapter/runtime model
2. add purpose or sub-purpose routing later
3. start small:
   - `research_reasoning`
   - `research_formatter`
4. choose models by observed capability, not brand loyalty
5. keep Jeff semantics independent from provider choice

## Expected benefit
- less vendor lock-in
- easier model experimentation
- better system stability
- cleaner path for hybrid local/cloud use later

---

## 10. How the six fixes fit together

These fixes are not separate random ideas.
They form one coherent repair direction.

### New robust synthesis shape
1. collect sources
2. assign short citation keys
3. build dynamic citation-key schema
4. run reasoning synthesis
5. optionally run one bounded formatting/repair pass if needed
6. deterministically remap citation keys to real source IDs
7. run provenance validation
8. persist/render artifact

This keeps:
- Jeff-owned semantics
- explicit provenance
- fail-closed validation
- source-aware artifacts

while reducing:
- model fragility
- raw source-id drift
- structured-output brittleness
- vendor dependence

---

## 11. Recommended implementation order

Do not try to build everything in one giant slice.

Recommended order:

### Slice A
- short citation keys `S1..Sn`
- dynamic citation enum
- deterministic remap to real source IDs

This is the highest-value repair.

### Slice B
- one bounded malformed-output repair pass

This helps models that reason well but format badly.

### Slice C
- split reasoning task from formatting task

Do this only after Slice A is stable.

### Slice D
- capability-profile routing for research roles

Do this after the synthesis contract itself is less fragile.

---

## 12. What not to do

Do not:
- weaken provenance validation
- silently auto-heal unknown source refs
- let the model invent backend source identities
- add infinite retries
- make deep research loops before fixing synthesis fragility
- hardcode one “blessed” model into the architecture
- move semantics into Infrastructure adapters

Jeff should become less model-fragile by moving fragile responsibilities into deterministic Jeff-owned logic, not by hoping one model behaves perfectly.

---

## 13. Final direction

The correct direction is:

- Jeff owns real source identity
- the model sees short citation keys
- the schema allows only those keys
- Jeff remaps keys back to real source IDs deterministically
- one bounded repair pass helps malformed structured output
- reasoning and formatting can separate
- model choice becomes capability-based, not vendor-based

That is how research becomes more universal, more robust, and less dependent on one specific model behaving perfectly in one-shot strict JSON mode.
