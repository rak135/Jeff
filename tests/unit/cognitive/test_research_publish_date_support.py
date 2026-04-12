import json
from pathlib import Path

from jeff.cognitive import (
    EvidenceItem,
    ResearchArtifact,
    ResearchArtifactStore,
    ResearchFinding,
    ResearchRequest,
    SourceItem,
    build_research_artifact_record,
)
from jeff.cognitive.research import web as web_module
from jeff.cognitive.research.contracts import EvidencePack


def test_publish_date_is_extracted_from_bounded_metadata_when_clearly_present() -> None:
    html = """
    <html>
      <head>
        <meta property="article:published_time" content="2026-04-12T10:30:00Z" />
        <script type="application/ld+json">
          {"@type":"Article","datePublished":"2026-04-12T10:30:00Z"}
        </script>
      </head>
      <body><article>Bounded support text.</article></body>
    </html>
    """

    published_at = web_module._extract_published_at_from_html(html)

    assert published_at == "2026-04-12T10:30:00+00:00"


def test_ambiguous_or_noisy_publish_date_cases_fail_safely_to_none() -> None:
    html = """
    <html>
      <head>
        <meta property="article:published_time" content="2026-04-12T10:30:00Z" />
        <script type="application/ld+json">
          {"@type":"Article","datePublished":"2026-04-13T10:30:00Z"}
        </script>
      </head>
    </html>
    """

    published_at = web_module._extract_published_at_from_html(html)

    assert published_at is None


def test_published_at_is_not_fabricated_from_missing_data() -> None:
    html = "<html><body><p>Bounded support text only.</p></body></html>"

    published_at = web_module._extract_published_at_from_html(html)

    assert published_at is None


def test_old_no_date_source_records_remain_valid(tmp_path: Path) -> None:
    store = ResearchArtifactStore(tmp_path)
    payload = {
        "artifact_id": "research-old",
        "project_id": "project-1",
        "work_unit_id": "wu-1",
        "run_id": "run-1",
        "question": "What does the bounded source support?",
        "source_mode": "web",
        "summary": "Older record without published_at still loads.",
        "findings": [{"text": "Older finding", "source_refs": ["source-1"]}],
        "inferences": [],
        "uncertainties": [],
        "recommendation": None,
        "source_ids": ["source-1"],
        "source_items": [
            {
                "source_id": "source-1",
                "source_type": "web",
                "title": "Older source",
                "locator": "https://example.com/a",
                "snippet": "Older bounded support",
            }
        ],
        "evidence_items": [{"text": "Older bounded support", "source_refs": ["source-1"]}],
        "created_at": "2026-04-12T10:00:00+00:00",
        "schema_version": "1.0",
    }
    path = tmp_path / "research_artifacts" / "research-old.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    loaded = store.load("research-old")

    assert loaded.source_items[0].published_at is None


def test_persisted_record_round_trip_preserves_published_at_when_present(tmp_path: Path) -> None:
    store = ResearchArtifactStore(tmp_path)
    record = build_research_artifact_record(_request(), _evidence_pack(), _artifact())
    store.save(record)

    loaded = store.load(record.artifact_id)

    assert loaded.source_items[0].published_at == "2026-04-12"


def _request() -> ResearchRequest:
    return ResearchRequest(
        question="What does the bounded source support?",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        source_mode="web",
    )


def _evidence_pack() -> EvidencePack:
    return EvidencePack(
        question="What does the bounded source support?",
        sources=(
            SourceItem(
                source_id="source-1",
                source_type="web",
                title="Bounded article",
                locator="https://example.com/a",
                snippet="The bounded rollout remains stable.",
                published_at="2026-04-12",
            ),
        ),
        evidence_items=(EvidenceItem(text="The bounded rollout remains stable.", source_refs=("source-1",)),),
    )


def _artifact() -> ResearchArtifact:
    return ResearchArtifact(
        question="What does the bounded source support?",
        summary="The bounded source supports a narrow rollout.",
        findings=(ResearchFinding(text="The article supports the bounded rollout.", source_refs=("source-1",)),),
        inferences=("A narrow path remains better supported.",),
        uncertainties=(),
        recommendation=None,
        source_ids=("source-1",),
    )
