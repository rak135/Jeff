# WORK_STATUS_UPDATE_compacted

Last updated: 2026-04-16  
Primary sources:
- [WORK_STATUS_UPDATE.md](C:/DATA/PROJECTS/JEFF/handoffs/system/WORK_STATUS_UPDATE.md)
- [FULL_REPO_REVIEW.md](C:/DATA/PROJECTS/JEFF/FULL_REPO_REVIEW.md)

## Purpose

This file is the compact current-status snapshot for the Jeff project.  
Use it as the first project-status read before diving into the rolling history in `WORK_STATUS_UPDATE.md`.

## Project Snapshot

- Jeff is currently a CLI-first, in-memory v1 backbone with a clean layered structure.
- The canonical backbone exists end to end: core state -> transitions -> governance -> cognitive stages -> orchestrator -> interface.
- The research vertical is the most mature part of the system and is the only cognitive stage currently using a real model adapter/runtime path.
- Research now runs through the live 3-step bounded-text pipeline:
  - Step 1: bounded text generation
  - Step 2: deterministic transform
  - Step 3: formatter fallback after Step 2 failure only
- Infrastructure now includes:
  - model adapter abstractions and providers
  - runtime assembly and config
  - vocabulary modules (`purposes`, `output_strategies`, `capability_profiles`)
  - `ContractRuntime`
- Proposal, selection, planning, evaluation, governance, action, memory, and orchestrator are implemented and tested, but outside research they remain deterministic/rule-based rather than model-backed.

## What Is Implemented Now

### Backbone

- Immutable global state and transition-controlled truth updates are in place.
- Canonical containers (`project`, `work_unit`, `run`) exist and are validated.
- Governance boundaries are explicit: policy, approval, readiness, and action-entry are separate concepts.
- Orchestrator sequencing, routing, validation, lifecycle, and trace exist as deterministic code.
- The CLI is the only operator surface and stays thin and truthful.

### Research

- Document and web research acquisition paths exist.
- Research artifacts persist as JSON support records.
- Research-to-memory handoff exists.
- Debug checkpoints are available through `/mode debug`.
- Citation remap, provenance validation, and fail-closed boundaries are strong.
- The 3-step transition is complete and active in production code.

### Infrastructure

- Fake and Ollama adapters exist.
- Runtime config and purpose-based adapter routing exist.
- `ContractRuntime` is present and research has adopted it for Step 1 and the formatter bridge runtime path.

## Current Reality And Limits

- Truth is still in-memory only. `GlobalState` is not persisted across restarts.
- Memory storage is still in-memory only.
- The orchestrator is a tested staged runner, not a live runtime loop or background service.
- No non-research cognitive stage currently uses a model adapter.
- Transition support is still narrow: only `create_project`, `create_work_unit`, and `create_run` are implemented.
- Web acquisition is intentionally basic and not yet a robust search/retrieval layer.
- The CLI is command-driven and practical, but it is not a broad API or GUI surface.

## Known Issues And Active Debt

- Full suite status from the 2026-04-15 review: `378 passed / 10 failed`.
- The 10 failing tests are known pre-existing failures caused by outdated fake-adapter fixtures that still assume the old JSON-first synthesis contract.
- Research artifact persistence currently uses a doubled path on disk:
  - configured root: `.jeff_runtime/research_artifacts`
  - effective write path: `.jeff_runtime/research_artifacts/research_artifacts`
- `ContractCallRequest` is still too thin for the clean `invoke()` path because it does not yet carry the full fields needed for JSON mode and reasoning configuration.
- The formatter bridge still uses the temporary infrastructure-facing name `research_repair`.
- `jeff/infrastructure/HANDOFF.md` is stale and does not reflect the newer vocabulary modules or `ContractRuntime`.
- Some compatibility surfaces remain intentionally in place:
  - `jeff/cognitive/research/legacy.py`
  - `invoke_with_request()` for full `ModelRequest` control

## Recommended Next Slice

The recommended next slice is a narrow infrastructure-hardening pass before any Proposal/Evaluation model adoption.

1. Expand `ContractCallRequest` to carry `response_mode`, `json_schema`, and `reasoning_effort`.
2. Move research Step 1 to the clean `ContractRuntime.invoke()` path.
3. Retire `research_repair` naming in infrastructure and use neutral formatter-bridge vocabulary.
4. Fix the doubled artifact-store path.
5. Rewrite the 10 outdated tests to emit valid Step 1 bounded text.
6. Refresh `jeff/infrastructure/HANDOFF.md`.

