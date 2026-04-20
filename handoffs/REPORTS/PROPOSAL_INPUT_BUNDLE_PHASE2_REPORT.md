# ProposalInputBundle Phase 2 Report

## Scope

Phase 2 extends the proposal-local `ProposalInputBundle` with two new bounded sections:

- `evidence_support`
- `memory_support`

It also adds deterministic governance signal promotion so current blocker, risk, and constraint signals already present in support can be promoted into `governance_relevant_support` without creating a new truth layer.

The implementation remains proposal-local, transient, non-canonical, and inspectable.

## Implemented changes

### Bundle model

- Added `ProposalEvidenceSupport` with bounded:
  - `evidence_summaries`
  - `uncertainty_summaries`
  - `contradiction_summaries`
  - `artifact_refs`
- Added `ProposalMemorySupport` with bounded:
  - `memory_ids`
  - `memory_summaries`
  - `memory_lessons`
  - `memory_risk_reminders`
  - `memory_precedents`
- Extended `ProposalInputBundle` to carry both sections.

### Bundle assembly

- `build_proposal_input_bundle(...)` now accepts optional `research_artifacts` and optional committed memory records.
- Added `resolve_committed_memory_support_records(...)` so direct `/proposal` and `/run` can enrich memory support from committed-memory IDs already present in `ContextPackage.memory_support_inputs`.
- Memory remains support-only and does not enter `truth_snapshot`.
- Evidence remains bounded and source-labeled.

### Governance signal extractor

- Added deterministic promotion of blocker/risk/constraint signals from already-available support.
- Promotion only scans bounded support already in scope:
  - `visible_constraints`
  - current execution support
  - direct support inputs
  - compiled knowledge support inputs
  - archive support inputs
  - research artifact summaries and uncertainties
- Added bounded caps and de-duplication.
- Fixed a classifier bug discovered during testing where `unresolved` was incorrectly matching the precedent classifier via the substring `resolved`.

### Request wiring

- Direct `/proposal` now builds and passes the richer bundle explicitly.
- `/run` now builds and passes the richer bundle explicitly.
- `/proposal repair` now reuses the persisted proposal bundle instead of rebuilding a thinner request.
- Fallback auto-build inside `ProposalGenerationRequest` remains available for non-CLI callers and now includes `research_artifacts`.

### Prompt/render/inspectability

- Added explicit `EVIDENCE_SUPPORT` and `MEMORY_SUPPORT` prompt sections to generation and repair prompts.
- Updated proposal prompt rendering to emit both sections.
- Updated JSON proposal record summaries to expose both sections.
- Updated text rendering to expose both sections.
- Updated runtime persistence to serialize and deserialize both sections with backward-compatible defaults.

## Tests

Targeted suites run:

```text
python -m pytest -q tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_api.py tests/integration/test_cli_proposal_operator_surface.py
```

Result:

```text
24 passed in 0.62s
```

Coverage added or extended for:

- prompt rendering of evidence support
- prompt rendering of memory support
- committed-memory-only support behavior
- no memory-to-truth bleed
- deterministic governance signal promotion
- persisted operator surface exposure for the new sections

## Live runtime verification

Live commands were run one at a time against the real workspace runtime.

### Direct `/proposal` thin case

Command intent:

```text
/proposal Frame bounded operator options
```

Observed result:

- `proposal_count=0`
- `truth_snapshot.item_count=3`
- `governance_relevant_support.item_count=0`
- `current_execution_support.item_count=0`
- `evidence_support.evidence_count=0`
- `memory_support.summary_count=0`

Interpretation:

- The current runtime scope had no retrievable bounded evidence or committed memory support for this request.
- Phase 2 behaved correctly by staying thin and honest instead of inventing support.

### Direct `/proposal` support-seeking case

Command intent:

```text
/proposal Use prior evidence and memory to frame bounded operator options for the current Jeff blocker state
```

Observed result:

- `proposal_count=0`
- `evidence_support.evidence_count=0`
- `memory_support.summary_count=0`

Interpretation:

- The live workspace still had no scope-matched archive or committed-memory support retrievable for this run.
- The new fields remained empty rather than leaking unsupported content.

### `/run` case

Command intent:

```text
/run What bounded rollout should execute now?
```

Observed result:

- created `run-9`
- completed successfully
- proposal summary retained exactly one serious option
- live context reported:
  - `truth_record_count=3`
  - `direct_support_count=0`
  - `compiled_knowledge_support_count=0`
  - `archive_support_count=0`
  - `memory_support_count=0`
- execution completed the repo-local smoke validation plan
- memory handoff later wrote `memory-1`, but that happened after proposal generation

### `/proposal show run-9`

Observed stored proposal bundle:

- `current_execution_support.item_count=2`
- `governance_relevant_support.item_count=5`
- `evidence_support.evidence_count=0`
- `memory_support.summary_count=0`
- repair path was used once because the initial proposal contained forbidden authority language in `why_now`, and the persisted repair succeeded

Interpretation:

- Phase 2 materially improved `/run` by making the execution and promoted governance basis explicit and inspectable.
- The deterministic governance extractor promoted visible constraint and blocker/constraint signal lines from the bounded `/run` support.

## Outcome summary

Phase 2 is implemented and verified.

- The new evidence and memory sections are real product code, persisted, inspectable, and prompt-visible.
- Memory remains support-only.
- Truth remains truth-first.
- Governance signal promotion is deterministic, bounded, and sourced from already-available support.
- Direct `/proposal` stays thin when the live runtime truly has thin support.
- `/run` now shows materially richer proposal basis under bounded execution constraints.