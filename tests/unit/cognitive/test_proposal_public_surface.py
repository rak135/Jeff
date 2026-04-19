from typing import get_type_hints

import jeff.cognitive as cognitive_module
import jeff.cognitive.proposal as proposal_module
from jeff.cognitive import ProposalResult as CognitiveProposalResult
from jeff.cognitive import ProposalInputPackage as CognitiveProposalInputPackage
from jeff.cognitive import ProposalGenerationBridgeRequest as CognitiveProposalGenerationBridgeRequest
from jeff.cognitive import build_and_run_proposal_generation as CognitiveBuildAndRunProposalGeneration
from jeff.cognitive import run_proposal_generation_pipeline as CognitiveRunProposalGenerationPipeline
from jeff.cognitive import consume_proposal_support_package as CognitiveConsumeProposalSupportPackage
from jeff.cognitive import validate_proposal_generation_result as CognitiveValidateProposalGenerationResult
from jeff.cognitive.proposal import (
    ProposalGenerationBridgeRequest,
    ProposalInputPackage,
    ProposalResult,
    ProposalResultOption,
    ProposalSupportConsumerRequest,
    ProposalType,
    build_and_run_proposal_generation,
    consume_proposal_support_package,
    run_proposal_generation_pipeline,
    validate_proposal_generation_result,
)
from jeff.cognitive.proposal.api import run_proposal_generation_pipeline as ModuleRunProposalGenerationPipeline
from jeff.cognitive.proposal.proposal_generation_bridge import (
    ProposalGenerationBridgeRequest as ModuleProposalGenerationBridgeRequest,
)
from jeff.cognitive.proposal.proposal_generation_bridge import (
    build_and_run_proposal_generation as ModuleBuildAndRunProposalGeneration,
)
from jeff.cognitive.proposal.proposal_support_package_consumer import (
    ProposalInputPackage as ConsumerProposalInputPackage,
)
from jeff.cognitive.proposal.proposal_support_package_consumer import (
    ProposalSupportConsumerRequest as ModuleProposalSupportConsumerRequest,
)
from jeff.cognitive.proposal.proposal_support_package_consumer import (
    consume_proposal_support_package as ModuleConsumeProposalSupportPackage,
)
from jeff.cognitive.proposal.contracts import ProposalResult as ContractProposalResult
from jeff.cognitive.proposal.contracts import ProposalResultOption as ContractProposalResultOption
from jeff.cognitive.proposal.validation import validate_proposal_generation_result as ModuleValidateProposalGenerationResult


def test_primary_proposal_public_imports_resolve_to_canonical_contracts() -> None:
    assert ProposalResult is ContractProposalResult
    assert CognitiveProposalResult is ProposalResult


def test_proposal_result_option_alias_is_available_through_contracts() -> None:
    assert ProposalResultOption is ContractProposalResultOption


def test_proposal_type_alias_remains_available_through_contracts() -> None:
    annotation = get_type_hints(ContractProposalResultOption)["proposal_type"]

    assert annotation == ProposalType


def test_proposal_validation_surface_remains_publicly_available() -> None:
    assert validate_proposal_generation_result is ModuleValidateProposalGenerationResult
    assert CognitiveValidateProposalGenerationResult is validate_proposal_generation_result


def test_proposal_pipeline_entry_remains_publicly_available() -> None:
    assert run_proposal_generation_pipeline is ModuleRunProposalGenerationPipeline
    assert CognitiveRunProposalGenerationPipeline is run_proposal_generation_pipeline


def test_proposal_generation_bridge_surface_remains_publicly_available() -> None:
    assert ProposalGenerationBridgeRequest is ModuleProposalGenerationBridgeRequest
    assert CognitiveProposalGenerationBridgeRequest is ProposalGenerationBridgeRequest
    assert build_and_run_proposal_generation is ModuleBuildAndRunProposalGeneration
    assert CognitiveBuildAndRunProposalGeneration is build_and_run_proposal_generation


def test_proposal_support_consumer_surface_remains_publicly_available() -> None:
    assert ProposalInputPackage is ConsumerProposalInputPackage
    assert CognitiveProposalInputPackage is ProposalInputPackage
    assert ProposalSupportConsumerRequest is ModuleProposalSupportConsumerRequest
    assert consume_proposal_support_package is ModuleConsumeProposalSupportPackage
    assert CognitiveConsumeProposalSupportPackage is consume_proposal_support_package


def test_legacy_option_and_set_shapes_are_removed_from_public_api() -> None:
    assert not hasattr(proposal_module, "ProposalOption")
    assert not hasattr(proposal_module, "ProposalSet")
    assert not hasattr(cognitive_module, "ProposalOption")
    assert not hasattr(cognitive_module, "ProposalSet")



def test_demoted_legacy_result_shapes_are_not_public_primary_exports() -> None:
    assert not hasattr(proposal_module, "ProposalDownstreamHandoff")
    assert not hasattr(proposal_module, "ValidatedProposalGenerationResult")
    assert not hasattr(proposal_module, "ValidatedProposalOption")
    assert not hasattr(cognitive_module, "ProposalDownstreamHandoff")
    assert not hasattr(cognitive_module, "ValidatedProposalGenerationResult")
    assert not hasattr(cognitive_module, "ValidatedProposalOption")
