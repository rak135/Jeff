"""Research synthesis behavior over explicit evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
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
    OutputStrategy,
    ModelTimeoutError,
    ModelTransportError,
)
from jeff.infrastructure.contract_runtime import ContractCallRequest, ContractRuntime

from ..types import require_text
from .bounded_syntax import STEP1_BOUNDED_SYNTAX_DESCRIPTION, validate_step1_bounded_text
from .prompt_files import load_prompt_file, render_prompt
from .contracts import EvidencePack, ResearchArtifact, ResearchFinding, ResearchRequest, validate_research_provenance
from .deterministic_transformer import transform_step1_bounded_text_to_candidate_payload
from .debug import ResearchDebugEmitter, emit_research_debug_event
from .errors import ResearchSynthesisError, ResearchSynthesisRuntimeError, ResearchSynthesisValidationError
from .fallback_policy import decide_formatter_fallback
from .formatter import (
    FORMATTER_BRIDGE_RUNTIME_OVERRIDE,
    build_research_formatter_model_request,
    validate_research_formatter_output,
)


@dataclass(frozen=True, slots=True)
class ModelFacingSource:
    citation_key: str
    source_type: str
    title: str | None
    locator: str | None
    snippet: str | None
    published_at: str | None


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
    prompt = _build_primary_synthesis_prompt(
        request=request,
        evidence_pack=evidence_pack,
        model_facing_sources=model_facing_sources,
        source_id_to_citation_key=source_id_to_citation_key,
        allowed_citation_keys=allowed_citation_keys,
    )

    return ModelRequest(
        request_id=f"research-synthesis:{request.project_id or 'none'}:{request.work_unit_id or 'none'}:{request.run_id or 'none'}:{request.question.lower().replace(' ', '-')}",
        project_id=request.project_id,
        work_unit_id=request.work_unit_id,
        run_id=request.run_id,
        purpose="research_synthesis",
        prompt=prompt,
        system_instructions=_primary_synthesis_system_instructions(),
        response_mode=ModelResponseMode.TEXT,
        json_schema=None,
        timeout_seconds=None,
        max_output_tokens=1200,
        reasoning_effort="medium",
        metadata={
            "research_question": request.question,
            "source_mode": request.source_mode,
            "expected_output_shape": "step1_bounded_text_v1",
            "adapter_id": adapter_id,
            "citation_keys": list(allowed_citation_keys),
            "source_count": len(evidence_pack.sources),
        },
    )


def synthesize_research(
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    adapter: ModelAdapter,
    formatter_adapter: ModelAdapter | None = None,
    debug_emitter: ResearchDebugEmitter | None = None,
    contract_runtime: ContractRuntime | None = None,
) -> ResearchArtifact:
    if not evidence_pack.evidence_items:
        raise ResearchSynthesisValidationError("research synthesis requires at least one evidence item")

    effective_formatter_adapter = formatter_adapter or adapter
    citation_key_map = build_citation_key_map(evidence_pack)
    emit_research_debug_event(
        debug_emitter,
        "source_key_map_built",
        keys=list(citation_key_map.keys()),
        source_key_map=_citation_key_map_preview(citation_key_map),
        source_count=len(evidence_pack.sources),
    )
    model_request = build_research_model_request(research_request, evidence_pack, adapter_id=adapter.adapter_id)
    payload = _invoke_step1_bounded_text_and_transform(
        research_request=research_request,
        evidence_pack=evidence_pack,
        adapter=adapter,
        formatter_adapter=effective_formatter_adapter,
        model_request=model_request,
        debug_emitter=debug_emitter,
        contract_runtime=contract_runtime,
    )

    artifact = _research_artifact_from_output(
        research_request=research_request,
        evidence_pack=evidence_pack,
        payload=payload,
        debug_emitter=debug_emitter,
    )
    emit_research_debug_event(
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
        emit_research_debug_event(
            debug_emitter,
            "provenance_validation_failed",
            reason=_bounded_debug_text(str(exc)),
            source_item_count=len(evidence_pack.sources),
            artifact_source_ids=list(artifact.source_ids),
        )
        raise
    emit_research_debug_event(
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
        formatter_adapter = infrastructure_services.get_adapter_for_purpose(
            FORMATTER_BRIDGE_RUNTIME_OVERRIDE,
            fallback_adapter_id=adapter.adapter_id,
        )
    except ModelAdapterError as exc:
        raise _runtime_error_from_exception(
            exc,
            adapter=None,
            adapter_id_hint=infrastructure_services.purpose_overrides.formatter_bridge or adapter_id or adapter.adapter_id,
        ) from exc
    return synthesize_research(
        research_request=research_request,
        evidence_pack=evidence_pack,
        adapter=adapter,
        formatter_adapter=formatter_adapter,
        debug_emitter=debug_emitter,
        contract_runtime=infrastructure_services.contract_runtime,
    )


def _research_artifact_from_output(
    *,
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    payload: dict[str, Any],
    debug_emitter: ResearchDebugEmitter | None = None,
) -> ResearchArtifact:
    citation_key_map = build_citation_key_map(evidence_pack)
    emit_research_debug_event(
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
        emit_research_debug_event(
            debug_emitter,
            "citation_remap_failed",
            reason=_bounded_debug_text(str(exc)),
            returned_citation_refs=_returned_citation_refs_preview(payload.get("findings")),
            allowed_citation_keys=list(citation_key_map.keys()),
        )
        raise

    emit_research_debug_event(
        debug_emitter,
        "citation_remap_succeeded",
        used_source_ids=list(artifact.source_ids),
        finding_count=len(artifact.findings),
    )
    return artifact


def _invoke_step1_bounded_text_and_transform(
    *,
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    adapter: ModelAdapter,
    formatter_adapter: ModelAdapter,
    model_request: ModelRequest,
    debug_emitter: ResearchDebugEmitter | None = None,
    contract_runtime: ContractRuntime | None = None,
) -> dict[str, Any]:
    emit_research_debug_event(
        debug_emitter,
        "content_generation_started",
        adapter_id=adapter.adapter_id,
        provider_name=getattr(adapter, "provider_name", None),
        model_name=getattr(adapter, "model_name", None),
        allowed_citation_keys=list(build_citation_key_map(evidence_pack).keys()),
    )
    try:
        if contract_runtime is not None:
            response = contract_runtime.invoke(
                ContractCallRequest(
                    purpose=model_request.purpose,
                    adapter_id=adapter.adapter_id,
                    routing_purpose="research",
                    output_strategy=OutputStrategy.BOUNDED_TEXT_THEN_PARSE,
                    prompt=model_request.prompt,
                    system_instructions=model_request.system_instructions,
                    request_id=model_request.request_id,
                    project_id=model_request.project_id,
                    work_unit_id=model_request.work_unit_id,
                    run_id=model_request.run_id,
                    response_mode=model_request.response_mode,
                    json_schema=model_request.json_schema,
                    timeout_seconds=model_request.timeout_seconds,
                    max_output_tokens=model_request.max_output_tokens,
                    reasoning_effort=model_request.reasoning_effort,
                    metadata=model_request.metadata,
                )
            )
        else:
            response = adapter.invoke(model_request)
    except ModelInvocationError as exc:
        emit_research_debug_event(
            debug_emitter,
            "content_generation_failed",
            failure_class=_failure_class_from_exception(exc),
            adapter_id=adapter.adapter_id,
            provider_name=getattr(adapter, "provider_name", None),
            model_name=getattr(adapter, "model_name", None),
            reason=_bounded_debug_text(str(exc)),
            raw_output_preview=_malformed_output_preview(exc),
        )
        raise _runtime_error_from_exception(exc, adapter=adapter) from exc

    try:
        if response.output_text is None:
            raise ResearchSynthesisValidationError("research synthesis requires text output")
        bounded_text = require_text(response.output_text, field_name="output_text")
    except (TypeError, ValueError, ResearchSynthesisValidationError) as exc:
        emit_research_debug_event(
            debug_emitter,
            "content_generation_failed",
            failure_class="validation_error",
            adapter_id=adapter.adapter_id,
            provider_name=getattr(adapter, "provider_name", None),
            model_name=getattr(adapter, "model_name", None),
            reason=_bounded_debug_text(str(exc)),
            raw_output_preview=_response_output_preview(response),
        )
        raise ResearchSynthesisValidationError(str(exc)) from exc

    emit_research_debug_event(
        debug_emitter,
        "content_generation_succeeded",
        adapter_id=adapter.adapter_id,
        provider_name=getattr(adapter, "provider_name", None),
        model_name=getattr(adapter, "model_name", None),
        raw_output_preview=_response_output_preview(response),
    )

    try:
        validate_step1_bounded_text(bounded_text)
    except ResearchSynthesisValidationError as exc:
        emit_research_debug_event(
            debug_emitter,
            "syntax_precheck_failed",
            reason=_bounded_debug_text(str(exc)),
            raw_output_preview=_bounded_preview(bounded_text),
        )
        raise

    emit_research_debug_event(
        debug_emitter,
        "deterministic_transform_started",
        raw_output_preview=_bounded_preview(bounded_text),
    )
    try:
        payload = transform_step1_bounded_text_to_candidate_payload(bounded_text)
    except ResearchSynthesisValidationError as exc:
        emit_research_debug_event(
            debug_emitter,
            "deterministic_transform_failed",
            reason=_bounded_debug_text(str(exc)),
            raw_output_preview=_bounded_preview(bounded_text),
        )
        fallback_decision = decide_formatter_fallback(
            bounded_text=bounded_text,
            transform_error=exc,
        )
        if not fallback_decision.allowed:
            raise
        return _attempt_formatter_fallback(
            research_request=research_request,
            evidence_pack=evidence_pack,
            formatter_adapter=formatter_adapter,
            model_request=model_request,
            bounded_text=bounded_text,
            transform_failure_reason=fallback_decision.reason,
            debug_emitter=debug_emitter,
            contract_runtime=contract_runtime,
        )
    emit_research_debug_event(
        debug_emitter,
        "deterministic_transform_succeeded",
        finding_count=len(payload.get("findings", [])),
        returned_citation_refs=_returned_citation_refs_preview(payload.get("findings")),
    )
    return payload


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

def build_research_formatter_bridge_model_request(
    request: ResearchRequest,
    evidence_pack: EvidencePack,
    bounded_text: str,
    *,
    primary_request: ModelRequest,
    adapter_id: str | None = None,
) -> ModelRequest:
    """Build the temporary Step 3 formatter bridge request directly.

    This helper exists for tests and narrow compatibility surfaces that need
    to construct the formatter bridge request outside the normal fallback path.
    """

    return build_research_formatter_model_request(
        request=request,
        evidence_pack=evidence_pack,
        bounded_text=bounded_text,
        transform_failure_reason="direct formatter bridge request",
        primary_request=primary_request,
        adapter_id=adapter_id,
    )



def _attempt_formatter_fallback(
    *,
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    formatter_adapter: ModelAdapter,
    model_request: ModelRequest,
    bounded_text: str,
    transform_failure_reason: str,
    debug_emitter: ResearchDebugEmitter | None = None,
    contract_runtime: ContractRuntime | None = None,
) -> dict[str, Any]:
    emit_research_debug_event(
        debug_emitter,
        "formatter_fallback_started",
        adapter_id=formatter_adapter.adapter_id,
        provider_name=getattr(formatter_adapter, "provider_name", None),
        model_name=getattr(formatter_adapter, "model_name", None),
        failure_class="structural_transform_failure",
        reason=_bounded_debug_text(transform_failure_reason),
        formatter_input_preview=_bounded_preview(bounded_text),
    )
    formatter_request = build_research_formatter_model_request(
        research_request,
        evidence_pack,
        bounded_text,
        transform_failure_reason=transform_failure_reason,
        primary_request=model_request,
        adapter_id=formatter_adapter.adapter_id,
    )

    try:
        if contract_runtime is not None:
            formatter_response = contract_runtime.invoke_with_request(
                formatter_request, adapter_id=formatter_adapter.adapter_id
            )
        else:
            formatter_response = formatter_adapter.invoke(formatter_request)
    except ModelInvocationError as exc:
        emit_research_debug_event(
            debug_emitter,
            "formatter_fallback_failed",
            failure_class=_failure_class_from_exception(exc),
            adapter_id=formatter_adapter.adapter_id,
            provider_name=getattr(formatter_adapter, "provider_name", None),
            model_name=getattr(formatter_adapter, "model_name", None),
            reason=_bounded_debug_text(str(exc)),
            raw_output_preview=_malformed_output_preview(exc),
        )
        raise _runtime_error_from_exception(exc, adapter=formatter_adapter) from exc

    if formatter_response.output_json is None:
        emit_research_debug_event(
            debug_emitter,
            "formatter_fallback_failed",
            failure_class="validation_error",
            adapter_id=formatter_adapter.adapter_id,
            provider_name=getattr(formatter_adapter, "provider_name", None),
            model_name=getattr(formatter_adapter, "model_name", None),
            reason="formatter fallback returned no JSON output",
            raw_output_preview=_response_output_preview(formatter_response),
        )
        raise ResearchSynthesisValidationError("formatter fallback requires JSON output")

    try:
        validated_payload = validate_research_formatter_output(formatter_response.output_json)
    except ResearchSynthesisValidationError as exc:
        emit_research_debug_event(
            debug_emitter,
            "formatter_fallback_failed",
            failure_class="validation_error",
            adapter_id=formatter_adapter.adapter_id,
            provider_name=getattr(formatter_adapter, "provider_name", None),
            model_name=getattr(formatter_adapter, "model_name", None),
            reason=_bounded_debug_text(str(exc)),
            raw_output_preview=_response_output_preview(formatter_response),
        )
        raise

    emit_research_debug_event(
        debug_emitter,
        "formatter_fallback_succeeded",
        adapter_id=formatter_adapter.adapter_id,
        provider_name=getattr(formatter_adapter, "provider_name", None),
        model_name=getattr(formatter_adapter, "model_name", None),
        raw_output_preview=_response_output_preview(formatter_response),
        returned_citation_refs=_returned_citation_refs_preview(validated_payload.get("findings")),
    )
    return validated_payload


def _primary_synthesis_system_instructions() -> str:
    system_instructions, _ = load_prompt_file("research/STEP1_SYNTHESIS.md")
    return system_instructions


def _build_primary_synthesis_prompt(
    *,
    request: ResearchRequest,
    evidence_pack: EvidencePack,
    model_facing_sources: tuple[ModelFacingSource, ...],
    source_id_to_citation_key: dict[str, str],
    allowed_citation_keys: tuple[str, ...],
) -> str:
    constraint_lines = _compact_section_lines(request.constraints or evidence_pack.constraints, prefix="C")
    contradiction_lines = _compact_section_lines(
        tuple(_rewrite_source_identifiers(item, source_id_to_citation_key) for item in evidence_pack.contradictions),
        prefix="X",
    )
    uncertainty_lines = _compact_section_lines(evidence_pack.uncertainties, prefix="U")
    source_lines = [
        "|".join(
            [
                source.citation_key,
                source.source_type or "n/a",
                source.title or "n/a",
                source.locator or "n/a",
                source.published_at or "n/a",
                source.snippet or "n/a",
            ]
        )
        for source in model_facing_sources
    ] or ["none"]
    evidence_lines = [
        (
            f"E{index}|refs={','.join(source_id_to_citation_key[source_ref] for source_ref in item.source_refs)}"
            f"|text={item.text}"
        )
        for index, item in enumerate(evidence_pack.evidence_items, start=1)
    ] or ["none"]

    _, template = load_prompt_file("research/STEP1_SYNTHESIS.md")
    return render_prompt(
        template,
        QUESTION=request.question,
        ALLOWED_CITATION_KEYS=", ".join(allowed_citation_keys),
        BOUNDED_SYNTAX=STEP1_BOUNDED_SYNTAX_DESCRIPTION,
        CONSTRAINTS="\n".join(constraint_lines),
        SOURCES="\n".join(source_lines),
        EVIDENCE="\n".join(evidence_lines),
        CONTRADICTIONS="\n".join(contradiction_lines),
        UNCERTAINTIES="\n".join(uncertainty_lines),
    )

def _compact_section_lines(values: tuple[str, ...], *, prefix: str) -> list[str]:
    if not values:
        return ["none"]
    return [f"{prefix}{index}|{value}" for index, value in enumerate(values, start=1)]


def _validate_payload_for_progression(payload: Any) -> dict[str, Any]:
    try:
        if not isinstance(payload, dict):
            raise ResearchSynthesisValidationError("research payload must be a JSON object")
        _required_string(payload, "summary")
        findings_payload = _required_list(payload, "findings")
        if not findings_payload:
            raise ResearchSynthesisValidationError("findings must contain at least one item")
        for item in findings_payload:
            if not isinstance(item, dict):
                raise ResearchSynthesisValidationError("research finding entries must be objects")
            _required_string(item, "text")
            source_refs = _required_string_list(item, "source_refs")
            if not source_refs:
                raise ResearchSynthesisValidationError("research synthesis findings must keep at least one source_ref")
        _required_string_list(payload, "inferences")
        _required_string_list(payload, "uncertainties")
        _optional_string(payload.get("recommendation"), field_name="recommendation")
        return payload
    except (TypeError, ValueError) as exc:
        raise ResearchSynthesisValidationError(str(exc)) from exc


def _rewrite_source_identifiers(text: str, source_id_to_citation_key: dict[str, str]) -> str:
    rewritten = text
    for source_id, citation_key in sorted(source_id_to_citation_key.items(), key=lambda item: len(item[0]), reverse=True):
        rewritten = rewritten.replace(source_id, citation_key)
    return rewritten
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
