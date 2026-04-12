from dataclasses import dataclass, field

import pytest

from jeff.cognitive import (
    EvidenceItem,
    EvidencePack,
    ResearchRequest,
    ResearchSynthesisRuntimeError,
    SourceItem,
    synthesize_research_with_runtime,
)
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


def test_runtime_repair_flow_recovers_from_primary_malformed_output() -> None:
    adapter = _ScriptedAdapter(
        script=(
            ModelMalformedOutputError(
                "primary malformed",
                raw_output='summary: repaired summary\nfindings: [{"text":"Observed fact","source_refs":["S1"]}]',
            ),
            {
                "summary": "Repaired summary.",
                "findings": [{"text": "Observed fact", "source_refs": ["S1"]}],
                "inferences": ["A bounded next step remains supported."],
                "uncertainties": ["No live validation was performed."],
                "recommendation": "Proceed with the bounded path.",
            },
        )
    )

    artifact = synthesize_research_with_runtime(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
        infrastructure_services=_services(adapter),
    )

    assert artifact.summary == "Repaired summary."
    assert artifact.findings[0].source_refs == ("source-a",)
    assert artifact.source_ids == ("source-a",)
    assert [request.purpose for request in adapter.requests] == ["research_synthesis", "research_synthesis_repair"]


def test_runtime_repair_flow_can_use_separate_repair_adapter_when_configured() -> None:
    primary_adapter = _ScriptedAdapter(
        adapter_id="research-primary",
        model_name="reasoning-model",
        script=(
            ModelMalformedOutputError(
                "primary malformed",
                raw_output='summary: repaired summary\nfindings: [{"text":"Observed fact","source_refs":["S1"]}]',
            ),
        ),
    )
    repair_adapter = _ScriptedAdapter(
        adapter_id="research-repair",
        model_name="formatter-model",
        script=(
            {
                "summary": "Repaired summary.",
                "findings": [{"text": "Observed fact", "source_refs": ["S1"]}],
                "inferences": ["A bounded next step remains supported."],
                "uncertainties": ["No live validation was performed."],
                "recommendation": "Proceed with the bounded path.",
            },
        ),
    )

    artifact = synthesize_research_with_runtime(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
        infrastructure_services=_services(
            primary_adapter,
            repair_adapter=repair_adapter,
            purpose_overrides=PurposeOverrides(research=primary_adapter.adapter_id, research_repair=repair_adapter.adapter_id),
        ),
    )

    assert artifact.findings[0].source_refs == ("source-a",)
    assert artifact.source_ids == ("source-a",)
    assert len(primary_adapter.requests) == 1
    assert len(repair_adapter.requests) == 1
    assert primary_adapter.requests[0].purpose == "research_synthesis"
    assert repair_adapter.requests[0].purpose == "research_synthesis_repair"
    assert repair_adapter.requests[0].metadata["adapter_id"] == "research-repair"


def test_runtime_repair_flow_still_fails_closed_when_repair_also_malformed() -> None:
    adapter = _ScriptedAdapter(
        script=(
            ModelMalformedOutputError("primary malformed", raw_output="summary: bad"),
            ModelMalformedOutputError("repair malformed", raw_output="still bad"),
        )
    )

    with pytest.raises(ResearchSynthesisRuntimeError, match="malformed_output"):
        synthesize_research_with_runtime(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            infrastructure_services=_services(adapter),
        )

    assert len(adapter.requests) == 2


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
    repair_adapter=None,
    purpose_overrides: PurposeOverrides | None = None,
) -> InfrastructureServices:
    registry = AdapterRegistry()
    registry.register(adapter)
    if repair_adapter is not None:
        registry.register(repair_adapter)
    return InfrastructureServices(
        model_adapter_registry=registry,
        default_model_adapter_id=adapter.adapter_id,
        purpose_overrides=purpose_overrides or PurposeOverrides(),
    )


@dataclass(slots=True)
class _ScriptedAdapter:
    script: tuple[object, ...]
    adapter_id: str = "repair-scripted"
    provider_name: str = "fake"
    model_name: str = "repair-model"
    requests: list[ModelRequest] = field(default_factory=list)

    def invoke(self, request_model: ModelRequest) -> ModelResponse:
        self.requests.append(request_model)
        step = self.script[len(self.requests) - 1]
        if isinstance(step, Exception):
            raise step
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
