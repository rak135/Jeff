"""Human-oriented truthful CLI render helpers."""

from __future__ import annotations

import os
from typing import Any
from typing import Mapping


_RESET = "\033[0m"
_STYLES = {
    "prompt": "\033[1;36m",
    "error": "\033[1;31m",
    "info": "\033[1;37m",
    "hint": "\033[2;37m",
}


def color_enabled(*, stream_isatty: bool, env: Mapping[str, str] | None = None) -> bool:
    current_env = os.environ if env is None else env
    if not stream_isatty:
        return False
    if "NO_COLOR" in current_env:
        return False
    return current_env.get("TERM", "") not in {"", "dumb"}


def format_prompt_text(prompt: str, *, use_color: bool) -> str:
    return _styled(f"[cmd] {prompt}", style="prompt", use_color=use_color)


def format_error_text(message: str, *, use_color: bool) -> str:
    return _styled(f"[error] {message}", style="error", use_color=use_color)


def format_info_text(message: str, *, use_color: bool) -> str:
    return _styled(f"[jeff] {message}", style="info", use_color=use_color)


def format_hint_text(message: str, *, use_color: bool) -> str:
    return _styled(f"[hint] {message}", style="hint", use_color=use_color)


def _styled(text: str, *, style: str, use_color: bool) -> str:
    if not use_color:
        return text
    return f"{_STYLES[style]}{text}{_RESET}"


def render_scope(payload: dict[str, Any]) -> str:
    session = payload["session"]
    support = payload.get("support") or {}
    lines = [
        "[session] scope",
        f"[support] scope_model={support.get('scope_model', 'session-local/process-local only')}",
        f"project_id={session['project_id'] or '-'}",
        f"work_unit_id={session['work_unit_id'] or '-'}",
        f"run_id={session['run_id'] or '-'}",
        f"output_mode={session['output_mode']}",
        f"json_output={session['json_output']}",
        "[hint] one-shot scope can be set with outer flags: --project <project_id> --work <work_unit_id> --run <run_id>",
    ]
    if session["project_id"] is None:
        lines.append("[hint] next=/project list then /project use <project_id>")
    elif session["work_unit_id"] is None:
        lines.append("[hint] next=/work list then /work use <work_unit_id>")
    elif session["run_id"] is None:
        lines.append("[hint] next=/inspect (creates a run when none exists) or /run list then /run use <run_id>")
    return "\n".join(lines)


def render_project_list(payload: dict[str, Any]) -> str:
    lines = ["[truth] projects"]
    for project in payload["truth"]["projects"]:
        lines.append(
            f"- {project['project_id']} name={project['name']} lifecycle={project['project_lifecycle_state']}"
        )
    return "\n".join(lines)


def render_work_unit_list(payload: dict[str, Any]) -> str:
    lines = [f"[truth] work_units project_id={payload['truth']['project_id']}"]
    for work_unit in payload["truth"]["work_units"]:
        lines.append(
            f"- {work_unit['work_unit_id']} objective={work_unit['objective']} "
            f"lifecycle={work_unit['work_unit_lifecycle_state']}"
        )
    return "\n".join(lines)


def render_run_list(payload: dict[str, Any]) -> str:
    lines = [
        f"[truth] runs project_id={payload['truth']['project_id']} work_unit_id={payload['truth']['work_unit_id']}"
    ]
    runs = payload["truth"]["runs"]
    if not runs:
        lines.append("- none")
    for run in runs:
        lines.append(f"- {run['run_id']} lifecycle={run['run_lifecycle_state']}")
    lines.append("[hint] use /run use <run_id> to select a current run")
    return "\n".join(lines)


