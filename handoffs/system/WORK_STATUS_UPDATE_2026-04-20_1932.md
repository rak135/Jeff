# Work Status Update 2026-04-20 19:32

## Completed

- Implemented ProposalInputBundle Phase 2 in product code.
- Added bounded `evidence_support` and `memory_support` sections.
- Added deterministic governance signal promotion into `governance_relevant_support`.
- Wired direct `/proposal`, `/run`, and `/proposal repair` to preserve the richer bundle.
- Updated prompt generation and repair surfaces.
- Updated persistence, JSON views, and text rendering.
- Added targeted unit and integration coverage.
- Ran targeted verification successfully.
- Ran live runtime verification one command at a time.

## Test result

```text
python -m pytest -q tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_api.py tests/integration/test_cli_proposal_operator_surface.py
24 passed in 0.62s
```

## Live verification result

- Direct `/proposal` on `run-8` stayed honestly thin.
- Direct `/proposal` with evidence/memory-seeking wording also stayed thin because the live scope had no retrievable archive or committed-memory support.
- `/run` created `run-9` and produced a persisted proposal bundle with:
  - `current_execution_support.item_count=2`
  - `governance_relevant_support.item_count=5`
  - `evidence_support.evidence_count=0`
  - `memory_support.summary_count=0`
- `/proposal show run-9` confirmed the persisted Phase 2 bundle and successful repair after one initial validation failure.

## Important note

The runtime later wrote `memory-1` during run memory handoff after `/run`, but that memory write occurred after proposal generation. That means the Phase 2 proposal bundle correctly did not claim memory support for the request that preceded that write.

## Current status

Phase 2 is complete for the implemented slice.