"""Stable output strategy vocabulary for typed LLM stages.

An output strategy describes *how* a model invocation's output will be
obtained and post-processed. This is a technical routing concept owned by
Infrastructure. It does not describe what the output means to any domain layer.
"""

from __future__ import annotations

from enum import Enum


class OutputStrategy(str, Enum):
    """Technical output strategies for model invocations.

    ``PLAIN_TEXT``
        Model output is used as-is. No structured post-processing applied.

    ``BOUNDED_TEXT_THEN_PARSE``
        Model is prompted to emit delimited text; the delimiter-bounded
        region is extracted and then parsed into a structured form.
        Corresponds to the Step 1 → Step 2 path in the research pipeline.

    ``BOUNDED_TEXT_THEN_FORMATTER``
        Model is prompted to emit delimited text; on parse failure the
        output falls back to a formatter rather than hard-failing.
        Corresponds to the Step 1 → Step 2 → Step 3 fallback path.
    """

    PLAIN_TEXT = "plain_text"
    BOUNDED_TEXT_THEN_PARSE = "bounded_text_then_parse"
    BOUNDED_TEXT_THEN_FORMATTER = "bounded_text_then_formatter"

    def has_formatter_fallback(self) -> bool:
        """Return True if this strategy includes a formatter fallback path."""
        return self == OutputStrategy.BOUNDED_TEXT_THEN_FORMATTER

    def requires_delimiter_extraction(self) -> bool:
        """Return True if this strategy requires bounded-text extraction."""
        return self in (
            OutputStrategy.BOUNDED_TEXT_THEN_PARSE,
            OutputStrategy.BOUNDED_TEXT_THEN_FORMATTER,
        )
