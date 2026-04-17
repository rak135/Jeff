"""Selection-local comparison request and prompt-bundle surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.core.schemas import ProposalId, Scope, coerce_proposal_id

from ..proposal import ProposalResultOption
from ..types import require_text
from .contracts import SelectionRequest
from .prompt_files import load_prompt_file, render_prompt

_EMPTY_SENTINEL = "NONE"


@dataclass(frozen=True, slots=True)
class SelectionComparisonRequest:
    """Bounded Selection comparison input centered on SelectionRequest."""

    request_id: str
    selection_request: SelectionRequest

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_text(self.request_id, field_name="request_id"))
        if not isinstance(self.selection_request, SelectionRequest):
            raise TypeError("selection_request must be a SelectionRequest")

    @classmethod
    def from_selection_request(cls, selection_request: SelectionRequest) -> SelectionComparisonRequest:
        return cls(
            request_id=selection_request.request_id,
            selection_request=selection_request,
        )

    @property
    def considered_proposal_ids(self) -> tuple[ProposalId, ...]:
        return self.selection_request.considered_proposal_ids

    @property
    def scope(self) -> Scope:
        return self.selection_request.proposal_result.scope


@dataclass(frozen=True, slots=True)
class SelectionComparisonPromptBundle:
    """Rendered Selection comparison prompt ready for later runtime use."""

    request_id: str
    scope: Scope
    considered_proposal_ids: tuple[ProposalId, ...]
    system_prompt: str
    prompt_text: str
    prompt_file: str = "COMPARISON.md"

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_text(self.request_id, field_name="request_id"))
        object.__setattr__(self, "system_prompt", require_text(self.system_prompt, field_name="system_prompt"))
        object.__setattr__(self, "prompt_text", require_text(self.prompt_text, field_name="prompt_text"))
        object.__setattr__(self, "prompt_file", require_text(self.prompt_file, field_name="prompt_file"))
        object.__setattr__(
            self,
            "considered_proposal_ids",
            tuple(coerce_proposal_id(str(proposal_id)) for proposal_id in self.considered_proposal_ids),
        )


def build_selection_comparison_prompt_bundle(
    request: SelectionComparisonRequest,
) -> SelectionComparisonPromptBundle:
    """Build a rendered Selection comparison prompt bundle from a Selection request."""

    system_prompt, template = load_prompt_file("COMPARISON.md")
    selection_request = request.selection_request
    proposal_result = selection_request.proposal_result
    prompt_text = render_prompt(
        template,
        REQUEST_ID=request.request_id,
        SCOPE=_format_scope(proposal_result.scope),
        CONSIDERED_PROPOSAL_IDS=_format_considered_proposal_ids(selection_request.considered_proposal_ids),
        SCARCITY_REASON=_format_optional_text(proposal_result.scarcity_reason),
        PROPOSAL_OPTIONS=_format_proposal_options(proposal_result.options),
    )
    return SelectionComparisonPromptBundle(
        request_id=request.request_id,
        scope=proposal_result.scope,
        considered_proposal_ids=selection_request.considered_proposal_ids,
        system_prompt=system_prompt,
        prompt_text=prompt_text,
    )


def _format_scope(scope: Scope) -> str:
    return (
        f"project_id={scope.project_id}; "
        f"work_unit_id={scope.work_unit_id or _EMPTY_SENTINEL}; "
        f"run_id={scope.run_id or _EMPTY_SENTINEL}"
    )


def _format_considered_proposal_ids(considered_proposal_ids: tuple[ProposalId, ...]) -> str:
    if not considered_proposal_ids:
        return _EMPTY_SENTINEL
    return ",".join(str(proposal_id) for proposal_id in considered_proposal_ids)


def _format_proposal_options(options: tuple[ProposalResultOption, ...]) -> str:
    if not options:
        return _EMPTY_SENTINEL

    rendered_blocks = [_format_option_block(option) for option in options]
    return "\n\n".join(rendered_blocks)


def _format_option_block(option: ProposalResultOption) -> str:
    lines = [
        f"OPTION_{option.option_index}:",
        f"option_index={option.option_index}",
        f"proposal_id={option.proposal_id}",
        f"proposal_type={option.proposal_type}",
        f"title={_single_line(option.title)}",
        f"why_now={_single_line(option.why_now)}",
        f"summary={_single_line(option.summary)}",
        f"constraints={_format_text_items(option.constraints)}",
        f"feasibility={_format_optional_text(option.feasibility)}",
        f"reversibility={_format_optional_text(option.reversibility)}",
        f"support_refs={_format_support_refs(option.support_refs)}",
        f"assumptions={_format_text_items(option.assumptions)}",
        f"main_risks={_format_text_items(option.main_risks)}",
        f"blockers={_format_text_items(option.blockers)}",
        f"planning_needed={'yes' if option.planning_needed else 'no'}",
    ]
    return "\n".join(lines)


def _format_text_items(items: tuple[str, ...]) -> str:
    if not items:
        return _EMPTY_SENTINEL
    return "; ".join(_single_line(item) for item in items)


def _format_support_refs(support_refs: tuple[str, ...]) -> str:
    if not support_refs:
        return _EMPTY_SENTINEL
    return ",".join(_single_line(ref) for ref in support_refs)


def _format_optional_text(value: str | None) -> str:
    if value is None:
        return _EMPTY_SENTINEL
    return _single_line(value)


def _single_line(value: str) -> str:
    collapsed = " ".join(part.strip() for part in value.splitlines() if part.strip())
    return collapsed or _EMPTY_SENTINEL
