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
    lines = [
        "[session] scope",
        f"project_id={session['project_id'] or '-'}",
        f"work_unit_id={session['work_unit_id'] or '-'}",
        f"run_id={session['run_id'] or '-'}",
        f"output_mode={session['output_mode']}",
        f"json_output={session['json_output']}",
    ]
    if session["project_id"] is None:
        lines.append("[hint] next=/project list then /project use <project_id>")
    elif session["work_unit_id"] is None:
        lines.append("[hint] next=/work list then /work use <work_unit_id>")
    elif session["run_id"] is None:
        lines.append("[hint] next=/inspect (auto-selects or creates a run) or /run list for manual history/debug")
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

    lines = [
        f"RUN {truth['run_id']}",
        f"[truth] project_id={truth['project_id']} work_unit_id={truth['work_unit_id']} run_lifecycle_state={truth['run_lifecycle_state']}",
    ]
    if not derived["flow_visible"]:
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
    routing = support["routing_decision"]
    if routing is not None:
        lines.append(
            f"[support] routing route_kind={routing['route_kind']} routed_outcome={routing['routed_outcome']} "
            f"source_stage={routing['source_stage']} reason={routing['reason_summary']}"
        )
    lines.append("[support] recent_events")
    for event in support["recent_events"]:
        lines.append(f"- #{event['ordinal']} {event['stage'] or '-'} {event['event_type']} {event['summary']}")
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
    return "\n".join(
        [
            f"request_type={derived['request_type']} target={derived['target']}",
            f"accepted={derived['accepted']} effect_state={derived['effect_state']}",
            f"note={support['note']}",
        ]
    )


def render_help() -> str:
    return "\n".join(
        [
            "Jeff CLI is command-driven.",
            "Use slash commands like /help or /project list.",
            "Plain text like 'hello' is not a supported command.",
            "Normal flow:",
            "1. /project list",
            "2. /project use <project_id>",
            "3. /work list",
            "4. /work use <work_unit_id>",
            "5. /inspect",
            "6. /trace [run_id] or /lifecycle [run_id]",
            "Manual history/debug:",
            "- /run list",
            "- /run use <run_id>",
            "- /show [run_id]",
            "Current startup uses explicit in-memory demo state only.",
            "",
            "Commands:",
            "/project list",
            "/project use <project_id>",
            "/work list",
            "/work use <work_unit_id>",
            "/inspect",
            "/run list",
            "/run use <run_id>",
            "/scope show",
            "/scope clear",
            "/show [run_id]",
            "/trace [run_id]",
            "/lifecycle [run_id]",
            "/mode <compact|debug>",
            "/json <on|off>",
            "/approve [run_id]",
            "/reject [run_id]",
            "/retry [run_id]",
            "/revalidate [run_id]",
            "/recover [run_id]",
            "/help",
        ]
    )
