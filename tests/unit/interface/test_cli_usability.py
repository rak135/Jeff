import os

import pytest

from jeff.interface import JeffCLI
from jeff.interface.render import color_enabled, format_error_text, format_prompt_text

from tests.fixtures.cli import build_interface_context


def test_run_list_requires_scope_then_lists_available_runs() -> None:
    context, _ = build_interface_context()
    cli = JeffCLI(context=context)

    with pytest.raises(ValueError, match="Use /project list, then /project use <project_id>"):
        cli.run_one_shot("/run list")

    cli.run_one_shot("/project use project-1")
    with pytest.raises(ValueError, match="Use /work list, then /work use <work_unit_id>"):
        cli.run_one_shot("/run list")

    cli.run_one_shot("/work use wu-1")
    text = cli.run_one_shot("/run list")

    assert "[truth] runs project_id=project-1 work_unit_id=wu-1" in text
    assert "- run-1 lifecycle=created" in text
    assert "/run use <run_id>" in text


def test_inspect_without_current_run_suggests_next_valid_commands() -> None:
    context, _ = build_interface_context()
    cli = JeffCLI(context=context)

    with pytest.raises(ValueError) as exc_info:
        cli.run_one_shot("/inspect")

    message = str(exc_info.value)
    assert "current session scope has no project_id" in message

    cli.run_one_shot("/project use project-1")
    with pytest.raises(ValueError) as exc_info:
        cli.run_one_shot("/inspect")

    message = str(exc_info.value)
    assert "current session scope has no work_unit_id" in message


def test_unknown_scope_ids_suggest_discovery_commands() -> None:
    context, _ = build_interface_context()
    cli = JeffCLI(context=context)

    with pytest.raises(ValueError, match="Use /project list"):
        cli.run_one_shot("/project use missing-project")

    cli.run_one_shot("/project use project-1")
    with pytest.raises(ValueError, match="Use /work list"):
        cli.run_one_shot("/work use missing-work")

    cli.run_one_shot("/work use wu-1")
    with pytest.raises(ValueError, match="Use /run list"):
        cli.run_one_shot("/run use missing-run")


def test_unsupported_command_guides_operator_to_help() -> None:
    context, _ = build_interface_context()
    cli = JeffCLI(context=context)

    with pytest.raises(ValueError) as exc_info:
        cli.run_one_shot("hello")

    message = str(exc_info.value)
    assert "unsupported command: hello" in message
    assert "command-driven" in message
    assert "/help" in message


def test_help_text_explains_normal_cli_flow() -> None:
    context, _ = build_interface_context()
    cli = JeffCLI(context=context)

    text = cli.run_one_shot("/help")

    assert "Jeff CLI is command-driven." in text
    assert "Session scope is session-local/process-local only." in text
    assert "Plain text like 'hello' is not a supported command." in text
    assert "Primary flow:" in text
    assert "History/debug:" in text
    assert "Conditionally available request-entry:" in text
    assert "Bounded receipt-only request-entry:" in text
    assert "Startup loads or initializes a persisted local runtime under .jeff_runtime and can load local runtime config for research." in text
    assert "/proposal show [run_id or proposal_id]" in text
    assert "/evaluation show" not in text


def test_readability_helpers_keep_plain_fallback_and_optional_color() -> None:
    plain_prompt = format_prompt_text("jeff:/project-1/wu-1>", use_color=False)
    colored_error = format_error_text("unsupported command", use_color=True)

    assert plain_prompt == "[cmd] jeff:/project-1/wu-1>"
    assert colored_error.startswith("\033[1;31m[error] unsupported command")
    assert colored_error.endswith("\033[0m")
    assert color_enabled(stream_isatty=False, env=os.environ) is False
    assert color_enabled(stream_isatty=True, env={"TERM": "dumb"}) is False
    assert color_enabled(stream_isatty=True, env={"TERM": "xterm-256color"}) is True
