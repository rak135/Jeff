# Submodule Name

- `jeff.cognitive.research`

# Parent Module

- `jeff.cognitive`

# Submodule Purpose

- Own bounded research contracts and the shared research pipeline from explicit inputs to source-aware support outputs, including acquisition, synthesis, persistence, and selective memory handoff.

# Boundaries / Non-Ownership

- Does not own canonical truth, governance permission, execution, outcome semantics, memory retrieval semantics, memory commit decisions, or provider implementations.
- Does not browse autonomously, schedule recurring work, mutate truth, or treat research artifacts as memory or truth.
- Does not persist raw provider outputs or giant source dumps.
- Memory handoff begins only after a validated research artifact exists and ends when the current Memory pipeline returns write/reject/defer.

# Owned Files / Areas

- `jeff/cognitive/research/__init__.py`
- `jeff/cognitive/research/contracts.py`
- `jeff/cognitive/research/bounded_syntax.py`
- `jeff/cognitive/research/synthesis.py`
- `jeff/cognitive/research/deterministic_transformer.py`
- `jeff/cognitive/research/formatter.py`
- `jeff/cognitive/research/fallback_policy.py`
- `jeff/cognitive/research/debug.py`
- `jeff/cognitive/research/documents.py`
- `jeff/cognitive/research/web.py`
- `jeff/cognitive/research/persistence.py`
- `jeff/cognitive/research/memory_handoff.py`
- `jeff/cognitive/research/errors.py`
- `jeff/cognitive/research/legacy.py`

# Canonical Docs to Read First

- `v1_doc/PLANNING_AND_RESEARCH_SPEC.md`
- `v1_doc/additional/RESEARCH_ARCHITECTURE.md`
- `v1_doc/CONTEXT_SPEC.md`
- `v1_doc/MEMORY_SPEC.md`
- `v1_doc/additional/MEMORY_ARCHITECTURE.md`
- `v1_doc/ARCHITECTURE.md`

# Current Implementation Reality

- `contracts.py` owns the active research request, source, evidence, finding, and artifact contracts.
- `bounded_syntax.py` owns the Step 1 bounded-text syntax contract and syntax validation helpers.
- `deterministic_transformer.py` owns the Step 2 deterministic parse/normalization path from bounded text into the candidate research payload shape.
- `formatter.py` and `fallback_policy.py` own the Step 3 formatter fallback bridge and formatter-eligibility checks after deterministic-transform failure.
- `synthesis.py` is now a live 3-step pipeline orchestrator:
  - Step 1 bounded text generation from an explicit `EvidencePack`
  - Step 2 deterministic transform as the primary normalization path
  - Step 3 formatter fallback only after Step 2 failure
- The current live synthesis path is no longer JSON-first on the primary branch.
- The current temporary formatter bridge still routes through the runtime `research_repair` override; this is a compatibility bridge for Step 3 formatter selection, not the primary path.
- `debug.py` now exposes truthful research checkpoints aligned to Step 1, Step 2, Step 3, remap, provenance, persistence, projection, and render boundaries.
- `documents.py` performs bounded local-document acquisition from explicit paths only and derives bounded evidence deterministically.
- `web.py` performs bounded web acquisition from explicit queries only, preserves URL provenance, and derives bounded evidence deterministically.
- Downstream after synthesis remains unchanged in role and semantics:
  - citation-key remap back to internal `source_id`
  - fail-closed provenance validation
  - persistence
  - projection/render
  - optional memory handoff
- `persistence.py` stores validated research artifacts as local JSON support records with scope, sources, evidence, timestamps, and stable retrieval/listing behavior.
- `memory_handoff.py` distills validated research artifacts into bounded memory-worthy inputs and delegates final write/reject/defer authority to the current Memory write pipeline.
- `legacy.py` still exists because real callers/tests still use `ResearchResult` and the compatibility request path; it is intentionally isolated and not the main path.
- CLI research integration now exists and has been verified against the live runtime; the CLI remains a thin operator surface over this package rather than the owner of research semantics.
- Orchestrator-integrated research continuation now exists in one bounded form: post-selection `research_followup` can enter the existing research stage, preserve a `ResearchArtifact`, and then pass that artifact through an explicit downstream sufficiency evaluation before stopping truthfully at the research boundary.

# Local Invariants / Contract Notes

- Synthesis starts from an explicit `EvidencePack`; the model is not allowed to invent the research process around it.
- Step 1 produces bounded text, not the final persisted artifact shape.
- Step 2 is the primary normalization path and must remain deterministic rather than semantic repair.
- Step 3 runs only after Step 2 failure and receives the bounded Step 1 artifact, not the original full evidence pack.
- The temporary `research_repair` runtime purpose is currently being used as a formatter bridge; that naming does not mean the main path is repair-first.
- Provenance is preserved through `source_id`, `source_refs`, persisted `source_items`, persisted `evidence_items`, and explicit web/document locators.
- Research artifacts are durable support records, not truth and not memory.
- Persistence stores only validated research outputs plus bounded supporting context; it does not store raw provider payloads.
- Document and web acquisition are bounded, deterministic enough for tests, and must stay explicit instead of becoming hidden crawl/search loops.
- Memory handoff is selective, distilled, and thin; it must not dump whole research artifacts into Memory or bypass the current Memory write pipeline.
- Orchestrator entry into research does not make research output permission, truth, action, governance, or execution authority.
- Research sufficiency evaluation downstream of orchestrator entry does not upgrade research into permission or truth; it only distinguishes decision-support-ready output from explicit unresolved gaps.
- Future research work must stay inside this package instead of reintroducing flat blob modules.

# Active Risks / Blockers / Unresolved Issues

- The web path is intentionally basic and bounded; richer freshness comparison, source ranking, and broader fetch logic remain unimplemented.
- Persistence is local JSON only; there is no operator-facing inspection surface yet.
- Research-to-memory gating is intentionally simple and could still over- or under-select some artifacts until more real usage sharpens the boundary.
- The legacy surface still exists and can drift if future work updates only the active path without checking remaining callers/tests.
- The temporary `research_repair` formatter bridge naming can mislead readers unless they check the actual 3-step runtime path.
- Orchestrator-integrated research continuation now exists only as a bounded research-plus-sufficiency boundary stop; there is still no hidden research-to-governance or research-to-execution shortcut.

# Next Continuation Steps

- If adding new research capability, place it in the appropriate local slice: contracts, bounded syntax, deterministic transform, formatter/fallback, acquisition, synthesis, persistence, or handoff.
- Keep future source providers or persistence reuse bounded and provenance-preserving.
- Re-check whether `legacy.py` is still needed whenever real callers/tests move off `ResearchResult` and compatibility request behavior.
- Keep the 3-step ownership boundary hard:
  - Research owns Step 1 syntax, Step 2 deterministic parsing, Step 3 fallback policy, and research semantics.
  - Infrastructure owns runtime/config and adapter routing.
  - Interface stays downstream.
- Add any broader downstream research bridge only after preserving the current separation between research artifacts, memory, truth, and permission.

# Related Handoffs

- `jeff/cognitive/HANDOFF.md`
- `handoffs/system/REPO_HANDOFF.md`
- `jeff/infrastructure/HANDOFF.md`
- `jeff/memory/HANDOFF.md`
- `jeff/orchestrator/HANDOFF.md`
