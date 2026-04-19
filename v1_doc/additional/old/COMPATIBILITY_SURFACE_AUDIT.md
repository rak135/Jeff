# Compatibility Surface Audit
**Audited:** 2026-04-16
**Branch:** master
**Auditor:** Claude (read-only, no code changes made)

---

# 1. Executive Verdict

The repo is **ready for a targeted legacy retirement slice now**, but only partially.

Three surfaces can be retired in a single clean slice with no migration work first:

- `build_research_repair_model_request()` — test-only wrapper, one test to update
- `repair_adapter` kwarg on `synthesize_research()` — zero callers remain, dead code
- `_legacy_research_mode` field mechanism in `ResearchRequest` — the field is private/internal, the `.research_mode` property is still active but the naming can be consolidated

One surface requires a migration step before deletion:

- `ResearchResult` / `legacy.py` — has a real runtime caller in `jeff/orchestrator/validation.py`; must migrate that caller to `ResearchArtifact` before the module can be deleted

One surface is intentional infrastructure design, not a compatibility artifact in the retirement sense:

- `formatter_bridge` purpose routing and the `FORMATTER_BRIDGE_RUNTIME_OVERRIDE` constant — actively used, correctly named, not slated for removal

One naming inconsistency is a documented temporary bridge:

- `FORMATTER_BRIDGE_REQUEST_PURPOSE = "research_synthesis_formatter"` (the `purpose` field on the `ModelRequest` itself) differs from the routing purpose `"formatter_bridge"` — comment in `formatter.py:46` explicitly marks this as a temporary bridge pending infrastructure naming cleanup

---

# 2. Compatibility Surface Inventory

| # | Surface | Location | Type |
|---|---------|----------|------|
| 1 | `ResearchResult` class | `jeff/cognitive/research/legacy.py:18` | Legacy class |
| 2 | `legacy.py` module | `jeff/cognitive/research/legacy.py` | Legacy module |
| 3 | `build_research_repair_model_request()` | `jeff/cognitive/research/synthesis.py:488` | Compat wrapper function |
| 4 | `repair_adapter` kwarg | `jeff/cognitive/research/synthesis.py:105` | Compat parameter |
| 5 | `_legacy_research_mode` field + `ResearchRequest.objective` / `ResearchRequest.research_mode` InitVars | `jeff/cognitive/research/contracts.py:40-43` | Compat InitVar aliases |
| 6 | `FORMATTER_BRIDGE_REQUEST_PURPOSE = "research_synthesis_formatter"` | `jeff/cognitive/research/formatter.py:14` | Temporary naming bridge |
| 7 | `formatter_bridge` hard-coded string in `runtime.py:39` | `jeff/infrastructure/runtime.py:39` | Domain-specific fallback logic |

---

# 3. Classification Table

| Surface | Defined in | Referenced in | Classification | Why it still exists | Retirement precondition |
|---------|-----------|---------------|----------------|--------------------|-----------------------|
| `ResearchResult` | `legacy.py:18` | `orchestrator/validation.py:8,49,168`; `cognitive/__init__.py:17`; 3 test files | **ACTIVE RUNTIME DEPENDENCY** | `orchestrator/validation.py` still type-checks stage output against it | Migrate `orchestrator/validation.py` to accept `ResearchArtifact` for the research stage |
| `legacy.py` (module) | `jeff/cognitive/research/legacy.py` | `research/__init__.py:25`, `cognitive/__init__.py:17` | **ACTIVE RUNTIME DEPENDENCY** (blocked by `ResearchResult`) | Cannot delete until `ResearchResult` has zero callers | Same as `ResearchResult` |
| `build_research_repair_model_request()` | `synthesis.py:488` | `test_research_synthesis_repair_pass.py:18,187` only | **TEST-ONLY** | One test validates that the legacy wrapper still delegates correctly | Update that one test to call `build_research_formatter_bridge_model_request()` directly |
| `repair_adapter` kwarg | `synthesis.py:105` | No callers remain (grep: zero hits in tests or production code) | **DEAD / REMOVABLE NOW** | Was an old parameter name; code pops it silently but nobody passes it | None — safe to delete the `**legacy_kwargs` machinery |
| `_legacy_research_mode` + `objective`/`research_mode` InitVars | `contracts.py:40-43` | `.research_mode` property used by `commands.py:144,391,934`, `render.py:185`, `errors.py:28,39,64,76`; `.objective` used by `json_views.py:58`, `context.py:69` | **ACTIVE RUNTIME DEPENDENCY** | Interface and error layers reference both properties actively | These properties are real interface contracts; the only thing that is legacy is the storage mechanism (`_legacy_research_mode` field vs a plain field) — see §5 |
| `FORMATTER_BRIDGE_REQUEST_PURPOSE = "research_synthesis_formatter"` | `formatter.py:14` | `formatter.py:48` only | **COMPATIBILITY-ONLY** (documented temporary bridge) | `formatter.py:46` comment: "keep using existing runtime purpose contract until infrastructure naming is cleaned up separately" | Decide on canonical purpose string for Step 3 formatter requests and align ModelRequest tagging with routing |
| `formatter_bridge` hard-coded in `runtime.py:39` | `runtime.py:39` | `runtime.py:39,60`, `purposes.py:21`, `config.py` throughout | **ACTIVE RUNTIME DEPENDENCY** | Implements the fallback rule: if no formatter adapter configured, fall back to research adapter | Not a compatibility artifact per se — this is the live routing logic; flagged here for completeness |

