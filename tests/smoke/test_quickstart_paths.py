from pathlib import Path

from tests.fixtures.entrypoint import REPO_ROOT, run_jeff


README_PATH = REPO_ROOT / "README.md"


def test_readme_documents_current_start_path_tests_and_deferrals() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "python -m jeff" in readme
    assert "python -m jeff --bootstrap-check" in readme
    assert "python -m jeff --reset-runtime --bootstrap-check" in readme
    assert "python -m jeff --project project-1 --work wu-1 --command \"/run list\" --json" in readme
    assert (
        "python -m pytest -q tests/smoke/test_bootstrap_smoke.py "
        "tests/smoke/test_cli_entry_smoke.py tests/smoke/test_quickstart_paths.py"
    ) in readme
    assert "- GUI" in readme
    assert "- broad API bridge" in readme
    assert "- broader `/run` action families" in readme
    assert "- broad memory CLI or UX" in readme
    assert "- autonomous continuation" in readme


def test_readme_describes_persisted_runtime_and_session_local_scope() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "persisted local runtime workspace under `.jeff_runtime`" in readme
    assert "A local `jeff.runtime.toml` enables the bounded repo-local validation `/run <repo-local-validation-objective>` path" in readme
    assert "`/project use`, `/work use`, and `/run use` update session-local/process-local scope only." in readme


def test_documented_bootstrap_check_command_works(tmp_path) -> None:
    result = run_jeff("--bootstrap-check", cwd=tmp_path)

    assert result.returncode == 0
    assert "bootstrap checks passed" in result.stdout
    assert "persisted runtime interface context bootstrapped" in result.stdout


def test_documented_show_json_quickstart_command_works(tmp_path) -> None:
    result = run_jeff("--project", "project-1", "--work", "wu-1", "--command", "/run list", "--json", cwd=tmp_path)

    assert result.returncode == 0
    assert "\"view\": \"run_list\"" in result.stdout
    assert '"runs": []' in result.stdout
