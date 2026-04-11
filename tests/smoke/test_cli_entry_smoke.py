import json

from tests.fixtures.entrypoint import run_jeff


def test_one_shot_help_reaches_cli_surface() -> None:
    result = run_jeff("--command", "/help")

    assert result.returncode == 0
    assert "Jeff CLI is command-driven." in result.stdout
    assert "/project list" in result.stdout
    assert "/run list" in result.stdout
    assert "/show [run_id]" in result.stdout


def test_one_shot_project_list_uses_bootstrapped_demo_context() -> None:
    result = run_jeff("--command", "/project list")

    assert result.returncode == 0
    assert "[truth] projects" in result.stdout
    assert "project-1" in result.stdout


def test_one_shot_show_json_exposes_truthful_operator_shape() -> None:
    result = run_jeff("--command", "/show run-1", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["view"] == "run_show"
    assert payload["truth"]["run_id"] == "run-1"
    assert payload["derived"]["flow_visible"] is True
    assert payload["derived"]["active_module"] == "cognitive"
    assert "recent_events" in payload["support"]


def test_unknown_one_shot_command_fails_clearly() -> None:
    result = run_jeff("--command", "/unknown")

    assert result.returncode != 0
    assert "unsupported command" in result.stderr
    assert "use /help" in result.stderr
