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
- `jeff/cognitive/research/synthesis.py`
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
- `synthesis.py` turns an explicit `EvidencePack` into a provider-neutral JSON model request, validates structured output fail-closed, and returns a validated `ResearchArtifact`.
- `documents.py` performs bounded local-document acquisition from explicit paths only and derives bounded evidence deterministically.
- `web.py` performs bounded web acquisition from explicit queries only, preserves URL provenance, and derives bounded evidence deterministically.
- `persistence.py` stores validated research artifacts as local JSON support records with scope, sources, evidence, timestamps, and stable retrieval/listing behavior.
- `memory_handoff.py` distills validated research artifacts into bounded memory-worthy inputs and delegates final write/reject/defer authority to the current Memory write pipeline.
- `legacy.py` still exists because real callers/tests still use `ResearchResult` and the compatibility request path; it is intentionally isolated and not the main path.

# Local Invariants / Contract Notes

- Synthesis starts from an explicit `EvidencePack`; the model is not allowed to invent the research process around it.
- Provenance is preserved through `source_id`, `source_refs`, persisted `source_items`, persisted `evidence_items`, and explicit web/document locators.
- Research artifacts are durable support records, not truth and not memory.
- Persistence stores only validated research outputs plus bounded supporting context; it does not store raw provider payloads.
- Document and web acquisition are bounded, deterministic enough for tests, and must stay explicit instead of becoming hidden crawl/search loops.
- Memory handoff is selective, distilled, and thin; it must not dump whole research artifacts into Memory or bypass the current Memory write pipeline.
- Future research work must stay inside this package instead of reintroducing flat blob modules.

# Active Risks / Blockers / Unresolved Issues

- The web path is intentionally basic and bounded; richer freshness comparison, source ranking, and broader fetch logic remain unimplemented.
- Persistence is local JSON only; there is no operator-facing inspection surface yet.
- Research-to-memory gating is intentionally simple and could still over- or under-select some artifacts until more real usage sharpens the boundary.
- The legacy surface still exists and can drift if future work updates only the active path without checking remaining callers/tests.
- There is still no orchestrator or CLI integration for the new research slices.

# Next Continuation Steps

- If adding new research capability, place it in the appropriate local slice: contracts, acquisition, synthesis, persistence, or handoff.
- Keep future source providers or persistence reuse bounded and provenance-preserving.
- Re-check whether `legacy.py` is still needed whenever real callers/tests move off `ResearchResult` and compatibility request behavior.
- Add downstream operator/orchestrator integration only after preserving the current separation between research artifacts, memory, and truth.

# Related Handoffs

- `jeff/cognitive/HANDOFF.md`
- `handoffs/system/REPO_HANDOFF.md`
- `jeff/infrastructure/HANDOFF.md`
- `jeff/memory/HANDOFF.md`
- `jeff/orchestrator/HANDOFF.md`
