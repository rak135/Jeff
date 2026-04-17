"""Selection-local contracts with bounded choice and explicit non-selection outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from jeff.core.schemas import ProposalId, SelectionId, coerce_proposal_id, coerce_selection_id

from ..proposal import ProposalResult
from ..types import require_text

SelectionDisposition = Literal["selected", "reject_all", "defer", "escalate"]
_NonSelectionOutcome = Literal["reject_all", "defer", "escalate"]


@dataclass(frozen=True, slots=True)
class SelectionRequest:
    """Single Selection input centered on the current ProposalResult contract."""

    request_id: str
    proposal_result: ProposalResult

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_text(self.request_id, field_name="request_id"))

    @property
    def considered_proposal_ids(self) -> tuple[ProposalId, ...]:
        return tuple(option.proposal_id for option in self.proposal_result.options)


@dataclass(frozen=True, slots=True)
class SelectionResult:
    """Bounded Selection output: one selected option max, or one honest non-selection outcome."""

    selection_id: SelectionId
    considered_proposal_ids: tuple[ProposalId, ...]
    selected_proposal_id: ProposalId | None = None
    non_selection_outcome: _NonSelectionOutcome | None = None
    rationale: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "selection_id",
            coerce_selection_id(str(self.selection_id)),
        )

        normalized_considered_ids = tuple(
            coerce_proposal_id(str(proposal_id)) for proposal_id in self.considered_proposal_ids
        )
        object.__setattr__(self, "considered_proposal_ids", normalized_considered_ids)

        if self.selected_proposal_id is not None:
            object.__setattr__(
                self,
                "selected_proposal_id",
                coerce_proposal_id(str(self.selected_proposal_id)),
            )

        object.__setattr__(self, "rationale", require_text(self.rationale, field_name="rationale"))

        seen_ids: set[str] = set()
        for proposal_id in self.considered_proposal_ids:
            proposal_id_text = str(proposal_id)
            if proposal_id_text in seen_ids:
                raise ValueError("considered proposal ids must be unique")
            seen_ids.add(proposal_id_text)

        chose_one = self.selected_proposal_id is not None
        chose_none = self.non_selection_outcome is not None
        if chose_one == chose_none:
            raise ValueError("selection must choose exactly one proposal or one explicit non-selection outcome")
        if chose_one and self.selected_proposal_id not in self.considered_proposal_ids:
            raise ValueError("selected proposal must come from the considered proposal set")

    @property
    def disposition(self) -> SelectionDisposition:
        if self.selected_proposal_id is not None:
            return "selected"
        return cast(SelectionDisposition, self.non_selection_outcome)