---

# 4. Research Legacy Analysis

## 4.1 `legacy.py` and `ResearchResult`

**File:** `jeff/cognitive/research/legacy.py`
**Lines:** 56 total

`ResearchResult` is a frozen dataclass with fields: `request`, `sources`, `findings`, `inferences`, `contradictions`, `uncertainty_notes`, `recommendation`. It pre-dates the v1 contract `ResearchArtifact` (defined in `contracts.py:268`).

**Who still uses it:**

| Caller | File | Lines | Role |
|--------|------|-------|------|
| `orchestrator/validation.py` | production | 8, 49, 168 | Maps `"research"` stage to `ResearchResult` type; `isinstance` check in `_scope_from_output()` |
| `cognitive/__init__.py` | export | 17, 59 | Re-exports to public surface |
| `research/__init__.py` | export | 25, 56 | Re-exports from research package |
| `test_research_models.py` | test | 3, 14, 43 | Tests `ResearchResult` construction/validation rules |
| `test_research_public_surface.py` | test | 9, 22 | Asserts `ResearchResult` is still publicly accessible |
| `test_orchestrator_handoff_validation.py` | test | 2, 164, 168 | Constructs `ResearchResult` instances to drive orchestrator validation logic |

**What breaks if deleted now:**
`jeff/orchestrator/validation.py:49` maps the `"research"` stage to `ResearchResult`, and `validation.py:168` does `isinstance(output, ResearchResult)`. Deleting `legacy.py` today would break orchestrator handoff validation at runtime.

**Required migration before deletion:**
Migrate `orchestrator/validation.py` to accept `ResearchArtifact` (from `contracts.py`) as the expected output type for the `"research"` stage. Once that is done, the three test files can be updated or deleted, and `legacy.py` can be removed along with its re-exports from both `__init__.py` files.

---

## 4.2 `build_research_repair_model_request()` — compat wrapper

**File:** `jeff/cognitive/research/synthesis.py:488–504`

```python
def build_research_repair_model_request(
    request: ResearchRequest,
    evidence_pack: EvidencePack,
    malformed_output: str,
    *,
    primary_request: ModelRequest,
    adapter_id: str | None = None,
) -> ModelRequest:
    """Legacy compatibility wrapper for older repair-era helper callers."""
    return build_research_formatter_bridge_model_request(
        request=request,
        evidence_pack=evidence_pack,
        bounded_text=malformed_output,
        primary_request=primary_request,
        adapter_id=adapter_id,
    )
```

**Who still uses it:**
- `tests/unit/cognitive/test_research_synthesis_repair_pass.py:18` (import)
- `tests/unit/cognitive/test_research_synthesis_repair_pass.py:187` (call site)

**Test that uses it:**
`test_legacy_repair_request_helper_still_maps_to_formatter_bridge_contract` at line 182. The test verifies the wrapper still produces a `ModelRequest` with `purpose == "research_synthesis_formatter"` and `metadata["formatter_input_kind"] == "step1_bounded_text"`.

**What breaks if deleted now:**
Only that one test. No production code calls this function.

**Required migration:**
Update `test_research_synthesis_repair_pass.py:187` to call `build_research_formatter_bridge_model_request()` directly. The test logic remains identical; only the import and function name change.

---

## 4.3 `repair_adapter` kwarg

**File:** `jeff/cognitive/research/synthesis.py:100,105`

