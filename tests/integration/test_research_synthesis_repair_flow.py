from dataclasses import dataclass, field

import pytest

from jeff.cognitive import (
    EvidenceItem,
    EvidencePack,
    ResearchRequest,
    ResearchSynthesisValidationError,
    ResearchSynthesisRuntimeError,
    SourceItem,
    synthesize_research_with_runtime,
)
from jeff.cognitive.research import synthesis as research_synthesis_module
from jeff.infrastructure import (
    AdapterRegistry,
    InfrastructureServices,
    ModelInvocationStatus,
    ModelMalformedOutputError,
    PurposeOverrides,
    ModelRequest,
    ModelResponse,
    ModelUsage,
)


def test_runtime_formatter_fallback_recovers_from_deterministic_transform_failure() -> None:
    primary_adapter = _ScriptedAdapter(script=(_valid_bounded_text(),))
    formatter_adapter = _ScriptedAdapter(
        adapter_id="research-formatter-bridge",
        model_name="formatter-model",
        script=(_valid_formatter_json(),),
    )

    original_transform = research_synthesis_module.transform_step1_bounded_text_to_candidate_payload

    def failing_transform(_: str) -> dict[str, object]:
        raise ResearchSynthesisValidationError("forced structural transform failure for formatter")

    research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = failing_transform
    try:
        artifact = synthesize_research_with_runtime(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            infrastructure_services=_services(
                primary_adapter,
                formatter_adapter=formatter_adapter,
                purpose_overrides=PurposeOverrides(research=primary_adapter.adapter_id, formatter_bridge=formatter_adapter.adapter_id),
            ),
        )
    finally:
        research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = original_transform

    assert artifact.summary == "Formatted summary."
    assert artifact.findings[0].source_refs == ("source-a",)
    assert len(primary_adapter.requests) == 1
    assert len(formatter_adapter.requests) == 1
    assert formatter_adapter.requests[0].purpose == "research_synthesis_formatter"


def test_runtime_formatter_fallback_uses_bounded_text_not_original_evidence_pack() -> None:
    primary_adapter = _ScriptedAdapter(script=(_valid_bounded_text(),))
    formatter_adapter = _ScriptedAdapter(
        adapter_id="research-formatter-bridge",
        model_name="formatter-model",
        script=(_valid_formatter_json(),),
    )
    original_transform = research_synthesis_module.transform_step1_bounded_text_to_candidate_payload

    def failing_transform(_: str) -> dict[str, object]:
        raise ResearchSynthesisValidationError("forced structural transform failure for formatter")

    research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = failing_transform
    try:
        synthesize_research_with_runtime(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            infrastructure_services=_services(
                primary_adapter,
                formatter_adapter=formatter_adapter,
                purpose_overrides=PurposeOverrides(research=primary_adapter.adapter_id, formatter_bridge=formatter_adapter.adapter_id),
            ),
        )
    finally:
        research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = original_transform

    formatter_request = formatter_adapter.requests[0]
    assert "BOUNDED_CONTENT:" in formatter_request.prompt
    assert "Do not use or reconstruct the original evidence pack." in formatter_request.prompt
    assert "Fact from source A." not in formatter_request.prompt
    assert "Fact from source B." not in formatter_request.prompt


def test_runtime_formatter_fallback_fails_closed_when_formatter_output_is_invalid() -> None:
    primary_adapter = _ScriptedAdapter(script=(_valid_bounded_text(),))
    formatter_adapter = _ScriptedAdapter(
        adapter_id="research-formatter-bridge",
        model_name="formatter-model",
        script=(
            {
                "summary": "Formatted summary.",
                "findings": [{"text": "Observed fact", "source_refs": ["S9"]}],
                "inferences": ["A bounded next step remains supported."],
                "uncertainties": ["No live validation was performed."],
                "recommendation": "Proceed with the bounded path.",
            },
        ),
    )
    original_transform = research_synthesis_module.transform_step1_bounded_text_to_candidate_payload
    events: list[dict[str, object]] = []

    def failing_transform(_: str) -> dict[str, object]:
        raise ResearchSynthesisValidationError("forced structural transform failure for formatter")

    research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = failing_transform
    try:
        with pytest.raises(ResearchSynthesisValidationError, match="unknown citation refs"):
            synthesize_research_with_runtime(
                research_request=_research_request(),
                evidence_pack=_evidence_pack(),
                infrastructure_services=_services(
                    primary_adapter,
                    formatter_adapter=formatter_adapter,
                    purpose_overrides=PurposeOverrides(research=primary_adapter.adapter_id, formatter_bridge=formatter_adapter.adapter_id),
                ),
                debug_emitter=events.append,
            )
    finally:
        research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = original_transform

    checkpoints = [event["checkpoint"] for event in events]
    assert "formatter_fallback_started" in checkpoints
    assert "formatter_fallback_succeeded" in checkpoints
    assert "citation_remap_failed" in checkpoints


