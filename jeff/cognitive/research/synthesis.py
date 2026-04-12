"""Research synthesis behavior over explicit evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from jeff.infrastructure import (
    InfrastructureServices,
    ModelAdapter,
    ModelAdapterError,
    ModelAdapterNotFoundError,
    ModelInvocationError,
    ModelMalformedOutputError,
    ModelProviderHTTPError,
    ModelRequest,
    ModelResponseMode,
    ModelTimeoutError,
    ModelTransportError,
)

from ..types import require_text
from .contracts import EvidencePack, ResearchArtifact, ResearchFinding, ResearchRequest, validate_research_provenance
from .errors import ResearchSynthesisError, ResearchSynthesisRuntimeError, ResearchSynthesisValidationError


@dataclass(frozen=True, slots=True)
class ModelFacingSource:
    citation_key: str
    source_type: str
    title: str | None
    locator: str | None
    snippet: str | None
    published_at: str | None


ResearchDebugEmitter = Callable[[dict[str, object]], None]


def build_research_model_request(
    request: ResearchRequest,
    evidence_pack: EvidencePack,
    adapter_id: str | None = None,
) -> ModelRequest:
    if request.question != evidence_pack.question:
        raise ValueError("research request question must match evidence pack question")

    citation_key_map = build_citation_key_map(evidence_pack)
    source_id_to_citation_key = {source_id: citation_key for citation_key, source_id in citation_key_map.items()}
    allowed_citation_keys = tuple(citation_key_map.keys())
    model_facing_sources = build_model_facing_sources(evidence_pack, citation_key_map)

    source_lines = [
        (
            f"- {source.citation_key} | type={source.source_type}"
            f" | title={source.title or 'n/a'}"
            f" | locator={source.locator or 'n/a'}"
            f" | published_at={source.published_at or 'n/a'}"
            f" | snippet={source.snippet or 'n/a'}"
        )
        for source in model_facing_sources
    ]
    evidence_lines = [
        f"- refs={', '.join(source_id_to_citation_key[source_ref] for source_ref in item.source_refs)} | text={item.text}"
        for item in evidence_pack.evidence_items
    ]
    contradiction_lines = [
        f"- {_rewrite_source_identifiers(item, source_id_to_citation_key)}"
        for item in evidence_pack.contradictions
    ] or ["- none"]
    uncertainty_lines = [f"- {item}" for item in evidence_pack.uncertainties] or ["- none"]
    constraint_lines = [f"- {item}" for item in (request.constraints or evidence_pack.constraints)] or ["- none"]
    allowed_citation_line = ", ".join(allowed_citation_keys)

    prompt = "\n".join(
        [
            "You are performing bounded research synthesis from prepared evidence only.",
            "Stay within the provided evidence.",
            "Do not invent sources, provenance, facts, or unstated certainty.",
            "Keep findings separate from inferences.",
            "Keep uncertainty explicit.",
            "Use only the provided citation keys in findings.source_refs.",
            "Return JSON only and follow the required schema exactly.",
            "",
            f"Question: {request.question}",
            "Constraints:",
            *constraint_lines,
            f"Allowed citation keys: {allowed_citation_line}",
            "Sources:",
            *source_lines,
            "Evidence Items:",
            *evidence_lines,
            "Contradictions:",
            *contradiction_lines,
            "Uncertainties:",
            *uncertainty_lines,
            "",
            "Required JSON shape:",
            '{"summary":"string","findings":[{"text":"string","source_refs":["S1"]}],"inferences":["string"],"uncertainties":["string"],"recommendation":"string or null"}',
        ]
    )

    return ModelRequest(
        request_id=f"research-synthesis:{request.project_id or 'none'}:{request.work_unit_id or 'none'}:{request.run_id or 'none'}:{request.question.lower().replace(' ', '-')}",
        project_id=request.project_id,
        work_unit_id=request.work_unit_id,
        run_id=request.run_id,
        purpose="research_synthesis",
        prompt=prompt,
        system_instructions=(
            "Synthesize only from provided evidence. "
            "Never claim unseen sources. "
            "Keep findings, inferences, and uncertainties distinct. "
            "Use only the request-local citation keys in findings.source_refs."
        ),
        response_mode=ModelResponseMode.JSON,
        json_schema=_build_research_synthesis_schema(allowed_citation_keys),
        timeout_seconds=None,
        max_output_tokens=1200,
        reasoning_effort="medium",
        metadata={
            "research_question": request.question,
            "source_mode": request.source_mode,
            "expected_output_shape": "research_artifact_v1",
            "adapter_id": adapter_id,
            "citation_keys": list(allowed_citation_keys),
            "source_count": len(evidence_pack.sources),
        },
    )


def synthesize_research(
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    adapter: ModelAdapter,
    repair_adapter: ModelAdapter | None = None,
    debug_emitter: ResearchDebugEmitter | None = None,
) -> ResearchArtifact:
    if not evidence_pack.evidence_items:
        raise ResearchSynthesisValidationError("research synthesis requires at least one evidence item")

    effective_repair_adapter = repair_adapter or adapter
    citation_key_map = build_citation_key_map(evidence_pack)
    _emit_research_debug_event(
        debug_emitter,
        "source_key_map_built",
        keys=list(citation_key_map.keys()),
        source_key_map=_citation_key_map_preview(citation_key_map),
        source_count=len(evidence_pack.sources),
    )
    model_request = build_research_model_request(research_request, evidence_pack, adapter_id=adapter.adapter_id)
    payload = _invoke_synthesis_payload_with_optional_repair(
        research_request=research_request,
        evidence_pack=evidence_pack,
        adapter=adapter,
        repair_adapter=effective_repair_adapter,
        model_request=model_request,
        debug_emitter=debug_emitter,
    )

    artifact = _research_artifact_from_output(
        research_request=research_request,
        evidence_pack=evidence_pack,
        payload=payload,
        debug_emitter=debug_emitter,
    )
    _emit_research_debug_event(
        debug_emitter,
        "provenance_validation_started",
        source_item_count=len(evidence_pack.sources),
        evidence_item_count=len(evidence_pack.evidence_items),
        artifact_source_ids=list(artifact.source_ids),
    )
    try:
        validate_research_provenance(
            findings=artifact.findings,
            source_ids=artifact.source_ids,
            source_items=evidence_pack.sources,
            evidence_items=evidence_pack.evidence_items,
        )
    except ResearchSynthesisValidationError as exc:
        _emit_research_debug_event(
            debug_emitter,
            "provenance_validation_failed",
            reason=_bounded_debug_text(str(exc)),
            source_item_count=len(evidence_pack.sources),
            artifact_source_ids=list(artifact.source_ids),
        )
        raise
    _emit_research_debug_event(
        debug_emitter,
        "provenance_validation_succeeded",
        source_item_count=len(evidence_pack.sources),
        artifact_source_ids=list(artifact.source_ids),
    )
    return artifact


def synthesize_research_with_runtime(
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    infrastructure_services: InfrastructureServices,
    adapter_id: str | None = None,
    debug_emitter: ResearchDebugEmitter | None = None,
) -> ResearchArtifact:
    try:
        adapter = (
            infrastructure_services.get_model_adapter(adapter_id)
            if adapter_id is not None
            else infrastructure_services.get_adapter_for_purpose("research")
        )
    except ModelAdapterError as exc:
        raise _runtime_error_from_exception(exc, adapter=None, adapter_id_hint=adapter_id) from exc
    try:
        repair_adapter = infrastructure_services.get_adapter_for_purpose(
            "research_repair",
            fallback_adapter_id=adapter.adapter_id,
        )
    except ModelAdapterError as exc:
        raise _runtime_error_from_exception(
            exc,
            adapter=None,
            adapter_id_hint=infrastructure_services.purpose_overrides.research_repair or adapter_id or adapter.adapter_id,
        ) from exc
    return synthesize_research(
        research_request=research_request,
        evidence_pack=evidence_pack,
        adapter=adapter,
        repair_adapter=repair_adapter,
        debug_emitter=debug_emitter,
    )


def _research_artifact_from_output(
    *,
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    payload: dict[str, Any],
    debug_emitter: ResearchDebugEmitter | None = None,
) -> ResearchArtifact:
    citation_key_map = build_citation_key_map(evidence_pack)
    _emit_research_debug_event(
        debug_emitter,
        "citation_remap_started",
        allowed_citation_keys=list(citation_key_map.keys()),
        returned_citation_refs=_returned_citation_refs_preview(payload.get("findings")),
    )
    try:
        summary = _required_string(payload, "summary")
        findings_payload = _required_list(payload, "findings")
        inferences = _required_string_list(payload, "inferences")
        uncertainties = _required_string_list(payload, "uncertainties")
        recommendation = _optional_string(payload.get("recommendation"), field_name="recommendation")

        known_citation_keys = set(citation_key_map)
        findings: list[ResearchFinding] = []
        used_source_ids: list[str] = []
        for item in findings_payload:
            if not isinstance(item, dict):
                raise ResearchSynthesisValidationError("research finding entries must be objects")
            text = _required_string(item, "text")
            source_refs = _required_string_list(item, "source_refs")
            if not source_refs:
                raise ResearchSynthesisValidationError("research synthesis findings must keep at least one source_ref")
            missing = [citation_key for citation_key in source_refs if citation_key not in known_citation_keys]
            if missing:
                raise ResearchSynthesisValidationError(
                    f"research synthesis returned unknown citation refs: {missing}",
                )
            remapped_source_refs = tuple(citation_key_map[citation_key] for citation_key in source_refs)
            findings.append(ResearchFinding(text=text, source_refs=remapped_source_refs))
            for source_id in remapped_source_refs:
                if source_id not in used_source_ids:
                    used_source_ids.append(source_id)

        if not findings:
            raise ResearchSynthesisValidationError("research artifact requires at least one finding")

        artifact = ResearchArtifact(
            question=research_request.question,
            summary=summary,
            findings=tuple(findings),
            inferences=tuple(inferences),
            uncertainties=tuple(uncertainties),
            recommendation=recommendation,
            source_ids=tuple(used_source_ids),
        )
    except ResearchSynthesisValidationError as exc:
        _emit_research_debug_event(
            debug_emitter,
            "citation_remap_failed",
            reason=_bounded_debug_text(str(exc)),
            returned_citation_refs=_returned_citation_refs_preview(payload.get("findings")),
            allowed_citation_keys=list(citation_key_map.keys()),
        )
        raise

    _emit_research_debug_event(
        debug_emitter,
        "citation_remap_succeeded",
        used_source_ids=list(artifact.source_ids),
        finding_count=len(artifact.findings),
    )
    return artifact


def _invoke_synthesis_payload_with_optional_repair(
    *,
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    adapter: ModelAdapter,
    repair_adapter: ModelAdapter,
    model_request: ModelRequest,
    debug_emitter: ResearchDebugEmitter | None = None,
) -> dict[str, Any]:
    _emit_research_debug_event(
        debug_emitter,
        "primary_synthesis_started",
        adapter_id=adapter.adapter_id,
        provider_name=getattr(adapter, "provider_name", None),
        model_name=getattr(adapter, "model_name", None),
        allowed_citation_keys=list(build_citation_key_map(evidence_pack).keys()),
    )
    try:
        response = adapter.invoke(model_request)
    except ModelInvocationError as exc:
        _emit_research_debug_event(
            debug_emitter,
            "primary_synthesis_failed",
            failure_class=_failure_class_from_exception(exc),
            adapter_id=adapter.adapter_id,
            provider_name=getattr(adapter, "provider_name", None),
            model_name=getattr(adapter, "model_name", None),
            reason=_bounded_debug_text(str(exc)),
            raw_output_preview=_malformed_output_preview(exc),
        )
        if not isinstance(exc, ModelMalformedOutputError):
            raise _runtime_error_from_exception(exc, adapter=adapter) from exc
        repaired_payload = _attempt_malformed_output_repair(
            research_request=research_request,
            evidence_pack=evidence_pack,
            repair_adapter=repair_adapter,
            model_request=model_request,
            malformed_error=exc,
            debug_emitter=debug_emitter,
        )
        if repaired_payload is None:
            raise _runtime_error_from_exception(exc, adapter=adapter) from exc
        return repaired_payload

    if response.output_json is None:
        raise ResearchSynthesisValidationError("research synthesis requires JSON output")
    _emit_research_debug_event(
        debug_emitter,
        "primary_synthesis_succeeded",
        adapter_id=adapter.adapter_id,
        provider_name=getattr(adapter, "provider_name", None),
        model_name=getattr(adapter, "model_name", None),
        raw_output_preview=_response_output_preview(response),
    )
    return response.output_json


def _required_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str):
        raise ResearchSynthesisValidationError(f"{field_name} must be a non-empty string")
    return require_text(value, field_name=field_name)


def _optional_string(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ResearchSynthesisValidationError(f"{field_name} must be a string or null")
    return require_text(value, field_name=field_name)


def _required_list(payload: dict[str, Any], field_name: str) -> list[Any]:
    value = payload.get(field_name)
    if not isinstance(value, list):
        raise ResearchSynthesisValidationError(f"{field_name} must be a list")
    return value


def _required_string_list(payload: dict[str, Any], field_name: str) -> list[str]:
    items = _required_list(payload, field_name)
    normalized: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise ResearchSynthesisValidationError(f"{field_name} entries must be strings")
        normalized.append(require_text(item, field_name=field_name))
    return normalized


def build_citation_key_map(evidence_pack: EvidencePack) -> dict[str, str]:
    return {f"S{index}": source.source_id for index, source in enumerate(evidence_pack.sources, start=1)}


def build_model_facing_sources(
    evidence_pack: EvidencePack,
    citation_key_map: dict[str, str] | None = None,
) -> tuple[ModelFacingSource, ...]:
    resolved_citation_key_map = citation_key_map or build_citation_key_map(evidence_pack)
    source_id_to_citation_key = {
        source_id: citation_key for citation_key, source_id in resolved_citation_key_map.items()
    }
    return tuple(
        ModelFacingSource(
            citation_key=source_id_to_citation_key[source.source_id],
            source_type=source.source_type,
            title=source.title,
            locator=source.locator,
            snippet=source.snippet,
            published_at=source.published_at,
        )
        for source in evidence_pack.sources
    )


def _build_research_synthesis_schema(allowed_citation_keys: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "source_refs": {
                            "type": "array",
                            "items": {"type": "string", "enum": list(allowed_citation_keys)},
                            "minItems": 1,
                        },
                    },
                    "required": ["text", "source_refs"],
                    "additionalProperties": False,
                },
                "minItems": 1,
            },
            "inferences": {"type": "array", "items": {"type": "string"}},
            "uncertainties": {"type": "array", "items": {"type": "string"}},
            "recommendation": {"type": ["string", "null"]},
        },
        "required": ["summary", "findings", "inferences", "uncertainties", "recommendation"],
        "additionalProperties": False,
    }


def build_research_repair_model_request(
    request: ResearchRequest,
    evidence_pack: EvidencePack,
    malformed_output: str,
    *,
    primary_request: ModelRequest,
    adapter_id: str | None = None,
) -> ModelRequest:
    if request.question != evidence_pack.question:
        raise ValueError("research request question must match evidence pack question")
    if primary_request.json_schema is None:
        raise ValueError("research repair request requires the primary JSON schema")

    citation_key_map = build_citation_key_map(evidence_pack)
    allowed_citation_keys = tuple(citation_key_map.keys())
    sanitized_output = _sanitize_repair_input(malformed_output, citation_key_map)
    prompt = "\n".join(
        [
            "You are repairing malformed research synthesis output.",
            "Convert the malformed content into valid JSON matching the exact schema.",
            "Do not add prose.",
            "Do not add new claims, source refs, evidence, or certainty.",
            "Preserve only content already present in the malformed content.",
            "Use only the allowed citation keys in findings.source_refs.",
            "",
            f"Question: {request.question}",
            f"Allowed citation keys: {', '.join(allowed_citation_keys)}",
            "Exact JSON schema:",
            json.dumps(primary_request.json_schema, sort_keys=True),
            "",
            "Malformed content to repair:",
            sanitized_output,
        ]
    )

    return ModelRequest(
        request_id=f"{primary_request.request_id}:repair",
        project_id=request.project_id,
        work_unit_id=request.work_unit_id,
        run_id=request.run_id,
        purpose="research_synthesis_repair",
        prompt=prompt,
        system_instructions=(
            "Repair malformed research synthesis output into valid JSON only. "
            "Do not add new reasoning or claims. "
            "Use only the request-local citation keys in findings.source_refs."
        ),
        response_mode=ModelResponseMode.JSON,
        json_schema=primary_request.json_schema,
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
            "repair_attempt": 1,
            "repair_target_request_id": primary_request.request_id,
        },
    )


def _attempt_malformed_output_repair(
    *,
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    repair_adapter: ModelAdapter,
    model_request: ModelRequest,
    malformed_error: ModelMalformedOutputError,
    debug_emitter: ResearchDebugEmitter | None = None,
) -> dict[str, Any] | None:
    raw_output = getattr(malformed_error, "raw_output", None)
    if raw_output is None:
        _emit_research_debug_event(
            debug_emitter,
            "repair_pass_failed",
            failure_class="malformed_output",
            adapter_id=repair_adapter.adapter_id,
            provider_name=getattr(repair_adapter, "provider_name", None),
            model_name=getattr(repair_adapter, "model_name", None),
            reason="no repair input available from malformed output",
        )
        return None

    repair_input = _sanitize_repair_input(raw_output, build_citation_key_map(evidence_pack))
    _emit_research_debug_event(
        debug_emitter,
        "repair_pass_started",
        adapter_id=repair_adapter.adapter_id,
        provider_name=getattr(repair_adapter, "provider_name", None),
        model_name=getattr(repair_adapter, "model_name", None),
        allowed_citation_keys=list(build_citation_key_map(evidence_pack).keys()),
        malformed_output_preview=_bounded_preview(raw_output),
        repair_input_preview=_bounded_preview(repair_input),
    )
    repair_request = build_research_repair_model_request(
        research_request,
        evidence_pack,
        raw_output,
        primary_request=model_request,
        adapter_id=repair_adapter.adapter_id,
    )

    try:
        repair_response = repair_adapter.invoke(repair_request)
    except ModelInvocationError as exc:
        _emit_research_debug_event(
            debug_emitter,
            "repair_pass_failed",
            failure_class=_failure_class_from_exception(exc),
            adapter_id=repair_adapter.adapter_id,
            provider_name=getattr(repair_adapter, "provider_name", None),
            model_name=getattr(repair_adapter, "model_name", None),
            reason=_bounded_debug_text(str(exc)),
            raw_output_preview=_malformed_output_preview(exc),
        )
        return None

    if repair_response.output_json is None:
        _emit_research_debug_event(
            debug_emitter,
            "repair_pass_failed",
            failure_class="validation_error",
            adapter_id=repair_adapter.adapter_id,
            provider_name=getattr(repair_adapter, "provider_name", None),
            model_name=getattr(repair_adapter, "model_name", None),
            reason="repair pass returned no JSON output",
        )
        return None
    _emit_research_debug_event(
        debug_emitter,
        "repair_pass_succeeded",
        adapter_id=repair_adapter.adapter_id,
        provider_name=getattr(repair_adapter, "provider_name", None),
        model_name=getattr(repair_adapter, "model_name", None),
        raw_output_preview=_response_output_preview(repair_response),
    )
    return repair_response.output_json


def _rewrite_source_identifiers(text: str, source_id_to_citation_key: dict[str, str]) -> str:
    rewritten = text
    for source_id, citation_key in sorted(source_id_to_citation_key.items(), key=lambda item: len(item[0]), reverse=True):
        rewritten = rewritten.replace(source_id, citation_key)
    return rewritten


def _sanitize_repair_input(malformed_output: str, citation_key_map: dict[str, str]) -> str:
    source_id_to_citation_key = {source_id: citation_key for citation_key, source_id in citation_key_map.items()}
    return _rewrite_source_identifiers(malformed_output, source_id_to_citation_key)


def _emit_research_debug_event(
    emitter: ResearchDebugEmitter | None,
    checkpoint: str,
    **payload: object,
) -> None:
    if emitter is None:
        return
    emitter(
        {
            "domain": "research",
            "checkpoint": checkpoint,
            "payload": payload,
        }
    )


def _citation_key_map_preview(citation_key_map: dict[str, str], *, limit: int = 5) -> list[str]:
    preview = [f"{citation_key}->{_short_source_id(source_id)}" for citation_key, source_id in citation_key_map.items()]
    if len(preview) <= limit:
        return preview
    return [*preview[:limit], f"+{len(preview) - limit} more"]


def _short_source_id(source_id: str, *, max_chars: int = 18) -> str:
    if len(source_id) <= max_chars:
        return source_id
    return f"{source_id[: max_chars - 3]}..."


def _returned_citation_refs_preview(value: Any, *, limit: int = 8) -> list[str]:
    refs: list[str] = []
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            source_refs = item.get("source_refs")
            if not isinstance(source_refs, list):
                continue
            for source_ref in source_refs:
                if isinstance(source_ref, str):
                    normalized = source_ref.strip()
                    if normalized:
                        refs.append(normalized)
    if len(refs) <= limit:
        return refs
    return [*refs[:limit], f"+{len(refs) - limit} more"]


def _failure_class_from_exception(exc: Exception) -> str:
    if isinstance(exc, ModelTimeoutError):
        return "timeout"
    if isinstance(exc, ModelTransportError):
        return "connection_error"
    if isinstance(exc, ModelProviderHTTPError):
        return "provider_http_failure"
    if isinstance(exc, ModelMalformedOutputError):
        return "malformed_output"
    if isinstance(exc, ModelAdapterNotFoundError):
        return "unsupported_runtime_configuration"
    if isinstance(exc, ModelAdapterError) and not isinstance(exc, ModelInvocationError):
        return "unsupported_runtime_configuration"
    return "invocation_failure"


def _malformed_output_preview(exc: Exception) -> str | None:
    if not isinstance(exc, ModelMalformedOutputError):
        return None
    raw_output = getattr(exc, "raw_output", None)
    if raw_output is None:
        return None
    return _bounded_preview(raw_output)


def _response_output_preview(response: Any) -> str | None:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return _bounded_preview(output_text)
    output_json = getattr(response, "output_json", None)
    if isinstance(output_json, dict):
        return _bounded_preview(json.dumps(output_json, sort_keys=True))
    return None


def _bounded_preview(value: str, *, max_chars: int = 180) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 3].rstrip()}..."


def _bounded_debug_text(value: str, *, max_chars: int = 180) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 3].rstrip()}..."


def _runtime_error_from_exception(
    exc: Exception,
    *,
    adapter: ModelAdapter | None,
    adapter_id_hint: str | None = None,
) -> ResearchSynthesisRuntimeError:
    if isinstance(exc, ModelTimeoutError):
        failure_class = "timeout"
    elif isinstance(exc, ModelTransportError):
        failure_class = "connection_error"
    elif isinstance(exc, ModelProviderHTTPError):
        failure_class = "provider_http_failure"
    elif isinstance(exc, ModelMalformedOutputError):
        failure_class = "malformed_output"
    elif isinstance(exc, ModelAdapterNotFoundError):
        failure_class = "unsupported_runtime_configuration"
    elif isinstance(exc, ModelAdapterError) and not isinstance(exc, ModelInvocationError):
        failure_class = "unsupported_runtime_configuration"
    else:
        failure_class = "invocation_failure"

    return ResearchSynthesisRuntimeError(
        failure_class=failure_class,
        reason=str(exc),
        adapter_id=getattr(adapter, "adapter_id", None) or adapter_id_hint,
        provider_name=getattr(adapter, "provider_name", None),
        model_name=getattr(adapter, "model_name", None),
        base_url=getattr(adapter, "base_url", None),
    )
