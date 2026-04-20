"""Transient structured support bundle for proposal generation."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.cognitive.context import ContextPackage
from jeff.cognitive.research.contracts import ResearchArtifact
from jeff.cognitive.types import SupportInput, normalize_text_list, require_text
from jeff.core.schemas import Scope
from jeff.memory import CommittedMemoryRecord
from jeff.memory.api import get_by_id

_GOVERNANCE_BLOCKER_MARKERS = (
    "blocker",
    "blocked",
    "prevent",
    "prevents",
    "prevented",
    "unresolved",
    "unavailable",
    "missing",
    "conflict",
    "contradiction",
    "dependency",
)
_GOVERNANCE_RISK_MARKERS = (
    "risk",
    "risky",
    "regression",
    "failure",
    "fragile",
    "uncertain",
    "uncertainty",
    "drift",
)
_GOVERNANCE_CONSTRAINT_MARKERS = (
    "constraint",
    "limited",
    "limit",
    "must",
    "only",
    "bounded",
    "scope",
    "restricted",
    "not a general",
    "stay inside",
)
_UNCERTAINTY_MARKERS = ("uncertain", "uncertainty", "unknown", "unclear", "not yet known")
_CONTRADICTION_MARKERS = ("contradiction", "contradict", "conflict", "conflicts", "inconsistent")
_MEMORY_RISK_MARKERS = ("risk", "avoid", "watch", "fragile", "regression", "conflict")
_MEMORY_PRECEDENT_MARKERS = ("previous", "prior", "earlier", "precedent", "worked")
_MEMORY_LESSON_MARKERS = ("lesson", "remember", "prefer", "keep", "use", "should")
_EVIDENCE_SUPPORT_LIMIT = 4
_UNCERTAINTY_SUPPORT_LIMIT = 3
_CONTRADICTION_SUPPORT_LIMIT = 2
_GOVERNANCE_BLOCKER_LIMIT = 2
_GOVERNANCE_RISK_LIMIT = 2
_GOVERNANCE_CONSTRAINT_LIMIT = 4
_MEMORY_SUMMARY_LIMIT = 3
_MEMORY_DETAIL_LIMIT = 3


@dataclass(frozen=True, slots=True)
class ProposalRequestFrame:
    objective: str
    trigger_summary: str
    purpose: str
    visible_constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "objective", require_text(self.objective, field_name="objective"))
        object.__setattr__(
            self,
            "trigger_summary",
            require_text(self.trigger_summary, field_name="trigger_summary"),
        )
        object.__setattr__(self, "purpose", require_text(self.purpose, field_name="purpose"))
        object.__setattr__(
            self,
            "visible_constraints",
            normalize_text_list(self.visible_constraints, field_name="visible_constraints"),
        )


@dataclass(frozen=True, slots=True)
class ProposalScopeFrame:
    project_id: str
    work_unit_id: str | None
    run_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", require_text(self.project_id, field_name="project_id"))
        if self.work_unit_id is not None:
            object.__setattr__(self, "work_unit_id", require_text(self.work_unit_id, field_name="work_unit_id"))
        if self.run_id is not None:
            object.__setattr__(self, "run_id", require_text(self.run_id, field_name="run_id"))


@dataclass(frozen=True, slots=True)
class ProposalTruthSnapshotItem:
    source_label: str
    truth_family: str
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_label", require_text(self.source_label, field_name="source_label"))
        object.__setattr__(self, "truth_family", require_text(self.truth_family, field_name="truth_family"))
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))


@dataclass(frozen=True, slots=True)
class ProposalSupportItem:
    source_label: str
    source_family: str
    summary: str
    source_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_label", require_text(self.source_label, field_name="source_label"))
        object.__setattr__(self, "source_family", require_text(self.source_family, field_name="source_family"))
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
        if self.source_id is not None:
            object.__setattr__(self, "source_id", require_text(self.source_id, field_name="source_id"))


@dataclass(frozen=True, slots=True)
class ProposalTruthSnapshot:
    items: tuple[ProposalTruthSnapshotItem, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))


@dataclass(frozen=True, slots=True)
class ProposalSupportSection:
    items: tuple[ProposalSupportItem, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))


@dataclass(frozen=True, slots=True)
class ProposalEvidenceSupport:
    evidence_summaries: tuple[ProposalSupportItem, ...] = ()
    uncertainty_summaries: tuple[ProposalSupportItem, ...] = ()
    contradiction_summaries: tuple[ProposalSupportItem, ...] = ()
    artifact_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_summaries", tuple(self.evidence_summaries))
        object.__setattr__(self, "uncertainty_summaries", tuple(self.uncertainty_summaries))
        object.__setattr__(self, "contradiction_summaries", tuple(self.contradiction_summaries))
        object.__setattr__(self, "artifact_refs", normalize_text_list(self.artifact_refs, field_name="artifact_refs"))


@dataclass(frozen=True, slots=True)
class ProposalMemorySupport:
    memory_ids: tuple[str, ...] = ()
    memory_summaries: tuple[ProposalSupportItem, ...] = ()
    memory_lessons: tuple[ProposalSupportItem, ...] = ()
    memory_risk_reminders: tuple[ProposalSupportItem, ...] = ()
    memory_precedents: tuple[ProposalSupportItem, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory_ids", normalize_text_list(self.memory_ids, field_name="memory_ids"))
        object.__setattr__(self, "memory_summaries", tuple(self.memory_summaries))
        object.__setattr__(self, "memory_lessons", tuple(self.memory_lessons))
        object.__setattr__(self, "memory_risk_reminders", tuple(self.memory_risk_reminders))
        object.__setattr__(self, "memory_precedents", tuple(self.memory_precedents))


@dataclass(frozen=True, slots=True)
class ProposalInputBundle:
    request_frame: ProposalRequestFrame
    scope_frame: ProposalScopeFrame
    truth_snapshot: ProposalTruthSnapshot
    governance_relevant_support: ProposalSupportSection
    current_execution_support: ProposalSupportSection
    evidence_support: ProposalEvidenceSupport
    memory_support: ProposalMemorySupport


def resolve_committed_memory_support_records(
    *,
    project_id: str,
    context_package: ContextPackage,
    store,
) -> tuple[CommittedMemoryRecord, ...]:
    if store is None:
        return ()
    records: list[CommittedMemoryRecord] = []
    seen: set[str] = set()
    for support in context_package.memory_support_inputs:
        if support.source_id is None or support.source_id in seen:
            continue
        record = get_by_id(project_id, support.source_id, store=store)
        if record is None:
            continue
        records.append(record)
        seen.add(str(record.memory_id))
    return tuple(records)


def build_proposal_input_bundle(
    *,
    objective: str,
    scope: Scope,
    context_package: ContextPackage,
    visible_constraints: tuple[str, ...] = (),
    current_execution_support: tuple[str, ...] = (),
    research_artifacts: tuple[ResearchArtifact, ...] = (),
    committed_memory_records: tuple[CommittedMemoryRecord, ...] = (),
) -> ProposalInputBundle:
    if context_package.scope != scope:
        raise ValueError("proposal input bundle requires a scope-matched context package")

    request_frame = ProposalRequestFrame(
        objective=objective,
        trigger_summary=context_package.trigger.trigger_summary,
        purpose=context_package.purpose,
        visible_constraints=visible_constraints,
    )
    scope_frame = ProposalScopeFrame(
        project_id=str(scope.project_id),
        work_unit_id=None if scope.work_unit_id is None else str(scope.work_unit_id),
        run_id=None if scope.run_id is None else str(scope.run_id),
    )
    truth_snapshot = ProposalTruthSnapshot(
        items=tuple(
            ProposalTruthSnapshotItem(
                source_label=f"truth_snapshot:{index}",
                truth_family=record.truth_family,
                summary=record.summary,
            )
            for index, record in enumerate(context_package.truth_records, start=1)
        )
    )
    current_execution_support_section = ProposalSupportSection(
        items=tuple(
            ProposalSupportItem(
                source_label=f"current_execution_support:{index}",
                source_family="execution_support",
                summary=summary,
            )
            for index, summary in enumerate(
                normalize_text_list(current_execution_support, field_name="current_execution_support"),
                start=1,
            )
        )
    )
    evidence_support = _build_evidence_support(
        context_package=context_package,
        research_artifacts=research_artifacts,
    )
    memory_support = _build_memory_support(
        context_package=context_package,
        committed_memory_records=committed_memory_records,
    )
    governance_relevant_support = _build_governance_relevant_support(
        context_package=context_package,
        visible_constraints=request_frame.visible_constraints,
        current_execution_support=current_execution_support_section,
        research_artifacts=research_artifacts,
    )
    return ProposalInputBundle(
        request_frame=request_frame,
        scope_frame=scope_frame,
        truth_snapshot=truth_snapshot,
        governance_relevant_support=governance_relevant_support,
        current_execution_support=current_execution_support_section,
        evidence_support=evidence_support,
        memory_support=memory_support,
    )


def _build_governance_relevant_support(
    *,
    context_package: ContextPackage,
    visible_constraints: tuple[str, ...],
    current_execution_support: ProposalSupportSection,
    research_artifacts: tuple[ResearchArtifact, ...],
) -> ProposalSupportSection:
    items: list[ProposalSupportItem] = []
    seen: set[tuple[str, str]] = set()

    for index, record in enumerate(context_package.governance_truth_records, start=1):
        _append_unique_item(
            items,
            seen,
            ProposalSupportItem(
                source_label=f"governance_truth:{index}",
                source_family="governance_truth",
                summary=record.summary,
            ),
        )
    for index, constraint in enumerate(visible_constraints, start=1):
        _append_unique_item(
            items,
            seen,
            ProposalSupportItem(
                source_label=f"visible_constraint:{index}",
                source_family="visible_constraint",
                summary=constraint,
            ),
        )

    signal_sources: list[ProposalSupportItem] = []
    for support in (
        context_package.support_inputs
        + context_package.compiled_knowledge_support_inputs
        + context_package.archive_support_inputs
    ):
        signal_sources.append(
            ProposalSupportItem(
                source_label=f"support:{len(signal_sources) + 1}",
                source_family=support.source_family,
                summary=support.summary,
                source_id=support.source_id,
            )
        )
    signal_sources.extend(current_execution_support.items)
    for artifact_index, artifact in enumerate(research_artifacts, start=1):
        signal_sources.append(
            ProposalSupportItem(
                source_label=f"research_artifact_summary:{artifact_index}",
                source_family="research_artifact",
                summary=artifact.summary,
            )
        )
        for uncertainty_index, uncertainty in enumerate(artifact.uncertainties, start=1):
            signal_sources.append(
                ProposalSupportItem(
                    source_label=f"research_artifact_uncertainty:{artifact_index}:{uncertainty_index}",
                    source_family="research_uncertainty",
                    summary=uncertainty,
                )
            )

    blocker_count = 0
    risk_count = 0
    constraint_count = 0
    for item in signal_sources:
        lowered = item.summary.lower()
        if blocker_count < _GOVERNANCE_BLOCKER_LIMIT and any(marker in lowered for marker in _GOVERNANCE_BLOCKER_MARKERS):
            if _append_unique_item(
                items,
                seen,
                ProposalSupportItem(
                    source_label=f"governance_signal:blocker:{blocker_count + 1}",
                    source_family="governance_blocker_signal",
                    summary=item.summary,
                    source_id=item.source_id,
                ),
            ):
                blocker_count += 1
        if risk_count < _GOVERNANCE_RISK_LIMIT and any(marker in lowered for marker in _GOVERNANCE_RISK_MARKERS):
            if _append_unique_item(
                items,
                seen,
                ProposalSupportItem(
                    source_label=f"governance_signal:risk:{risk_count + 1}",
                    source_family="governance_risk_signal",
                    summary=item.summary,
                    source_id=item.source_id,
                ),
            ):
                risk_count += 1
        if constraint_count < _GOVERNANCE_CONSTRAINT_LIMIT and any(
            marker in lowered for marker in _GOVERNANCE_CONSTRAINT_MARKERS
        ):
            if _append_unique_item(
                items,
                seen,
                ProposalSupportItem(
                    source_label=f"governance_signal:constraint:{constraint_count + 1}",
                    source_family="governance_constraint_signal",
                    summary=item.summary,
                    source_id=item.source_id,
                ),
            ):
                constraint_count += 1

    return ProposalSupportSection(items=tuple(items))


def _build_evidence_support(
    *,
    context_package: ContextPackage,
    research_artifacts: tuple[ResearchArtifact, ...],
) -> ProposalEvidenceSupport:
    evidence_items: list[ProposalSupportItem] = []
    uncertainty_items: list[ProposalSupportItem] = []
    contradiction_items: list[ProposalSupportItem] = []
    artifact_refs: list[str] = []
    seen_evidence: set[tuple[str, str]] = set()
    seen_uncertainty: set[tuple[str, str]] = set()
    seen_contradiction: set[tuple[str, str]] = set()

    for support in (
        context_package.archive_support_inputs
        + tuple(
            support
            for support in context_package.ordered_support_inputs
            if support.source_family in {"research", "evidence", "compiled_knowledge"}
        )
    ):
        if len(evidence_items) < _EVIDENCE_SUPPORT_LIMIT:
            _append_unique_item(
                evidence_items,
                seen_evidence,
                ProposalSupportItem(
                    source_label=f"evidence_support:{len(evidence_items) + 1}",
                    source_family=support.source_family,
                    summary=support.summary,
                    source_id=support.source_id,
                ),
            )
        if support.source_id is not None and support.source_id not in artifact_refs:
            artifact_refs.append(support.source_id)
        _append_keyword_summary(
            target_items=uncertainty_items,
            seen=seen_uncertainty,
            limit=_UNCERTAINTY_SUPPORT_LIMIT,
            source_label_prefix="evidence_uncertainty",
            source_family="evidence_uncertainty",
            source_item=support,
            markers=_UNCERTAINTY_MARKERS,
        )
        _append_keyword_summary(
            target_items=contradiction_items,
            seen=seen_contradiction,
            limit=_CONTRADICTION_SUPPORT_LIMIT,
            source_label_prefix="evidence_contradiction",
            source_family="evidence_contradiction",
            source_item=support,
            markers=_CONTRADICTION_MARKERS,
        )

    for artifact_index, artifact in enumerate(research_artifacts, start=1):
        for finding_index, finding in enumerate(artifact.findings, start=1):
            if len(evidence_items) >= _EVIDENCE_SUPPORT_LIMIT:
                break
            _append_unique_item(
                evidence_items,
                seen_evidence,
                ProposalSupportItem(
                    source_label=f"research_finding:{artifact_index}:{finding_index}",
                    source_family="research_finding",
                    summary=finding.text,
                ),
            )
            for source_ref in finding.source_refs:
                if source_ref not in artifact_refs:
                    artifact_refs.append(source_ref)
        for uncertainty_index, uncertainty in enumerate(artifact.uncertainties, start=1):
            if len(uncertainty_items) >= _UNCERTAINTY_SUPPORT_LIMIT:
                break
            _append_unique_item(
                uncertainty_items,
                seen_uncertainty,
                ProposalSupportItem(
                    source_label=f"research_uncertainty:{artifact_index}:{uncertainty_index}",
                    source_family="research_uncertainty",
                    summary=uncertainty,
                ),
            )
            if any(marker in uncertainty.lower() for marker in _CONTRADICTION_MARKERS):
                _append_unique_item(
                    contradiction_items,
                    seen_contradiction,
                    ProposalSupportItem(
                        source_label=f"research_contradiction:{artifact_index}:{uncertainty_index}",
                        source_family="research_contradiction",
                        summary=uncertainty,
                    ),
                )
        if any(marker in artifact.summary.lower() for marker in _CONTRADICTION_MARKERS):
            _append_unique_item(
                contradiction_items,
                seen_contradiction,
                ProposalSupportItem(
                    source_label=f"research_summary_contradiction:{artifact_index}",
                    source_family="research_contradiction",
                    summary=artifact.summary,
                ),
            )
        for source_id in artifact.source_ids:
            if source_id not in artifact_refs:
                artifact_refs.append(source_id)

    return ProposalEvidenceSupport(
        evidence_summaries=tuple(evidence_items[:_EVIDENCE_SUPPORT_LIMIT]),
        uncertainty_summaries=tuple(uncertainty_items[:_UNCERTAINTY_SUPPORT_LIMIT]),
        contradiction_summaries=tuple(contradiction_items[:_CONTRADICTION_SUPPORT_LIMIT]),
        artifact_refs=tuple(artifact_refs[:_EVIDENCE_SUPPORT_LIMIT + _UNCERTAINTY_SUPPORT_LIMIT]),
    )


def _build_memory_support(
    *,
    context_package: ContextPackage,
    committed_memory_records: tuple[CommittedMemoryRecord, ...],
) -> ProposalMemorySupport:
    memory_ids: list[str] = []
    summary_items: list[ProposalSupportItem] = []
    lesson_items: list[ProposalSupportItem] = []
    risk_items: list[ProposalSupportItem] = []
    precedent_items: list[ProposalSupportItem] = []
    seen_summary: set[tuple[str, str]] = set()
    seen_lesson: set[tuple[str, str]] = set()
    seen_risk: set[tuple[str, str]] = set()
    seen_precedent: set[tuple[str, str]] = set()

    if committed_memory_records:
        for index, record in enumerate(committed_memory_records[:_MEMORY_SUMMARY_LIMIT], start=1):
            memory_id = str(record.memory_id)
            if memory_id not in memory_ids:
                memory_ids.append(memory_id)
            _append_unique_item(
                summary_items,
                seen_summary,
                ProposalSupportItem(
                    source_label=f"memory_summary:{index}",
                    source_family="memory",
                    summary=f"{record.summary}. Why it matters: {record.why_it_matters}",
                    source_id=memory_id,
                ),
            )
            for point_index, point in enumerate(record.remembered_points, start=1):
                lowered = point.lower()
                if len(risk_items) < _MEMORY_DETAIL_LIMIT and any(marker in lowered for marker in _MEMORY_RISK_MARKERS):
                    _append_unique_item(
                        risk_items,
                        seen_risk,
                        ProposalSupportItem(
                            source_label=f"memory_risk:{index}:{point_index}",
                            source_family="memory_risk_reminder",
                            summary=point,
                            source_id=memory_id,
                        ),
                    )
                if len(precedent_items) < _MEMORY_DETAIL_LIMIT and any(
                    marker in lowered for marker in _MEMORY_PRECEDENT_MARKERS
                ):
                    _append_unique_item(
                        precedent_items,
                        seen_precedent,
                        ProposalSupportItem(
                            source_label=f"memory_precedent:{index}:{point_index}",
                            source_family="memory_precedent",
                            summary=point,
                            source_id=memory_id,
                        ),
                    )
                if len(lesson_items) < _MEMORY_DETAIL_LIMIT and any(marker in lowered for marker in _MEMORY_LESSON_MARKERS):
                    _append_unique_item(
                        lesson_items,
                        seen_lesson,
                        ProposalSupportItem(
                            source_label=f"memory_lesson:{index}:{point_index}",
                            source_family="memory_lesson",
                            summary=point,
                            source_id=memory_id,
                        ),
                    )
    else:
        for index, support in enumerate(context_package.memory_support_inputs[:_MEMORY_SUMMARY_LIMIT], start=1):
            if support.source_id is not None and support.source_id not in memory_ids:
                memory_ids.append(support.source_id)
            _append_unique_item(
                summary_items,
                seen_summary,
                ProposalSupportItem(
                    source_label=f"memory_summary:{index}",
                    source_family="memory",
                    summary=support.summary,
                    source_id=support.source_id,
                ),
            )

    return ProposalMemorySupport(
        memory_ids=tuple(memory_ids[:_MEMORY_SUMMARY_LIMIT]),
        memory_summaries=tuple(summary_items[:_MEMORY_SUMMARY_LIMIT]),
        memory_lessons=tuple(lesson_items[:_MEMORY_DETAIL_LIMIT]),
        memory_risk_reminders=tuple(risk_items[:_MEMORY_DETAIL_LIMIT]),
        memory_precedents=tuple(precedent_items[:_MEMORY_DETAIL_LIMIT]),
    )


def _append_keyword_summary(
    *,
    target_items: list[ProposalSupportItem],
    seen: set[tuple[str, str]],
    limit: int,
    source_label_prefix: str,
    source_family: str,
    source_item: SupportInput,
    markers: tuple[str, ...],
) -> None:
    if len(target_items) >= limit:
        return
    lowered = source_item.summary.lower()
    if not any(marker in lowered for marker in markers):
        return
    _append_unique_item(
        target_items,
        seen,
        ProposalSupportItem(
            source_label=f"{source_label_prefix}:{len(target_items) + 1}",
            source_family=source_family,
            summary=source_item.summary,
            source_id=source_item.source_id,
        ),
    )


def _append_unique_item(
    target_items: list[ProposalSupportItem],
    seen: set[tuple[str, str]],
    item: ProposalSupportItem,
) -> bool:
    key = (item.source_family, item.summary.lower())
    if key in seen:
        return False
    target_items.append(item)
    seen.add(key)
    return True