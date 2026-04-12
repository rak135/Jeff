"""Adapter-layer exceptions."""


class ModelAdapterError(Exception):
    """Base adapter-layer failure."""


class ModelAdapterNotFoundError(ModelAdapterError):
    """Requested adapter is not registered."""


class ModelInvocationError(ModelAdapterError):
    """Adapter invocation failed."""


class ModelTransportError(ModelInvocationError):
    """Adapter transport or connection failed."""


class ModelProviderHTTPError(ModelInvocationError):
    """Adapter received a provider HTTP failure."""


class ModelTimeoutError(ModelInvocationError):
    """Adapter invocation timed out."""


class ModelMalformedOutputError(ModelInvocationError):
    """Adapter returned output that could not satisfy the requested shape."""

    def __init__(self, message: str, *, raw_output: str | None = None) -> None:
        self.raw_output = _bounded_raw_output(raw_output)
        super().__init__(message)


def _bounded_raw_output(value: str | None, *, max_chars: int = 6000) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 3].rstrip()}..."
