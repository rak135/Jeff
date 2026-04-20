## 2026-04-19 22:29 — Hardened proposal step 1 contract

- Scope: proposal generation prompt, parser, validator, repair pass, and live `/run` verification
- Done:
  - rewrote `STEP1_GENERATION.md` to a stricter research-style bounded contract with exact fallback markers and anti-authority rules
  - added `STEP1_REPAIR.md` and one correction-guided repair retry in the proposal pipeline
  - aligned proposal parsing and validation to canonical fallback markers and narrower authority leakage checks
  - updated proposal unit tests and `/run` integration fixtures to the new contract
  - verified live `/run` against the configured Ollama runtime and observed successful end-to-end completion
- Validation: `pytest tests/unit/cognitive/test_proposal_parsing.py tests/unit/cognitive/test_proposal_validation.py tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_api.py -q` and `pytest tests/unit/cognitive/test_proposal_parsing.py tests/unit/cognitive/test_proposal_validation.py tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_api.py tests/unit/cognitive/proposal/test_proposal_generation_bridge.py tests/integration/test_cli_run_live_context_execution.py -q` both passed; live `/run` completed with `run-2`
- Current state: proposal now passes the live configured provider path well enough for `/run` to reach selection, governance, execution, and evaluation successfully
- Next step: add optional environment-gated acceptance coverage for live-provider proposal success to protect this path from regressions
- Files:
  - PROMPTS/proposal/STEP1_GENERATION.md
  - PROMPTS/proposal/STEP1_REPAIR.md
  - jeff/cognitive/proposal/api.py
  - jeff/cognitive/proposal/parsing.py
  - jeff/cognitive/proposal/validation.py
  - tests/integration/test_cli_run_live_context_execution.py