import pytest

from jeff.cognitive.proposal import (
    ParsedProposalGenerationResult,
    ProposalGenerationParseError,
    ProposalGenerationPromptBundle,
    ProposalGenerationRawResult,
    parse_proposal_generation_result,
)
from jeff.core.schemas import Scope
from jeff.infrastructure import ModelUsage


def test_parse_zero_option_output() -> None:
    result = parse_proposal_generation_result(
        _raw_result(
            "PROPOSAL_COUNT: 0\n"
            "SCARCITY_REASON: No honest option is currently supported.\n",
        )
    )

    assert isinstance(result, ParsedProposalGenerationResult)
    assert result.proposal_count == 0
    assert result.scarcity_reason == "No honest option is currently supported."
    assert result.options == ()


def test_parse_one_option_output() -> None:
    result = parse_proposal_generation_result(
        _raw_result(
            "PROPOSAL_COUNT: 1\n"
            "SCARCITY_REASON: Only one serious path remains.\n"
            "OPTION_1_TYPE: investigate\n"
            "OPTION_1_TITLE: Confirm the blocker\n"
            "OPTION_1_SUMMARY: Run a bounded investigation.\n"
            "OPTION_1_WHY_NOW: Current contradiction blocks stronger action.\n"
            "OPTION_1_ASSUMPTIONS: Evidence is available; blocker is inspectable\n"
            "OPTION_1_RISKS: Investigation may confirm no viable path\n"
            "OPTION_1_CONSTRAINTS: Stay inside project scope\n"
            "OPTION_1_BLOCKERS: Direct action remains blocked\n"
            "OPTION_1_PLANNING_NEEDED: no\n"
            "OPTION_1_FEASIBILITY: Feasible with current evidence\n"
            "OPTION_1_REVERSIBILITY: Fully reversible\n"
            "OPTION_1_SUPPORT_REFS: ctx-1,research-2\n",
        )
    )

    assert result.proposal_count == 1
    option = result.options[0]
    assert option.proposal_type == "investigate"
    assert option.assumptions == ("Evidence is available", "blocker is inspectable")
    assert option.support_refs == ("ctx-1", "research-2")
    assert option.planning_needed is False


def test_parse_two_option_output() -> None:
    result = parse_proposal_generation_result(
        _raw_result(
            "PROPOSAL_COUNT: 2\n"
            "SCARCITY_REASON: NONE\n"
            "OPTION_1_TYPE: direct_action\n"
            "OPTION_1_TITLE: Apply the bounded patch\n"
            "OPTION_1_SUMMARY: Make the small safe change now.\n"
            "OPTION_1_WHY_NOW: The path is already supported.\n"
            "OPTION_1_ASSUMPTIONS: NONE\n"
            "OPTION_1_RISKS: Small rollback cost\n"
            "OPTION_1_CONSTRAINTS: Current scope only\n"
            "OPTION_1_BLOCKERS: NONE\n"
            "OPTION_1_PLANNING_NEEDED: no\n"
            "OPTION_1_FEASIBILITY: High under current support\n"
            "OPTION_1_REVERSIBILITY: Straightforward rollback\n"
            "OPTION_1_SUPPORT_REFS: ctx-1\n"
            "OPTION_2_TYPE: investigate\n"
            "OPTION_2_TITLE: Gather one more signal\n"
            "OPTION_2_SUMMARY: Check the unresolved edge case first.\n"
            "OPTION_2_WHY_NOW: Remaining uncertainty still matters.\n"
            "OPTION_2_ASSUMPTIONS: The signal can be gathered quickly\n"
            "OPTION_2_RISKS: Slower progress\n"
            "OPTION_2_CONSTRAINTS: Must stay inside current work unit\n"
            "OPTION_2_BLOCKERS: NONE\n"
            "OPTION_2_PLANNING_NEEDED: no\n"
            "OPTION_2_FEASIBILITY: Feasible with current tools\n"
            "OPTION_2_REVERSIBILITY: Investigation only\n"
            "OPTION_2_SUPPORT_REFS: ctx-1,research-1\n",
        )
    )

    assert result.proposal_count == 2
    assert result.scarcity_reason is None
    assert tuple(option.option_index for option in result.options) == (1, 2)