def render_run_show(payload: dict[str, Any]) -> str:
    truth = payload["truth"]
    derived = payload["derived"]
    support = payload["support"]
    telemetry = payload["telemetry"]
    live_context = support.get("live_context")
    execution = support.get("execution_summary")
    planning = support.get("planning_summary")

    lines = [
        f"RUN {truth['run_id']}",
        (
            f"[truth] project_id={truth['project_id']} work_unit_id={truth['work_unit_id']} "
            f"run_lifecycle_state={truth['run_lifecycle_state']}"
        ),
        (
            f"[truth] last_execution_status={truth['last_execution_status'] or '-'} "
            f"last_outcome_state={truth['last_outcome_state'] or '-'} "
            f"last_evaluation_verdict={truth['last_evaluation_verdict'] or '-'}"
        ),
    ]
    if not derived["flow_visible"]:
        if live_context is not None:
            lines.extend(_render_live_context_lines(live_context, prefix="[support][live_context]"))
        lines.append("[derived] no orchestrator flow is attached to this run")
        return "\n".join(lines)

    lines.extend(
        [
            f"[derived] flow_family={derived['flow_family']} orchestrator_lifecycle_state={derived['orchestrator_lifecycle_state']}",
            f"[derived] active_stage={derived['active_stage'] or '-'} active_module={derived['active_module'] or '-'}",
            f"[derived] selected_proposal_id={derived['selected_proposal_id'] or '-'} governance_outcome={derived['governance_outcome'] or '-'} allowed_now={derived['allowed_now']}",
            f"[derived] approval_verdict={derived['approval_verdict'] or '-'} execution_status={derived['execution_status'] or '-'} outcome_state={derived['outcome_state'] or '-'} evaluation_verdict={derived['evaluation_verdict'] or '-'}",
            f"[telemetry] elapsed_seconds={telemetry['elapsed_seconds']} events_seen={telemetry['events_seen']} health_posture={telemetry['health_posture']}",
        ]
    )
    if derived.get("memory_handoff_attempted"):
        handoff_result = derived.get("memory_handoff_result")
        if handoff_result is not None:
            handoff_line = (
                f"[support][memory_handoff] outcome={handoff_result['write_outcome']} "
                f"candidate_id={handoff_result['candidate_id']}"
            )
            if handoff_result["memory_id"] is not None:
                handoff_line += f" memory_id={handoff_result['memory_id']}"
            lines.append(handoff_line)
        if derived.get("memory_handoff_note"):
            lines.append(f"[support][memory_handoff] note={derived['memory_handoff_note']}")
    elif derived.get("memory_handoff_note"):
        lines.append(f"[support][memory_handoff] note={derived['memory_handoff_note']}")
    flow_reason_summary = support.get("flow_reason_summary")
    if flow_reason_summary:
        lines.append(f"[support] flow_reason={_compact_text(flow_reason_summary)}")
    routing = support["routing_decision"]
    if routing is not None:
        lines.append(
            f"[support] routing route_kind={routing['route_kind']} routed_outcome={routing['routed_outcome']} "
            f"source_stage={routing['source_stage']} reason={routing['reason_summary']}"
        )
    request_entry_hint = support.get("request_entry_hint")
    if request_entry_hint is not None:
        conditional_commands = request_entry_hint.get("conditional_commands") or []
        receipt_only_commands = request_entry_hint.get("receipt_only_commands") or []
        if conditional_commands:
            lines.append(f"[next] request_entry={' | '.join(conditional_commands)}")
        if receipt_only_commands:
            lines.append(f"[next] receipt_only_request_entry={' | '.join(receipt_only_commands)}")
    if live_context is not None:
        lines.extend(_render_live_context_lines(live_context, prefix="[support][live_context]"))
    if execution is not None and execution["available"]:
        lines.append(
            f"[support][execution] family={execution['execution_family'] or '-'} "
            f"command_id={execution['execution_command_id'] or '-'} exit_code={execution['exit_code']}"
        )
        if execution["output_summary"] is not None:
            lines.append(f"[support][execution] summary={_compact_text(execution['output_summary'])}")
        if execution["stdout_excerpt"] is not None:
            lines.append(f"[support][execution] stdout={_compact_text(execution['stdout_excerpt'])}")
        if execution["stderr_excerpt"] is not None:
            lines.append(f"[support][execution] stderr={_compact_text(execution['stderr_excerpt'])}")
    proposal = support["proposal_summary"]
    if proposal["available"]:
        lines.append(
            f"[support][proposal] serious_option_count={proposal['serious_option_count']} "
            f"selected_proposal_id={proposal['selected_proposal_id'] or '-'} "
            f"non_selection_outcome={proposal['non_selection_outcome'] or '-'}"
        )
        if proposal["scarcity_reason"] is not None:
            lines.append(f"[support][proposal] scarcity_reason={proposal['scarcity_reason']}")
        for option in proposal["retained_options"]:
            lines.append(
                f"- proposal {option['proposal_id']} type={option['proposal_type']} "
                f"assumptions={option['assumption_count']} risks={option['risk_count']} "
                f"summary={_compact_text(option['summary'])}"
            )
    else:
        lines.append(f"[support][proposal] missing={proposal['missing_reason']}")

    if planning is not None and planning["available"]:
        lines.append(
            f"[support][planning] plan_id={planning['plan_id']} status={planning['plan_status']} "
            f"active_step_id={planning['active_step_id'] or '-'} step_count={planning['step_count']} "
            f"checkpoint_count={planning['checkpoint_count']}"
        )
        lines.append(
            f"[support][planning] active_step={planning['active_step_title'] or '-'} "
            f"resume_posture={planning['resume_posture']}"
        )
        candidate = planning["candidate_action"]
        if candidate is not None:
            if candidate["available"]:
                lines.append(
                    f"[support][planning] candidate_action step_id={candidate['step_id']} "
                    f"action_id={candidate['action_id']} intent={_compact_text(candidate['intent_summary'])}"
                )
            else:
                lines.append(f"[support][planning] candidate_action={candidate['summary']}")
        active_runtime = planning.get("active_step_runtime")
        if active_runtime is not None:
            lines.append(
                f"[support][planning] active_step_runtime state={active_runtime['runtime_state']} "
                f"governance={active_runtime['last_governance_outcome'] or '-'} "
                f"execution={active_runtime['last_execution_status'] or '-'} "
                f"evaluation={active_runtime['last_evaluation_verdict'] or '-'}"
            )
    elif planning is not None:
        lines.append(f"[support][planning] missing={planning['missing_reason']}")

    evaluation = support["evaluation_summary"]
    if evaluation["available"]:
        lines.append(
            f"[support][evaluation] verdict={evaluation['evaluation_verdict']} "
            f"recommended_next_step={evaluation['recommended_next_step']}"
        )
        if evaluation["evidence_posture_summary"] is not None:
            lines.append(f"[support][evaluation] evidence={evaluation['evidence_posture_summary']}")
        if evaluation["strongest_reason_summary"] is not None:
            lines.append(f"[support][evaluation] reason={_compact_text(evaluation['strongest_reason_summary'])}")
    else:
        lines.append(f"[support][evaluation] missing={evaluation['missing_reason']}")

    lines.append("[support] recent_events")
    for event in support["recent_events"]:
        lines.append(f"- #{event['ordinal']} {event['stage'] or '-'} {event['event_type']} {event['summary']}")
    return "\n".join(lines)