After that, the next major phase should be Proposal adoption of `ContractRuntime`, then Evaluation adoption.

## Explicitly Not Recommended Next

- Do not start broad orchestrator-runtime-loop work yet.
- Do not start global-state persistence until the needed transition vocabulary is clearer.
- Do not add new model providers speculatively.
- Do not rewrite `commands.py` yet.
- Do not introduce Instructor, Guardrails, or BAML yet.

## Milestone Arc

- 2026-04-10: core backbone, governance, cognitive contracts, action/outcome/evaluation, memory, orchestrator skeleton, and CLI-first surface were established.
- 2026-04-11: startup/packaging, handoffs, test reorganization, CLI flow improvements, infrastructure adapter/runtime foundations, and initial research runtime slices landed.
- 2026-04-12: research robustness improved across provenance, transparency, error surfacing, repair handling, debug checkpoints, and Ollama structured JSON requests.
- 2026-04-13: the 3-step bounded-text research transition was completed and made the live primary path.
- 2026-04-15: infrastructure vocabulary modules and `ContractRuntime` landed, and research adopted the runtime path.

## Practical Reading Order

1. Read this file for the current status.
2. Read [REPO_HANDOFF.md](C:/DATA/PROJECTS/JEFF/handoffs/system/REPO_HANDOFF.md) for startup and repo orientation.
3. Read the nearest module handoff for the area being changed.
4. Use [WORK_STATUS_UPDATE.md](C:/DATA/PROJECTS/JEFF/handoffs/system/WORK_STATUS_UPDATE.md) only when you need detailed implementation history.


## 2026-04-17 12:30 - Proposal Slice A package split

- Scope: cognitive proposal contract surface
- Done:
  - converted `jeff.cognitive.proposal` from a flat module into a dedicated package
  - moved Proposal contract ownership into `jeff/cognitive/proposal/contracts.py`
  - preserved public imports through `jeff.cognitive.proposal` and `jeff.cognitive`, including `ProposalType`
  - added a local Proposal handoff and updated the parent cognitive handoff
  - added focused import-surface coverage for the package split
- Validation: `python -m pytest -q tests/unit/cognitive/test_proposal_public_surface.py tests/unit/cognitive/test_proposal_rules.py tests/unit/cognitive/test_selection_rules.py tests/unit/cognitive/test_conditional_planning.py` passed (`10 passed`)
- Current state: Proposal is now a bounded package with unchanged contract semantics and no runtime/model wiring added
- Next step: add later Proposal runtime/prompt work inside the new package without widening into selection or governance
- Files:
  - jeff/cognitive/proposal/__init__.py
  - jeff/cognitive/proposal/contracts.py
  - jeff/cognitive/proposal/HANDOFF.md
  - jeff/cognitive/HANDOFF.md
  - tests/unit/cognitive/test_proposal_public_surface.py


## 2026-04-17 12:38 - Proposal Slice B prompt contract surface

- Scope: proposal prompt contract and local prompt loading surface
- Done:
  - added canonical `PROMPTS/proposal/STEP1_GENERATION.md` with strict bounded-output and anti-authority rules
  - added `jeff/cognitive/proposal/prompt_files.py` for Proposal-local prompt loading and placeholder rendering
  - updated prompt docs and marked legacy `PROMPTS/proposal/GENERATION.md` as non-canonical
  - added focused unit tests for prompt loading, rendering, and contract markers
- Validation: `python -m pytest -q tests/unit/cognitive/test_proposal_prompt_files.py tests/unit/cognitive/test_proposal_public_surface.py tests/unit/cognitive/test_proposal_rules.py` passed (`11 passed`)
- Current state: Proposal now has a loadable Step 1 prompt contract but still no model/runtime wiring
- Next step: add Slice C generation request building on top of this contract without introducing runtime calls yet
- Files:
  - PROMPTS/proposal/STEP1_GENERATION.md
  - jeff/cognitive/proposal/prompt_files.py
  - tests/unit/cognitive/test_proposal_prompt_files.py
  - jeff/cognitive/proposal/HANDOFF.md
  - PROMPTS/README.md

