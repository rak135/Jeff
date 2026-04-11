"""Adapter-layer exceptions."""


class ModelAdapterError(Exception):
    """Base adapter-layer failure."""


class ModelAdapterNotFoundError(ModelAdapterError):
    """Requested adapter is not registered."""


class ModelInvocationError(ModelAdapterError):
    """Adapter invocation failed."""


class ModelTimeoutError(ModelInvocationError):
    """Adapter invocation timed out."""


class ModelMalformedOutputError(ModelInvocationError):
    """Adapter returned output that could not satisfy the requested shape."""