def _render_live_context_lines(live_context: Mapping[str, Any], *, prefix: str) -> list[str]:
    lines = [
        f"{prefix} purpose={live_context['purpose']}",
        f"{prefix} truth_families={','.join(live_context['truth_families'])}",
        f"{prefix} governance_truth_count={live_context['governance_truth_count']}",
        (
            f"{prefix} support_counts="
            f"memory:{live_context['memory_support_count']} "
            f"compiled_knowledge:{live_context['compiled_knowledge_support_count']} "
            f"archive:{live_context['archive_support_count']} "
            f"direct:{live_context['direct_support_count']}"
        ),
    ]
    ordered_support_families = live_context["ordered_support_source_families"]
    lines.append(
        f"{prefix} support_order=" + (",".join(ordered_support_families) if ordered_support_families else "NONE")
    )
    return lines


def render_selection_review(payload: dict[str, Any]) -> str:
    truth = payload["truth"]
    proposal = payload["proposal"]
    selection = payload["selection"]
    override = payload["override"]
    resolved = payload["resolved_choice"]
    action_formation = payload["action_formation"]
    governance_handoff = payload["governance_handoff"]
    support = payload["support"]

    lines = [
        f"SELECTION REVIEW run_id={truth['run_id']}",
        f"[truth] project_id={truth['project_id']} work_unit_id={truth['work_unit_id']}",
    ]

    if selection["available"]:
        lines.append(
            f"[selection] disposition={selection['disposition']} "
            f"selected_proposal_id={selection['selected_proposal_id'] or '-'} "
            f"non_selection_outcome={selection['non_selection_outcome'] or '-'}"
        )
        if payload["support"]["selection_rationale_summary"] is not None:
            lines.append(f"[selection] rationale={payload['support']['selection_rationale_summary']}")
    else:
        lines.append(f"[selection] missing={selection['missing_reason']}")

    if proposal["available"]:
        lines.append(
            f"[proposal] serious_option_count={proposal['serious_option_count']} "
            f"selected_proposal_id={proposal['selected_proposal_id'] or '-'} "
            f"non_selection_outcome={proposal['non_selection_outcome'] or '-'}"
        )
        if proposal["scarcity_reason"] is not None:
            lines.append(f"[proposal] scarcity_reason={proposal['scarcity_reason']}")
        for option in proposal["retained_options"]:
            lines.append(
                f"- retained {option['proposal_id']} type={option['proposal_type']} "
                f"assumptions={option['assumption_count']} risks={option['risk_count']} "
                f"summary={_compact_text(option['summary'])}"
            )
    else:
        lines.append(f"[proposal] missing={proposal['missing_reason']}")

    if override["available"]:
        lines.append(
            f"[override] exists={override['exists']} "
            f"chosen_proposal_id={override['chosen_proposal_id'] or '-'}"
        )
        if override["missing_reason"] is not None:
            lines.append(f"[override] note={override['missing_reason']}")
    else:
        lines.append(f"[override] missing={override['missing_reason']}")

    if resolved["available"]:
        lines.append(
            f"[resolved_choice] effective_source={resolved['effective_source']} "
            f"effective_proposal_id={resolved['effective_proposal_id'] or '-'} "
            f"non_selection_outcome={resolved['non_selection_outcome'] or '-'}"
        )
    else:
        lines.append(f"[resolved_choice] missing={resolved['missing_reason']}")

    if action_formation["available"]:
        lines.append(
            f"[action_formation] action_formed={action_formation['action_formed']} "
            f"action_id={action_formation['action_id'] or '-'} "
            f"proposal_type={action_formation['proposal_type'] or '-'}"
        )
        if action_formation["no_action_reason"] is not None:
            lines.append(f"[action_formation] note={action_formation['no_action_reason']}")
    else:
        lines.append(f"[action_formation] missing={action_formation['missing_reason']}")

    if governance_handoff["available"]:
        lines.append(
            f"[governance_handoff] governance_evaluated={governance_handoff['governance_evaluated']} "
            f"governance_outcome={governance_handoff['governance_outcome'] or '-'} "
            f"allowed_now={governance_handoff['allowed_now']}"
        )
        if governance_handoff["no_governance_reason"] is not None:
            lines.append(f"[governance_handoff] note={governance_handoff['no_governance_reason']}")
    else:
        lines.append(f"[governance_handoff] missing={governance_handoff['missing_reason']}")

    lines.append(
        f"[support] selection_review_attached={support['selection_review_attached']} "
        f"materialized_effective_proposal_available={support['materialized_effective_proposal_available']}"
    )
    return "\n".join(lines)


