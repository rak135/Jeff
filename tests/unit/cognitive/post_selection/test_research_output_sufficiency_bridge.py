import pytest

from jeff.cognitive import ResearchArtifact, ResearchFinding
from jeff.cognitive.post_selection import (
    ResearchOutputSufficiencyError,
    ResearchOutputSufficiencyRequest,
    ResearchOutputSufficiencyResult,
    evaluate_research_output_sufficiency,
)


def test_clearly_sufficient_research_output_is_decision_support_ready() -> None:
    result = evaluate_research_output_sufficiency(
        ResearchOutputSufficiencyRequest(
            request_id="research-sufficiency-1",
            research_artifact=_artifact(),
        )
    )

    assert result.sufficient_for_downstream_use is True
    assert result.downstream_target == "decision_support_ready"
    assert result.unresolved_items == ()
    assert result.contradictions_present is False
    assert result.insufficiency_reason is None


def test_insufficient_research_output_preserves_explicit_missing_items() -> None:
    result = evaluate_research_output_sufficiency(
        ResearchOutputSufficiencyRequest(
            request_id="research-sufficiency-2",
            research_artifact=_artifact(
                uncertainties=("whether the vendor still supports the current export path",),
            ),
        )
    )

    assert result.sufficient_for_downstream_use is False
    assert result.downstream_target == "more_research_needed"
    assert result.unresolved_items == (
        "Need a source-backed answer for whether the vendor still supports the current export path.",
    )
    assert result.insufficiency_reason is not None


def test_unresolved_contradictions_make_research_insufficient() -> None:
    result = evaluate_research_output_sufficiency(
        ResearchOutputSufficiencyRequest(
            request_id="research-sufficiency-3",
            research_artifact=_artifact(
                summary="Contradictory source-backed claims remain visible in the current research output.",
            ),
        )
    )

    assert result.sufficient_for_downstream_use is False
    assert result.contradictions_present is True
    assert result.downstream_target == "more_research_needed"
    assert result.unresolved_items == (
        "Need a source-backed resolution for contradictory research claims before downstream use.",
    )


def test_malformed_research_output_fails_closed() -> None:
    artifact = _artifact()
    object.__setattr__(artifact, "findings", ())

    with pytest.raises(ResearchOutputSufficiencyError) as exc_info:
        evaluate_research_output_sufficiency(
            ResearchOutputSufficiencyRequest(
                request_id="research-sufficiency-4",
                research_artifact=artifact,
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("missing_findings",)


def test_blank_request_id_raises_typed_error() -> None:
    with pytest.raises(ResearchOutputSufficiencyError) as exc_info:
        evaluate_research_output_sufficiency(
            ResearchOutputSufficiencyRequest(
                request_id="   ",
                research_artifact=_artifact(),
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("invalid_request_id",)


def test_insufficient_result_without_explicit_unresolved_items_is_invalid() -> None:
    with pytest.raises(ValueError, match="unresolved_items"):
        ResearchOutputSufficiencyResult(
            evaluation_id="research-sufficiency-5",
            sufficient_for_downstream_use=False,
            downstream_target="more_research_needed",
            key_supported_points=("Supported point",),
            unresolved_items=(),
            contradictions_present=False,
            insufficiency_reason="Research remains insufficient.",
            summary="Insufficient research output.",
        )


def test_supported_points_are_preserved_in_bounded_inspectable_form() -> None:
    result = evaluate_research_output_sufficiency(
        ResearchOutputSufficiencyRequest(
            request_id="research-sufficiency-6",
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
        )
    )

    assert result.key_supported_points == (
        "The current API keeps the batch endpoint behind the enterprise plan.",
        "The free tier still exposes only the limited single-item export path.",
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
