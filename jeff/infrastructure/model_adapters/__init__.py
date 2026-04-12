"""Provider-neutral model adapter contracts and registry."""

from .base import ModelAdapter
from .errors import (
    ModelAdapterError,
    ModelAdapterNotFoundError,
    ModelInvocationError,
    ModelMalformedOutputError,
    ModelProviderHTTPError,
    ModelTimeoutError,
    ModelTransportError,
)
from .factory import AdapterFactoryConfig, AdapterProviderKind, create_model_adapter
from .providers import FakeModelAdapter, OllamaModelAdapter
from .registry import AdapterRegistry
from .telemetry import ModelTelemetryEvent, telemetry_from_response
from .types import (
    ModelInvocationStatus,
    ModelRequest,
    ModelResponse,
    ModelResponseMode,
    ModelUsage,
)

__all__ = [
    "AdapterRegistry",
    "AdapterFactoryConfig",
    "AdapterProviderKind",
    "FakeModelAdapter",
    "ModelAdapter",
    "ModelAdapterError",
    "ModelAdapterNotFoundError",
    "ModelInvocationError",
    "ModelInvocationStatus",
    "ModelMalformedOutputError",
    "ModelProviderHTTPError",
    "ModelRequest",
    "ModelResponse",
    "ModelResponseMode",
    "ModelTelemetryEvent",
    "ModelTimeoutError",
    "ModelTransportError",
    "ModelUsage",
    "OllamaModelAdapter",
    "create_model_adapter",
    "telemetry_from_response",
]