def render_plan_show(payload: dict[str, Any]) -> str:
    truth = payload["truth"]
    plan = payload["plan"]
    active_step = payload["active_step"]
    active_runtime = payload.get("active_step_runtime")
    latest_runtime = payload.get("latest_step_runtime")
    candidate = payload["candidate_action"]
    lines = [
        f"PLAN run_id={truth['run_id']}",
        f"[truth] project_id={truth['project_id']} work_unit_id={truth['work_unit_id']}",
        (
            f"[plan] plan_id={plan['plan_id']} selected_proposal_id={plan['selected_proposal_id'] or '-'} "
            f"status={plan['plan_status']} active_step_id={plan['active_step_id'] or '-'}"
        ),
        (
            f"[plan] step_count={plan['step_count']} checkpoint_count={plan['checkpoint_count']} "
            f"resume_posture={plan['resume_posture']}"
        ),
        f"[plan] objective={_compact_text(plan['bounded_objective'])}",
    ]
    if active_step is not None:
        lines.append(
            f"[active_step] step_id={active_step['step_id']} order={active_step['step_order']} "
            f"type={active_step['step_type']} status={active_step['step_status']}"
        )
        lines.append(f"[active_step] title={_compact_text(active_step['title'])}")
        lines.append(f"[active_step] candidate_action={_compact_text(active_step['candidate_action_summary'])}")
    if active_runtime is not None:
        lines.append(
            f"[active_step_runtime] state={active_runtime['runtime_state']} governance={active_runtime['last_governance_outcome'] or '-'} "
            f"execution={active_runtime['last_execution_status'] or '-'} outcome={active_runtime['last_outcome_state'] or '-'} "
            f"evaluation={active_runtime['last_evaluation_verdict'] or '-'}"
        )
        if active_runtime["latest_checkpoint_decision"] is not None:
            lines.append(
                f"[active_step_runtime] latest_checkpoint={active_runtime['latest_checkpoint_decision']} "
                f"summary={_compact_text(active_runtime['latest_checkpoint_summary'])}"
            )
    if candidate["available"]:
        lines.append(
            f"[candidate_action] action_id={candidate['action_id']} step_id={candidate['step_id']} "
            f"intent={_compact_text(candidate['intent_summary'])}"
        )
    else:
        lines.append(f"[candidate_action] note={candidate['summary']}")
    if payload["checkpoint_history"]:
        latest = payload["checkpoint_history"][-1]
        lines.append(
            f"[checkpoint] latest_decision={latest['decision']} step_id={latest['step_id']} "
            f"resulting_plan_status={latest['resulting_plan_status']}"
        )
        lines.append(f"[checkpoint] summary={_compact_text(latest['summary'])}")
    if latest_runtime is not None and latest_runtime is not active_runtime:
        lines.append(
            f"[latest_runtime] step_id={latest_runtime['step_id']} state={latest_runtime['runtime_state']} "
            f"execution={latest_runtime['last_execution_status'] or '-'} evaluation={latest_runtime['last_evaluation_verdict'] or '-'}"
        )
    return "\n".join(lines)


def render_plan_steps(payload: dict[str, Any]) -> str:
    truth = payload["truth"]
    lines = [f"PLAN STEPS run_id={truth['run_id']}", f"[truth] plan_id={truth['plan_id']}"]
    for step in payload["steps"]:
        lines.append(
            f"- step_id={step['step_id']} order={step['step_order']} type={step['step_type']} "
            f"status={step['step_status']} checkpoint_required={step['checkpoint_required']} "
            f"title={_compact_text(step['title'])}"
        )
        runtime = step.get("runtime")
        if runtime is not None:
            lines.append(
                f"  runtime state={runtime['runtime_state']} governance={runtime['last_governance_outcome'] or '-'} "
                f"execution={runtime['last_execution_status'] or '-'} evaluation={runtime['last_evaluation_verdict'] or '-'}"
            )
    return "\n".join(lines)


def render_plan_checkpoint(payload: dict[str, Any]) -> str:
    truth = payload["truth"]
    checkpoint = payload["checkpoint"]
    lines = [
        f"PLAN CHECKPOINT run_id={truth['run_id']}",
        f"[truth] plan_id={truth['plan_id']}",
        (
            f"[checkpoint] available={checkpoint['available']} plan_status={checkpoint['plan_status']} "
            f"active_step_id={checkpoint['active_step_id'] or '-'} resume_posture={checkpoint['resume_posture']}"
        ),
    ]
    latest = checkpoint["latest"]
    if latest is not None:
        lines.append(
            f"[checkpoint] latest_decision={latest['decision']} step_id={latest['step_id']} "
            f"resulting_plan_status={latest['resulting_plan_status']}"
        )
        lines.append(f"[checkpoint] summary={_compact_text(latest['summary'])}")
    latest_runtime = checkpoint.get("latest_runtime")
    if latest_runtime is not None:
        lines.append(
            f"[checkpoint] latest_runtime_state={latest_runtime['runtime_state']} execution={latest_runtime['last_execution_status'] or '-'} "
            f"evaluation={latest_runtime['last_evaluation_verdict'] or '-'}"
        )
    return "\n".join(lines)


