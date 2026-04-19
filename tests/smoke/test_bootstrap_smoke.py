from jeff.bootstrap import build_demo_interface_context, run_startup_preflight

from tests.fixtures.entrypoint import run_jeff


def test_demo_context_bootstraps_with_project_run_and_flow() -> None:
    context = build_demo_interface_context()

    assert tuple(context.state.projects.keys()) == ("project-1",)
    assert "wu-1" in context.state.projects["project-1"].work_units
    assert "run-1" in context.state.projects["project-1"].work_units["wu-1"].runs
    assert "run-1" in context.flow_runs
    assert "run-1" in context.selection_reviews


def test_startup_preflight_reports_operator_entry_ready(tmp_path) -> None:
    checks = run_startup_preflight(base_dir=tmp_path)

    assert "package imports resolved" in checks
    assert "persisted runtime interface context bootstrapped" in checks
    assert "fresh runtime contains no seeded runs" in checks
    assert any("CLI entry surface" in check for check in checks)


def test_module_entry_help_path_boots_cleanly(tmp_path) -> None:
    result = run_jeff("--help", cwd=tmp_path)

    assert result.returncode == 0
    assert "python -m jeff --command \"/help\"" in result.stdout
    assert "persisted runtime workspace under .jeff_runtime/" in result.stdout
    assert "jeff.runtime.toml enables the bounded repo-local validation /run objective path and research commands" in result.stdout


def test_module_entry_non_tty_does_not_hang_and_explains_next_step(tmp_path) -> None:
    result = run_jeff(input_text="", cwd=tmp_path)

    assert result.returncode == 0
    assert "No interactive terminal detected. Use --command for one-shot mode; /project use, /work use, and /run use stay process-local to this Jeff process." in result.stdout
    assert "python -m jeff --project project-1 --work wu-1 --command \"/run list\" --json" in result.stdout


def test_invalid_startup_flag_combination_fails_clearly(tmp_path) -> None:
    result = run_jeff("--json", cwd=tmp_path)

    assert result.returncode != 0
    assert "--json requires --command" in result.stderr
