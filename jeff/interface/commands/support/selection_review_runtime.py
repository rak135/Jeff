"""InterfaceContext/runtime-store wrappers around selection review records."""

from __future__ import annotations

from jeff.core.schemas import Scope
from jeff.core.containers.models import Run
from jeff.orchestrator import FlowRunResult

from jeff.cognitive.post_selection.selection_review import materialize_selection_review_from_available_data
from jeff.cognitive.post_selection.selection_review_record import SelectionReviewRecord

from ..models import InterfaceContext


def ensure_selection_review_for_run(
    *,
    context: InterfaceContext,
    run: Run,
    flow_run: FlowRunResult | None,
) -> tuple[InterfaceContext, SelectionReviewRecord | None]:
    return _selection_review_for_run_with_context_update(
        context=context,
        run=run,
        flow_run=flow_run,
        persist=True,
    )


def materialize_selection_review_for_run(
    *,
    context: InterfaceContext,
    run: Run,
    flow_run: FlowRunResult | None,
) -> tuple[InterfaceContext, SelectionReviewRecord | None]:
    return _selection_review_for_run_with_context_update(
        context=context,
        run=run,
        flow_run=flow_run,
        persist=False,
    )


def replace_selection_review(
    *,
    context: InterfaceContext,
    run_id: str,
    selection_review: SelectionReviewRecord,
) -> InterfaceContext:
    return _store_selection_review_in_context(
        context=context,
        run_id=run_id,
        selection_review=selection_review,
        persist=True,
    )


def _selection_review_for_run_with_context_update(
    *,
    context: InterfaceContext,
    run: Run,
    flow_run: FlowRunResult | None,
    persist: bool,
) -> tuple[InterfaceContext, SelectionReviewRecord | None]:
    run_id = str(run.run_id)
    existing_review = context.selection_reviews.get(run_id)
    selection_review = materialize_selection_review_from_available_data(
        existing_review=existing_review,
        flow_run=flow_run,
    )
    if selection_review is None:
        return context, None
    if existing_review == selection_review:
        return context, selection_review
    return _store_selection_review_in_context(
        context=context,
        run_id=run_id,
        selection_review=selection_review,
        persist=persist,
    ), selection_review


def _store_selection_review_in_context(
    *,
    context: InterfaceContext,
    run_id: str,
    selection_review: SelectionReviewRecord,
    persist: bool,
) -> InterfaceContext:
    if persist and context.runtime_store is not None:
        context.runtime_store.save_selection_review(run_id, selection_review)
    next_reviews = dict(context.selection_reviews)
    next_reviews[run_id] = selection_review
    return InterfaceContext(
        state=context.state,
        flow_runs=context.flow_runs,
        selection_reviews=next_reviews,
        infrastructure_services=context.infrastructure_services,
        research_artifact_store=context.research_artifact_store,
        research_archive_store=context.research_archive_store,
        knowledge_store=context.knowledge_store,
        memory_store=context.memory_store,
        research_memory_handoff_enabled=context.research_memory_handoff_enabled,
        runtime_store=context.runtime_store,
        startup_summary=context.startup_summary,
    )


def _selection_review_for_context(*, context: InterfaceContext, scope: Scope) -> SelectionReviewRecord | None:
    if scope.run_id is None:
        return None

    run_id = str(scope.run_id)
    return materialize_selection_review_from_available_data(
        existing_review=context.selection_reviews.get(run_id),
        flow_run=context.flow_runs.get(run_id),
    )