def render_plan_execute(payload: dict[str, Any]) -> str:
    truth = payload["truth"]
    attempt = payload["execution_attempt"]
    plan = payload["plan"]
    active_runtime = payload.get("active_step_runtime")
    lines = [
        f"PLAN EXECUTE run_id={truth['run_id']}",
        f"[truth] plan_id={truth['plan_id']}",
        (
            f"[attempt] active_step_id={attempt['active_step_id'] or '-'} executable={attempt['executable']} "
            f"executed={attempt['executed']} action_id={attempt['action_id'] or '-'}"
        ),
        f"[attempt] reason={_compact_text(attempt['reason'])}",
        (
            f"[plan] status={plan['plan_status']} active_step_id={plan['active_step_id'] or '-'} "
            f"resume_posture={plan['resume_posture']} checkpoint_count={plan['checkpoint_count']}"
        ),
    ]
    governance = payload.get("governance")
    if governance is not None:
        lines.append(
            f"[governance] outcome={governance['governance_outcome']} allowed_now={governance['allowed_now']} "
            f"approval_verdict={governance['approval_verdict']} readiness={governance['readiness_state']}"
        )
        if governance["reason_summary"]:
            lines.append(f"[governance] reason={_compact_text(governance['reason_summary'])}")
    execution = payload.get("execution")
    if execution is not None:
        lines.append(
            f"[execution] status={execution['execution_status']} command_id={execution['execution_command_id'] or '-'} "
            f"exit_code={execution['exit_code']}"
        )
        if execution["output_summary"] is not None:
            lines.append(f"[execution] summary={_compact_text(execution['output_summary'])}")
    outcome = payload.get("outcome")
    if outcome is not None:
        lines.append(
            f"[outcome] state={outcome['outcome_state']} completion={_compact_text(outcome['observed_completion_posture'])}"
        )
    evaluation = payload.get("evaluation")
    if evaluation is not None:
        lines.append(
            f"[evaluation] verdict={evaluation['evaluation_verdict']} next_step={evaluation['recommended_next_step']}"
        )
        lines.append(f"[evaluation] rationale={_compact_text(evaluation['rationale'])}")
    checkpoint = payload.get("checkpoint")
    if checkpoint is not None:
        lines.append(
            f"[checkpoint] decision={checkpoint['decision']} resulting_plan_status={checkpoint['resulting_plan_status']} "
            f"next_active_step_id={checkpoint['next_active_step_id'] or '-'}"
        )
        lines.append(f"[checkpoint] summary={_compact_text(checkpoint['summary'])}")
    if active_runtime is not None:
        lines.append(
            f"[active_step_runtime] state={active_runtime['runtime_state']} governance={active_runtime['last_governance_outcome'] or '-'} "
            f"execution={active_runtime['last_execution_status'] or '-'} evaluation={active_runtime['last_evaluation_verdict'] or '-'}"
        )
    return "\n".join(lines)


def render_selection_override_receipt(payload: dict[str, Any]) -> str:
    truth = payload["truth"]
    derived = payload["derived"]
    override = payload["override"]
    resolved = payload["resolved_choice"]
    action_formation = payload["action_formation"]
    governance_handoff = payload["governance_handoff"]
    support = payload["support"]

    lines = [
        f"SELECTION OVERRIDE RECORDED run_id={truth['run_id']}",
        (
            f"[selection] original_disposition={truth['original_selection_disposition'] or '-'} "
            f"original_selected_proposal_id={truth['original_selected_proposal_id'] or '-'}"
        ),
        (
            f"[override] override_created={derived['override_created']} "
            f"chosen_proposal_id={override['chosen_proposal_id'] or '-'}"
        ),
    ]

    if resolved["available"]:
        lines.append(
            f"[resolved_choice] resolved_choice_updated={derived['resolved_choice_updated']} "
            f"effective_source={resolved['effective_source']} "
            f"effective_proposal_id={resolved['effective_proposal_id'] or '-'}"
        )
    else:
        lines.append(f"[resolved_choice] missing={resolved['missing_reason']}")

    if action_formation["available"]:
        lines.append(
            f"[action_formation] action_formed={action_formation['action_formed']} "
            f"action_id={action_formation['action_id'] or '-'}"
        )
        if action_formation["no_action_reason"] is not None:
            lines.append(f"[action_formation] note={action_formation['no_action_reason']}")
    else:
        lines.append(f"[action_formation] missing={action_formation['missing_reason']}")

    if governance_handoff["available"]:
        lines.append(
            f"[governance_handoff] governance_evaluated={governance_handoff['governance_evaluated']} "
            f"governance_outcome={governance_handoff['governance_outcome'] or '-'} "
            f"allowed_now={governance_handoff['allowed_now']}"
        )
        if governance_handoff["no_governance_reason"] is not None:
            lines.append(f"[governance_handoff] note={governance_handoff['no_governance_reason']}")
    else:
        lines.append(f"[governance_handoff] missing={governance_handoff['missing_reason']}")

    lines.append(
        f"[support] original_selection_unchanged={truth['original_selection_unchanged']} "
        "override_is_separate_support=True execution_started=False"
    )
    lines.append(f"[support] note={support['note']}")
    return "\n".join(lines)


