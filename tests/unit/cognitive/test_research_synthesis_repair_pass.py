from dataclasses import dataclass, field

import pytest

from jeff.cognitive import (
    EvidenceItem,
    EvidencePack,
    ResearchRequest,
    ResearchSynthesisRuntimeError,
    ResearchSynthesisValidationError,
    SourceItem,
    synthesize_research,
)
from jeff.cognitive.research import synthesis as research_synthesis_module
from jeff.cognitive.research.synthesis import (
    build_research_formatter_bridge_model_request,
    build_research_model_request,
    build_research_repair_model_request,
)
from jeff.infrastructure import ModelInvocationStatus, ModelMalformedOutputError, ModelRequest, ModelResponse, ModelUsage


def test_live_bounded_text_path_does_not_invoke_formatter_adapter_when_primary_succeeds() -> None:
    primary_adapter = _ScriptedAdapter(script=(_valid_bounded_text(),))
    formatter_adapter = _ScriptedAdapter(adapter_id="formatter-bridge", script=(_valid_formatter_json(),))

    artifact = synthesize_research(_research_request(), _evidence_pack(), primary_adapter, formatter_adapter=formatter_adapter)

    assert artifact.summary == "Observed summary."
    assert len(primary_adapter.requests) == 1
    assert len(formatter_adapter.requests) == 0


def test_formatter_fallback_runs_after_deterministic_transform_failure_only() -> None:
    primary_adapter = _ScriptedAdapter(script=(_valid_bounded_text(),))
    formatter_adapter = _ScriptedAdapter(adapter_id="formatter-bridge", script=(_valid_formatter_json(),))
    events: list[dict[str, object]] = []

    original_transform = research_synthesis_module.transform_step1_bounded_text_to_candidate_payload

    def failing_transform(_: str) -> dict[str, object]:
        raise ResearchSynthesisValidationError("forced structural transform failure for formatter")

    research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = failing_transform
    try:
        artifact = synthesize_research(
            _research_request(),
            _evidence_pack(),
            primary_adapter,
            formatter_adapter=formatter_adapter,
            debug_emitter=events.append,
        )
    finally:
        research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = original_transform

    assert artifact.summary == "Observed summary."
    assert artifact.findings[0].source_refs == ("source-a",)
    checkpoints = [event["checkpoint"] for event in events]
    assert "deterministic_transform_failed" in checkpoints
    assert "formatter_fallback_started" in checkpoints
    assert "formatter_fallback_succeeded" in checkpoints
    assert checkpoints.index("deterministic_transform_failed") < checkpoints.index("formatter_fallback_started")
    assert formatter_adapter.requests[0].purpose == "research_synthesis_repair"


def test_formatter_request_uses_bounded_text_not_full_evidence_input() -> None:
    primary_adapter = _ScriptedAdapter(script=(_valid_bounded_text(),))
    formatter_adapter = _ScriptedAdapter(adapter_id="formatter-bridge", script=(_valid_formatter_json(),))
    original_transform = research_synthesis_module.transform_step1_bounded_text_to_candidate_payload

    def failing_transform(_: str) -> dict[str, object]:
        raise ResearchSynthesisValidationError("forced structural transform failure for formatter")

    research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = failing_transform
    try:
        synthesize_research(_research_request(), _evidence_pack(), primary_adapter, formatter_adapter=formatter_adapter)
    finally:
        research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = original_transform

    formatter_request = formatter_adapter.requests[0]
    assert "BOUNDED_CONTENT:" in formatter_request.prompt
    assert "Do not use or reconstruct the original evidence pack." in formatter_request.prompt
    assert "EVIDENCE:" not in formatter_request.prompt
    assert "Fact from source A." not in formatter_request.prompt
    assert "source-a" not in formatter_request.prompt
    assert formatter_request.metadata["formatter_input_kind"] == "step1_bounded_text"


def test_formatter_output_is_validated_hard_before_downstream_handoff() -> None:
    primary_adapter = _ScriptedAdapter(script=(_valid_bounded_text(),))
    formatter_adapter = _ScriptedAdapter(
        adapter_id="formatter-bridge",
        script=(
            {
                "summary": "Observed summary.",
                "findings": [{"text": "Observed fact", "source_refs": "S1"}],
                "inferences": ["A bounded next step remains supported."],
                "uncertainties": ["No live validation was performed."],
                "recommendation": "Proceed with the bounded path.",
            },
        ),
    )
    events: list[dict[str, object]] = []
    original_transform = research_synthesis_module.transform_step1_bounded_text_to_candidate_payload

    def failing_transform(_: str) -> dict[str, object]:
        raise ResearchSynthesisValidationError("forced structural transform failure for formatter")

    research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = failing_transform
    try:
        with pytest.raises(ResearchSynthesisValidationError, match="source_refs must be a list"):
            synthesize_research(
                _research_request(),
                _evidence_pack(),
                primary_adapter,
                formatter_adapter=formatter_adapter,
                debug_emitter=events.append,
            )
    finally:
        research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = original_transform

    checkpoints = [event["checkpoint"] for event in events]
    assert "formatter_fallback_started" in checkpoints
    assert "formatter_fallback_failed" in checkpoints
    assert "formatter_fallback_succeeded" not in checkpoints
    assert "citation_remap_started" not in checkpoints


