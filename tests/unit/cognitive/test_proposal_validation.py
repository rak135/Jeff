import pytest

from jeff.cognitive.proposal import (
    ParsedProposalGenerationResult,
    ParsedProposalOption,
    ProposalGenerationPromptBundle,
    ProposalGenerationRawResult,
    ProposalGenerationValidationError,
    ProposalResult,
    parse_proposal_generation_result,
    validate_proposal_generation_result,
)
from jeff.core.schemas import Scope
from jeff.infrastructure import ModelUsage

_ONE_OPTION_BLOCK = (
    "OPTION_1_TYPE: investigate\n"
    "OPTION_1_TITLE: Confirm the blocker directly\n"
    "OPTION_1_SUMMARY: Run one bounded investigation against the blocker.\n"
    "OPTION_1_WHY_NOW: The blocker still prevents a stronger proposal set.\n"
    "OPTION_1_ASSUMPTIONS: The blocker can be inspected quickly\n"
    "OPTION_1_RISKS: Investigation may confirm no viable path\n"
    "OPTION_1_CONSTRAINTS: Stay inside the current work unit\n"
    "OPTION_1_BLOCKERS: Direct change remains blocked\n"
    "OPTION_1_PLANNING_NEEDED: no\n"
    "OPTION_1_FEASIBILITY: Feasible with current evidence\n"
    "OPTION_1_REVERSIBILITY: Fully reversible\n"
    "OPTION_1_SUPPORT_REFS: ctx-1,research-2\n"
)


def test_validate_zero_option_result_with_explicit_scarcity_reason() -> None:
    validated = validate_proposal_generation_result(
        _parsed_result(
            "PROPOSAL_COUNT: 0\n"
            "SCARCITY_REASON: No honest option survives the current contradiction.\n",
        )
    )

    assert isinstance(validated, ProposalResult)
    assert len(validated.options) == 0
    assert validated.scarcity_reason == "No honest option survives the current contradiction."


def test_validate_one_option_result_with_explicit_scarcity_reason() -> None:
    validated = validate_proposal_generation_result(
        _parsed_result(
            "PROPOSAL_COUNT: 1\n"
            "SCARCITY_REASON: Only one serious path is currently grounded.\n"
            "OPTION_1_TYPE: investigate\n"
            "OPTION_1_TITLE: Confirm the blocker directly\n"
            "OPTION_1_SUMMARY: Run one bounded investigation against the blocker.\n"
            "OPTION_1_WHY_NOW: The blocker still prevents a stronger proposal set.\n"
            "OPTION_1_ASSUMPTIONS: The blocker can be inspected quickly\n"
            "OPTION_1_RISKS: Investigation may confirm no viable path\n"
            "OPTION_1_CONSTRAINTS: Stay inside the current work unit\n"
            "OPTION_1_BLOCKERS: Direct change remains blocked\n"
            "OPTION_1_PLANNING_NEEDED: no\n"
            "OPTION_1_FEASIBILITY: Feasible with current evidence\n"
            "OPTION_1_REVERSIBILITY: Fully reversible\n"
            "OPTION_1_SUPPORT_REFS: ctx-1,research-2\n",
        )
    )

    assert validated.scarcity_reason == "Only one serious path is currently grounded."
    assert validated.options[0].proposal_type == "investigate"


