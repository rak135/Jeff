## 2026-04-15 09:00 — Infrastructure Slice 6: vocabulary modules added

- Scope: jeff/infrastructure vocabulary layer
- Done:
  - added `purposes.py` with `Purpose` enum (RESEARCH, RESEARCH_REPAIR, PROPOSAL, PLANNING, EVALUATION) — values match existing PurposeOverrides string keys
  - added `output_strategies.py` with `OutputStrategy` enum (PLAIN_TEXT, BOUNDED_TEXT_THEN_PARSE, BOUNDED_TEXT_THEN_FORMATTER)
  - added `capability_profiles.py` with `CapabilityProfile` dataclass and `CapabilityProfileRegistry`
  - exported all three from `jeff/infrastructure/__init__.py`
  - added 20 focused unit tests across three new test files (all pass)
- Validation: 63/63 infrastructure unit tests pass; no regressions
- Current state: vocabulary modules exist, are reusable, contain no research/domain semantics; research runtime behavior unchanged; config.py and runtime.py untouched
- Next step: Slice 7 — wire vocabulary into runtime routing or begin Proposal/Evaluation domain layer
- Files:
  - jeff/infrastructure/purposes.py (new)
  - jeff/infrastructure/output_strategies.py (new)
  - jeff/infrastructure/capability_profiles.py (new)
  - jeff/infrastructure/__init__.py (4 lines added)
  - tests/unit/infrastructure/test_purposes.py (new)
  - tests/unit/infrastructure/test_output_strategies.py (new)
  - tests/unit/infrastructure/test_capability_profiles.py (new)
