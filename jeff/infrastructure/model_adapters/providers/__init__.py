"""Infrastructure-owned model adapter providers."""

from .fake import FakeModelAdapter
from .ollama import OllamaModelAdapter

__all__ = ["FakeModelAdapter", "OllamaModelAdapter"]
