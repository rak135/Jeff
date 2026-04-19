import json

from tests.fixtures.entrypoint import run_jeff


def test_one_shot_help_reaches_cli_surface(tmp_path) -> None:
    result = run_jeff("--command", "/help", cwd=tmp_path)

    assert result.returncode == 0
    assert "Jeff CLI is command-driven." in result.stdout
    assert "/project list" in result.stdout
    assert "Primary flow:" in result.stdout
    assert "/run list" in result.stdout
    assert "/show [run_id]" in result.stdout
    assert "/proposal show" not in result.stdout
    assert "/evaluation show" not in result.stdout
    assert "A local jeff.runtime.toml enables /run <repo-local-validation-objective> and /research ..." in result.stdout
    assert "/run runs one bounded repo-local pytest validation plan under the current model configuration." in result.stdout
    assert "Session scope is session-local/process-local only." in result.stdout


def test_process_help_mentions_runtime_reset_flag(tmp_path) -> None:
    result = run_jeff("--help", cwd=tmp_path)

    assert result.returncode == 0
    assert "--reset-runtime" in result.stdout
    assert "jeff.runtime.toml enables the bounded repo-local validation /run objective path and research commands" in result.stdout


def test_reset_runtime_flag_rebuilds_runtime_home_cleanly(tmp_path) -> None:
    result = run_jeff("--reset-runtime", "--bootstrap-check", cwd=tmp_path)

    assert result.returncode == 0
    assert "reset local runtime workspace at" in result.stdout
    assert "bootstrap checks passed" in result.stdout
    assert (tmp_path / ".jeff_runtime" / "config" / "runtime.lock.json").exists()
    assert (tmp_path / ".jeff_runtime" / "state" / "canonical_state.json").exists()


def test_one_shot_project_list_uses_bootstrapped_demo_context(tmp_path) -> None:
    result = run_jeff("--command", "/project list", cwd=tmp_path)

    assert result.returncode == 0
    assert "[truth] projects" in result.stdout
    assert "project-1" in result.stdout


def test_one_shot_project_list_emits_json_when_requested(tmp_path) -> None:
    result = run_jeff("--command", "/project list", "--json", cwd=tmp_path)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["view"] == "project_list"
    project_ids = [project["project_id"] for project in payload["truth"]["projects"]]
    assert "project-1" in project_ids


def test_one_shot_work_list_emits_json_when_requested(tmp_path) -> None:
    result = run_jeff("--project", "project-1", "--command", "/work list", "--json", cwd=tmp_path)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["view"] == "work_unit_list"
    assert payload["truth"]["project_id"] == "project-1"
    assert [work_unit["work_unit_id"] for work_unit in payload["truth"]["work_units"]] == ["wu-1"]


def test_one_shot_run_list_emits_json_when_requested(tmp_path) -> None:
    result = run_jeff("--project", "project-1", "--work", "wu-1", "--command", "/run list", "--json", cwd=tmp_path)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["view"] == "run_list"
    assert payload["truth"]["project_id"] == "project-1"
    assert payload["truth"]["work_unit_id"] == "wu-1"
    assert payload["truth"]["runs"] == []


def test_unknown_one_shot_command_fails_clearly(tmp_path) -> None:
    result = run_jeff("--command", "/unknown", cwd=tmp_path)

    assert result.returncode != 0
    assert "unsupported command" in result.stderr
    assert "use /help" in result.stderr


def test_one_shot_scope_flags_support_show_without_persistent_tty(tmp_path) -> None:
    result = run_jeff("--project", "project-1", "--work", "wu-1", "--command", "/inspect", cwd=tmp_path)

    assert result.returncode == 0
    assert "RUN run-1" in result.stdout
    assert "[derived] no orchestrator flow is attached to this run" in result.stdout


def test_repeated_one_shot_commands_share_temporary_session_scope(tmp_path) -> None:
    result = run_jeff(
        "--project",
        "project-1",
        "--work",
        "wu-1",
        "--command",
        "/inspect",
        "--command",
        "/selection show",
        cwd=tmp_path,
    )

    assert result.returncode == 0
    assert "RUN run-1" in result.stdout
    assert "SELECTION REVIEW run_id=run-1" in result.stdout
    assert "[proposal] missing=no proposal summary is available for this run" in result.stdout


def test_repeated_one_shot_session_json_toggle_applies_when_outer_json_is_unset(tmp_path) -> None:
    result = run_jeff(
        "--project",
        "project-1",
        "--work",
        "wu-1",
        "--command",
        "/inspect",
        "--command",
        "/json on",
        "--command",
        "/show",
        cwd=tmp_path,
    )

    assert result.returncode == 0
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert "json_output set to True" in lines
    payload = json.loads(lines[-1])
    assert payload["view"] == "run_show"
    assert payload["truth"]["run_id"] == "run-1"


def test_text_only_commands_remain_text_only_under_outer_json_flag(tmp_path) -> None:
    result = run_jeff("--command", "/help", "--json", cwd=tmp_path)

    assert result.returncode == 0
    assert result.stdout.startswith("Jeff CLI is command-driven.")
    assert '"view"' not in result.stdout


def test_selection_override_without_a_selection_review_fails_truthfully(tmp_path) -> None:
    result = run_jeff(
        "--project",
        "project-1",
        "--work",
        "wu-1",
        "--command",
        "/inspect",
        "--command",
        '/selection override proposal-2 --why "Operator wants the alternate bounded demo path."',
        cwd=tmp_path,
    )

    assert result.returncode != 0
    assert "no selection review data is available for run run-1" in result.stderr