def render_proposal_record(payload: dict[str, Any]) -> str:
    truth = payload["truth"]
    derived = payload["derived"]
    proposal = payload["proposal"]
    proposal_input_bundle = payload.get("proposal_input_bundle") or {}
    attempts = payload["attempts"]
    artifacts = payload["artifacts"]

    lines = [
        f"PROPOSAL {truth['proposal_id']}",
        (
            f"[truth] project_id={truth['scope']['project_id']} "
            f"work_unit_id={truth['scope']['work_unit_id'] or '-'} "
            f"run_id={truth['scope']['run_id'] or '-'}"
        ),
        f"[truth] objective={truth['objective']}",
        (
            f"[derived] status={derived['proposal_status']} repair_used={derived['repair_used']} "
            f"final_validation_outcome={derived['final_validation_outcome']}"
        ),
    ]
    if truth["source_proposal_id"] is not None:
        lines.append(f"[derived] source_proposal_id={truth['source_proposal_id']}")
    if derived["final_failure_stage"] is not None:
        lines.append(
            f"[derived] final_failure_stage={derived['final_failure_stage']} error={derived['final_error_message']}"
        )
    lines.append(
        f"[proposal] proposal_count={proposal['proposal_count']} scarcity_reason={proposal['scarcity_reason'] or '-'} summary_source={proposal['summary_source']}"
    )
    if proposal["retained_options"]:
        for option in proposal["retained_options"]:
            lines.append(
                f"- option {option['proposal_id']} type={option['proposal_type']} title={option['title']} summary={_compact_text(option['summary'])}"
            )
    else:
        lines.append("- no retained options available")
    if proposal_input_bundle:
        request_frame = proposal_input_bundle["request_frame"]
        truth_snapshot = proposal_input_bundle["truth_snapshot"]
        governance_support = proposal_input_bundle["governance_relevant_support"]
        execution_support = proposal_input_bundle["current_execution_support"]
        evidence_support = proposal_input_bundle["evidence_support"]
        memory_support = proposal_input_bundle["memory_support"]
        lines.append(
            "[proposal_input_bundle] "
            f"purpose={request_frame['purpose']} "
            f"truth_items={truth_snapshot['item_count']} "
            f"governance_support_items={governance_support['item_count']} "
            f"execution_support_items={execution_support['item_count']} "
            f"evidence_items={evidence_support['evidence_count']} "
            f"memory_items={memory_support['summary_count']}"
        )
        if request_frame["visible_constraints"]:
            lines.append(
                "[proposal_input_bundle] visible_constraints="
                + " | ".join(request_frame["visible_constraints"])
            )
        for item in truth_snapshot["items"]:
            lines.append(
                f"- truth_basis {item['source_label']} family={item['truth_family']} summary={_compact_text(item['summary'])}"
            )
        for item in governance_support["items"]:
            lines.append(
                f"- governance_basis {item['source_label']} family={item['source_family']} summary={_compact_text(item['summary'])}"
            )
        for item in execution_support["items"]:
            lines.append(
                f"- execution_basis {item['source_label']} family={item['source_family']} summary={_compact_text(item['summary'])}"
            )
        if evidence_support["artifact_refs"]:
            lines.append("[proposal_input_bundle] evidence_refs=" + " | ".join(evidence_support["artifact_refs"]))
        for item in evidence_support["evidence_summaries"]:
            lines.append(
                f"- evidence_basis {item['source_label']} family={item['source_family']} summary={_compact_text(item['summary'])}"
            )
        for item in evidence_support["uncertainty_summaries"]:
            lines.append(
                f"- evidence_uncertainty {item['source_label']} family={item['source_family']} summary={_compact_text(item['summary'])}"
            )
        for item in evidence_support["contradiction_summaries"]:
            lines.append(
                f"- evidence_contradiction {item['source_label']} family={item['source_family']} summary={_compact_text(item['summary'])}"
            )
        if memory_support["memory_ids"]:
            lines.append("[proposal_input_bundle] memory_ids=" + " | ".join(memory_support["memory_ids"]))
        for item in memory_support["memory_summaries"]:
            lines.append(
                f"- memory_basis {item['source_label']} family={item['source_family']} summary={_compact_text(item['summary'])}"
            )
        for item in memory_support["memory_lessons"]:
            lines.append(
                f"- memory_lesson {item['source_label']} family={item['source_family']} summary={_compact_text(item['summary'])}"
            )
        for item in memory_support["memory_risk_reminders"]:
            lines.append(
                f"- memory_risk {item['source_label']} family={item['source_family']} summary={_compact_text(item['summary'])}"
            )
        for item in memory_support["memory_precedents"]:
            lines.append(
                f"- memory_precedent {item['source_label']} family={item['source_family']} summary={_compact_text(item['summary'])}"
            )
    lines.append(
        f"[attempt][initial] raw={attempts['initial']['raw_available']} parsed={attempts['initial']['parsed_available']} proposal_result={attempts['initial']['proposal_result_available']} failure_stage={attempts['initial']['failure_stage'] or '-'}"
    )
    if attempts["repair"] is not None:
        lines.append(
            f"[attempt][repair] raw={attempts['repair']['raw_available']} parsed={attempts['repair']['parsed_available']} proposal_result={attempts['repair']['proposal_result_available']} failure_stage={attempts['repair']['failure_stage'] or '-'}"
        )
    if artifacts["record_ref"] is not None:
        lines.append(f"[artifacts] record={artifacts['record_ref']}")
    if artifacts["initial_raw_ref"] is not None or artifacts["initial_parsed_ref"] is not None:
        lines.append(
            f"[artifacts] initial_raw={artifacts['initial_raw_ref'] or '-'} initial_parsed={artifacts['initial_parsed_ref'] or '-'}"
        )
    if artifacts["repair_raw_ref"] is not None or artifacts["repair_parsed_ref"] is not None:
        lines.append(
            f"[artifacts] repair_raw={artifacts['repair_raw_ref'] or '-'} repair_parsed={artifacts['repair_parsed_ref'] or '-'}"
        )
    return "\n".join(lines)


