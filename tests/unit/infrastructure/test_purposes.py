"""Unit tests for jeff.infrastructure.purposes."""

from jeff.infrastructure.purposes import Purpose


def test_purpose_values_match_config_strings() -> None:
    """Enum values must match the string keys used in PurposeOverrides."""
    assert Purpose.RESEARCH.value == "research"
    assert Purpose.RESEARCH_REPAIR.value == "research_repair"
    assert Purpose.PROPOSAL.value == "proposal"
    assert Purpose.PLANNING.value == "planning"
    assert Purpose.EVALUATION.value == "evaluation"


def test_known_names_returns_all_purpose_strings() -> None:
    known = Purpose.known_names()
    assert known == {"research", "research_repair", "proposal", "planning", "evaluation"}


def test_purpose_is_str_subclass_so_it_works_as_string_key() -> None:
    assert Purpose.RESEARCH == "research"
    assert Purpose.RESEARCH_REPAIR == "research_repair"


def test_is_repair_variant_only_true_for_research_repair() -> None:
    assert Purpose.RESEARCH_REPAIR.is_repair_variant() is True
    for purpose in (Purpose.RESEARCH, Purpose.PROPOSAL, Purpose.PLANNING, Purpose.EVALUATION):
        assert purpose.is_repair_variant() is False


def test_purpose_from_value_roundtrip() -> None:
    for member in Purpose:
        assert Purpose(member.value) is member
