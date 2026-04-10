"""Canonical root state models for the Jeff core."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from jeff.core.containers.models import Project, freeze_mapping
from jeff.core.schemas.ids import TransitionId, coerce_transition_id


@dataclass(frozen=True, slots=True)
class StateMeta:
    state_version: int = 0
    last_transition_id: TransitionId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state_version, int):
            raise TypeError("state_version must be an integer")
        if self.state_version < 0:
            raise ValueError("state_version must be zero or greater")

        if self.last_transition_id is not None:
            object.__setattr__(
                self,
                "last_transition_id",
                coerce_transition_id(str(self.last_transition_id)),
            )


@dataclass(frozen=True, slots=True)
class SystemState:
    system_lifecycle_state: str = "ready"

    def __post_init__(self) -> None:
        if not isinstance(self.system_lifecycle_state, str):
            raise TypeError("system_lifecycle_state must be a string")
        if not self.system_lifecycle_state.strip():
            raise ValueError("system_lifecycle_state must be a non-empty string")


@dataclass(frozen=True, slots=True)
class GlobalState:
    state_meta: StateMeta = field(default_factory=StateMeta)
    system: SystemState = field(default_factory=SystemState)
    projects: Mapping[str, Project] = field(default_factory=dict)

    def __post_init__(self) -> None:
        frozen_projects = freeze_mapping(self.projects)
        for key, project in frozen_projects.items():
            if key != project.project_id:
                raise ValueError("project registry keys must match project.project_id")
        object.__setattr__(self, "projects", frozen_projects)
