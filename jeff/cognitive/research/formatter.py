"""Step 3 formatter fallback over an existing Step 1 bounded artifact."""

from __future__ import annotations

import json
from typing import Any

from jeff.infrastructure import ModelRequest, ModelResponseMode

from .contracts import EvidencePack, ResearchRequest
from .prompt_files import load_prompt_file, render_prompt
from .validators import build_candidate_research_json_schema, validate_candidate_research_payload

FORMATTER_BRIDGE_RUNTIME_OVERRIDE = "formatter_bridge"
FORMATTER_BRIDGE_REQUEST_PURPOSE = "research_synthesis_formatter"


def build_research_formatter_model_request(
    request: ResearchRequest,
    evidence_pack: EvidencePack,
    bounded_text: str,
    *,
    transform_failure_reason: str,
    primary_request: ModelRequest,
    adapter_id: str | None = None,
) -> ModelRequest:
    if request.question != evidence_pack.question:
        raise ValueError("research request question must match evidence pack question")

    citation_key_map = build_citation_key_map(evidence_pack)
    allowed_citation_keys = tuple(citation_key_map.keys())
    json_schema = build_candidate_research_json_schema(allowed_citation_keys)
    sanitized_bounded_text = _sanitize_formatter_input(bounded_text, citation_key_map)
    prompt = _build_formatter_prompt(
        request=request,
        allowed_citation_keys=allowed_citation_keys,
        json_schema=json_schema,
        bounded_text=sanitized_bounded_text,
        transform_failure_reason=transform_failure_reason,
    )

    return ModelRequest(
        request_id=f"{primary_request.request_id}:formatter",
        project_id=request.project_id,
        work_unit_id=request.work_unit_id,
        run_id=request.run_id,
        # Deliberate temporary bridge: keep using the existing runtime purpose
        # contract until infrastructure naming is cleaned up separately.
        purpose=FORMATTER_BRIDGE_REQUEST_PURPOSE,
        prompt=prompt,
        system_instructions=_formatter_system_instructions(),
        response_mode=ModelResponseMode.JSON,
        json_schema=json_schema,
        timeout_seconds=primary_request.timeout_seconds,
        max_output_tokens=primary_request.max_output_tokens,
        reasoning_effort="low",
        metadata={
            "research_question": request.question,
            "source_mode": request.source_mode,
            "expected_output_shape": "research_artifact_v1",
            "adapter_id": adapter_id,
            "citation_keys": list(allowed_citation_keys),
            "source_count": len(evidence_pack.sources),
            "formatter_attempt": 1,
            "formatter_input_kind": "step1_bounded_text",
            "formatter_target_request_id": primary_request.request_id,
        },
    )


def validate_research_formatter_output(payload: Any) -> dict[str, Any]:
    return validate_candidate_research_payload(payload)


def build_citation_key_map(evidence_pack: EvidencePack) -> dict[str, str]:
    return {f"S{index}": source.source_id for index, source in enumerate(evidence_pack.sources, start=1)}


def _formatter_system_instructions() -> str:
    system_instructions, _ = load_prompt_file("research/STEP3_FORMATTER.md")
    return system_instructions


def _build_formatter_prompt(
    *,
    request: ResearchRequest,
    allowed_citation_keys: tuple[str, ...],
    json_schema: dict[str, Any],
    bounded_text: str,
    transform_failure_reason: str,
) -> str:
    compact_schema = json.dumps(json_schema, sort_keys=True, separators=(",", ":"))
    _, template = load_prompt_file("research/STEP3_FORMATTER.md")
    return render_prompt(
        template,
        QUESTION=request.question,
        ALLOWED_CITATION_KEYS=", ".join(allowed_citation_keys),
        TRANSFORM_FAILURE=transform_failure_reason,
        JSON_SCHEMA=compact_schema,
        BOUNDED_CONTENT=bounded_text,
    )


def _sanitize_formatter_input(bounded_text: str, citation_key_map: dict[str, str]) -> str:
    source_id_to_citation_key = {source_id: citation_key for citation_key, source_id in citation_key_map.items()}
    return _rewrite_source_identifiers(bounded_text, source_id_to_citation_key)


def _rewrite_source_identifiers(text: str, source_id_to_citation_key: dict[str, str]) -> str:
    rewritten = text
    for source_id, citation_key in sorted(source_id_to_citation_key.items(), key=lambda item: len(item[0]), reverse=True):
        rewritten = rewritten.replace(source_id, citation_key)
    return rewritten
