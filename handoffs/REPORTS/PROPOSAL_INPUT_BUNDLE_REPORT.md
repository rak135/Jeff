# PROPOSAL_INPUT_BUNDLE_REPORT.md

## 1. What changed

Implemented a bounded, transient `ProposalInputBundle` slice for proposal generation.

- Added explicit proposal-local bundle models for:
  - `request_frame`
  - `scope_frame`
  - `truth_snapshot`
  - `governance_relevant_support`
  - `current_execution_support`
- Wired `ProposalGenerationRequest` to build and carry the bundle automatically.
- Updated proposal prompt rendering to consume the bundle directly instead of reconstructing the same shape ad hoc from loosely flattened inputs.
- Persisted the bundle on proposal operator records for bounded inspectability.
- Exposed the bundle basis on proposal JSON/text inspection surfaces.

## 2. Files changed

- `jeff/cognitive/proposal/input_bundle.py`
- `jeff/cognitive/proposal/generation.py`
- `jeff/cognitive/proposal/operator_records.py`
- `jeff/cognitive/proposal/__init__.py`
- `jeff/cognitive/__init__.py`
- `jeff/runtime_persistence.py`
- `jeff/interface/commands/scope.py`
- `jeff/interface/json_views.py`
- `jeff/interface/render.py`
- `PROMPTS/proposal/STEP1_GENERATION.md`
- `PROMPTS/proposal/STEP1_REPAIR.md`
- `tests/unit/cognitive/test_proposal_generation.py`
- `tests/unit/cognitive/test_proposal_api.py`
- `tests/integration/test_cli_proposal_operator_surface.py`

## 3. Bundle structure

`ProposalInputBundle` contains only transient proposal-support data:

- `request_frame`
  - objective
  - trigger summary
  - purpose
  - visible constraints
- `scope_frame`
  - project id
  - work unit id
  - run id
- `truth_snapshot`
  - canonical truth records only
- `governance_relevant_support`
  - governance truth summaries when present
  - visible constraints
- `current_execution_support`
  - explicit current execution-family support passed by callers when available

Phase 2 fields were intentionally not added in this slice:

- `evidence_support`
- `memory_support`

## 4. Where each field comes from

- `request_frame`
  - from `ProposalGenerationRequest.objective`
  - from `ContextPackage.trigger.trigger_summary`
  - from `ContextPackage.purpose`
  - from `ProposalGenerationRequest.visible_constraints`
- `scope_frame`
  - from the existing request scope
- `truth_snapshot`
  - from `ContextPackage.truth_records`
  - intentionally excludes governance truth and all support sources
- `governance_relevant_support`
  - from `ContextPackage.governance_truth_records`
  - plus visible constraints
- `current_execution_support`
  - from explicit `ProposalGenerationRequest.current_execution_support`
  - `/run` now passes its bounded repo-local execution-family constraints here

## 5. What stayed out of canonical state

No new canonical state fields were added.

The bundle is:

- not written into canonical state
- not treated as truth
- not used to mutate current truth
- only persisted inside proposal operator records for proposal inspectability

Memory was not upgraded into truth and was not added as a new bundle section in this phase.

## 6. How Proposal now consumes the bundle

Proposal now consumes the bundle through `ProposalGenerationRequest.proposal_input_bundle`.

`STEP1_GENERATION.md` and `STEP1_REPAIR.md` now receive these sections directly:

- `REQUEST_FRAME`
- `SCOPE_FRAME`
- `TRUTH_SNAPSHOT`
- `GOVERNANCE_RELEVANT_SUPPORT`
- `CURRENT_EXECUTION_SUPPORT`

Research support remains separate in this phase and continues to flow through the existing research-support inputs.

## 7. Inspectability changes

Proposal operator record JSON now includes a bounded `proposal_input_bundle` summary with:

- request frame
- scope frame
- truth snapshot items
- governance support items
- current execution support items

Text rendering now shows a compact basis summary so operators can distinguish:

- thin output caused by thin support
- richer output caused by explicit execution/governance support

The surface remains bounded. It does not dump full context blobs.

## 8. Tests run and results

Focused suite run:

`pytest tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_api.py tests/integration/test_cli_proposal_operator_surface.py tests/integration/test_cli_run_live_context_execution.py -q`

Result:

- `33 passed in 25.49s`

Coverage added/updated includes:

- bundle rendering into proposal prompts
- separation between truth snapshot and support sections
- current execution support propagation into runtime prompt input
- no memory-to-truth bleed into the bundle truth snapshot
- persisted proposal inspectability for direct `/proposal` and `/run`

## 9. Real commands executed

Executed one at a time against the configured runtime/provider:

1. `python -m jeff --project project-1 --work wu-1 --command "/run list" --json`
2. `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal Review README quickstart wording and propose one bounded improvement step." --json`
3. `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal show proposal-record-run-2-20260420T171256.599602+0000-review-readme-quickstart-wording" --json`
4. `python -m jeff --project project-1 --work wu-1 --command "/run What bounded rollout should execute now?" --json`
5. `python -m jeff --project project-1 --work wu-1 --run run-8 --command "/proposal show run-8" --json`

## 10. Whether proposal quality improved in live behavior

Yes, but specifically where current execution support existed.

Observed live behavior:

- Direct `/proposal` on `Review README quickstart wording and propose one bounded improvement step.` remained thin and returned `proposal_count=0`.
  - This was honest.
  - The persisted bundle showed why: only canonical truth was available; there was no governance-relevant support, no current execution support, and no README content support.
- `/run "What bounded rollout should execute now?"` improved materially.
  - Proposal produced `proposal_count=1`.
  - Scarcity reason was specific: the execution surface is limited to one fixed repo-local validation plan.
  - The retained option was concretely scoped to `Execute repo-local validation plan`.
  - Constraints and support refs were grounded in the bundle support sections rather than generic fallback alone.

Precise quality outcome:

- improved for scarcity reasoning: yes
- improved for current execution path grounding: yes
- improved for constraint grounding: yes
- improved for blocker/risk richness in the tested `/run` case: partially
  - constraints became clearer
  - assumptions were more grounded
  - risks/blockers were still sparse when support itself was sparse
- improved for thin direct proposal cases without added support: no material change
  - the slice exposed the thinness honestly instead of hiding it

## 11. Exact remaining gaps / next best step

Remaining gaps:

- `governance_relevant_support` currently includes governance truth summaries plus visible constraints, but not a richer proposal-local extraction of current blocker/risk signals from broader support sources.
- `current_execution_support` is currently strongest on `/run` because that call site now passes explicit execution-family support. Direct `/proposal` still depends on whatever support is already present in current context.
- `evidence_support` and `memory_support` were intentionally left out of phase 1 to keep the slice bounded.

Next best step:

Add a small bounded extractor that promotes current blocker/risk/constraint signals from existing support inputs into `governance_relevant_support` for direct `/proposal` when such signals already exist in current context, without introducing any new truth layer or broad context rewrite.