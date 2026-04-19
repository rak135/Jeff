# Module Name

- `jeff.memory`

# Module Purpose

- Own durable non-truth continuity: candidate creation, write discipline, retrieval, storage, and canonical linking support.

# Current Role in Jeff

- Creates memory candidates from allowed inputs, decides whether they should be written, stores committed records, and retrieves scoped memory views without overriding current truth.

# Boundaries / Non-Ownership

- Does not own canonical truth, proposal generation, approval, readiness, evaluation verdicts, or transition commit.
- Does not let memory become current truth.
- Does not allow non-Memory code to author memory candidates directly.

# Owned Files / Areas

- `jeff/memory/models.py`
- `jeff/memory/types.py`
- `jeff/memory/write_pipeline.py`
- `jeff/memory/store.py`
- `jeff/memory/retrieval.py`

# Dependencies In / Out

- In: reads Core truth for scope and link validation and consumes evaluation-backed signals or other allowed inputs.
- Out: returns committed memory records, retrieval views, and committed memory IDs for transition linkage only.

# Canonical Docs to Read First

- `v1_doc/ARCHITECTURE.md`
- `v1_doc/MEMORY_SPEC.md`
- `v1_doc/MEMORY_ARCHITECTURE.md`

# Current Implementation Reality

- Runtime wiring now depends on `MemoryStoreProtocol` rather than a single concrete store.
- Research memory handoff can use the runtime-selected `in_memory` or `postgres` backend.
- Retrieval is truth-first and scope-filtered.
- The implementation protects candidate creation, write discipline, and project isolation with targeted negative tests.

# Important Invariants

- Only Memory creates memory candidates.
- Memory does not override current truth.
- Canonical state may reference only committed memory IDs.
- Project isolation still applies to retrieval and linking.

# Active Risks / Unresolved Issues

- Broad memory UX remains intentionally deferred; v1 exposes only bounded research handoff and retrieval-adjacent value.
- Any shortcut that treats retrieved memory as current truth would break this module's core contract.

# Next Continuation Steps

- Keep follow-up work focused on discipline, retrieval correctness, and narrow backend truthfulness rather than expanding a `/memory` command family.

# Submodule Map

- `models.py`: candidate, record, and write-decision models; no separate handoff.
- `write_pipeline.py`: candidate creation and write discipline; no separate handoff.
- `store.py`: in-memory store; no separate handoff.
- `retrieval.py`: truth-first retrieval and canonical linking helpers; no separate handoff.
- `types.py`: literal families; no separate handoff.

# Related Handoffs

- `handoffs/system/REPO_HANDOFF.md`
- `jeff/core/HANDOFF.md`
- `jeff/cognitive/HANDOFF.md`
- `jeff/orchestrator/HANDOFF.md`
