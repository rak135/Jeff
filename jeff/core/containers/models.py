"""Minimal canonical container models for Phase 1."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, TypeVar

from jeff.core.schemas.ids import (
    ProjectId,
    RunId,
    WorkUnitId,
    coerce_project_id,
    coerce_run_id,
    coerce_work_unit_id,
)

K = TypeVar("K")
V = TypeVar("V")


def _require_non_empty(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")

    return normalized


def freeze_mapping(mapping: Mapping[K, V] | None = None) -> Mapping[K, V]:
    return MappingProxyType(dict(mapping or {}))


@dataclass(frozen=True, slots=True)
class Run:
    run_id: RunId
    project_id: ProjectId
    work_unit_id: WorkUnitId
    run_lifecycle_state: str = "created"

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", coerce_run_id(str(self.run_id)))
        object.__setattr__(self, "project_id", coerce_project_id(str(self.project_id)))
        object.__setattr__(
            self,
            "work_unit_id",
            coerce_work_unit_id(str(self.work_unit_id)),
        )
        object.__setattr__(
            self,
            "run_lifecycle_state",
            _require_non_empty(
                self.run_lifecycle_state,
                field_name="run_lifecycle_state",
            ),
        )


@dataclass(frozen=True, slots=True)
class WorkUnit:
    work_unit_id: WorkUnitId
    project_id: ProjectId
    objective: str
    work_unit_lifecycle_state: str = "open"
    runs: Mapping[RunId, Run] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "work_unit_id",
            coerce_work_unit_id(str(self.work_unit_id)),
        )
        object.__setattr__(self, "project_id", coerce_project_id(str(self.project_id)))
        object.__setattr__(
            self,
            "objective",
            _require_non_empty(self.objective, field_name="objective"),
        )
        object.__setattr__(
            self,
            "work_unit_lifecycle_state",
            _require_non_empty(
                self.work_unit_lifecycle_state,
                field_name="work_unit_lifecycle_state",
            ),
        )

        frozen_runs = freeze_mapping(self.runs)
        for key, run in frozen_runs.items():
            if key != run.run_id:
                raise ValueError("run registry keys must match run.run_id")
            if run.project_id != self.project_id:
                raise ValueError("run.project_id must match owning work unit project_id")
            if run.work_unit_id != self.work_unit_id:
                raise ValueError("run.work_unit_id must match owning work unit work_unit_id")
        object.__setattr__(self, "runs", frozen_runs)


@dataclass(frozen=True, slots=True)
class Project:
    project_id: ProjectId
    name: str
    project_lifecycle_state: str = "active"
    work_units: Mapping[WorkUnitId, WorkUnit] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", coerce_project_id(str(self.project_id)))
        object.__setattr__(self, "name", _require_non_empty(self.name, field_name="name"))
        object.__setattr__(
            self,
            "project_lifecycle_state",
            _require_non_empty(
                self.project_lifecycle_state,
                field_name="project_lifecycle_state",
            ),
        )

        frozen_work_units = freeze_mapping(self.work_units)
        for key, work_unit in frozen_work_units.items():
            if key != work_unit.work_unit_id:
                raise ValueError("work unit registry keys must match work_unit.work_unit_id")
            if work_unit.project_id != self.project_id:
                raise ValueError(
                    "work_unit.project_id must match the owning project.project_id",
                )
        object.__setattr__(self, "work_units", frozen_work_units)
