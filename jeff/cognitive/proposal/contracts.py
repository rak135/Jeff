"""Bounded proposal contracts with one primary Proposal result surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jeff.core.schemas import ProposalId, Scope, coerce_proposal_id

from ..types import normalize_text_list, normalized_identity, require_text

ProposalType = Literal[
    "direct_action",
    "investigate",
    "clarify",
    "defer",
    "escalate",
    "planning_insertion",
]


@dataclass(frozen=True, slots=True)
class ProposalResultOption:
    """Primary rich Proposal option contract for v1 runtime success/handoff use."""

    option_index: int
    proposal_id: ProposalId
    proposal_type: ProposalType
    title: str
    why_now: str
    summary: str
    constraints: tuple[str, ...] = ()
    feasibility: str | None = None
    reversibility: str | None = None
    support_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    main_risks: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    planning_needed: bool = False

    def __post_init__(self) -> None:
        if self.option_index <= 0:
            raise ValueError("option_index must be greater than zero")
        object.__setattr__(
            self,
            "proposal_id",
            coerce_proposal_id(str(self.proposal_id)),
        )
        object.__setattr__(self, "title", require_text(self.title, field_name="title"))
        object.__setattr__(self, "why_now", require_text(self.why_now, field_name="why_now"))
        object.__setattr__(
            self,
            "summary",
            require_text(self.summary, field_name="summary"),
        )
        object.__setattr__(
            self,
            "constraints",
            normalize_text_list(self.constraints, field_name="constraints"),
        )
        object.__setattr__(
            self,
            "support_refs",
            normalize_text_list(self.support_refs, field_name="support_refs"),
        )
        object.__setattr__(
            self,
            "assumptions",
            normalize_text_list(self.assumptions, field_name="assumptions"),
        )
        object.__setattr__(
            self,
            "main_risks",
            normalize_text_list(self.main_risks, field_name="main_risks"),
        )
        object.__setattr__(
            self,
            "blockers",
            normalize_text_list(self.blockers, field_name="blockers"),
        )
        if self.feasibility is not None:
            object.__setattr__(self, "feasibility", require_text(self.feasibility, field_name="feasibility"))
        if self.reversibility is not None:
            object.__setattr__(
                self,
                "reversibility",
                require_text(self.reversibility, field_name="reversibility"),
            )


@dataclass(frozen=True, slots=True)
class ProposalResult:
    """Primary current Proposal-local success and downstream handoff contract."""

    request_id: str
    scope: Scope
    options: tuple[ProposalResultOption, ...]
    scarcity_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_text(self.request_id, field_name="request_id"))
        
        if len(self.options) > 3:
            raise ValueError("proposal generation may return at most 3 serious options")
        if len(self.options) < 2:
            if self.scarcity_reason is None or not self.scarcity_reason.strip():
                raise ValueError("scarcity_reason is required when fewer than 2 serious options exist")
            object.__setattr__(
                self,
                "scarcity_reason",
                require_text(self.scarcity_reason, field_name="scarcity_reason"),
            )
        elif self.scarcity_reason is not None:
            object.__setattr__(
                self,
                "scarcity_reason",
                require_text(self.scarcity_reason, field_name="scarcity_reason"),
            )

        seen_ids: set[str] = set()
        seen_signatures: set[tuple[str, str]] = set()
        for option in self.options:
            option_id = str(option.proposal_id)
            if option_id in seen_ids:
                raise ValueError("proposal ids must be unique inside proposal result")
            seen_ids.add(option_id)

            signature = (option.proposal_type, normalized_identity(option.summary))
            if signature in seen_signatures:
                raise ValueError("proposal generation must not pad near-duplicate serious options")
            seen_signatures.add(signature)

    @property
    def proposal_count(self) -> int:
        return len(self.options)