def test_parse_three_option_output() -> None:
    result = parse_proposal_generation_result(
        _raw_result(
            "PROPOSAL_COUNT: 3\n"
            "SCARCITY_REASON: NONE\n"
            "OPTION_1_TYPE: direct_action\n"
            "OPTION_1_TITLE: Apply the patch\n"
            "OPTION_1_SUMMARY: Do the small change now.\n"
            "OPTION_1_WHY_NOW: Current support is sufficient.\n"
            "OPTION_1_ASSUMPTIONS: NONE\n"
            "OPTION_1_RISKS: Small regression risk\n"
            "OPTION_1_CONSTRAINTS: Current project only\n"
            "OPTION_1_BLOCKERS: NONE\n"
            "OPTION_1_PLANNING_NEEDED: no\n"
            "OPTION_1_FEASIBILITY: High\n"
            "OPTION_1_REVERSIBILITY: Good\n"
            "OPTION_1_SUPPORT_REFS: ctx-1\n"
            "OPTION_2_TYPE: planning_insertion\n"
            "OPTION_2_TITLE: Plan the multi-step path\n"
            "OPTION_2_SUMMARY: Structure the riskier work first.\n"
            "OPTION_2_WHY_NOW: The work may require coordination.\n"
            "OPTION_2_ASSUMPTIONS: Multi-step work is actually needed\n"
            "OPTION_2_RISKS: Planning overhead\n"
            "OPTION_2_CONSTRAINTS: Review checkpoints required\n"
            "OPTION_2_BLOCKERS: NONE\n"
            "OPTION_2_PLANNING_NEEDED: yes\n"
            "OPTION_2_FEASIBILITY: Moderate\n"
            "OPTION_2_REVERSIBILITY: High before execution\n"
            "OPTION_2_SUPPORT_REFS: ctx-1,research-1\n"
            "OPTION_3_TYPE: escalate\n"
            "OPTION_3_TITLE: Escalate the judgment boundary\n"
            "OPTION_3_SUMMARY: Bring the risk tradeoff to the operator.\n"
            "OPTION_3_WHY_NOW: Autonomous choice would cross a judgment boundary.\n"
            "OPTION_3_ASSUMPTIONS: NONE\n"
            "OPTION_3_RISKS: Slower decision velocity\n"
            "OPTION_3_CONSTRAINTS: Requires operator attention\n"
            "OPTION_3_BLOCKERS: Judgment boundary remains unresolved\n"
            "OPTION_3_PLANNING_NEEDED: no\n"
            "OPTION_3_FEASIBILITY: Feasible if operator input is available\n"
            "OPTION_3_REVERSIBILITY: Fully reversible\n"
            "OPTION_3_SUPPORT_REFS: ctx-1\n",
        )
    )

    assert result.proposal_count == 3
    assert result.options[1].planning_needed is True
    assert result.options[2].proposal_type == "escalate"


def test_missing_required_markers_fail_explicitly() -> None:
    with pytest.raises(ProposalGenerationParseError, match="missing PROPOSAL_COUNT"):
        parse_proposal_generation_result(_raw_result("SCARCITY_REASON: Missing count\n"))

    with pytest.raises(ProposalGenerationParseError, match="missing SCARCITY_REASON"):
        parse_proposal_generation_result(_raw_result("PROPOSAL_COUNT: 0\n"))

    with pytest.raises(ProposalGenerationParseError, match="missing required fields"):
        parse_proposal_generation_result(
            _raw_result(
                "PROPOSAL_COUNT: 1\n"
                "SCARCITY_REASON: Only one path\n"
                "OPTION_1_TYPE: investigate\n",
            )
        )


def test_option_field_extraction_is_deterministic() -> None:
    parsed = parse_proposal_generation_result(
        _raw_result(
            "PROPOSAL_COUNT: 1\n"
            "SCARCITY_REASON: Only one path remains.\n"
            "OPTION_1_TYPE: clarify\n"
            "OPTION_1_TITLE: Clarify the missing scope edge\n"
            "OPTION_1_SUMMARY: Ask one bounded clarifying question.\n"
            "OPTION_1_WHY_NOW: Scope ambiguity still blocks stronger framing.\n"
            "OPTION_1_ASSUMPTIONS: The operator can answer quickly\n"
            "OPTION_1_RISKS: Delay if no answer arrives\n"
            "OPTION_1_CONSTRAINTS: Must stay bounded to current ask\n"
            "OPTION_1_BLOCKERS: Scope remains ambiguous\n"
            "OPTION_1_PLANNING_NEEDED: no\n"
            "OPTION_1_FEASIBILITY: NONE\n"
            "OPTION_1_REVERSIBILITY: Fully reversible\n"
            "OPTION_1_SUPPORT_REFS: ctx-1,research-4\n",
        )
    )

    option = parsed.options[0]
    assert option.title == "Clarify the missing scope edge"
    assert option.feasibility is None
    assert option.reversibility == "Fully reversible"
    assert option.support_refs == ("ctx-1", "research-4")


def test_parser_consumes_slice_d_raw_result_surface_without_runtime() -> None:
    raw_result = _raw_result(
        "PROPOSAL_COUNT: 0\n"
        "SCARCITY_REASON: No honest option survives current contradiction.\n",
    )

    parsed = parse_proposal_generation_result(raw_result)

    assert parsed.raw_result is raw_result
    assert parsed.raw_result.adapter_id == "adapter-1"


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
