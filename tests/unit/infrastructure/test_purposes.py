"""Unit tests for jeff.infrastructure.purposes."""

from jeff.infrastructure.purposes import Purpose


def test_purpose_values_match_config_strings() -> None:
    """Enum values must match the string keys used in PurposeOverrides."""
    assert Purpose.RESEARCH.value == "research"
    assert Purpose.FORMATTER_BRIDGE.value == "formatter_bridge"
    assert Purpose.PROPOSAL.value == "proposal"
    assert Purpose.SELECTION.value == "selection"
    assert Purpose.PLANNING.value == "planning"
    assert Purpose.EVALUATION.value == "evaluation"


def test_known_names_returns_all_purpose_strings() -> None:
    known = Purpose.known_names()
    assert known == {"research", "formatter_bridge", "proposal", "selection", "planning", "evaluation"}


def test_purpose_is_str_subclass_so_it_works_as_string_key() -> None:
    assert Purpose.RESEARCH == "research"
    assert Purpose.FORMATTER_BRIDGE == "formatter_bridge"
    assert Purpose.SELECTION == "selection"


def test_purpose_from_value_roundtrip() -> None:
    for member in Purpose:
        assert Purpose(member.value) is member