def render_proposal_raw(payload: dict[str, Any]) -> str:
    lines = [
        f"PROPOSAL RAW {payload['truth']['proposal_id']}",
        f"[truth] run_id={payload['truth']['run_id'] or '-'} objective={payload['truth']['objective']}",
    ]
    if payload["truth"]["source_proposal_id"] is not None:
        lines.append(f"[truth] source_proposal_id={payload['truth']['source_proposal_id']}")
    for attempt in payload["attempts"]:
        lines.append(
            f"[attempt] kind={attempt['attempt_kind']} prompt_file={attempt['prompt_file'] or '-'} request_id={attempt['request_id'] or '-'} raw_ref={attempt['raw_artifact_ref'] or '-'}"
        )
        if attempt["raw_output_text"] is None:
            lines.append(f"raw_unavailable={attempt['missing_reason']}")
        else:
            lines.append(attempt["raw_output_text"])
    return "\n".join(lines)


def render_proposal_validation(payload: dict[str, Any]) -> str:
    support = payload["support"]
    lines = [
        f"PROPOSAL VALIDATE {payload['truth']['proposal_id']}",
        (
            f"[derived] attempt_kind={payload['derived']['attempt_kind']} "
            f"parse_success={payload['derived']['parse_success']} validation_success={payload['derived']['validation_success']}"
        ),
    ]
    if support["parse_error"] is not None:
        lines.append(f"[support] parse_error={support['parse_error']}")
    if support["validation_issues"]:
        lines.append("[support] validation_issues")
        for issue in support["validation_issues"]:
            lines.append(
                f"- code={issue['code']} option_index={issue['option_index'] or '-'} message={issue['message']}"
            )
    lines.append(
        f"[proposal] proposal_count={support['proposal_count']} scarcity_reason={support['scarcity_reason'] or '-'}"
    )
    for option in support["retained_options"]:
        lines.append(
            f"- option {option['proposal_id']} type={option['proposal_type']} title={option['title']} summary={_compact_text(option['summary'])}"
        )
    lines.append(
        f"[artifacts] raw={payload['artifacts']['raw_ref'] or '-'} parsed={payload['artifacts']['parsed_ref'] or '-'} validation={payload['artifacts']['validation_ref'] or '-'}"
    )
    return "\n".join(lines)


def render_lifecycle(payload: dict[str, Any]) -> str:
    derived = payload["derived"]
    telemetry = payload["telemetry"]
    return "\n".join(
        [
            "[derived] lifecycle",
            f"flow_id={derived['flow_id']}",
            f"flow_family={derived['flow_family']}",
            f"lifecycle_state={derived['lifecycle_state']}",
            f"current_stage={derived['current_stage'] or '-'} active_module={derived['active_module'] or '-'}",
            f"reason_summary={derived['reason_summary'] or '-'}",
            f"[telemetry] elapsed_seconds={telemetry['elapsed_seconds']} events_seen={telemetry['events_seen']} health_posture={telemetry['health_posture']}",
        ]
    )


def render_trace(payload: dict[str, Any]) -> str:
    lines = [
        f"TRACE flow_id={payload['derived']['flow_id']} run_id={payload['derived']['run_id'] or '-'}",
    ]
    for event in payload["support"]["events"]:
        lines.append(
            f"{event['ordinal']}. stage={event['stage'] or '-'} type={event['event_type']} summary={event['summary']}"
        )
    lines.append(
        f"[telemetry] elapsed_seconds={payload['telemetry']['elapsed_seconds']} events_seen={payload['telemetry']['events_seen']}"
    )
    return "\n".join(lines)


def render_request_receipt(payload: dict[str, Any]) -> str:
    derived = payload["derived"]
    support = payload["support"]
    lines = [
        f"request_type={derived['request_type']} target={derived['target']}",
        f"accepted={derived['accepted']} effect_state={derived['effect_state']}",
    ]
    detail = support.get("detail") or {}
    if detail:
        rendered = " ".join(f"{key}={value}" for key, value in detail.items())
        lines.append(f"detail={rendered}")
    lines.append(f"note={support['note']}")
    return "\n".join(lines)


