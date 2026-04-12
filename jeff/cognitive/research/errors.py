"""Research-specific synthesis errors."""


class ResearchSynthesisError(Exception):
    """Research synthesis failed closed."""


class ResearchSynthesisValidationError(ResearchSynthesisError):
    """Research synthesis output failed validation."""


class ResearchProvenanceValidationError(ResearchSynthesisValidationError):
    """Research provenance linkage failed validation."""


class ResearchSynthesisRuntimeError(ResearchSynthesisError):
    """Research synthesis failed at the adapter/runtime invocation boundary."""

    def __init__(
        self,
        *,
        failure_class: str,
        reason: str,
        adapter_id: str | None = None,
        provider_name: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        research_mode: str | None = None,
        project_id: str | None = None,
        work_unit_id: str | None = None,
        run_id: str | None = None,
    ) -> None:
        self.failure_class = failure_class
        self.reason = _bounded_reason(reason)
        self.adapter_id = adapter_id
        self.provider_name = provider_name
        self.model_name = model_name
        self.base_url = base_url
        self.research_mode = research_mode
        self.project_id = project_id
        self.work_unit_id = work_unit_id
        self.run_id = run_id
        super().__init__(self.operator_message)

    @property
    def operator_message(self) -> str:
        details: list[str] = []
        if self.provider_name:
            details.append(f"provider={self.provider_name}")
        if self.adapter_id:
            details.append(f"adapter={self.adapter_id}")
        if self.model_name:
            details.append(f"model={self.model_name}")
        if self.base_url:
            details.append(f"base_url={self.base_url}")
        if self.reason:
            details.append(f"reason={self.reason}")
        suffix = f" ({' '.join(details)})" if details else ""
        return f"research synthesis failed: {self.failure_class}{suffix}"

    def with_context(
        self,
        *,
        research_mode: str | None,
        project_id: str | None,
        work_unit_id: str | None,
        run_id: str | None,
    ) -> "ResearchSynthesisRuntimeError":
        return ResearchSynthesisRuntimeError(
            failure_class=self.failure_class,
            reason=self.reason,
            adapter_id=self.adapter_id,
            provider_name=self.provider_name,
            model_name=self.model_name,
            base_url=self.base_url,
            research_mode=research_mode,
            project_id=project_id,
            work_unit_id=work_unit_id,
            run_id=run_id,
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "error_code": self.failure_class,
            "message": self.operator_message,
            "reason": self.reason,
            "provider_name": self.provider_name,
            "adapter_id": self.adapter_id,
            "model_name": self.model_name,
            "base_url": self.base_url,
        }


def _bounded_reason(message: str, *, max_chars: int = 180) -> str:
    normalized = " ".join(message.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 3].rstrip()}..."
