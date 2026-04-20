# Work Status Update 2026-04-20 19:49

## Completed

- Audited direct `/proposal` scope/state behavior.
- Verified that direct `/proposal` is always run-scoped after resolution and reads canonical project/work_unit/run truth.
- Identified the bounded direct-proposal support gap: archive retrieval was not enabled on the direct `/proposal` path even when scope-matched archive artifacts existed.
- Implemented the bounded direct-proposal fix in [jeff/interface/commands/proposal.py](jeff/interface/commands/proposal.py).
- Added targeted CLI integration coverage for:
  - single-run auto-resolution
  - multi-run ambiguity
  - direct proposal archive + committed-memory support
  - persisted readback of the richer direct proposal basis
- Ran targeted proposal tests successfully.
- Ran live serial runtime verification successfully.

## Test result

```text
python -m pytest -q tests/integration/test_cli_proposal_operator_surface.py tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_api.py
27 passed in 0.78s
```

## Live verification result

- `project-1 / wu-1` without explicit run still fails closed for direct `/proposal` because `wu-1` has multiple runs.
- direct `/proposal` on `run-1` for `What is Jeff architecture?` now receives real archive-backed evidence support:
  - `evidence_support.evidence_count = 2`
  - `artifact_refs = [artifact-a40760a8dd0c48d6, artifact-40af7a0f2b804520]`
- `proposal show`, `proposal raw`, and `proposal validate` all reflected the richer direct proposal basis.
- committed memory support remained absent in the live one-shot CLI because startup built an empty `InMemoryMemoryStore` and `memory-1` was not present in that new process.
- `/run` remained execution-support-driven and unchanged in its core behavior.

## Current status

This slice is complete.

The direct `/proposal` path now benefits from real scope-matched archive/evidence support when it actually exists, and the exact remaining live memory gap is now isolated to startup/store persistence rather than proposal-bundle wiring.