import pytest

from jeff.cognitive import ResearchArtifact, ResearchFinding
from jeff.cognitive.post_selection import (
    ResearchDecisionSupportRequest,
    ResearchOutputSufficiencyResult,
    ResearchProposalConsumerRequest,
    build_research_decision_support_handoff,
    consume_research_for_proposal_support,
)
from jeff.cognitive.proposal import (
    ProposalSupportConsumerError,
    ProposalSupportConsumerRequest,
    consume_proposal_support_package,
)


def test_lawful_proposal_support_package_builds_proposal_input_package() -> None:
    package = consume_proposal_support_package(
        ProposalSupportConsumerRequest(
            request_id="proposal-input-1",
            proposal_support_package=_proposal_support_package(),
        )
    )

    assert package.proposal_input_ready is True
    assert package.package_id == "proposal-input:proposal-input-1"
    assert package.source_proposal_support_package_id == "proposal-support:research-proposal-support-1"
    assert package.supported_findings == (
        "The current export path is limited by plan tier and should be compared before any choice.",
    )
    assert package.provenance_refs == ("source-1",)


def test_not_ready_proposal_support_package_refuses_to_build_proposal_input() -> None:
    proposal_support_package = _proposal_support_package()
    object.__setattr__(proposal_support_package, "proposal_support_ready", False)

    with pytest.raises(ProposalSupportConsumerError) as exc_info:
        consume_proposal_support_package(
            ProposalSupportConsumerRequest(
                request_id="proposal-input-2",
                proposal_support_package=proposal_support_package,
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("proposal_support_not_ready",)


def test_malformed_proposal_support_package_fails_closed() -> None:
    proposal_support_package = _proposal_support_package()
    object.__setattr__(proposal_support_package, "supported_findings", ())

    with pytest.raises(ProposalSupportConsumerError) as exc_info:
        consume_proposal_support_package(
            ProposalSupportConsumerRequest(
                request_id="proposal-input-3",
                proposal_support_package=proposal_support_package,
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("missing_supported_findings",)


def test_blank_request_id_raises_typed_error() -> None:
    with pytest.raises(ProposalSupportConsumerError) as exc_info:
        consume_proposal_support_package(
            ProposalSupportConsumerRequest(
                request_id="   ",
                proposal_support_package=_proposal_support_package(),
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("invalid_request_id",)


def test_supported_findings_are_preserved_in_bounded_inspectable_form() -> None:
    package = consume_proposal_support_package(
        ProposalSupportConsumerRequest(
            request_id="proposal-input-4",
            proposal_support_package=_proposal_support_package(
                artifact=_artifact(
                    findings=(
                        ResearchFinding(
                            text="The current API keeps the batch endpoint behind the enterprise plan.",
                            source_refs=("source-1",),
                        ),
                        ResearchFinding(
                            text="The free tier still exposes only the limited single-item export path.",
                            source_refs=("source-2",),
                        ),
                    ),
                    source_ids=("source-1", "source-2"),
                ),
                sufficiency_result=ResearchOutputSufficiencyResult(
                    evaluation_id="research-sufficiency-4",
                    sufficient_for_downstream_use=True,
                    downstream_target="decision_support_ready",
                    key_supported_points=(
                        "The current API keeps the batch endpoint behind the enterprise plan.",
                        "The free tier still exposes only the limited single-item export path.",
                    ),
                    unresolved_items=(),
                    contradictions_present=False,
                    insufficiency_reason=None,
                    summary="Research is decision-support-ready.",
                ),
            ),
        )
    )

    assert package.supported_findings == (
        "The current API keeps the batch endpoint behind the enterprise plan.",
        "The free tier still exposes only the limited single-item export path.",
    )


def test_uncertainty_and_contradiction_remain_visible_when_present() -> None:
    package = consume_proposal_support_package(
        ProposalSupportConsumerRequest(
            request_id="proposal-input-5",
            proposal_support_package=_proposal_support_package(
                artifact=_artifact(
                    summary="Conflicting source-backed claims remain visible but bounded.",
                    uncertainties=("whether the current export tier still allows the bounded batch path",),
                ),
                sufficiency_result=ResearchOutputSufficiencyResult(
                    evaluation_id="research-sufficiency-5",
                    sufficient_for_downstream_use=True,
                    downstream_target="decision_support_ready",
                    key_supported_points=(
                        "The current export path is limited by plan tier and should be compared before any choice.",
                    ),
                    unresolved_items=("Need a current-date confirmation for the export tier.",),
                    contradictions_present=True,
                    insufficiency_reason=None,
                    summary="Research is decision-support-ready with visible contradiction notes.",
                ),
            ),
        )
    )

    assert package.uncertainty_points == ("whether the current export tier still allows the bounded batch path",)
    assert package.contradiction_notes == ("Conflicting source-backed claims remain visible but bounded.",)
    assert package.missing_information_markers == (
        "Need a current-date confirmation for the export tier.",
        "whether the current export tier still allows the bounded batch path",
    )


def test_recommendation_candidates_do_not_become_hidden_proposal_choices() -> None:
    package = consume_proposal_support_package(
        ProposalSupportConsumerRequest(
            request_id="proposal-input-6",
            proposal_support_package=_proposal_support_package(
                artifact=_artifact(
                    recommendation="Compare the bounded export options before the next explicit proposal stage.",
                ),
            ),
        )
    )

    assert package.recommendation_candidates == (
        "Compare the bounded export options before the next explicit proposal stage.",
    )
    assert "not proposal output" in package.summary


def test_missing_information_markers_are_preserved() -> None:
    proposal_support_package = _proposal_support_package()
    object.__setattr__(
        proposal_support_package,
        "missing_information_markers",
        (
            "Need a source-backed answer for current bulk export latency.",
            "Need a comparison between option A and B on current export latency.",
        ),
    )

    package = consume_proposal_support_package(
        ProposalSupportConsumerRequest(
            request_id="proposal-input-7",
            proposal_support_package=proposal_support_package,
        )
    )

    assert package.missing_information_markers == (
        "Need a source-backed answer for current bulk export latency.",
        "Need a comparison between option A and B on current export latency.",
    )


def _proposal_support_package(
    *,
    artifact: ResearchArtifact | None = None,
    sufficiency_result: ResearchOutputSufficiencyResult | None = None,
):
    artifact = _artifact() if artifact is None else artifact
    sufficiency_result = _sufficient_result() if sufficiency_result is None else sufficiency_result
    decision_support_handoff = build_research_decision_support_handoff(
        ResearchDecisionSupportRequest(
            request_id="research-decision-support-1",
            research_artifact=artifact,
            research_sufficiency_result=sufficiency_result,
        )
    )
    return consume_research_for_proposal_support(
        ResearchProposalConsumerRequest(
            request_id="research-proposal-support-1",
            research_decision_support_handoff=decision_support_handoff,
        )
    )


def _artifact(
    *,
    summary: str = "The current research output preserves bounded support without granting authority.",
    findings: tuple[ResearchFinding, ...] | None = None,
    inferences: tuple[str, ...] = ("The bounded evidence is enough for decision support.",),
    uncertainties: tuple[str, ...] = (),
    recommendation: str | None = "Use this as support-only input for the next explicit operator decision.",
    source_ids: tuple[str, ...] = ("source-1",),
) -> ResearchArtifact:
    return ResearchArtifact(
        question="What current export path should the operator compare before choosing the next step?",
        summary=summary,
        findings=(
            ResearchFinding(
                text="The current export path is limited by plan tier and should be compared before any choice.",
                source_refs=("source-1",),
            ),
        )
        if findings is None
        else findings,
        inferences=inferences,
        uncertainties=uncertainties,
        recommendation=recommendation,
        source_ids=source_ids,
    )


def _sufficient_result() -> ResearchOutputSufficiencyResult:
    return ResearchOutputSufficiencyResult(
        evaluation_id="research-sufficiency-1",
        sufficient_for_downstream_use=True,
        downstream_target="decision_support_ready",
        key_supported_points=(
            "The current export path is limited by plan tier and should be compared before any choice.",
        ),
        unresolved_items=(),
        contradictions_present=False,
        insufficiency_reason=None,
        summary="Research is decision-support-ready.",
    )