```python
def synthesize_research(
    ...,
    **legacy_kwargs: Any,
) -> ResearchArtifact:
    compatibility_formatter_adapter = legacy_kwargs.pop("repair_adapter", None)
    if legacy_kwargs:
        raise TypeError(...)
    effective_formatter_adapter = formatter_adapter or compatibility_formatter_adapter or adapter
```

**Who still uses it:**
Nobody. `grep -r "repair_adapter"` across the entire codebase returns exactly one hit: the `pop()` at `synthesis.py:105`. There are no callers that pass this keyword argument.

**Classification:** DEAD / REMOVABLE NOW

**What breaks if deleted:**
Nothing. Removing the `**legacy_kwargs` machinery and the `repair_adapter` pop is safe immediately.

---

## 4.4 `_legacy_research_mode` / `objective` / `research_mode` InitVars in `ResearchRequest`

**File:** `jeff/cognitive/research/contracts.py:40–43,103,118–119`

These are three compat InitVars on the frozen dataclass:
- `objective: InitVar[str | None]` — alias for `question`
- `scope: InitVar[Scope | None]` — deprecated; used only to hydrate project/work_unit/run_id
- `research_mode: InitVar[ResearchMode | None]` — stored into `_legacy_research_mode`

**Properties that expose these:**
- `.objective` — returns `self.question`
- `.research_mode` — returns `getattr(self, "_legacy_research_mode")`

**Who still uses the `.research_mode` property (active):**
- `jeff/interface/commands.py:144,391,934` — passes `research_mode=exc.research_mode` / `research_mode=spec.mode`
- `jeff/interface/render.py:185` — renders `derived['research_mode']`
- `jeff/cognitive/research/errors.py:28,39,64,76` — `ResearchSynthesisError` carries `research_mode`

**Who still uses `.objective` property (active):**
- `jeff/interface/json_views.py:58` — `"objective": work_unit.objective`
- `jeff/core/containers/models.py:80` — uses `self.objective`

**Classification:** The `.research_mode` and `.objective` properties are ACTIVE RUNTIME dependencies. The mechanism that backs them (`_legacy_research_mode` private field + InitVar indirection) is implementation-level legacy, but the properties themselves are not removable without changing the interface layer. This is best treated as internal cleanup debt, not a compatibility surface ready for retirement.

---

## 4.5 `FORMATTER_BRIDGE_REQUEST_PURPOSE = "research_synthesis_formatter"` naming inconsistency

**File:** `jeff/cognitive/research/formatter.py:14,48`

The Step 3 `ModelRequest` is tagged `purpose="research_synthesis_formatter"` (a tracing/logging identifier), while the routing purpose used to select the adapter is `"formatter_bridge"`. These two strings serve different roles, but the comment at `formatter.py:46` explicitly calls this a "deliberate temporary bridge" pending infrastructure naming cleanup.

**Implication:** This is not harmful at runtime. The routing infrastructure uses the `FORMATTER_BRIDGE_RUNTIME_OVERRIDE` string for adapter selection; the `purpose` field on `ModelRequest` is used for tracing metadata only. The inconsistency is cosmetic but worth resolving in an infrastructure naming cleanup pass.

---

# 5. Infrastructure / Runtime Compatibility Analysis

## 5.1 `formatter_bridge` special-case in `runtime.py`

**File:** `jeff/infrastructure/runtime.py:36–44`

```python
def get_adapter_for_purpose(self, purpose: str, *, fallback_adapter_id: str | None = None) -> ModelAdapter:
    override_adapter_id = self.purpose_overrides.for_purpose(purpose)
    if override_adapter_id is None:
        if purpose == "formatter_bridge":
            if fallback_adapter_id is not None:
                return self.get_model_adapter(fallback_adapter_id)
            return self.get_adapter_for_purpose("research")
        return self.get_default_model_adapter()
    return self.get_model_adapter(override_adapter_id)
```

**Classification:** ACTIVE RUNTIME DEPENDENCY

This is the live fallback rule: if no `formatter_bridge` override is configured, fall back to the `research` adapter rather than the default adapter. This is correct behavior, not a compatibility shim. The only thing "legacy" about it is the hard-coded domain string `"formatter_bridge"` rather than using `Purpose.FORMATTER_BRIDGE.value`. That is a trivial cleanup.

**Also noted:** `build_infrastructure_services()` at `runtime.py:60` iterates a hard-coded list of purpose strings including `"formatter_bridge"` for adapter warm-up. Same pattern — correct behavior, trivial cleanup to use the `Purpose` enum values.

