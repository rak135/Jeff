"""Support links, supersession links, and merge links for committed memory.

Memory may thin-link to research archive, compiled knowledge, source refs,
evidence refs, related committed memory, and supersession targets.
Memory must not own persistence of those objects.
"""

from __future__ import annotations

from jeff.core.schemas import MemoryId

from .ids import MemoryLinkId, coerce_link_id
from .models import CommittedMemoryRecord, MemorySupportRef
from .schemas import MemoryLink
from .types import LINK_TYPES, utc_now

_link_counter = 0


def _next_link_id() -> MemoryLinkId:
    global _link_counter
    _link_counter += 1
    return coerce_link_id(f"mlink-{_link_counter}")


def build_support_links(
    *,
    record: CommittedMemoryRecord,
) -> tuple[MemoryLink, ...]:
    """Create thin-link records from a committed record's support_refs."""
    links: list[MemoryLink] = []
    for ref in record.support_refs:
        link_type = _ref_kind_to_link_type(ref.ref_kind)
        links.append(
            MemoryLink(
                memory_link_id=_next_link_id(),
                memory_id=record.memory_id,
                link_type=link_type,
                target_id=ref.ref_id,
                target_family=ref.ref_kind,
            )
        )
    return tuple(links)


def build_supersession_link(
    *,
    new_memory_id: MemoryId,
    superseded_memory_id: MemoryId,
) -> MemoryLink:
    """Create a supersedes_ref link from new record to superseded record."""
    return MemoryLink(
        memory_link_id=_next_link_id(),
        memory_id=new_memory_id,
        link_type="supersedes_ref",
        target_id=str(superseded_memory_id),
        target_family="memory_record",
    )


def build_merge_link(
    *,
    target_memory_id: MemoryId,
    merged_into_memory_id: MemoryId,
) -> MemoryLink:
    """Create a merged_into_ref link."""
    return MemoryLink(
        memory_link_id=_next_link_id(),
        memory_id=target_memory_id,
        link_type="merged_into_ref",
        target_id=str(merged_into_memory_id),
        target_family="memory_record",
    )


def _ref_kind_to_link_type(ref_kind: str) -> str:
    _map = {
        "artifact": "research_artifact_ref",
        "evidence": "evidence_ref",
        "research": "research_artifact_ref",
        "evaluation": "evidence_ref",
        "operator_input": "source_ref",
    }
    return _map.get(ref_kind, "source_ref")
