from pathlib import Path

from tests.fixtures.entrypoint import REPO_ROOT, run_jeff


README_PATH = REPO_ROOT / "README.md"


def test_readme_documents_current_start_path_tests_and_deferrals() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "python -m jeff" in readme
    assert "python -m jeff --bootstrap-check" in readme
    assert "python -m jeff --command \"/show run-1\" --json" in readme
    assert (
        "python -m pytest -q tests/smoke/test_bootstrap_smoke.py "
        "tests/smoke/test_cli_entry_smoke.py tests/smoke/test_quickstart_paths.py"
    ) in readme
    assert "- GUI" in readme
    assert "- broad API bridge" in readme
    assert "- advanced memory backend" in readme
    assert "- autonomous continuation" in readme


def test_documented_bootstrap_check_command_works() -> None:
    result = run_jeff("--bootstrap-check")

    assert result.returncode == 0
    assert "bootstrap checks passed" in result.stdout
    assert "persisted runtime interface context bootstrapped" in result.stdout


def test_documented_show_json_quickstart_command_works() -> None:
    result = run_jeff("--command", "/show run-1", "--json")

    assert result.returncode == 0
    assert "\"view\": \"run_show\"" in result.stdout
    assert "\"run_id\": \"run-1\"" in result.stdout