def render_research_result(payload: dict[str, Any]) -> str:
    truth = payload["truth"]
    derived = payload["derived"]
    support = payload["support"]
    live_context = support.get("live_context")
    proposal_followup = support.get("proposal_followup")

    lines = [
        (
            f"RESEARCH {derived['research_mode']} "
            f"project_id={truth['project_id']} work_unit_id={truth['work_unit_id']} run_id={truth['run_id']}"
        ),
        f"artifact_id={support['artifact_id']}",
        f"artifact_locator={support['artifact_locator'] or '-'}",
        f"source_count={support['source_count']}",
        f"question={support['question']}",
        f"summary={support['summary']}",
        "[support] findings",
    ]
    for finding in support["findings"]:
        lines.append(f"- {finding['text']}")
        for source in finding["resolved_sources"]:
            lines.append(f"  source: {_render_source_label(source)}")
            if source.get("published_at"):
                lines.append(f"  published: {source['published_at']}")

    lines.append("[support] uncertainties")
    if support["uncertainties"]:
        for uncertainty in support["uncertainties"]:
            lines.append(f"- {uncertainty}")
    else:
        lines.append("- none")

    lines.append(f"recommendation={support['recommendation'] or '-'}")
    lines.append(f"persistence={support['persistence_note']}")

    if live_context is not None:
        lines.append("[support] live_context")
        lines.append(f"live_context_purpose={live_context['purpose']}")
        lines.append(f"truth_families={','.join(live_context['truth_families'])}")
        lines.append(f"governance_truth_count={live_context['governance_truth_count']}")
        lines.append(
            "support_counts="
            f"memory:{live_context['memory_support_count']} "
            f"compiled_knowledge:{live_context['compiled_knowledge_support_count']} "
            f"archive:{live_context['archive_support_count']} "
            f"direct:{live_context['direct_support_count']}"
        )
        ordered_support_families = live_context["ordered_support_source_families"]
        lines.append(
            "support_order=" + (",".join(ordered_support_families) if ordered_support_families else "NONE")
        )

    if proposal_followup is not None:
        lines.append("[support] proposal_followup")
        if proposal_followup["proposal_generation_ran"]:
            lines.append(
                f"proposal_followup=ran serious_option_count={proposal_followup['proposal_count']}"
            )
        else:
            lines.append("proposal_followup=not_available")
        lines.append(f"proposal_request_built={proposal_followup['proposal_request_built']}")
        if proposal_followup["no_generation_reason"] is not None:
            lines.append(f"proposal_followup_reason={proposal_followup['no_generation_reason']}")

    if not derived["handoff_memory_requested"]:
        lines.append("memory_handoff=not requested")
        return "\n".join(lines)

    handoff_result = derived["memory_handoff_result"]
    if not derived["memory_handoff_performed"] or handoff_result is None:
        lines.append("memory_handoff=requested but not performed")
        return "\n".join(lines)

    handoff_line = f"memory_handoff={handoff_result['write_outcome']}"
    if handoff_result["memory_id"] is not None:
        handoff_line += f" memory_id={handoff_result['memory_id']}"
    lines.append(handoff_line)
    for reason in handoff_result["reasons"]:
        lines.append(f"- memory_reason: {reason}")
    return "\n".join(lines)


def render_research_debug_event(event: dict[str, Any]) -> str:
    checkpoint = event.get("checkpoint", "unknown")
    payload = event.get("payload", {})
    parts = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if value is None:
                continue
            parts.append(f"{key}={_render_debug_value(value)}")
    suffix = f" {' '.join(parts)}" if parts else ""
    return f"[debug][research] {checkpoint}{suffix}"


def _render_source_label(source: dict[str, Any]) -> str:
    title = source.get("title")
    locator = source.get("locator")
    source_type = source.get("source_type") or "source"

    if title and locator:
        return f"{title} | {locator}"
    if title:
        return title
    if locator:
        return locator
    return f"{source_type} source"


def _render_debug_value(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ",".join(str(item) for item in value)
    if isinstance(value, dict):
        return ",".join(f"{key}:{value[key]}" for key in value)
    return str(value)


def render_help() -> str:
    return "\n".join(
        [
            "Jeff CLI is command-driven.",
            "Session scope is session-local/process-local only. /project use, /work use, /run use, and /scope clear change this Jeff process only; use outer --project/--work/--run for one-shot scope.",
            "Use slash commands like /help or /project list.",
            "Plain text like 'hello' is not a supported command.",
            "Primary flow:",
            "- /project list",
            "- /project use <project_id>",
            "- /work list",
            "- /work use <work_unit_id>",
            "- /proposal \"<objective>\"",
            "- /run <repo-local-validation-objective>",
            "- /inspect",
            "- /show [run_id]",
            "- /proposal show [run_id or proposal_id]",
            "- /proposal raw [run_id or proposal_id]",
            "- /proposal validate [run_id or proposal_id]",
            "- /proposal repair [run_id or proposal_id]",
            "- /selection show [run_id]",
            '- /selection override <proposal_id> --why "<operator rationale>" [run_id]',
            "- /plan show [run_id]",
            "- /plan steps [run_id]",
            "- /plan execute [run_id]",
            "- /plan checkpoint [decision] [run_id]",
            "History/debug:",
            "- /run list",
            "- /run use <run_id>",
            "- /trace [run_id]",
            "- /lifecycle [run_id]",
            "- /scope show",
            "- /scope clear",
            "- /mode <compact|debug>",
            "- /json <on|off>",
            "Conditionally available request-entry:",
            "- /approve [run_id] (only when routed_outcome=approval_required)",
            "- /reject [run_id] (only when routed_outcome=approval_required or revalidate)",
            "- /revalidate [run_id] (only when routed_outcome=revalidate and approval is already granted)",
            "Bounded receipt-only request-entry:",
            "- /retry [run_id] (only when routed_outcome=retry)",
            "- /recover [run_id] (only when routed_outcome=recover)",
            "Research:",
            '- /research docs "<question>" <path1> [<path2> ...] [--handoff-memory]',
            '- /research web "<question>" <query1> [<query2> ...] [--handoff-memory]',
            "Startup loads or initializes a persisted local runtime under .jeff_runtime and can load local runtime config for research.",
            "A local jeff.runtime.toml enables /proposal, /run <repo-local-validation-objective>, and /research ...; without it, read/history commands remain available but those runtime-backed paths stay unavailable.",
            "/run runs one bounded repo-local pytest validation plan under the current model configuration. It is not a general command runner.",
            "/proposal is a bounded inspect/debug surface only. It does not select, approve, execute, or mutate truth.",
            "approve/revalidate/reject only apply when the current run routed to the required request-entry state. retry/recover remain receipt-only when surfaced.",
            "One-shot --json applies to one-shot output only. /json on affects the current interactive or repeated-command session only.",
            "Research memory uses the runtime-selected backend when config enables handoff; there is no broad /memory command family.",
        ]
    )


def _compact_text(text: str, *, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."
