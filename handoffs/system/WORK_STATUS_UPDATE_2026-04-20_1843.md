## 2026-04-20 18:43 - Proposal audit and bounded tuning pass

- Scope: proposal prompts, `/run` proposal persistence, and live operator verification
- Done:
  - ran a real black-box proposal and `/run` audit against the configured Ollama runtime with serialized live commands
  - tuned proposal generation and repair prompts to reduce generic single-option scarcity and fallback wording
  - added persisted proposal operator records for `/run` proposal attempts
  - added `/run`-specific proposal constraints so generic bounded-rollout wording still surfaces the fixed validation path
  - added targeted unit and integration coverage for the new prompt guidance and `/run` proposal inspection path
- Validation: `python -m pytest -q tests/unit/cognitive/test_proposal_prompt_files.py tests/unit/cognitive/test_proposal_generation.py tests/integration/test_cli_proposal_operator_surface.py tests/integration/test_cli_run_live_context_execution.py` passed with `29 passed`; live `/proposal` and `/run` re-tests completed
- Current state: proposal is operator-inspectable after `/run`, live output quality is improved, and generic `/run` wording is working again under the bounded validation surface
- Next step: add structured bounded-plan support into proposal input if richer live assumptions/risks/constraints are still needed
- Files:
  - PROMPTS/proposal/STEP1_GENERATION.md
  - PROMPTS/proposal/STEP1_REPAIR.md
  - jeff/cognitive/proposal/operator_records.py
  - jeff/interface/commands/proposal.py
  - jeff/interface/commands/scope.py
  - PROPOSAL_BLACK_BOX_AND_TUNING_REPORT.md
