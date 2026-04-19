"""Truth-first context package and assembler."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.cognitive.research.archive.retrieval import ResearchArchiveRetrievalRequest, retrieve_archive
from jeff.core.state import GlobalState
from jeff.core.schemas import Scope
from jeff.governance import Approval, CurrentTruthSnapshot, Policy, Readiness
from jeff.knowledge import KnowledgeRetrievalRequest, retrieve_project_knowledge
from jeff.memory import MemoryRetrievalRequest, retrieve_memory

from .types import SupportInput, TriggerInput, TruthRecord, normalized_identity, require_text

_DEFAULT_MEMORY_SUPPORT_BUDGET = 3
_DEFAULT_COMPILED_KNOWLEDGE_BUDGET = 2
_DEFAULT_ARCHIVE_SUPPORT_BUDGET = 2

_COMPILED_KNOWLEDGE_PURPOSE_MARKERS = (
    "research continuation",
    "research follow up",
    "topic research continuation",
    "topic oriented research continuation",
    "synthesis follow up",
    "operator explanation",
    "proposal support",
    "bounded decision support",
)
_COMPILED_KNOWLEDGE_EXCLUSION_MARKERS = (
    "current truth",
    "current state",
    "state answer",
    "status check",
    "memory continuity",
    "memory only",
)
_ARCHIVE_REQUIRED_MARKERS = (
    "direct evidence",
    "raw evidence",
    "archive evidence",
    "source verification",
    "dated evidence",
    "historical comparison",
    "direct support",
)
_GOVERNANCE_PURPOSE_MARKERS = (
    "proposal support",
    "decision support",
    "action preparation",
    "action prep",
    "evaluation follow up",
    "evaluation followup",
    "operator explanation",
    "approval",
    "readiness",
    "governance",
    "constraint",
    "risk posture",
)
_GOVERNANCE_EXCLUSION_MARKERS = (
    "research continuation",
    "topic research continuation",
    "thematic research",
    "memory only",
)


@dataclass(frozen=True, slots=True)
class ContextPurposePolicy:
    include_memory: bool
    include_compiled_knowledge: bool
    include_archive_support: bool
    include_governance_truth: bool


@dataclass(frozen=True, slots=True)
class ContextPackage:
    purpose: str
    trigger: TriggerInput
    scope: Scope
    truth_records: tuple[TruthRecord, ...]
    support_inputs: tuple[SupportInput, ...] = ()
    governance_truth_records: tuple[TruthRecord, ...] = ()
    memory_support_inputs: tuple[SupportInput, ...] = ()
    compiled_knowledge_support_inputs: tuple[SupportInput, ...] = ()
    archive_support_inputs: tuple[SupportInput, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "purpose", require_text(self.purpose, field_name="purpose"))
        if not self.truth_records:
            raise ValueError("context package must anchor on current truth records")

    @property
    def ordered_truth_records(self) -> tuple[TruthRecord, ...]:
        return self.truth_records + self.governance_truth_records

    @property
    def ordered_support_inputs(self) -> tuple[SupportInput, ...]:
        # Context ownership keeps support ordering explicit and inspectable:
        # canonical truth -> governance truth -> committed memory -> compiled knowledge -> archive/raw support -> direct bounded support.
        return (
            self.memory_support_inputs
            + self.compiled_knowledge_support_inputs
            + self.archive_support_inputs
            + self.support_inputs
        )


def assemble_context_package(
    *,
    trigger: TriggerInput,
    purpose: str,
    scope: Scope,
    state: GlobalState,
    support_inputs: tuple[SupportInput, ...] | None = None,
    memory_store=None,
    knowledge_store=None,
    archive_store=None,
    knowledge_topic_query: str | None = None,
    governance_truth: CurrentTruthSnapshot | None = None,
    governance_policy: Policy | None = None,
    governance_approval: Approval | None = None,
    governance_readiness: Readiness | None = None,
    memory_support_budget: int = _DEFAULT_MEMORY_SUPPORT_BUDGET,
    compiled_knowledge_budget: int = _DEFAULT_COMPILED_KNOWLEDGE_BUDGET,
    archive_support_budget: int = _DEFAULT_ARCHIVE_SUPPORT_BUDGET,
) -> ContextPackage:
    truth_records = _extract_truth_records(state=state, scope=scope)
    validated_support = tuple(_validate_support(scope=scope, support=support) for support in (support_inputs or ()))
    support_policy = _policy_for_purpose(purpose)
    governance_truth_records = _extract_governance_truth_records(
        scope=scope,
        support_policy=support_policy,
        governance_truth=governance_truth,
        governance_policy=governance_policy,
        governance_approval=governance_approval,
        governance_readiness=governance_readiness,
    )
    truth_anchor = " | ".join(record.summary for record in truth_records + governance_truth_records)
    memory_support_inputs = _retrieve_memory_support_inputs(
        scope=scope,
        purpose=purpose,
        trigger=trigger,
        store=memory_store,
        budget=memory_support_budget,
        truth_anchor=truth_anchor,
        support_policy=support_policy,
    )
    compiled_knowledge_support_inputs = _retrieve_compiled_knowledge_support_inputs(
        scope=scope,
        purpose=purpose,
        trigger=trigger,
        store=knowledge_store,
        support_policy=support_policy,
        budget=compiled_knowledge_budget,
        topic_query=knowledge_topic_query,
    )
    archive_support_inputs = _retrieve_archive_support_inputs(
        scope=scope,
        purpose=purpose,
        store=archive_store,
        support_policy=support_policy,
        budget=archive_support_budget,
    )

    return ContextPackage(
        purpose=purpose,
        trigger=trigger,
        scope=scope,
        truth_records=truth_records,
        governance_truth_records=governance_truth_records,
        support_inputs=validated_support,
        memory_support_inputs=memory_support_inputs,
        compiled_knowledge_support_inputs=compiled_knowledge_support_inputs,
        archive_support_inputs=archive_support_inputs,
    )


def _extract_truth_records(*, state: GlobalState, scope: Scope) -> tuple[TruthRecord, ...]:
    project = state.projects.get(scope.project_id)
    if project is None:
        raise ValueError("context scope project_id does not exist in canonical truth")

    records: list[TruthRecord] = [
        TruthRecord(
            truth_family="project",
            scope=Scope(project_id=project.project_id),
            summary=f"project:{project.project_id} {project.name} [{project.project_lifecycle_state}]",
        ),
    ]

    if scope.work_unit_id is not None:
        work_unit = project.work_units.get(scope.work_unit_id)
        if work_unit is None:
            raise ValueError("context scope work_unit_id does not exist in canonical truth")
        records.append(
            TruthRecord(
                truth_family="work_unit",
                scope=Scope(project_id=project.project_id, work_unit_id=work_unit.work_unit_id),
                summary=(
                    f"work_unit:{work_unit.work_unit_id} {work_unit.objective} "
                    f"[{work_unit.work_unit_lifecycle_state}]"
                ),
            ),
        )

        if scope.run_id is not None:
            run = work_unit.runs.get(scope.run_id)
            if run is None:
                raise ValueError("context scope run_id does not exist in canonical truth")
            records.append(
                TruthRecord(
                    truth_family="run",
                    scope=Scope(
                        project_id=project.project_id,
                        work_unit_id=work_unit.work_unit_id,
                        run_id=run.run_id,
                    ),
                    summary=f"run:{run.run_id} [{run.run_lifecycle_state}]",
                ),
            )

    return tuple(records)


def _extract_governance_truth_records(
    *,
    scope: Scope,
    support_policy: ContextPurposePolicy,
    governance_truth: CurrentTruthSnapshot | None,
    governance_policy: Policy | None,
    governance_approval: Approval | None,
    governance_readiness: Readiness | None,
) -> tuple[TruthRecord, ...]:
    if not support_policy.include_governance_truth:
        return ()

    if governance_truth is not None:
        _validate_governance_truth_scope(scope=scope, truth=governance_truth)

    governance_scope = governance_truth.scope if governance_truth is not None else scope
    records: list[TruthRecord] = []

    if governance_truth is not None and governance_truth.blocked_reasons:
        records.append(
            TruthRecord(
                truth_family="governance_blocker",
                scope=governance_scope,
                summary="governance_blocker: " + "; ".join(governance_truth.blocked_reasons),
            )
        )

    integrity_markers: list[str] = []
    if governance_truth is not None:
        if governance_truth.degraded_truth:
            integrity_markers.append("degraded_truth")
        if governance_truth.truth_mismatch:
            integrity_markers.append("truth_mismatch")
    if integrity_markers:
        records.append(
            TruthRecord(
                truth_family="governance_integrity",
                scope=governance_scope,
                summary="governance_integrity: " + ", ".join(integrity_markers),
            )
        )

    constraint_markers: list[str] = []
    if governance_truth is not None:
        if governance_truth.requires_revalidation:
            constraint_markers.append("requires_revalidation")
        if not governance_truth.direction_ok:
            constraint_markers.append("direction_no_longer_ok")
        if not governance_truth.target_available:
            constraint_markers.append("target_unavailable")
    if constraint_markers:
        records.append(
            TruthRecord(
                truth_family="governance_constraint",
                scope=governance_scope,
                summary="governance_constraint: " + ", ".join(constraint_markers),
            )
        )

    if governance_policy is not None and governance_policy.approval_required:
        current_approval = "absent" if governance_approval is None else governance_approval.approval_verdict
        records.append(
            TruthRecord(
                truth_family="governance_approval_dependency",
                scope=governance_scope,
                summary=(
                    "governance_approval_dependency: approval_required "
                    f"current_approval={current_approval}"
                ),
            )
        )

    if governance_readiness is not None and (
        governance_readiness.reasons
        or governance_readiness.cautions
        or governance_readiness.readiness_state not in {"ready", "ready_with_cautions"}
    ):
        details = governance_readiness.reasons or governance_readiness.cautions
        summary = f"governance_readiness: {governance_readiness.readiness_state}"
        if details:
            summary += " " + "; ".join(details)
        records.append(
            TruthRecord(
                truth_family="governance_readiness",
                scope=governance_scope,
                summary=summary,
            )
        )

    return tuple(records)


def _validate_support(*, scope: Scope, support: SupportInput) -> SupportInput:
    if support.scope.project_id != scope.project_id:
        raise ValueError("context support must stay inside the current project scope")

    if scope.work_unit_id is None and support.scope.work_unit_id is not None:
        raise ValueError("work-unit-scoped support cannot be injected into project-only context")
    if scope.work_unit_id is not None and support.scope.work_unit_id not in {None, scope.work_unit_id}:
        raise ValueError("context support must stay inside the current work_unit scope")

    if scope.run_id is None and support.scope.run_id is not None:
        raise ValueError("run-scoped support cannot be injected into broader context")
    if scope.run_id is not None and support.scope.run_id not in {None, scope.run_id}:
        raise ValueError("context support must stay inside the current run scope")

    return support


def _policy_for_purpose(purpose: str) -> ContextPurposePolicy:
    normalized_purpose = normalized_identity(purpose)
    include_archive_support = any(marker in normalized_purpose for marker in _ARCHIVE_REQUIRED_MARKERS)
    include_compiled_knowledge = any(
        marker in normalized_purpose for marker in _COMPILED_KNOWLEDGE_PURPOSE_MARKERS
    )
    if any(marker in normalized_purpose for marker in _COMPILED_KNOWLEDGE_EXCLUSION_MARKERS):
        include_compiled_knowledge = False
    include_memory = include_compiled_knowledge or include_archive_support or "support" in normalized_purpose
    include_governance_truth = any(marker in normalized_purpose for marker in _GOVERNANCE_PURPOSE_MARKERS)
    if any(marker in normalized_purpose for marker in _GOVERNANCE_EXCLUSION_MARKERS):
        include_governance_truth = False
    return ContextPurposePolicy(
        include_memory=include_memory,
        include_compiled_knowledge=include_compiled_knowledge,
        include_archive_support=include_archive_support,
        include_governance_truth=include_governance_truth,
    )


def _validate_governance_truth_scope(*, scope: Scope, truth: CurrentTruthSnapshot) -> None:
    if truth.scope.project_id != scope.project_id:
        raise ValueError("governance truth must stay inside the current project scope")

    if scope.work_unit_id is None and truth.scope.work_unit_id is not None:
        raise ValueError("work-unit governance truth cannot be injected into project-only context")
    if scope.work_unit_id is not None and truth.scope.work_unit_id not in {None, scope.work_unit_id}:
        raise ValueError("governance truth must stay inside the current work_unit scope")

    if scope.run_id is None and truth.scope.run_id is not None:
        raise ValueError("run-scoped governance truth cannot be injected into broader context")
    if scope.run_id is not None and truth.scope.run_id not in {None, scope.run_id}:
        raise ValueError("governance truth must stay inside the current run scope")


def _retrieve_memory_support_inputs(
    *,
    scope: Scope,
    purpose: str,
    trigger: TriggerInput,
    store,
    budget: int,
    truth_anchor: str,
    support_policy: ContextPurposePolicy,
) -> tuple[SupportInput, ...]:
    if store is None or not support_policy.include_memory:
        return ()

    retrieval_result = retrieve_memory(
        request=MemoryRetrievalRequest(
            purpose=purpose,
            scope=scope,
            query_text=_support_query_text(purpose=purpose, trigger=trigger),
            result_limit=budget,
            truth_anchor=truth_anchor,
        ),
        store=store,
    )
    return tuple(_memory_record_to_support_input(record) for record in retrieval_result.records)


def _retrieve_compiled_knowledge_support_inputs(
    *,
    scope: Scope,
    purpose: str,
    trigger: TriggerInput,
    store,
    support_policy: ContextPurposePolicy,
    budget: int,
    topic_query: str | None,
) -> tuple[SupportInput, ...]:
    if store is None or not support_policy.include_compiled_knowledge:
        return ()

    retrieval_result = retrieve_project_knowledge(
        KnowledgeRetrievalRequest(
            project_id=str(scope.project_id),
            purpose=purpose,
            artifact_family="topic_note",
            work_unit_id=str(scope.work_unit_id) if scope.work_unit_id is not None else None,
            run_id=str(scope.run_id) if scope.run_id is not None else None,
            topic_query=topic_query,
            limit=budget,
        ),
        store=store,
    )
    return tuple(_compiled_knowledge_artifact_to_support_input(artifact) for artifact in retrieval_result.artifacts)


def _retrieve_archive_support_inputs(
    *,
    scope: Scope,
    purpose: str,
    store,
    support_policy: ContextPurposePolicy,
    budget: int,
) -> tuple[SupportInput, ...]:
    if store is None or not support_policy.include_archive_support:
        return ()

    retrieval_result = retrieve_archive(
        request=ResearchArchiveRetrievalRequest(
            purpose=purpose,
            scope=scope,
            result_limit=budget,
        ),
        store=store,
    )
    return tuple(_archive_record_to_support_input(record) for record in retrieval_result.records)


def _support_query_text(*, purpose: str, trigger: TriggerInput) -> str:
    return f"{purpose}. {trigger.trigger_summary}"


def _memory_record_to_support_input(record) -> SupportInput:
    conflict_label = ""
    if record.conflict_posture != "none":
        conflict_label = f" [conflict:{record.conflict_posture}]"
    summary = f"{record.summary}{conflict_label} Why it matters: {record.why_it_matters}"
    return SupportInput(
        source_family="memory",
        scope=record.scope,
        source_id=str(record.memory_id),
        summary=summary,
    )


def _compiled_knowledge_artifact_to_support_input(artifact) -> SupportInput:
    status_label = ""
    if artifact.status != "fresh":
        status_label = f" [{artifact.status}]"
    detail = artifact.topic_framing or artifact.source_summary or artifact.title
    summary = f"{artifact.title}{status_label}. {detail}"
    return SupportInput(
        source_family="compiled_knowledge",
        scope=Scope(
            project_id=artifact.project_id,
            work_unit_id=artifact.work_unit_id,
            run_id=artifact.run_id,
        ),
        source_id=str(artifact.artifact_id),
        summary=summary,
    )


def _archive_record_to_support_input(record) -> SupportInput:
    question = getattr(record, "question_or_objective", None)
    question_suffix = f" Question: {question}" if isinstance(question, str) and question.strip() else ""
    return SupportInput(
        source_family="archive",
        scope=Scope(
            project_id=record.project_id,
            work_unit_id=record.work_unit_id,
            run_id=record.run_id,
        ),
        source_id=str(record.artifact_id),
        summary=f"{record.title}. {record.summary}{question_suffix}",
    )
