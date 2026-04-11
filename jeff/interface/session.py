"""Local CLI session scope and display mode state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OutputMode = Literal["compact", "debug"]


def _normalize_optional(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string or None")
    normalized = value.strip()
    return normalized or None


@dataclass(frozen=True, slots=True)
class SessionScope:
    project_id: str | None = None
    work_unit_id: str | None = None
    run_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _normalize_optional(self.project_id, field_name="project_id"))
        object.__setattr__(self, "work_unit_id", _normalize_optional(self.work_unit_id, field_name="work_unit_id"))
        object.__setattr__(self, "run_id", _normalize_optional(self.run_id, field_name="run_id"))

        if self.project_id is None and (self.work_unit_id is not None or self.run_id is not None):
            raise ValueError("work_unit_id and run_id require project_id in session scope")
        if self.work_unit_id is None and self.run_id is not None:
            raise ValueError("run_id requires work_unit_id in session scope")


@dataclass(frozen=True, slots=True)
class CliSession:
    scope: SessionScope = SessionScope()
    output_mode: OutputMode = "compact"
    json_output: bool = False

    @property
    def prompt(self) -> str:
        project = self.scope.project_id or ""
        work_unit = self.scope.work_unit_id or ""
        base = f"jeff:/{project}/{work_unit}>".replace("//", "/")
        return base if base != "jeff:/>" else "jeff:/>"

    def with_scope(self, *, project_id: str | None, work_unit_id: str | None, run_id: str | None) -> "CliSession":
        return CliSession(
            scope=SessionScope(project_id=project_id, work_unit_id=work_unit_id, run_id=run_id),
            output_mode=self.output_mode,
            json_output=self.json_output,
        )

    def clear_scope(self) -> "CliSession":
        return self.with_scope(project_id=None, work_unit_id=None, run_id=None)

    def with_mode(self, output_mode: OutputMode) -> "CliSession":
        return CliSession(scope=self.scope, output_mode=output_mode, json_output=self.json_output)

    def with_json_output(self, enabled: bool) -> "CliSession":
        return CliSession(scope=self.scope, output_mode=self.output_mode, json_output=enabled)