def test_validate_two_option_result() -> None:
    validated = validate_proposal_generation_result(
        _parsed_result(
            "PROPOSAL_COUNT: 2\n"
            "SCARCITY_REASON: No additional scarcity explanation identified from the provided support.\n"
            "OPTION_1_TYPE: direct_action\n"
            "OPTION_1_TITLE: Apply the bounded patch\n"
            "OPTION_1_SUMMARY: Apply the smallest safe patch now.\n"
            "OPTION_1_WHY_NOW: Current support already bounds the change.\n"
            "OPTION_1_ASSUMPTIONS: The failing edge is already reproduced\n"
            "OPTION_1_RISKS: Small regression risk remains\n"
            "OPTION_1_CONSTRAINTS: Stay inside the current project scope\n"
            "OPTION_1_BLOCKERS: No explicit blockers identified from the provided support.\n"
            "OPTION_1_PLANNING_NEEDED: no\n"
            "OPTION_1_FEASIBILITY: Feasible with current evidence\n"
            "OPTION_1_REVERSIBILITY: Straightforward rollback\n"
            "OPTION_1_SUPPORT_REFS: ctx-1,research-1\n"
            "OPTION_2_TYPE: investigate\n"
            "OPTION_2_TITLE: Gather one more signal\n"
            "OPTION_2_SUMMARY: Check the unresolved edge case first.\n"
            "OPTION_2_WHY_NOW: Remaining uncertainty still matters.\n"
            "OPTION_2_ASSUMPTIONS: The signal can be collected quickly\n"
            "OPTION_2_RISKS: Progress slows while evidence is gathered\n"
            "OPTION_2_CONSTRAINTS: Keep the investigation inside current scope\n"
            "OPTION_2_BLOCKERS: No explicit blockers identified from the provided support.\n"
            "OPTION_2_PLANNING_NEEDED: no\n"
            "OPTION_2_FEASIBILITY: Feasible with current tools\n"
            "OPTION_2_REVERSIBILITY: Investigation only\n"
            "OPTION_2_SUPPORT_REFS: ctx-1,research-3\n",
        )
    )

    assert len(validated.options) == 2
    assert validated.scarcity_reason is None


def test_validate_three_option_result() -> None:
    validated = validate_proposal_generation_result(
        _parsed_result(
            "PROPOSAL_COUNT: 3\n"
            "SCARCITY_REASON: No additional scarcity explanation identified from the provided support.\n"
            "OPTION_1_TYPE: direct_action\n"
            "OPTION_1_TITLE: Apply the bounded patch\n"
            "OPTION_1_SUMMARY: Apply the smallest safe patch now.\n"
            "OPTION_1_WHY_NOW: Current support already bounds the change.\n"
            "OPTION_1_ASSUMPTIONS: The failing edge is already reproduced\n"
            "OPTION_1_RISKS: Small regression risk remains\n"
            "OPTION_1_CONSTRAINTS: Stay inside the current project scope\n"
            "OPTION_1_BLOCKERS: No explicit blockers identified from the provided support.\n"
            "OPTION_1_PLANNING_NEEDED: no\n"
            "OPTION_1_FEASIBILITY: Feasible with current evidence\n"
            "OPTION_1_REVERSIBILITY: Straightforward rollback\n"
            "OPTION_1_SUPPORT_REFS: ctx-1,research-1\n"
            "OPTION_2_TYPE: planning_insertion\n"
            "OPTION_2_TITLE: Structure the multi-step path\n"
            "OPTION_2_SUMMARY: Insert a bounded plan before riskier work.\n"
            "OPTION_2_WHY_NOW: The remaining work has multiple dependent steps.\n"
            "OPTION_2_ASSUMPTIONS: Coordination cost is justified by the risk profile\n"
            "OPTION_2_RISKS: Planning overhead may slow immediate progress\n"
            "OPTION_2_CONSTRAINTS: Keep the plan limited to the current task frame\n"
            "OPTION_2_BLOCKERS: No explicit blockers identified from the provided support.\n"
            "OPTION_2_PLANNING_NEEDED: yes\n"
            "OPTION_2_FEASIBILITY: Feasible with current support\n"
            "OPTION_2_REVERSIBILITY: High before later downstream stages\n"
            "OPTION_2_SUPPORT_REFS: ctx-1,research-4\n"
            "OPTION_3_TYPE: escalate\n"
            "OPTION_3_TITLE: Escalate the judgment boundary\n"
            "OPTION_3_SUMMARY: Escalate the unresolved risk tradeoff to the operator.\n"
            "OPTION_3_WHY_NOW: The remaining uncertainty crosses a judgment boundary.\n"
            "OPTION_3_ASSUMPTIONS: Operator review is available soon\n"
            "OPTION_3_RISKS: Slower decision velocity while waiting\n"
            "OPTION_3_CONSTRAINTS: Requires operator attention\n"
            "OPTION_3_BLOCKERS: Autonomous judgment remains bounded\n"
            "OPTION_3_PLANNING_NEEDED: no\n"
            "OPTION_3_FEASIBILITY: Feasible if operator input is available\n"
            "OPTION_3_REVERSIBILITY: Fully reversible\n"
            "OPTION_3_SUPPORT_REFS: ctx-1\n",
        )
    )

    assert len(validated.options) == 3
    assert validated.options[1].planning_needed is True


