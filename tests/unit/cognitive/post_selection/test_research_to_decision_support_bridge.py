import pytest

from jeff.cognitive import ResearchArtifact, ResearchFinding
from jeff.cognitive.post_selection import (
    ResearchDecisionSupportError,
    ResearchDecisionSupportRequest,
    ResearchOutputSufficiencyResult,
    build_research_decision_support_handoff,
)


def test_sufficient_research_output_builds_decision_support_handoff() -> None:
    handoff = build_research_decision_support_handoff(
        ResearchDecisionSupportRequest(
            request_id="research-decision-support-1",
            research_artifact=_artifact(),
            research_sufficiency_result=_sufficient_result(),
        )
    )

    assert handoff.decision_support_ready is True
    assert handoff.handoff_id == "research-decision-support:research-decision-support-1"
    assert handoff.research_artifact_ref.startswith("research-question:")
    assert handoff.supported_findings == (
        "The current export path is limited by plan tier and should be compared before any choice.",
    )
    assert handoff.provenance_refs == ("source-1",)


def test_insufficient_research_result_refuses_to_build_handoff() -> None:
    with pytest.raises(ResearchDecisionSupportError) as exc_info:
        build_research_decision_support_handoff(
            ResearchDecisionSupportRequest(
                request_id="research-decision-support-2",
                research_artifact=_artifact(),
                research_sufficiency_result=ResearchOutputSufficiencyResult(
                    evaluation_id="research-sufficiency-insufficient",
                    sufficient_for_downstream_use=False,
                    downstream_target="more_research_needed",
                    key_supported_points=(
                        "The current export path is limited by plan tier and should be compared before any choice.",
                    ),
                    unresolved_items=("Need a current-date confirmation for the export tier.",),
                    contradictions_present=False,
                    insufficiency_reason="Research remains insufficient.",
                    summary="Insufficient research output.",
                ),
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("research_not_sufficient", "unsupported_downstream_target")


def test_malformed_research_output_fails_closed() -> None:
    artifact = _artifact()
    object.__setattr__(artifact, "findings", ())

    with pytest.raises(ResearchDecisionSupportError) as exc_info:
        build_research_decision_support_handoff(
            ResearchDecisionSupportRequest(
                request_id="research-decision-support-3",
                research_artifact=artifact,
                research_sufficiency_result=_sufficient_result(),
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("missing_findings",)


def test_malformed_sufficiency_result_fails_closed() -> None:
    sufficiency_result = _sufficient_result()
    object.__setattr__(sufficiency_result, "key_supported_points", ())

    with pytest.raises(ResearchDecisionSupportError) as exc_info:
        build_research_decision_support_handoff(
            ResearchDecisionSupportRequest(
                request_id="research-decision-support-4",
                research_artifact=_artifact(),
                research_sufficiency_result=sufficiency_result,
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("missing_supported_points",)


def test_blank_request_id_raises_typed_error() -> None:
    with pytest.raises(ResearchDecisionSupportError) as exc_info:
        build_research_decision_support_handoff(
            ResearchDecisionSupportRequest(
                request_id="   ",
                research_artifact=_artifact(),
                research_sufficiency_result=_sufficient_result(),
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("invalid_request_id",)


def test_supported_findings_are_preserved_in_bounded_inspectable_form() -> None:
    handoff = build_research_decision_support_handoff(
        ResearchDecisionSupportRequest(
            request_id="research-decision-support-5",
            research_artifact=_artifact(
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
            research_sufficiency_result=ResearchOutputSufficiencyResult(
                evaluation_id="research-sufficiency-5",
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
        )
    )

    assert handoff.supported_findings == (
        "The current API keeps the batch endpoint behind the enterprise plan.",
        "The free tier still exposes only the limited single-item export path.",
    )


def test_uncertainty_and_contradiction_remain_visible_when_present() -> None:
    handoff = build_research_decision_support_handoff(
        ResearchDecisionSupportRequest(
            request_id="research-decision-support-6",
            research_artifact=_artifact(
                summary="Conflicting source-backed claims remain visible but bounded.",
                uncertainties=("whether the current export tier still allows the bounded batch path",),
            ),
            research_sufficiency_result=ResearchOutputSufficiencyResult(
                evaluation_id="research-sufficiency-6",
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
        )
    )

    assert handoff.uncertainty_points == ("whether the current export tier still allows the bounded batch path",)
    assert handoff.contradiction_notes == ("Conflicting source-backed claims remain visible but bounded.",)
    assert handoff.missing_information_markers == (
        "Need a current-date confirmation for the export tier.",
        "whether the current export tier still allows the bounded batch path",
    )


def test_recommendation_candidates_remain_visible_without_becoming_decisions() -> None:
    handoff = build_research_decision_support_handoff(
        ResearchDecisionSupportRequest(
            request_id="research-decision-support-7",
            research_artifact=_artifact(
                recommendation="Compare the bounded export options before the next explicit operator decision.",
            ),
            research_sufficiency_result=_sufficient_result(),
        )
    )

    assert handoff.recommendation_candidates == (
        "Compare the bounded export options before the next explicit operator decision.",
    )
    assert "does not authorize proposal choice" in handoff.summary


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
