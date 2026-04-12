from dataclasses import dataclass, field
from typing import Any

import pytest

from jeff.cognitive import (
    EvidenceItem,
    EvidencePack,
    ResearchRequest,
    ResearchArtifact,
    ResearchSynthesisRuntimeError,
    SourceItem,
    build_research_model_request,
    synthesize_research,
)
from jeff.infrastructure import (
    FakeModelAdapter,
    ModelInvocationError,
    ModelInvocationStatus,
    ModelMalformedOutputError,
    ModelProviderHTTPError,
    ModelRequest,
    ModelResponse,
    ModelTimeoutError,
    ModelUsage,
)


def test_timeout_class_error_is_surfaced_distinctly() -> None:
    with pytest.raises(ResearchSynthesisRuntimeError) as exc_info:
        synthesize_research(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            adapter=FakeModelAdapter(
                adapter_id="research-timeout",
                provider_name="fake",
                model_name="research-model",
                forced_exception=ModelTimeoutError("timed out while waiting for provider"),
            ),
        )

    error = exc_info.value
    assert error.failure_class == "timeout"
    assert error.adapter_id == "research-timeout"
    assert error.provider_name == "fake"
    assert error.model_name == "research-model"
    assert "timeout" in str(error)


def test_malformed_output_is_surfaced_distinctly_from_timeout() -> None:
    with pytest.raises(ResearchSynthesisRuntimeError) as exc_info:
        synthesize_research(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            adapter=FakeModelAdapter(
                adapter_id="research-malformed",
                provider_name="fake",
                model_name="research-model",
                forced_exception=ModelMalformedOutputError("adapter returned malformed output"),
            ),
        )

    assert exc_info.value.failure_class == "malformed_output"


def test_malformed_output_can_succeed_via_one_repair_pass() -> None:
    adapter = _ScriptedAdapter(
        script=(
            ModelMalformedOutputError(
                "adapter returned malformed output",
                raw_output='summary: repaired summary\nfindings: [{"text":"Observed fact","source_refs":["S1"]}]',
            ),
            {
                "summary": "Repaired summary.",
                "findings": [{"text": "Observed fact", "source_refs": ["S1"]}],
                "inferences": [],
                "uncertainties": [],
                "recommendation": None,
            },
        )
    )

    artifact = synthesize_research(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
        adapter=adapter,
    )

    assert isinstance(artifact, ResearchArtifact)
    assert artifact.findings[0].source_refs == ("source-a",)
    assert [request.purpose for request in adapter.requests] == ["research_synthesis", "research_synthesis_repair"]


def test_failed_repair_keeps_malformed_output_classification() -> None:
    adapter = _ScriptedAdapter(
        script=(
            ModelMalformedOutputError("primary malformed", raw_output="summary: bad"),
            ModelMalformedOutputError("repair malformed", raw_output="still bad"),
        )
    )

    with pytest.raises(ResearchSynthesisRuntimeError) as exc_info:
        synthesize_research(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            adapter=adapter,
        )

    assert exc_info.value.failure_class == "malformed_output"
    assert len(adapter.requests) == 2


def test_generic_invocation_error_remains_bounded_and_truthful() -> None:
    with pytest.raises(ResearchSynthesisRuntimeError) as exc_info:
        synthesize_research(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            adapter=FakeModelAdapter(
                adapter_id="research-generic",
                provider_name="fake",
                model_name="research-model",
                forced_exception=ModelInvocationError("socket boom\nTraceback: internal details that should stay bounded"),
            ),
        )

    error = exc_info.value
    assert error.failure_class == "invocation_failure"
    assert "\n" not in error.reason
    assert "Traceback:" in error.reason
    assert len(error.reason) <= 180


def test_provider_http_failure_does_not_trigger_repair() -> None:
    adapter = _ScriptedAdapter(script=(ModelProviderHTTPError("provider failure"),))

    with pytest.raises(ResearchSynthesisRuntimeError) as exc_info:
        synthesize_research(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            adapter=adapter,
        )

    assert exc_info.value.failure_class == "provider_http_failure"
    assert len(adapter.requests) == 1


def test_effective_timeout_path_does_not_hardcode_lower_request_timeout() -> None:
    adapter = _CapturingAdapter()

    synthesize_research(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
        adapter=adapter,
    )

    assert adapter.captured_timeout_seconds is None


def test_build_research_model_request_leaves_timeout_to_runtime_adapter_when_no_explicit_override() -> None:
    request = build_research_model_request(_research_request(), _evidence_pack(), adapter_id="research-runtime")

    assert request.timeout_seconds is None


@dataclass(slots=True)
class _CapturingAdapter:
    adapter_id: str = "research-runtime"
    provider_name: str = "fake"
    model_name: str = "research-model"
    captured_timeout_seconds: int | None = None

    def invoke(self, request_model):  # type: ignore[no-untyped-def]
        self.captured_timeout_seconds = request_model.timeout_seconds
        return FakeModelAdapter(
            adapter_id=self.adapter_id,
            provider_name=self.provider_name,
            model_name=self.model_name,
            default_json_response={
                "summary": "The prepared evidence supports a bounded conclusion.",
                "findings": [{"text": "Source A describes the current state.", "source_refs": ["S1"]}],
                "inferences": [],
                "uncertainties": [],
                "recommendation": None,
            },
        ).invoke(request_model)


@dataclass(slots=True)
class _ScriptedAdapter:
    script: tuple[object, ...]
    adapter_id: str = "research-scripted"
    provider_name: str = "fake"
    model_name: str = "research-model"
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
            SourceItem(
                source_id="source-a",
                source_type="document",
                title="Bounded Note A",
                locator="doc://a",
                snippet="Source A says the current state is stable.",
            ),
        ),
        evidence_items=(EvidenceItem(text="The current state is stable.", source_refs=("source-a",)),),
    )
