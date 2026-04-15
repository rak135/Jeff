"""Thin reusable contract runtime surface for strategy-aware LLM calls.

Provides a small, purpose-aware, strategy-aware entrypoint for invoking model
adapters. Domain layers (Research, Proposal, Evaluation) use this surface to
run LLM calls without directly constructing ModelRequest objects.

This module does NOT:
- own what findings, inferences, or uncertainties mean
- own formatter fallback logic
- own deterministic parsing
- own research / proposal / evaluation semantics
- enforce any output post-processing

The response is always a raw ModelResponse. Callers are responsible for
interpreting the output according to their domain contracts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from .model_adapters.types import ModelRequest, ModelResponse, ModelResponseMode
from .output_strategies import OutputStrategy
from .purposes import Purpose

if TYPE_CHECKING:
    from .runtime import InfrastructureServices


def _resolve_purpose_string(purpose: str | Purpose) -> str:
    """Normalize a purpose argument to a plain string adapter routing key."""
    if isinstance(purpose, Purpose):
        return purpose.value
    return str(purpose)


def _strategy_to_response_mode(strategy: OutputStrategy) -> ModelResponseMode:
    """Return the ModelResponseMode that corresponds to an OutputStrategy.

    All current strategies use TEXT mode at the adapter level:
    - PLAIN_TEXT: text output used as-is
    - BOUNDED_TEXT_THEN_PARSE: model emits delimited text (still TEXT mode)
    - BOUNDED_TEXT_THEN_FORMATTER: model emits delimited text with fallback (still TEXT mode)

    If a future strategy requires native JSON-mode adapter enforcement, a new
    branch should be added here at that time.
    """
    _ = strategy  # all strategies → TEXT today; kept explicit for future extension
    return ModelResponseMode.TEXT


@dataclass(frozen=True, slots=True)
class ContractCallRequest:
    """Thin, validated call descriptor for a single strategy-aware LLM invocation.

    Attributes
    ----------
    purpose:
        Routing purpose. Accepts a ``Purpose`` enum or a raw string for
        backwards compatibility with existing callers.
    output_strategy:
        The output strategy for this call. Informs adapter mode selection
        and is surfaced to callers for post-processing decisions.
    prompt:
        The user-facing prompt text.
    system_instructions:
        Optional system-level instructions to prepend. None means no system prompt.
    request_id:
        Stable caller-supplied ID for tracing. Auto-generated (UUID4) if None.
    project_id:
        Optional project scope for tracing/telemetry.
    work_unit_id:
        Optional work unit scope for tracing/telemetry.
    run_id:
        Optional run ID for tracing/telemetry.
    timeout_seconds:
        Per-call timeout override. None means use the adapter default.
    max_output_tokens:
        Optional output token cap. None means no cap.
    metadata:
        Caller-supplied key/value metadata forwarded to the ModelRequest.
    """

    purpose: str | Purpose
    output_strategy: OutputStrategy
    prompt: str
    system_instructions: str | None = None
    request_id: str | None = None
    project_id: str | None = None
    work_unit_id: str | None = None
    run_id: str | None = None
    timeout_seconds: int | None = None
    max_output_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.output_strategy, OutputStrategy):
            raise TypeError("output_strategy must be an OutputStrategy")
        prompt = self.prompt
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero when provided")
        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be greater than zero when provided")


class ContractRuntime:
    """Thin runtime entrypoint for purpose-aware, strategy-aware LLM calls.

    Wraps ``InfrastructureServices`` to provide a single ``invoke`` method
    that handles:
    - purpose → adapter selection (via existing InfrastructureServices routing)
    - output strategy → ModelResponseMode mapping
    - request_id generation when not caller-supplied
    - ModelRequest construction
    - adapter invocation

    Does not interpret, transform, or validate the response content.
    """

    def __init__(self, services: InfrastructureServices) -> None:
        self._services = services

    def invoke(self, call: ContractCallRequest) -> ModelResponse:
        """Invoke the appropriate adapter for *call* and return the raw response.

        Parameters
        ----------
        call:
            The call descriptor. ``purpose`` selects the adapter;
            ``output_strategy`` selects the response mode.

        Returns
        -------
        ModelResponse
            Raw response from the adapter. The caller is responsible for all
            domain-level post-processing.
        """
        purpose_str = _resolve_purpose_string(call.purpose)
        adapter = self._services.get_adapter_for_purpose(purpose_str)
        request_id = call.request_id or str(uuid.uuid4())
        request = ModelRequest(
            request_id=request_id,
            project_id=call.project_id,
            work_unit_id=call.work_unit_id,
            run_id=call.run_id,
            purpose=purpose_str,
            prompt=call.prompt,
            system_instructions=call.system_instructions,
            response_mode=_strategy_to_response_mode(call.output_strategy),
            json_schema=None,
            timeout_seconds=call.timeout_seconds,
            max_output_tokens=call.max_output_tokens,
            reasoning_effort=None,
            metadata=dict(call.metadata),
        )
        return adapter.invoke(request)

    def invoke_with_request(self, request: ModelRequest, *, adapter_id: str) -> ModelResponse:
        """Dispatch a pre-built ModelRequest via a specific adapter ID.

        For callers that construct full ModelRequest objects before dispatch —
        for example, the research layer which needs fields (reasoning_effort,
        JSON schema) not yet exposed by ContractCallRequest. The request is
        forwarded as-is; ContractRuntime handles only the adapter lookup.

        Parameters
        ----------
        request:
            A fully constructed ModelRequest.
        adapter_id:
            The ID of the adapter to use. Must be registered in the registry.
        """
        adapter = self._services.get_model_adapter(adapter_id)
        return adapter.invoke(request)

    def invoke_with_adapter(self, call: ContractCallRequest, *, adapter_id: str) -> ModelResponse:
        """Invoke a specific adapter by ID rather than purpose routing.

        Useful for repair / retry paths where the caller has already resolved
        which adapter to use. Does not bypass the registry — the adapter_id
        must still be registered.

        Parameters
        ----------
        call:
            The call descriptor. ``purpose`` is still forwarded to the request
            for tracing, but does not influence adapter selection here.
        adapter_id:
            The explicit adapter to use.
        """
        adapter = self._services.get_model_adapter(adapter_id)
        purpose_str = _resolve_purpose_string(call.purpose)
        request_id = call.request_id or str(uuid.uuid4())
        request = ModelRequest(
            request_id=request_id,
            project_id=call.project_id,
            work_unit_id=call.work_unit_id,
            run_id=call.run_id,
            purpose=purpose_str,
            prompt=call.prompt,
            system_instructions=call.system_instructions,
            response_mode=_strategy_to_response_mode(call.output_strategy),
            json_schema=None,
            timeout_seconds=call.timeout_seconds,
            max_output_tokens=call.max_output_tokens,
            reasoning_effort=None,
            metadata=dict(call.metadata),
        )
        return adapter.invoke(request)