## 2026-04-17 12:48 - Proposal Slice C generation entry surface

- Scope: proposal generation request and prompt-bundle entry
- Done:
  - added `jeff/cognitive/proposal/generation.py` with bounded request and prompt-bundle models
  - added `build_proposal_generation_prompt_bundle()` on top of `STEP1_GENERATION.md`
  - rendered scope, truth snapshot, visible constraints, optional research support, and other support into the Proposal Step 1 prompt
  - kept the surface Proposal-local with no runtime/model invocation and no parsing
- Validation: `python -m pytest -q tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_prompt_files.py tests/unit/cognitive/test_proposal_public_surface.py tests/unit/cognitive/test_proposal_rules.py` passed (`15 passed`)
- Current state: Proposal now has a generation-ready prompt bundle for later runtime adoption without adding Slice D behavior
- Next step: add Slice D runtime handoff on top of this bundle without adding parsing or normalization yet
- Files:
  - jeff/cognitive/proposal/generation.py
  - jeff/cognitive/proposal/__init__.py
  - tests/unit/cognitive/test_proposal_generation.py
  - jeff/cognitive/__init__.py

## 2026-04-17 12:55 - Proposal Slice D runtime handoff

- Scope: proposal Step 1 runtime handoff
- Done:
  - added a Proposal-local runtime handoff on top of `ProposalGenerationPromptBundle`
  - routed the Step 1 call through `services.contract_runtime.invoke(...)` with Proposal purpose routing
  - added a raw Proposal generation result surface that keeps raw text and minimal runtime metadata only
  - kept the path fail-closed with no parsing, normalization, validation, or repair behavior
- Validation: `python -m pytest -q tests/unit/cognitive/test_proposal_generation_runtime.py tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_prompt_files.py tests/unit/cognitive/test_proposal_public_surface.py tests/unit/cognitive/test_proposal_rules.py` passed (`19 passed`)
- Current state: Proposal can now perform one bounded Step 1 runtime call and return raw generation output without interpreting it
- Next step: add Slice E parsing on top of the raw result without widening runtime behavior
- Files:
  - jeff/cognitive/proposal/generation.py
  - jeff/cognitive/proposal/__init__.py
  - tests/unit/cognitive/test_proposal_generation_runtime.py
  - jeff/cognitive/proposal/HANDOFF.md  

## 2026-04-17 13:00 - Proposal Slice E deterministic parsing

- Scope: proposal Step 1 raw-output parsing
- Done:
  - added a Proposal-local deterministic parser for the Step 1 bounded text shape
  - added parsed-result models for top-level Proposal output and per-option field extraction
  - wired the parser to consume Slice D raw results with fail-closed malformed-shape errors
  - kept parsing separate from validation, repair, retry, and runtime behavior
- Validation: `python -m pytest -q tests/unit/cognitive/test_proposal_parsing.py tests/unit/cognitive/test_proposal_generation_runtime.py tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_prompt_files.py tests/unit/cognitive/test_proposal_public_surface.py tests/unit/cognitive/test_proposal_rules.py` passed (`26 passed`)
- Current state: Proposal can now turn raw Step 1 text into structured parsed data without semantic judgment
- Next step: add Slice F semantic validation on top of the parsed result without adding repair behavior
- Files:
  - jeff/cognitive/proposal/parsing.py
  - jeff/cognitive/proposal/__init__.py
  - tests/unit/cognitive/test_proposal_parsing.py
  - jeff/cognitive/proposal/HANDOFF.md


## 2026-04-17 13:21 - Proposal Slice F semantic validation

- Scope: proposal Step 1 semantic validation on top of parsed output
- Done:
  - added a Proposal-local semantic validator with explicit validation issues and fail-closed errors
  - added a validated Proposal result surface that keeps the canonical ProposalSet plus validated option linkage
  - enforced scarcity, duplicate-padding rejection, required semantic fields, and authority-language rejection
  - kept validation separate from repair, retry, runtime, parsing, and selection behavior