## 5.2 `PurposeOverrides` field naming

**File:** `jeff/infrastructure/config.py:109`

The `formatter_bridge` field in `PurposeOverrides` is correctly named and directly maps to the `Purpose.FORMATTER_BRIDGE` enum value. No compatibility concern here; this is the canonical name.

## 5.3 No `research_repair` naming remains in production code

`research_repair` appears only in documentation files (`FULL_REPO_REVIEW.md`, build plan docs, handoff notes). It does not appear in any production `.py` file or test file as a symbol. The migration from `research_repair` → `formatter_bridge` is already complete at the code level.

---

# 6. Test-Only Compatibility Analysis

## 6.1 Tests validating `build_research_repair_model_request()` wrapper

**File:** `tests/unit/cognitive/test_research_synthesis_repair_pass.py`

- Line 18: imports `build_research_repair_model_request`
- Line 182–196: test `test_legacy_repair_request_helper_still_maps_to_formatter_bridge_contract` — explicitly tests the legacy wrapper delegates correctly

This test exists solely to ensure the compatibility wrapper hasn't drifted from the real function. Once the wrapper is deleted, this test should be deleted or repurposed to directly test `build_research_formatter_bridge_model_request()`.

## 6.2 Tests validating `ResearchResult` construction

**File:** `tests/unit/cognitive/test_research_models.py`

Lines 3, 14, 43 — constructs `ResearchResult` instances and validates their invariants (source-finding cross-reference, inference index bounds, etc.). These tests exist solely because `ResearchResult` still exists. Once `orchestrator/validation.py` is migrated to `ResearchArtifact`, these tests lose their justification.

## 6.3 Test asserting `ResearchResult` is still on the public surface

**File:** `tests/unit/cognitive/test_research_public_surface.py:21–22`

```python
def test_legacy_research_result_is_isolated_but_still_public() -> None:
    assert ResearchResult.__module__ == "jeff.cognitive.research.legacy"
```

This test explicitly asserts that `ResearchResult` is still accessible at `jeff.cognitive.research.ResearchResult`. This test must be deleted as part of the retirement, not just updated.

## 6.4 Integration test using `ResearchResult` as orchestrator output

**File:** `tests/integration/test_orchestrator_handoff_validation.py:2,164,168`

Constructs `ResearchResult` instances (line 164) to simulate research-stage output going into the orchestrator handoff validation. This is the integration-level twin of the production `orchestrator/validation.py` dependency. Must be updated to construct `ResearchArtifact` instances instead.

---

# 7. Dead Surfaces Removable Now

Only one surface is unambiguously dead with zero callers:

| Surface | Evidence of zero callers | Safe to remove? |
|---------|--------------------------|-----------------|
| `repair_adapter` kwarg in `synthesize_research()` | `grep -r "repair_adapter"` returns exactly one hit: the `pop()` itself in `synthesis.py:105`. No test, no production code passes this kwarg. | Yes — remove `**legacy_kwargs`, the `pop()`, and the `compatibility_formatter_adapter` variable |

The `build_research_repair_model_request()` function is not dead by the strict definition (one test still calls it), but it is test-only and can be removed immediately if that test is updated in the same commit.

---

# 8. Recommended Retirement Order

Retire in this exact sequence to avoid breaking anything mid-slice:

**Step 1 — Remove dead `repair_adapter` kwarg (zero migration required)**

In `jeff/cognitive/research/synthesis.py`:
- Remove `**legacy_kwargs: Any` from `synthesize_research()` signature
- Remove the `compatibility_formatter_adapter = legacy_kwargs.pop("repair_adapter", None)` line
- Remove the `if legacy_kwargs: raise TypeError(...)` guard
- Update `effective_formatter_adapter` to just `formatter_adapter or adapter`

No test changes needed. Nothing else references this kwarg.

**Step 2 — Retire `build_research_repair_model_request()` wrapper (one test to update)**

In `jeff/cognitive/research/synthesis.py`:
- Delete `build_research_repair_model_request()` (lines 488–504)
- Remove it from `__init__.py` exports if present

In `tests/unit/cognitive/test_research_synthesis_repair_pass.py`:
- Change the import from `build_research_repair_model_request` to `build_research_formatter_bridge_model_request`
- Update `test_legacy_repair_request_helper_still_maps_to_formatter_bridge_contract` to call `build_research_formatter_bridge_model_request()` directly (the assertion body stays the same)
- Rename the test to reflect it now tests the real function

