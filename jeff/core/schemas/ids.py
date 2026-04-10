"""Typed ID primitives shared by the Phase 1 core."""

from __future__ import annotations

from typing import NewType

ProjectId = NewType("ProjectId", str)
WorkUnitId = NewType("WorkUnitId", str)
RunId = NewType("RunId", str)
TransitionId = NewType("TransitionId", str)
MemoryId = NewType("MemoryId", str)


def validate_typed_id(value: str, *, field_name: str) -> str:
    """Return a normalized ID value or raise if the shared ID contract is broken."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")

    return normalized


def coerce_project_id(value: str) -> ProjectId:
    return ProjectId(validate_typed_id(value, field_name="project_id"))


def coerce_work_unit_id(value: str) -> WorkUnitId:
    return WorkUnitId(validate_typed_id(value, field_name="work_unit_id"))


def coerce_run_id(value: str) -> RunId:
    return RunId(validate_typed_id(value, field_name="run_id"))


def coerce_transition_id(value: str) -> TransitionId:
    return TransitionId(validate_typed_id(value, field_name="transition_id"))


def coerce_memory_id(value: str) -> MemoryId:
    return MemoryId(validate_typed_id(value, field_name="memory_id"))
