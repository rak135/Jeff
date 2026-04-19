"""Distinct approval contract for bounded actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jeff.core.schemas import ActionId, coerce_action_id

ApprovalVerdict = Literal[
    "granted",
    "denied",
    "absent",
    "stale",
    "mismatched",
    "not_required",
]

_BOUND_VERDICTS = {"granted", "denied", "stale", "mismatched"}


@dataclass(frozen=True, slots=True)
class Approval:
    approval_verdict: ApprovalVerdict
    action_id: ActionId | None = None
    action_binding_key: str | None = None
    basis_state_version: int | None = None

    def __post_init__(self) -> None:
        if self.approval_verdict in _BOUND_VERDICTS:
            if self.action_id is None:
                raise ValueError(
                    "action_id is required when approval_verdict is bound to a specific action",
                )
            if self.action_binding_key is None or not self.action_binding_key.strip():
                raise ValueError(
                    "action_binding_key is required when approval_verdict is bound to a specific action",
                )
            if not isinstance(self.basis_state_version, int):
                raise ValueError(
                    "basis_state_version is required when approval_verdict is bound to a specific action",
                )

        if self.action_id is not None:
            object.__setattr__(self, "action_id", coerce_action_id(str(self.action_id)))

        if self.action_binding_key is not None:
            normalized = self.action_binding_key.strip()
            if not normalized:
                raise ValueError("action_binding_key must be non-empty when provided")
            object.__setattr__(self, "action_binding_key", normalized)

        if self.basis_state_version is not None and self.basis_state_version < 0:
            raise ValueError("basis_state_version must be zero or greater")

    @classmethod
    def granted_for(cls, *, action_id: str, action_binding_key: str, basis_state_version: int) -> "Approval":
        return cls(
            approval_verdict="granted",
            action_id=action_id,
            action_binding_key=action_binding_key,
            basis_state_version=basis_state_version,
        )

    @classmethod
    def denied_for(cls, *, action_id: str, action_binding_key: str, basis_state_version: int) -> "Approval":
        return cls(
            approval_verdict="denied",
            action_id=action_id,
            action_binding_key=action_binding_key,
            basis_state_version=basis_state_version,
        )

    @classmethod
    def absent(cls) -> "Approval":
        return cls(approval_verdict="absent")

    @classmethod
    def not_required(cls) -> "Approval":
        return cls(approval_verdict="not_required")