def test_more_than_three_options_are_rejected() -> None:
    with pytest.raises(ProposalGenerationValidationError, match="0..3") as exc_info:
        validate_proposal_generation_result(
            _unsafe_parsed_result(
                proposal_count=4,
                scarcity_reason=None,
                options=(
                    _option(1, title="Option 1", summary="Summary 1", why_now="Why 1"),
                    _option(2, title="Option 2", summary="Summary 2", why_now="Why 2"),
                    _option(3, title="Option 3", summary="Summary 3", why_now="Why 3"),
                    _option(4, title="Option 4", summary="Summary 4", why_now="Why 4"),
                ),
            )
        )

    assert _issue_codes(exc_info.value) == ("proposal_count_out_of_range",)


@pytest.mark.parametrize("proposal_count, option_block", [("0", ""), ("1", _ONE_OPTION_BLOCK)])
def test_missing_scarcity_reason_for_zero_or_one_option_is_rejected(
    proposal_count: str,
    option_block: str,
) -> None:
    with pytest.raises(ProposalGenerationValidationError, match="scarcity_reason") as exc_info:
        validate_proposal_generation_result(
            _unsafe_parsed_result(
                proposal_count=int(proposal_count),
                scarcity_reason=None,
                options=(() if proposal_count == "0" else (_option(1, title="Option 1", summary="Summary 1", why_now="Why 1"),)),
            )
        )

    assert _issue_codes(exc_info.value) == ("missing_scarcity_reason",)


def test_canonical_absence_markers_are_accepted_without_self_contradiction() -> None:
    validated = validate_proposal_generation_result(
        _parsed_result(
            "PROPOSAL_COUNT: 1\n"
            "SCARCITY_REASON: Only one path remains.\n"
            "OPTION_1_TYPE: clarify\n"
            "OPTION_1_TITLE: Clarify the scope edge\n"
            "OPTION_1_SUMMARY: Ask one bounded clarifying question.\n"
            "OPTION_1_WHY_NOW: Scope ambiguity still blocks stronger framing.\n"
            "OPTION_1_ASSUMPTIONS: No explicit assumptions identified from the provided support.\n"
            "OPTION_1_RISKS: No explicit risks identified from the provided support.\n"
            "OPTION_1_CONSTRAINTS: No explicit constraints identified from the provided support.\n"
            "OPTION_1_BLOCKERS: No explicit blockers identified from the provided support.\n"
            "OPTION_1_PLANNING_NEEDED: no\n"
            "OPTION_1_FEASIBILITY: No explicit feasibility statement identified from the provided support.\n"
            "OPTION_1_REVERSIBILITY: No explicit reversibility statement identified from the provided support.\n"
            "OPTION_1_SUPPORT_REFS: none\n",
        )
    )

    assert validated.options[0].assumptions == ()
    assert validated.options[0].main_risks == ()
    assert validated.options[0].constraints == ()
    assert validated.options[0].blockers == ()
    assert validated.options[0].feasibility is None
    assert validated.options[0].reversibility is None