**Step 3 — Migrate orchestrator validation to `ResearchArtifact` (required before legacy.py deletion)**

In `jeff/orchestrator/validation.py`:
- Replace `ResearchResult` import with `ResearchArtifact` from `jeff.cognitive.research.contracts`
- Update the stage-type map entry: `"research": ResearchArtifact`
- Update the `isinstance` check at line 168

In `tests/integration/test_orchestrator_handoff_validation.py`:
- Replace `ResearchResult` construction with `ResearchArtifact` instances
- Update the import

**Step 4 — Delete `legacy.py` and clean up exports (after Step 3 complete)**

- Delete `jeff/cognitive/research/legacy.py`
- Remove `from .legacy import ResearchResult` from `research/__init__.py:25`
- Remove `"ResearchResult"` from `research/__init__.py:56` `__all__`
- Remove `ResearchResult` from `jeff/cognitive/__init__.py:17,59`
- Delete `tests/unit/cognitive/test_research_models.py` (only tests `ResearchResult` invariants)
- Delete the `test_legacy_research_result_is_isolated_but_still_public` test in `test_research_public_surface.py`

**Step 5 (optional, lower priority) — Resolve `FORMATTER_BRIDGE_REQUEST_PURPOSE` naming inconsistency**

In `jeff/cognitive/research/formatter.py`:
- Decide on canonical purpose string for Step 3 `ModelRequest` tagging
- The options are: keep `"research_synthesis_formatter"` as a tracing label (fine), or align it with `"formatter_bridge"` for consistency
- Remove the "temporary bridge" comment once the naming decision is made final

---

# 9. Minimum Safe Retirement Slice

The smallest correct next implementation slice that is both safe and meaningful:

**Slice: "Repair-era compat removal"**

Scope: Steps 1 and 2 from §8 above.

Files changed:
- `jeff/cognitive/research/synthesis.py` — remove `repair_adapter` kwarg machinery (lines 100, 105–108, 110 partial), delete `build_research_repair_model_request()` (lines 488–504)
- `tests/unit/cognitive/test_research_synthesis_repair_pass.py` — update import and rename/rewrite the one legacy wrapper test

Files unchanged: everything else. This slice does not touch `legacy.py`, `ResearchResult`, orchestrator validation, or infrastructure.

**Risk:** Minimal. The only test affected is the one that explicitly tests the legacy wrapper. The production path is unchanged.

**Outcome:** Eliminates two repair-era compat surfaces with no migration prerequisite.

---

# 10. Red Flags

**Do not delete these before their preconditions are met:**

1. **`legacy.py` / `ResearchResult`** — `jeff/orchestrator/validation.py` is a production runtime caller. Deleting `legacy.py` before migrating `orchestrator/validation.py` will break the orchestrator's ability to validate research-stage output at runtime. This is not test-only breakage.

2. **`.research_mode` property on `ResearchRequest`** — `jeff/interface/commands.py` passes this to error construction and request building at three call sites. Do not remove the property without updating the entire interface layer.

3. **`.objective` property on `ResearchRequest`** — Used by `json_views.py` and `core/containers/models.py`. Do not remove without checking every call site.

4. **`FORMATTER_BRIDGE_RUNTIME_OVERRIDE` constant in `formatter.py`** — This is the live adapter routing key. Not a compatibility surface; do not delete it.

5. **`formatter_bridge` special-case in `runtime.py:39`** — The fallback logic `if purpose == "formatter_bridge": return self.get_adapter_for_purpose("research")` is a real runtime fallback that production config depends on. It only looks like a compat shim because the string is hard-coded rather than using the `Purpose` enum.

---

# 11. Final Recommendation

**Immediate retirement slice (Steps 1 and 2) — proceed now.**

The `repair_adapter` kwarg is dead code with zero callers. The `build_research_repair_model_request()` wrapper is test-only with a single test caller that is trivially updated. Neither requires any migration work. Both can be deleted in a single focused PR with low risk.

**One migration slice required before legacy.py deletion (Step 3).**

`ResearchResult` / `legacy.py` cannot be deleted until `jeff/orchestrator/validation.py` is migrated to use `ResearchArtifact`. That migration is self-contained but touches the orchestrator validation contract, which warrants its own PR and test coverage review.

**Steps 4 and 5** follow naturally from Steps 1–3 and should be done as immediate follow-up, not deferred.

**Do not** attempt to delete `legacy.py` in the same slice as the repair-era compat removal. The orchestrator dependency is a real runtime blocker.

---

*Audit complete. No code was modified.*