def test_runtime_content_generation_failure_does_not_trigger_formatter_fallback() -> None:
    adapter = _ScriptedAdapter(script=(ModelMalformedOutputError("primary malformed", raw_output="SUMMARY: bad"),))

    with pytest.raises(ResearchSynthesisRuntimeError, match="malformed_output"):
        synthesize_research_with_runtime(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            infrastructure_services=_services(adapter),
        )

    assert len(adapter.requests) == 1


def _research_request() -> ResearchRequest:
    return ResearchRequest(
        question="What does the prepared evidence support?",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
    )


def _evidence_pack() -> EvidencePack:
    return EvidencePack(
        question="What does the prepared evidence support?",
        sources=(
            SourceItem(source_id="source-a", source_type="document", title="A", locator="doc://a", snippet="A"),
            SourceItem(source_id="source-b", source_type="document", title="B", locator="doc://b", snippet="B"),
        ),
        evidence_items=(
            EvidenceItem(text="Fact from source A.", source_refs=("source-a",)),
            EvidenceItem(text="Fact from source B.", source_refs=("source-b",)),
        ),
    )


def _services(
    adapter,
    *,
    formatter_adapter=None,
    purpose_overrides: PurposeOverrides | None = None,
) -> InfrastructureServices:
    registry = AdapterRegistry()
    registry.register(adapter)
    if formatter_adapter is not None:
        registry.register(formatter_adapter)
    return InfrastructureServices(
        model_adapter_registry=registry,
        default_model_adapter_id=adapter.adapter_id,
        purpose_overrides=purpose_overrides or PurposeOverrides(),
    )


@dataclass(slots=True)
class _ScriptedAdapter:
    script: tuple[object, ...]
    adapter_id: str = "formatter-scripted"
    provider_name: str = "fake"
    model_name: str = "formatter-model"
    requests: list[ModelRequest] = field(default_factory=list)

    def invoke(self, request_model: ModelRequest) -> ModelResponse:
        self.requests.append(request_model)
        step = self.script[len(self.requests) - 1]
        if isinstance(step, Exception):
            raise step
        if request_model.response_mode.value == "TEXT":
            assert isinstance(step, str)
            return ModelResponse(
                request_id=request_model.request_id,
                adapter_id=self.adapter_id,
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=ModelInvocationStatus.COMPLETED,
                output_text=step,
                output_json=None,
                usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2, estimated_cost=0.0, latency_ms=1),
                warnings=(),
                raw_response_ref=f"fake://{self.adapter_id}/{request_model.request_id}",
            )
        assert isinstance(step, dict)
        return ModelResponse(
            request_id=request_model.request_id,
            adapter_id=self.adapter_id,
            provider_name=self.provider_name,
            model_name=self.model_name,
            status=ModelInvocationStatus.COMPLETED,
            output_text=None,
            output_json=step,
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2, estimated_cost=0.0, latency_ms=1),
            warnings=(),
            raw_response_ref=f"fake://{self.adapter_id}/{request_model.request_id}",
        )


def _valid_bounded_text() -> str:
    return "\n".join(
        [
            "SUMMARY:",
            "Observed summary.",
            "",
            "FINDINGS:",
            "- text: Observed fact",
            "  cites: S1",
            "",
            "INFERENCES:",
            "- A bounded next step remains supported.",
            "",
            "UNCERTAINTIES:",
            "- No live validation was performed.",
            "",
            "RECOMMENDATION:",
            "Proceed with the bounded path.",
        ]
    )


def _valid_formatter_json() -> dict[str, object]:
    return {
        "summary": "Formatted summary.",
        "findings": [{"text": "Observed fact", "source_refs": ["S1"]}],
        "inferences": ["A bounded next step remains supported."],
        "uncertainties": ["No live validation was performed."],
        "recommendation": "Proceed with the bounded path.",
    }
