"""Minimal transition models for Phase 1 truth mutation."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Mapping

from jeff.core.schemas.envelopes import ValidationIssue
from jeff.core.schemas.ids import TransitionId, coerce_transition_id
from jeff.core.schemas.scope import Scope
from jeff.core.state.models import GlobalState

TransitionType = Literal["create_project", "create_work_unit", "create_run", "update_run"]
TransitionOutcome = Literal["committed", "rejected"]
ALLOWED_TRANSITION_TYPES = {"create_project", "create_work_unit", "create_run", "update_run"}


def _freeze_payload(value: Mapping[str, object] | None) -> Mapping[str, object]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True, slots=True)
class TransitionRequest:
    transition_id: TransitionId
    transition_type: TransitionType
    basis_state_version: int
    scope: Scope
    payload: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transition_id",
            coerce_transition_id(str(self.transition_id)),
        )
        if self.transition_type not in ALLOWED_TRANSITION_TYPES:
            raise ValueError(f"unsupported transition_type: {self.transition_type}")

        if not isinstance(self.basis_state_version, int):
            raise TypeError("basis_state_version must be an integer")
        if self.basis_state_version < 0:
            raise ValueError("basis_state_version must be zero or greater")

        object.__setattr__(self, "payload", _freeze_payload(self.payload))


@dataclass(frozen=True, slots=True)
class CandidateState:
    state: GlobalState
    changed_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.changed_paths:
            raise ValueError("candidate state must declare at least one changed path")


@dataclass(frozen=True, slots=True)
class TransitionResult:
    transition_id: TransitionId
    transition_result: TransitionOutcome
    state_before_version: int
    state_after_version: int
    state: GlobalState
    changed_paths: tuple[str, ...] = ()
    validation_errors: tuple[ValidationIssue, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transition_id",
            coerce_transition_id(str(self.transition_id)),
        )
