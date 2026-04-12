"""Research-domain contracts."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Literal

from jeff.core.schemas import Scope

from ..types import normalize_text_list, require_text
from .errors import ResearchProvenanceValidationError

ResearchMode = Literal["direct_output", "decision_support"]


@dataclass(frozen=True, slots=True)
class ResearchRequest:
    question: str | None = None
    project_id: str | None = None
    work_unit_id: str | None = None
    run_id: str | None = None
    constraints: tuple[str, ...] = ()
    source_mode: str = "prepared_evidence"
    document_paths: tuple[str, ...] = ()
    include_extensions: tuple[str, ...] = ()
    max_files: int = 20
    max_chars_per_file: int = 8000
    max_evidence_items: int = 20
    web_queries: tuple[str, ...] = ()
    max_web_results: int = 10
    max_web_pages: int = 5
    max_chars_per_page: int = 12000
    max_web_evidence_items: int | None = None
    _legacy_research_mode: ResearchMode = field(init=False, repr=False)
    objective: InitVar[str | None] = None
    scope: InitVar[Scope | None] = None
    research_mode: InitVar[ResearchMode | None] = None

    def __post_init__(
        self,
        objective: str | None,
        scope: Scope | None,
        research_mode: ResearchMode | None,
    ) -> None:
        if isinstance(objective, property):
            objective = None
        if isinstance(scope, property):
            scope = None
        if isinstance(research_mode, property):
            research_mode = None

        question = self.question if self.question is not None else objective
        if question is None:
            raise ValueError("research request requires question or objective")

        object.__setattr__(self, "question", require_text(question, field_name="question"))
        object.__setattr__(self, "constraints", normalize_text_list(self.constraints, field_name="constraints"))
        object.__setattr__(self, "source_mode", require_text(self.source_mode, field_name="source_mode"))
        object.__setattr__(self, "document_paths", normalize_text_list(self.document_paths, field_name="document_paths"))
        object.__setattr__(self, "web_queries", normalize_text_list(self.web_queries, field_name="web_queries"))
        object.__setattr__(
            self,
            "include_extensions",
            tuple(_normalize_extension(extension) for extension in self.include_extensions),
        )

        if self.project_id is not None:
            object.__setattr__(self, "project_id", require_text(self.project_id, field_name="project_id"))
        if self.work_unit_id is not None:
            object.__setattr__(self, "work_unit_id", require_text(self.work_unit_id, field_name="work_unit_id"))
        if self.run_id is not None:
            object.__setattr__(self, "run_id", require_text(self.run_id, field_name="run_id"))

        if scope is not None:
            if self.project_id is None and scope.project_id is not None:
                object.__setattr__(self, "project_id", str(scope.project_id))
            if self.work_unit_id is None and scope.work_unit_id is not None:
                object.__setattr__(self, "work_unit_id", str(scope.work_unit_id))
            if self.run_id is None and scope.run_id is not None:
                object.__setattr__(self, "run_id", str(scope.run_id))

        if self.max_files <= 0:
            raise ValueError("max_files must be greater than zero")
        if self.max_chars_per_file <= 0:
            raise ValueError("max_chars_per_file must be greater than zero")
        if self.max_evidence_items <= 0:
            raise ValueError("max_evidence_items must be greater than zero")
        if self.max_web_results <= 0:
            raise ValueError("max_web_results must be greater than zero")
        if self.max_web_pages <= 0:
            raise ValueError("max_web_pages must be greater than zero")
        if self.max_chars_per_page <= 0:
            raise ValueError("max_chars_per_page must be greater than zero")
        if self.max_web_evidence_items is not None and self.max_web_evidence_items <= 0:
            raise ValueError("max_web_evidence_items must be greater than zero when provided")

        object.__setattr__(self, "_legacy_research_mode", research_mode or "direct_output")

    @property
    def objective(self) -> str:
        return self.question

    @property
    def scope(self) -> Scope:
        return Scope(
            project_id=self.project_id,
            work_unit_id=self.work_unit_id,
            run_id=self.run_id,
        )

    @property
    def research_mode(self) -> ResearchMode:
        return getattr(self, "_legacy_research_mode")


@dataclass(frozen=True, slots=True)
class SourceItem:
    source_id: str
    source_type: str
    title: str | None = None
    locator: str | None = None
    snippet: str | None = None
    published_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", require_text(self.source_id, field_name="source_id"))
        object.__setattr__(self, "source_type", require_text(self.source_type, field_name="source_type"))
        if self.title is not None:
            object.__setattr__(self, "title", require_text(self.title, field_name="title"))
        if self.locator is not None:
            object.__setattr__(self, "locator", require_text(self.locator, field_name="locator"))
        if self.snippet is not None:
            object.__setattr__(self, "snippet", require_text(self.snippet, field_name="snippet"))
        if self.published_at is not None:
            object.__setattr__(self, "published_at", require_text(self.published_at, field_name="published_at"))


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    text: str
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", require_text(self.text, field_name="text"))
        object.__setattr__(self, "source_refs", normalize_text_list(self.source_refs, field_name="source_refs"))
        if not self.source_refs:
            raise ValueError("evidence items must keep at least one source_ref")


@dataclass(frozen=True, slots=True)
class EvidencePack:
    question: str
    sources: tuple[SourceItem, ...]
    evidence_items: tuple[EvidenceItem, ...]
    contradictions: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "question", require_text(self.question, field_name="question"))
        object.__setattr__(
            self,
            "contradictions",
            normalize_text_list(self.contradictions, field_name="contradictions"),
        )
        object.__setattr__(
            self,
            "uncertainties",
            normalize_text_list(self.uncertainties, field_name="uncertainties"),
        )
        object.__setattr__(self, "constraints", normalize_text_list(self.constraints, field_name="constraints"))

        source_ids = {source.source_id for source in self.sources}
        if not source_ids:
            raise ValueError("evidence pack requires at least one source")
        if len(source_ids) != len(self.sources):
            raise ValueError("evidence pack source ids must be unique")

        for evidence_item in self.evidence_items:
            missing = [source_id for source_id in evidence_item.source_refs if source_id not in source_ids]
            if missing:
                raise ValueError(f"evidence item references unknown source ids: {missing}")


@dataclass(frozen=True, slots=True)
class ResearchFinding:
    text: str
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", require_text(self.text, field_name="text"))
        object.__setattr__(self, "source_refs", normalize_text_list(self.source_refs, field_name="source_refs"))
        if not self.source_refs:
            raise ValueError("research synthesis findings must keep at least one source_ref")


@dataclass(frozen=True, slots=True)
class ResearchArtifact:
    question: str
    summary: str
    findings: tuple[ResearchFinding, ...]
    inferences: tuple[str, ...]
    uncertainties: tuple[str, ...]
    recommendation: str | None
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "question", require_text(self.question, field_name="question"))
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
        object.__setattr__(self, "inferences", normalize_text_list(self.inferences, field_name="inferences"))
        object.__setattr__(
            self,
            "uncertainties",
            normalize_text_list(self.uncertainties, field_name="uncertainties"),
        )
        object.__setattr__(self, "source_ids", normalize_text_list(self.source_ids, field_name="source_ids"))
        if self.recommendation is not None:
            object.__setattr__(
                self,
                "recommendation",
                require_text(self.recommendation, field_name="recommendation"),
            )
        if not self.findings:
            raise ValueError("research artifact requires at least one finding")
        if not self.source_ids:
            raise ValueError("research artifact requires at least one source_id")


def validate_research_provenance(
    *,
    findings: tuple[ResearchFinding, ...],
    source_ids: tuple[str, ...],
    source_items: tuple[SourceItem, ...],
    evidence_items: tuple[EvidenceItem, ...] = (),
) -> None:
    known_source_ids: set[str] = set()
    duplicate_source_ids: set[str] = set()
    for source in source_items:
        source_id = require_text(source.source_id, field_name="source_id")
        if source_id in known_source_ids:
            duplicate_source_ids.add(source_id)
        known_source_ids.add(source_id)

    if duplicate_source_ids:
        duplicates = sorted(duplicate_source_ids)
        raise ResearchProvenanceValidationError(
            f"research provenance contains duplicate source ids: {duplicates}",
        )
    if not known_source_ids:
        raise ResearchProvenanceValidationError("research provenance requires at least one source item")

    for finding in findings:
        _validate_source_refs(finding.source_refs, known_source_ids=known_source_ids, owner_label="finding")

    for evidence_item in evidence_items:
        _validate_source_refs(
            evidence_item.source_refs,
            known_source_ids=known_source_ids,
            owner_label="evidence item",
        )

    for source_id in source_ids:
        normalized_source_id = require_text(source_id, field_name="source_ids")
        if normalized_source_id not in known_source_ids:
            raise ResearchProvenanceValidationError(
                f"research provenance lists unknown source id: {normalized_source_id}",
            )


def _validate_source_refs(
    source_refs: tuple[str, ...],
    *,
    known_source_ids: set[str],
    owner_label: str,
) -> None:
    if not source_refs:
        raise ResearchProvenanceValidationError(f"{owner_label} must keep at least one source_ref")
    for source_ref in source_refs:
        normalized_source_ref = require_text(source_ref, field_name="source_refs")
        if normalized_source_ref not in known_source_ids:
            raise ResearchProvenanceValidationError(
                f"{owner_label} references unknown source ids: {normalized_source_ref}",
            )


def _normalize_extension(value: str) -> str:
    normalized = require_text(value, field_name="include_extensions").lower()
    if not normalized.startswith("."):
        normalized = f".{normalized}"
    return normalized
