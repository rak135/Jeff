from pathlib import Path

from jeff.core.schemas import Scope
from jeff.memory import HashEmbedder, LocalFileMemoryStore
from jeff.memory.models import CommittedMemoryRecord, MemorySupportRef
from jeff.memory.types import utc_now


def _record(memory_id: str = "memory-1") -> CommittedMemoryRecord:
    now = utc_now()
    return CommittedMemoryRecord(
        memory_id=memory_id,
        memory_type="semantic",
        scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
        summary="Persisted local memory survives restart.",
        remembered_points=("Proposal support should still find this after a fresh process.",),
        why_it_matters="This verifies the local durable backend rather than an in-process fake.",
        support_quality="strong",
        stability="stable",
        created_at=now,
        updated_at=now,
        support_refs=(
            MemorySupportRef(
                ref_kind="research",
                ref_id="artifact-1",
                summary="Bounded artifact grounding.",
            ),
        ),
    )


def test_local_file_store_persists_records_and_embeddings_across_reload(tmp_path: Path) -> None:
    store = LocalFileMemoryStore(tmp_path / "memory")
    record = _record()
    embedder = HashEmbedder()

    store._store_committed_record(record)
    store.store_embedding("memory-1", embedder.embed(record.summary))

    reloaded = LocalFileMemoryStore(tmp_path / "memory")
    reloaded_record = reloaded.get_committed("memory-1")
    semantic_hits = reloaded.search_semantic(
        "project-1",
        embedder.embed("local memory survives restart"),
        memory_type_filter=None,
        limit=3,
    )

    assert reloaded_record is not None
    assert reloaded_record.summary == record.summary
    assert semantic_hits
    assert str(semantic_hits[0].memory_id) == "memory-1"


def test_local_file_store_allocate_memory_id_persists_counter_across_reload(tmp_path: Path) -> None:
    first = LocalFileMemoryStore(tmp_path / "memory")
    assert str(first.allocate_memory_id()) == "memory-1"

    reloaded = LocalFileMemoryStore(tmp_path / "memory")
    assert str(reloaded.allocate_memory_id()) == "memory-2"