def test_duplicate_padding_style_options_are_rejected() -> None:
    with pytest.raises(ProposalGenerationValidationError, match="not materially distinct") as exc_info:
        validate_proposal_generation_result(
            _parsed_result(
                "PROPOSAL_COUNT: 2\n"
                "SCARCITY_REASON: No additional scarcity explanation identified from the provided support.\n"
                "OPTION_1_TYPE: direct_action\n"
                "OPTION_1_TITLE: Apply the safe patch\n"
                "OPTION_1_SUMMARY: Apply the safe patch now.\n"
                "OPTION_1_WHY_NOW: Current support already bounds the change.\n"
                "OPTION_1_ASSUMPTIONS: The failing edge is already reproduced\n"
                "OPTION_1_RISKS: Small regression risk remains\n"
                "OPTION_1_CONSTRAINTS: Stay inside current project scope\n"
                "OPTION_1_BLOCKERS: No explicit blockers identified from the provided support.\n"
                "OPTION_1_PLANNING_NEEDED: no\n"
                "OPTION_1_FEASIBILITY: Feasible with current evidence\n"
                "OPTION_1_REVERSIBILITY: Straightforward rollback\n"
                "OPTION_1_SUPPORT_REFS: ctx-1\n"
                "OPTION_2_TYPE: investigate\n"
                "OPTION_2_TITLE: Apply the safe patch\n"
                "OPTION_2_SUMMARY: Apply the safe patch now.\n"
                "OPTION_2_WHY_NOW: Current support already bounds the change.\n"
                "OPTION_2_ASSUMPTIONS: The failing edge is already reproduced\n"
                "OPTION_2_RISKS: Small regression risk remains\n"
                "OPTION_2_CONSTRAINTS: Stay inside current project scope\n"
                "OPTION_2_BLOCKERS: No explicit blockers identified from the provided support.\n"
                "OPTION_2_PLANNING_NEEDED: no\n"
                "OPTION_2_FEASIBILITY: Feasible with current evidence\n"
                "OPTION_2_REVERSIBILITY: Straightforward rollback\n"
                "OPTION_2_SUPPORT_REFS: ctx-1\n",
            )
        )

    assert _issue_codes(exc_info.value) == ("duplicate_option",)


def test_authority_leakage_is_rejected() -> None:
    with pytest.raises(ProposalGenerationValidationError, match="authority language") as exc_info:
        validate_proposal_generation_result(
            _parsed_result(
                "PROPOSAL_COUNT: 1\n"
                "SCARCITY_REASON: Only one serious path remains.\n"
                "OPTION_1_TYPE: direct_action\n"
                "OPTION_1_TITLE: Apply the bounded patch\n"
                "OPTION_1_SUMMARY: Apply the change now because approval is implied.\n"
                "OPTION_1_WHY_NOW: Current support already bounds the change.\n"
                "OPTION_1_ASSUMPTIONS: The failing edge is already reproduced\n"
                "OPTION_1_RISKS: Small regression risk remains\n"
                "OPTION_1_CONSTRAINTS: Stay inside current project scope\n"
                "OPTION_1_BLOCKERS: No explicit blockers identified from the provided support.\n"
                "OPTION_1_PLANNING_NEEDED: no\n"
                "OPTION_1_FEASIBILITY: Ready to start now\n"
                "OPTION_1_REVERSIBILITY: Straightforward rollback\n"
                "OPTION_1_SUPPORT_REFS: ctx-1\n",
            )
        )

    assert _issue_codes(exc_info.value) == ("authority_leakage", "authority_leakage")


def test_planning_needed_does_not_imply_plan_authority() -> None:
    validated = validate_proposal_generation_result(
        _parsed_result(
            "PROPOSAL_COUNT: 1\n"
            "SCARCITY_REASON: Only one serious path is currently grounded.\n"
            "OPTION_1_TYPE: planning_insertion\n"
            "OPTION_1_TITLE: Structure the multi-step path\n"
            "OPTION_1_SUMMARY: Insert a bounded plan before riskier work.\n"
            "OPTION_1_WHY_NOW: The remaining work has multiple dependent steps.\n"
            "OPTION_1_ASSUMPTIONS: Coordination cost is justified by the risk profile\n"
            "OPTION_1_RISKS: Planning overhead may slow immediate progress\n"
            "OPTION_1_CONSTRAINTS: Keep the plan limited to the current task frame\n"
            "OPTION_1_BLOCKERS: No explicit blockers identified from the provided support.\n"
            "OPTION_1_PLANNING_NEEDED: yes\n"
            "OPTION_1_FEASIBILITY: Feasible with current support\n"
            "OPTION_1_REVERSIBILITY: High before later downstream stages\n"
            "OPTION_1_SUPPORT_REFS: ctx-1,research-1\n",
        )
    )

    assert validated.options[0].planning_needed is True
    assert validated.options[0].proposal_type == "planning_insertion"


