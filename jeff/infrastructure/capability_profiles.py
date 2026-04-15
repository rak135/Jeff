"""Minimal capability profile vocabulary for model/provider metadata.

A capability profile captures what a model adapter is known to support
at a technical level. This is used as lightweight metadata for future
routing decisions. It does not encode domain semantics.

Deliberately thin: only surface what is needed to make routing decisions.
Do not overbuild before routing logic actually needs it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CapabilityProfile:
    """Immutable capability metadata for a single model/adapter.

    Attributes
    ----------
    adapter_id:
        The adapter this profile describes. Must match a registered adapter.
    supports_structured_output:
        True if the model can be reliably prompted for structured/bounded output.
        Relevant for strategies that require delimiter extraction.
    max_context_tokens:
        Known context window size in tokens, if available. None means unknown.
    provider_kind:
        Provider kind string (e.g. "ollama", "fake"). Matches AdapterProviderKind
        string values for loose cross-reference without a hard import.
    """

    adapter_id: str
    supports_structured_output: bool = True
    max_context_tokens: int | None = None
    provider_kind: str | None = None

    def can_use_strategy(self, strategy_requires_delimiter: bool) -> bool:
        """Return True if this profile is compatible with the given strategy requirement.

        Parameters
        ----------
        strategy_requires_delimiter:
            Pass ``OutputStrategy.requires_delimiter_extraction()`` result here.
        """
        if strategy_requires_delimiter and not self.supports_structured_output:
            return False
        return True


@dataclass(frozen=True, slots=True)
class CapabilityProfileRegistry:
    """Immutable registry of capability profiles keyed by adapter_id.

    Intentionally simple: a thin lookup layer, not a dispatch framework.
    """

    _profiles: tuple[CapabilityProfile, ...] = field(default_factory=tuple)

    def get(self, adapter_id: str) -> CapabilityProfile | None:
        """Return the profile for *adapter_id*, or None if not registered."""
        for profile in self._profiles:
            if profile.adapter_id == adapter_id:
                return profile
        return None

    def with_profile(self, profile: CapabilityProfile) -> "CapabilityProfileRegistry":
        """Return a new registry with *profile* added (or replacing an existing one)."""
        updated = tuple(p for p in self._profiles if p.adapter_id != profile.adapter_id)
        return CapabilityProfileRegistry(_profiles=updated + (profile,))

    def adapter_ids(self) -> frozenset[str]:
        """Return the set of adapter IDs with registered profiles."""
        return frozenset(p.adapter_id for p in self._profiles)
