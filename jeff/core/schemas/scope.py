"""Shared project/work-unit/run scope block."""

from __future__ import annotations

from dataclasses import dataclass

from .ids import (
    ProjectId,
    RunId,
    WorkUnitId,
    coerce_project_id,
    coerce_run_id,
    coerce_work_unit_id,
)


@dataclass(frozen=True, slots=True)
class Scope:
    project_id: ProjectId
    work_unit_id: WorkUnitId | None = None
    run_id: RunId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", coerce_project_id(str(self.project_id)))

        if self.work_unit_id is not None:
            object.__setattr__(
                self,
                "work_unit_id",
                coerce_work_unit_id(str(self.work_unit_id)),
            )

        if self.run_id is not None:
            object.__setattr__(self, "run_id", coerce_run_id(str(self.run_id)))

        if self.run_id is not None and self.work_unit_id is None:
            raise ValueError("run_id requires work_unit_id in the shared scope block")
