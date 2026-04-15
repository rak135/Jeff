from pathlib import Path

from jeff.cognitive import ResearchRequest, collect_document_sources, run_document_research
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    build_infrastructure_services,
)
from tests.fixtures.research import bounded_research_text_from_payload


def test_local_documents_and_fake_default_adapter_drive_end_to_end_research(tmp_path: Path) -> None:
    document = tmp_path / "plan.md"
    document.write_text(
        "The bounded plan keeps the rollout stable.\n"
        "The bounded plan avoids widening the surface.\n",
        encoding="utf-8",
    )
    request = ResearchRequest(
        question="What does the bounded plan support?",
        document_paths=(str(document),),
        source_mode="local_documents",
    )
    source_id = collect_document_sources(request)[0].source_id

    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="fake-model",
                    fake_text_response=bounded_research_text_from_payload(
                        {
                        "summary": "The documents support a bounded rollout.",
                        "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": ["S1"]}],
                        "inferences": ["A narrow implementation remains better supported."],
                        "uncertainties": ["No external validation was performed."],
                        "recommendation": "Proceed with the bounded path.",
                        }
                    ),
                ),
            ),
        )
    )

    artifact = run_document_research(request, services)

    assert artifact.summary == "The documents support a bounded rollout."
    assert artifact.source_ids == (source_id,)


def test_explicit_adapter_selection_works_with_multiple_registered_fake_adapters(
    tmp_path: Path,
) -> None:
    document = tmp_path / "notes.md"
    document.write_text(
        "The secondary note says the bounded path is safer.\n",
        encoding="utf-8",
    )
    request = ResearchRequest(
        question="What does the bounded path support?",
        document_paths=(str(document),),
        source_mode="local_documents",
    )
    source_id = collect_document_sources(request)[0].source_id

    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="fake-model",
                    fake_text_response=bounded_research_text_from_payload(
                        {
                        "summary": "Default summary.",
                        "findings": [{"text": "Default finding", "source_refs": ["S1"]}],
                        "inferences": [],
                        "uncertainties": [],
                        "recommendation": None,
                        }
                    ),
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-secondary",
                    model_name="fake-model-2",
                    fake_text_response=bounded_research_text_from_payload(
                        {
                        "summary": "Secondary summary.",
                        "findings": [{"text": "Secondary finding", "source_refs": ["S1"]}],
                        "inferences": ["Secondary inference"],
                        "uncertainties": ["Secondary uncertainty"],
                        "recommendation": "Use the secondary adapter.",
                        }
                    ),
                ),
            ),
        )
    )

    artifact = run_document_research(request, services, adapter_id="fake-secondary")

    assert artifact.summary == "Secondary summary."
    assert artifact.findings[0].text == "Secondary finding"
