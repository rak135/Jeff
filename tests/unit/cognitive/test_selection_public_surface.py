from __future__ import annotations

from pathlib import Path

from jeff.cognitive import SelectionDisposition, SelectionRequest, SelectionResult
from jeff.cognitive.selection import SelectionDisposition as PackageSelectionDisposition
from jeff.cognitive.selection import SelectionRequest as PackageSelectionRequest
from jeff.cognitive.selection import SelectionResult as PackageSelectionResult
from jeff.cognitive.selection import run_selection
from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.core.schemas import Scope


def test_selection_public_surface_resolves_from_package_and_root_exports() -> None:
    assert SelectionRequest is PackageSelectionRequest
    assert SelectionResult is PackageSelectionResult
    assert SelectionDisposition == PackageSelectionDisposition
    assert callable(run_selection)


def test_selection_request_stays_centered_on_proposal_result() -> None:
    proposal_result = ProposalResult(
        request_id="proposal-request-1",
        scope=Scope(project_id="project-1", work_unit_id="wu-1"),
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type="direct_action",
                title="Do the bounded thing",
                why_now="It is the only serious option.",
                summary="Do the bounded thing",
            ),
        ),
        scarcity_reason="Only one serious option exists.",
    )

    request = SelectionRequest(
        request_id="selection-request-1",
        proposal_result=proposal_result,
    )

    assert request.considered_proposal_ids == ("proposal-1",)


def test_selection_contract_shape_avoids_permission_fields() -> None:
    field_names = set(SelectionResult.__dataclass_fields__)

    assert "approval" not in field_names
    assert "approved" not in field_names
    assert "readiness" not in field_names
    assert "permission" not in field_names


def test_flat_selection_module_is_replaced_by_package() -> None:
    selection_package_init = Path(__file__).resolve().parents[3] / "jeff" / "cognitive" / "selection" / "__init__.py"
    legacy_flat_module = Path(__file__).resolve().parents[3] / "jeff" / "cognitive" / "selection.py"

    assert selection_package_init.exists()
    assert not legacy_flat_module.exists()
