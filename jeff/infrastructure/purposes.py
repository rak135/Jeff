"""Stable purpose vocabulary for infrastructure-owned routing surfaces.

Purposes are technical routing labels used to select model adapters and
configure runtime behavior. They do not carry semantic meaning about what
a finding, proposal, or evaluation *is* — that belongs to domain layers.
"""

from __future__ import annotations

from enum import Enum


class Purpose(str, Enum):
    """Stable names for adapter routing purposes.

    Each value matches the string key used in PurposeOverrides and
    runtime config so callers can use the enum without string literals.
    """

    RESEARCH = "research"
    FORMATTER_BRIDGE = "formatter_bridge"
    PROPOSAL = "proposal"
    SELECTION = "selection"
    PLANNING = "planning"
    EVALUATION = "evaluation"

    @classmethod
    def known_names(cls) -> frozenset[str]:
        """Return the set of known purpose string values."""
        return frozenset(member.value for member in cls)