def test_formatter_cannot_introduce_invented_citation_keys() -> None:
    primary_adapter = _ScriptedAdapter(script=(_valid_bounded_text(),))
    formatter_adapter = _ScriptedAdapter(
        adapter_id="formatter-bridge",
        script=(
            {
                "summary": "Observed summary.",
                "findings": [{"text": "Observed fact", "source_refs": ["S9"]}],
                "inferences": ["A bounded next step remains supported."],
                "uncertainties": ["No live validation was performed."],
                "recommendation": "Proceed with the bounded path.",
            },
        ),
    )
    original_transform = research_synthesis_module.transform_step1_bounded_text_to_candidate_payload

    def failing_transform(_: str) -> dict[str, object]:
        raise ResearchSynthesisValidationError("forced structural transform failure for formatter")

    research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = failing_transform
    try:
        with pytest.raises(ResearchSynthesisValidationError, match="unknown citation refs"):
            synthesize_research(
                _research_request(),
                _evidence_pack(),
                primary_adapter,
                formatter_adapter=formatter_adapter,
            )
    finally:
        research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = original_transform


def test_formatter_bridge_request_helper_builds_json_contract_from_text_mode_primary_request() -> None:
    request = _research_request()
    evidence_pack = _evidence_pack()
    primary_request = build_research_model_request(request, evidence_pack, adapter_id="research-primary")

    formatter_request = build_research_formatter_bridge_model_request(
        request,
        evidence_pack,
        '```json {"summary":"Observed","findings":[{"text":"Observed fact","source_refs":"S1"}]} ```',
        primary_request=primary_request,
        adapter_id="formatter-bridge",
    )

    assert formatter_request.purpose == "research_synthesis_repair"
    assert formatter_request.response_mode.value == "JSON"
    assert formatter_request.json_schema is not None
    assert "Output exactly one JSON object matching json_schema." in formatter_request.prompt
    assert "source-a" not in formatter_request.prompt
    assert "source-b" not in formatter_request.prompt


def test_legacy_repair_request_helper_still_maps_to_formatter_bridge_contract() -> None:
    request = _research_request()
    evidence_pack = _evidence_pack()
    primary_request = build_research_model_request(request, evidence_pack, adapter_id="research-primary")

    legacy_request = build_research_repair_model_request(
        request,
        evidence_pack,
        "SUMMARY:\nObserved summary.",
        primary_request=primary_request,
        adapter_id="formatter-bridge",
    )

    assert legacy_request.purpose == "research_synthesis_repair"
    assert legacy_request.metadata["formatter_input_kind"] == "step1_bounded_text"


def test_malformed_primary_output_does_not_trigger_formatter_attempt() -> None:
    primary_adapter = _ScriptedAdapter(script=(ModelMalformedOutputError("primary malformed", raw_output="SUMMARY: bad"),))
    formatter_adapter = _ScriptedAdapter(adapter_id="formatter-bridge", script=(_valid_formatter_json(),))

    with pytest.raises(ResearchSynthesisRuntimeError, match="malformed_output"):
        synthesize_research(_research_request(), _evidence_pack(), primary_adapter, formatter_adapter=formatter_adapter)

    assert len(primary_adapter.requests) == 1
    assert len(formatter_adapter.requests) == 0


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
            "- text: Observed fact.",
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
        "summary": "Observed summary.",
        "findings": [{"text": "Observed fact.", "source_refs": ["S1"]}],
        "inferences": ["A bounded next step remains supported."],
        "uncertainties": ["No live validation was performed."],
        "recommendation": "Proceed with the bounded path.",
    }


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
            SourceItem(
                source_id="source-b",
                source_type="document",
                title="Bounded Note B",
                locator="doc://b",
                snippet="Source B says the same constraint still holds.",
            ),
        ),
        evidence_items=(
            EvidenceItem(text="Fact from source A.", source_refs=("source-a",)),
            EvidenceItem(text="Fact from source B.", source_refs=("source-b",)),
        ),
    )
