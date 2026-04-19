"""Governed execution entry and execution result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import sys

from jeff.contracts import Action
from jeff.governance import ActionEntryDecision

from .types import ExecutionStatus, SupportRef, normalize_text_list, require_text


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_optional_text(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return require_text(value, field_name=field_name)


def _truncate_output(text: str | None, *, max_length: int = 400) -> str | None:
    if text is None:
        return None
    normalized = text.strip()
    if not normalized:
        return None
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


@dataclass(frozen=True, slots=True)
class RepoLocalValidationPlan:
    command_id: str
    argv: tuple[str, ...]
    working_directory: str
    description: str
    timeout_seconds: int = 180
    success_exit_codes: tuple[int, ...] = (0,)

    def __post_init__(self) -> None:
        object.__setattr__(self, "command_id", require_text(self.command_id, field_name="command_id"))
        object.__setattr__(self, "description", require_text(self.description, field_name="description"))
        if not self.argv:
            raise ValueError("argv must include at least one command token")
        object.__setattr__(
            self,
            "argv",
            tuple(require_text(token, field_name="argv") for token in self.argv),
        )
        object.__setattr__(
            self,
            "working_directory",
            str(Path(require_text(self.working_directory, field_name="working_directory"))),
        )
        if not isinstance(self.timeout_seconds, int):
            raise TypeError("timeout_seconds must be an integer")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if not self.success_exit_codes:
            raise ValueError("success_exit_codes must include at least one exit code")
        object.__setattr__(self, "success_exit_codes", tuple(int(code) for code in self.success_exit_codes))

    @property
    def display_command(self) -> str:
        return subprocess.list2cmdline(list(self.argv))


@dataclass(frozen=True, slots=True)
class GovernedExecutionRequest:
    action: Action
    governance_decision: ActionEntryDecision

    def __post_init__(self) -> None:
        if not isinstance(self.action, Action):
            raise TypeError("execution requires a bounded Action")
        if not isinstance(self.governance_decision, ActionEntryDecision):
            raise TypeError("execution requires an ActionEntryDecision governance pass")
        if not self.governance_decision.allowed_now:
            raise ValueError("execution may begin only when governance allowed_now is true")
        if self.governance_decision.governance_outcome != "allowed_now":
            raise ValueError("execution requires an allowed_now governance outcome")
        if self.governance_decision.action_id != str(self.action.action_id):
            raise ValueError("governance decision does not match the action_id being executed")
        if self.governance_decision.action_binding_key != self.action.binding_key:
            raise ValueError("governance decision does not bind to this exact bounded action")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    governed_request: GovernedExecutionRequest
    execution_status: ExecutionStatus
    output_summary: str | None = None
    artifact_refs: tuple[SupportRef, ...] = ()
    trace_refs: tuple[SupportRef, ...] = ()
    observed_side_effect_notes: tuple[str, ...] = ()
    execution_errors: tuple[str, ...] = ()
    execution_warnings: tuple[str, ...] = ()
    started_at: str | None = None
    ended_at: str | None = None
    execution_family: str | None = None
    execution_command_id: str | None = None
    executed_command: str | None = None
    working_directory: str | None = None
    exit_code: int | None = None
    stdout_excerpt: str | None = None
    stderr_excerpt: str | None = None

    def __post_init__(self) -> None:
        if self.output_summary is not None:
            object.__setattr__(
                self,
                "output_summary",
                require_text(self.output_summary, field_name="output_summary"),
            )
        object.__setattr__(
            self,
            "observed_side_effect_notes",
            normalize_text_list(
                self.observed_side_effect_notes,
                field_name="observed_side_effect_notes",
            ),
        )
        object.__setattr__(
            self,
            "execution_errors",
            normalize_text_list(self.execution_errors, field_name="execution_errors"),
        )
        object.__setattr__(
            self,
            "execution_warnings",
            normalize_text_list(self.execution_warnings, field_name="execution_warnings"),
        )
        object.__setattr__(
            self,
            "execution_family",
            _normalize_optional_text(self.execution_family, field_name="execution_family"),
        )
        object.__setattr__(
            self,
            "execution_command_id",
            _normalize_optional_text(self.execution_command_id, field_name="execution_command_id"),
        )
        object.__setattr__(
            self,
            "executed_command",
            _normalize_optional_text(self.executed_command, field_name="executed_command"),
        )
        object.__setattr__(
            self,
            "working_directory",
            _normalize_optional_text(self.working_directory, field_name="working_directory"),
        )
        object.__setattr__(
            self,
            "stdout_excerpt",
            _normalize_optional_text(self.stdout_excerpt, field_name="stdout_excerpt"),
        )
        object.__setattr__(
            self,
            "stderr_excerpt",
            _normalize_optional_text(self.stderr_excerpt, field_name="stderr_excerpt"),
        )
        if self.exit_code is not None and not isinstance(self.exit_code, int):
            raise TypeError("exit_code must be an integer or None")

        for ref in self.artifact_refs:
            if ref.ref_type != "artifact":
                raise ValueError("artifact_refs may contain only artifact support refs")
        for ref in self.trace_refs:
            if ref.ref_type != "trace":
                raise ValueError("trace_refs may contain only trace support refs")

    @property
    def action_id(self) -> str:
        return str(self.governed_request.action.action_id)

    @property
    def scope(self):
        return self.governed_request.action.scope


def execute_governed_action(
    request: GovernedExecutionRequest,
    *,
    output_summary: str | None = None,
    execution_status: ExecutionStatus = "completed",
    execution_plan: RepoLocalValidationPlan | None = None,
) -> ExecutionResult:
    """Execute or record the current bounded governed action result."""

    if not isinstance(request, GovernedExecutionRequest):
        raise TypeError("execution requires a GovernedExecutionRequest")

    if execution_plan is not None:
        return _execute_repo_local_validation_plan(
            request,
            execution_plan=execution_plan,
            output_summary=output_summary,
        )

    return ExecutionResult(
        governed_request=request,
        execution_status=execution_status,
        output_summary=output_summary,
    )


def _execute_repo_local_validation_plan(
    request: GovernedExecutionRequest,
    *,
    execution_plan: RepoLocalValidationPlan,
    output_summary: str | None,
) -> ExecutionResult:
    started_at = _utc_timestamp()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTEST_CURRENT_TEST", None)

    try:
        completed = subprocess.run(
            execution_plan.argv,
            cwd=execution_plan.working_directory,
            capture_output=True,
            text=True,
            timeout=execution_plan.timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_excerpt = _truncate_output(exc.stdout)
        stderr_excerpt = _truncate_output(exc.stderr)
        ended_at = _utc_timestamp()
        return ExecutionResult(
            governed_request=request,
            execution_status="interrupted",
            output_summary=(
                output_summary
                or f"repo-local validation {execution_plan.command_id} timed out after {execution_plan.timeout_seconds}s"
            ),
            execution_errors=(f"timed out after {execution_plan.timeout_seconds}s",),
            started_at=started_at,
            ended_at=ended_at,
            execution_family="repo_local_validation",
            execution_command_id=execution_plan.command_id,
            executed_command=execution_plan.display_command,
            working_directory=execution_plan.working_directory,
            stdout_excerpt=stdout_excerpt,
            stderr_excerpt=stderr_excerpt,
        )
    except OSError as exc:
        ended_at = _utc_timestamp()
        return ExecutionResult(
            governed_request=request,
            execution_status="failed",
            output_summary=output_summary or f"repo-local validation {execution_plan.command_id} could not start",
            execution_errors=(str(exc),),
            started_at=started_at,
            ended_at=ended_at,
            execution_family="repo_local_validation",
            execution_command_id=execution_plan.command_id,
            executed_command=execution_plan.display_command,
            working_directory=execution_plan.working_directory,
        )

    ended_at = _utc_timestamp()
    stdout_excerpt = _truncate_output(completed.stdout)
    stderr_excerpt = _truncate_output(completed.stderr)
    succeeded = completed.returncode in execution_plan.success_exit_codes
    resolved_status: ExecutionStatus = "completed" if succeeded else "failed"
    resolved_summary = output_summary or (
        f"repo-local validation {execution_plan.command_id} exited with code {completed.returncode}"
    )

    errors: tuple[str, ...] = ()
    if not succeeded:
        error_summary = stderr_excerpt or stdout_excerpt or f"process exited with code {completed.returncode}"
        errors = (error_summary,)

    warnings: tuple[str, ...] = ()
    if succeeded and stderr_excerpt is not None:
        warnings = (stderr_excerpt,)

    return ExecutionResult(
        governed_request=request,
        execution_status=resolved_status,
        output_summary=resolved_summary,
        execution_errors=errors,
        execution_warnings=warnings,
        started_at=started_at,
        ended_at=ended_at,
        execution_family="repo_local_validation",
        execution_command_id=execution_plan.command_id,
        executed_command=execution_plan.display_command,
        working_directory=execution_plan.working_directory,
        exit_code=completed.returncode,
        stdout_excerpt=stdout_excerpt,
        stderr_excerpt=stderr_excerpt,
    )