- Validation: `python -m pytest -q tests/unit/cognitive/test_proposal_validation.py tests/unit/cognitive/test_proposal_parsing.py tests/unit/cognitive/test_proposal_generation_runtime.py tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_prompt_files.py tests/unit/cognitive/test_proposal_public_surface.py tests/unit/cognitive/test_proposal_rules.py` passed (`39 passed`)
- Current state: Proposal can now turn parsed Step 1 output into a lawful validated Proposal surface or explicit validation errors without adding repair or orchestration behavior
- Next step: add downstream handoff shaping only in a later bounded slice if explicitly requested
- Files:
  - jeff/cognitive/proposal/validation.py
  - jeff/cognitive/proposal/__init__.py
  - tests/unit/cognitive/test_proposal_validation.py
  - jeff/cognitive/proposal/HANDOFF.md


## 2026-04-17 13:29 - Proposal Slice G composed module entry

- Scope: proposal end-to-end composition and downstream handoff shaping
- Done:
  - added a thin Proposal-local API entry that composes prompt build, runtime handoff, parse, and validation
  - added explicit success and failure result surfaces that keep runtime, parse, and validation failures distinct
  - added a Proposal-local downstream handoff shape that preserves both the canonical ProposalSet and richer validated linkage
  - kept the entry fail-closed without repair, retry, selection wiring, or orchestrator behavior
- Validation: `python -m pytest -q tests/unit/cognitive/test_proposal_api.py tests/unit/cognitive/test_proposal_validation.py tests/unit/cognitive/test_proposal_parsing.py tests/unit/cognitive/test_proposal_generation_runtime.py tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_prompt_files.py tests/unit/cognitive/test_proposal_public_surface.py tests/unit/cognitive/test_proposal_rules.py` passed (`45 passed`)
- Current state: Proposal now has one bounded module-local entry that returns either validated downstream handoff data or explicit stage-specific failure
- Next step: add downstream consumption only in a later bounded slice if explicitly requested
- Files:
  - jeff/cognitive/proposal/api.py
  - jeff/cognitive/proposal/__init__.py
  - tests/unit/cognitive/test_proposal_api.py
  - jeff/cognitive/proposal/HANDOFF.md


## 2026-04-17 13:38 - Proposal Slice H contract consolidation

- Scope: proposal contract consolidation around one primary runtime success surface
- Done:
  - added `ProposalResult` and `ProposalResultOption` as the primary current Proposal-local success and downstream handoff contracts
  - updated validation to return `ProposalResult` directly and updated the composed API to carry `proposal_result` instead of parallel validated/handoff wrappers
  - demoted `ValidatedProposalGenerationResult`, `ValidatedProposalOption`, and `ProposalDownstreamHandoff` from public exports
  - kept `ProposalOption` and `ProposalSet` as the carried compatibility subset because existing downstream code still depends on them
- Validation: `python -m pytest -q tests/unit/cognitive/test_proposal_api.py tests/unit/cognitive/test_proposal_validation.py tests/unit/cognitive/test_proposal_parsing.py tests/unit/cognitive/test_proposal_generation_runtime.py tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_prompt_files.py tests/unit/cognitive/test_proposal_public_surface.py tests/unit/cognitive/test_proposal_rules.py tests/unit/cognitive/test_selection_rules.py tests/unit/cognitive/test_conditional_planning.py` passed (`52 passed`)
- Current state: Proposal now has one clear primary runtime success contract while the older narrow set remains as compatibility-only carried structure
- Next step: let downstream Selection-facing work consume `ProposalResult` or its carried `ProposalSet` explicitly in a later bounded slice
- Files:
  - jeff/cognitive/proposal/contracts.py
  - jeff/cognitive/proposal/validation.py
  - jeff/cognitive/proposal/api.py
  - tests/unit/cognitive/test_proposal_api.py

## 2026-04-17 13:54 - Proposal downstream consumer migration

- Scope: proposal downstream consumer switch from legacy narrow shapes to `ProposalResult`
- Done:
  - migrated Selection, Planning, and orchestrator proposal-stage validation to consume `ProposalResult`
  - removed `ProposalOption` and `ProposalSet` from `jeff.cognitive.proposal` and `jeff.cognitive` public exports
  - updated orchestrator and acceptance flow tests to emit `ProposalResult` instead of `ProposalSet`
  - pushed remaining legacy construction sites into explicit `jeff.cognitive.proposal.contracts` imports for compatibility-only use
