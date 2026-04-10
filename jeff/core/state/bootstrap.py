"""Bootstrap helpers for the canonical state root."""

from __future__ import annotations

from .models import GlobalState, StateMeta, SystemState


def bootstrap_global_state() -> GlobalState:
    return GlobalState(state_meta=StateMeta(), system=SystemState(), projects={})