def test_feasibility_wording_does_not_become_readiness() -> None:
    validated = validate_proposal_generation_result(
        _parsed_result(
            "PROPOSAL_COUNT: 1\n"
            "SCARCITY_REASON: Only one serious path is currently grounded.\n"
            "OPTION_1_TYPE: direct_action\n"
            "OPTION_1_TITLE: Apply the bounded patch\n"
            "OPTION_1_SUMMARY: Apply the smallest safe patch now.\n"
            "OPTION_1_WHY_NOW: Current support already bounds the change.\n"
            "OPTION_1_ASSUMPTIONS: The failing edge is already reproduced\n"
            "OPTION_1_RISKS: Small regression risk remains\n"
            "OPTION_1_CONSTRAINTS: Stay inside the current project scope\n"
            "OPTION_1_BLOCKERS: No explicit blockers identified from the provided support.\n"
            "OPTION_1_PLANNING_NEEDED: no\n"
            "OPTION_1_FEASIBILITY: Feasible with current evidence and tooling\n"
            "OPTION_1_REVERSIBILITY: Straightforward rollback\n"
            "OPTION_1_SUPPORT_REFS: ctx-1\n",
        )
    )

    assert validated.options[0].feasibility == "Feasible with current evidence and tooling"
    assert validated.options[0].summary == "Apply the smallest safe patch now."


def _parsed_result(raw_text: str) -> ParsedProposalGenerationResult:
    return parse_proposal_generation_result(_raw_result(raw_text))


def _raw_result(raw_text: str) -> ProposalGenerationRawResult:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    bundle = ProposalGenerationPromptBundle(
        request_id="proposal-generation:project-1:wu-1:run-1:test",
        scope=scope,
        objective="Frame bounded proposal options",
        system_instructions="Proposal generates possibilities, not authority.",
        prompt="TASK: bounded proposal generation",
    )
    return ProposalGenerationRawResult(
        prompt_bundle=bundle,
        request_id=bundle.request_id,
        scope=scope,
        raw_output_text=raw_text,
        adapter_id="adapter-1",
        provider_name="fake",
        model_name="fake-model",
        usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
    )


def _issue_codes(error: ProposalGenerationValidationError) -> tuple[str, ...]:
    return tuple(issue.code for issue in error.issues)


def _option(
    option_index: int,
    *,
    title: str,
    summary: str,
    why_now: str,
) -> ParsedProposalOption:
    return ParsedProposalOption(
        option_index=option_index,
        proposal_type="investigate",
        title=title,
        summary=summary,
        why_now=why_now,
        assumptions=("A bounded assumption",),
        risks=("A bounded risk",),
        constraints=("A bounded constraint",),
        blockers=(),
        planning_needed=False,
        feasibility="Feasible with current evidence",
        reversibility="Fully reversible",
        support_refs=("ctx-1",),
    )


def _unsafe_parsed_result(
    *,
    proposal_count: int,
    scarcity_reason: str | None,
    options: tuple[ParsedProposalOption, ...],
) -> ParsedProposalGenerationResult:
    parsed_result = object.__new__(ParsedProposalGenerationResult)
    object.__setattr__(parsed_result, "raw_result", _raw_result("PROPOSAL_COUNT: 0\nSCARCITY_REASON: placeholder\n"))
    object.__setattr__(parsed_result, "proposal_count", proposal_count)
    object.__setattr__(parsed_result, "scarcity_reason", scarcity_reason)
    object.__setattr__(parsed_result, "options", options)
    return parsed_result