- Validation: `python -m pytest -q tests/unit/cognitive/test_selection_rules.py tests/unit/cognitive/test_conditional_planning.py tests/unit/cognitive/test_proposal_public_surface.py tests/unit/cognitive/test_proposal_api.py tests/unit/cognitive/test_proposal_validation.py tests/unit/cognitive/test_proposal_rules.py tests/unit/orchestrator/test_orchestrator_stage_order.py tests/unit/orchestrator/test_orchestrator_trace_and_lifecycle.py tests/unit/orchestrator/test_orchestrator_failure_routing.py tests/acceptance/test_acceptance_backbone_flow.py tests/acceptance/test_acceptance_truthfulness.py tests/acceptance/test_acceptance_scope_isolation.py tests/antidrift/test_antidrift_semantic_boundaries.py` passed (`59 passed`)
- Current state: `ProposalResult` is now the downstream-consumed Proposal shape and old narrow shapes are no longer public peers
- Next step: remove the remaining carried `proposal_set` / `proposal` compatibility objects in a separate contract-removal slice if explicitly requested
- Files:
  - jeff/cognitive/selection.py
  - jeff/cognitive/planning.py
  - jeff/orchestrator/validation.py
  - jeff/cognitive/proposal/__init__.py  

## 2026-04-17 16:42 â€” Selection Slice A package foundation

- Scope: cognitive selection package and contract surface
- Done:
  - replaced the flat `jeff/cognitive/selection.py` module with a dedicated `jeff/cognitive/selection/` package
  - added `SelectionRequest`, `SelectionResult`, and `SelectionDisposition` in `selection/contracts.py`
  - updated `jeff.cognitive` exports and local handoff docs for the new Selection package boundary
  - updated focused Selection tests to target the package surface and verify the flat module is gone
- Validation: `python -m pytest -q tests/unit/cognitive/test_selection_public_surface.py tests/unit/cognitive/test_selection_rules.py tests/unit/cognitive/test_conditional_planning.py tests/unit/orchestrator/test_orchestrator_failure_routing.py tests/unit/orchestrator/test_orchestrator_stage_order.py tests/unit/orchestrator/test_orchestrator_trace_and_lifecycle.py tests/integration/test_orchestrator_handoff_validation.py tests/acceptance/test_acceptance_backbone_flow.py` passed (`32 passed`)
- Current state: Selection now has a dedicated package-local contract surface with explicit bounded choice and non-selection outcomes, but still no runtime/comparison/validation engine behavior
- Next step: build later Selection behavior inside the new package without reintroducing flat-module or governance drift
- Files:
  - jeff/cognitive/selection/__init__.py
  - jeff/cognitive/selection/contracts.py
  - jeff/cognitive/selection/HANDOFF.md
  - jeff/cognitive/__init__.py
  - tests/unit/cognitive/test_selection_public_surface.py


## 2026-04-17 16:54 â€” Selection Slice B deterministic choice behavior

- Scope: cognitive selection package behavior
- Done:
  - added `jeff/cognitive/selection/decision.py` with deterministic Selection-local comparison and choice behavior
  - added `run_selection(...)` as the package entry for bounded Selection decisions from `SelectionRequest`
  - implemented explicit `selected`, `reject_all`, `defer`, and `escalate` outcomes from visible proposal factors only
  - added focused Selection behavior tests and updated handoffs for the new package reality
- Validation: `python -m pytest -q tests/unit/cognitive/test_selection_public_surface.py tests/unit/cognitive/test_selection_rules.py tests/unit/cognitive/test_selection_decision.py tests/unit/cognitive/test_conditional_planning.py tests/unit/orchestrator/test_orchestrator_failure_routing.py tests/unit/orchestrator/test_orchestrator_stage_order.py tests/unit/orchestrator/test_orchestrator_trace_and_lifecycle.py tests/integration/test_orchestrator_handoff_validation.py tests/acceptance/test_acceptance_backbone_flow.py` passed (`39 passed`)
- Current state: Selection now has a deterministic bounded choice entry inside its package, while runtime, validation, and orchestrator wiring remain separate and unimplemented here
- Next step: add later Selection refinement without turning this package into governance, validation, or runtime glue
- Files:
  - jeff/cognitive/selection/decision.py
  - jeff/cognitive/selection/__init__.py
  - jeff/cognitive/selection/HANDOFF.md
  - tests/unit/cognitive/test_selection_decision.py
  - tests/unit/cognitive/test_selection_public_surface.py