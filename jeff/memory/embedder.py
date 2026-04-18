"""Vector embedding protocol and implementations for semantic memory retrieval.

VectorEmbedder converts text to a fixed-dimension float vector.
HashEmbedder is deterministic and requires no external API — suitable for tests
and environments without an embedding service.  NullEmbedder produces zero vectors
and effectively disables semantic retrieval.

Production deployments should provide an embedder that calls a real model or API.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol, runtime_checkable


@runtime_checkable
class VectorEmbedder(Protocol):
    """Protocol for text-to-vector embedding."""

    @property
    def dimension(self) -> int:
        """Return the embedding vector dimension."""
        ...

    def embed(self, text: str) -> list[float]:
        """Return a unit-norm float vector for the given text."""
        ...


class NullEmbedder:
    """Returns zero vectors. Semantic retrieval will always return empty results."""

    dimension: int = 64

    def embed(self, text: str) -> list[float]:
        return [0.0] * self.dimension


class HashEmbedder:
    """Deterministic character-bigram hash embedding.

    Produces a consistent unit-norm vector from text using a hashing trick on
    character bigrams.  Semantically unrelated texts that share bigrams will appear
    similar, so this is NOT suitable for production semantic retrieval.  Use only
    for tests or as a stand-in when no real model is available.
    """

    dimension: int = 64

    def embed(self, text: str) -> list[float]:
        normalized = text.lower().strip()
        vector = [0.0] * self.dimension
        for i in range(len(normalized) - 1):
            bigram = normalized[i : i + 2]
            h = int(hashlib.md5(bigram.encode(), usedforsecurity=False).hexdigest(), 16)
            vector[h % self.dimension] += 1.0
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        return vector
