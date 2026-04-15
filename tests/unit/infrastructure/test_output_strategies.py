"""Unit tests for jeff.infrastructure.output_strategies."""

from jeff.infrastructure.output_strategies import OutputStrategy


def test_output_strategy_values_are_stable_strings() -> None:
    assert OutputStrategy.PLAIN_TEXT.value == "plain_text"
    assert OutputStrategy.BOUNDED_TEXT_THEN_PARSE.value == "bounded_text_then_parse"
    assert OutputStrategy.BOUNDED_TEXT_THEN_FORMATTER.value == "bounded_text_then_formatter"


def test_has_formatter_fallback_only_for_formatter_strategy() -> None:
    assert OutputStrategy.BOUNDED_TEXT_THEN_FORMATTER.has_formatter_fallback() is True
    assert OutputStrategy.BOUNDED_TEXT_THEN_PARSE.has_formatter_fallback() is False
    assert OutputStrategy.PLAIN_TEXT.has_formatter_fallback() is False


def test_requires_delimiter_extraction_for_bounded_strategies() -> None:
    assert OutputStrategy.BOUNDED_TEXT_THEN_PARSE.requires_delimiter_extraction() is True
    assert OutputStrategy.BOUNDED_TEXT_THEN_FORMATTER.requires_delimiter_extraction() is True
    assert OutputStrategy.PLAIN_TEXT.requires_delimiter_extraction() is False


def test_output_strategy_is_str_subclass() -> None:
    assert OutputStrategy.PLAIN_TEXT == "plain_text"


def test_output_strategy_from_value_roundtrip() -> None:
    for member in OutputStrategy:
        assert OutputStrategy(member.value) is member
