"""Tests for refactored research debug helpers and source collection."""

import pytest

from jeff.cognitive.research.debug import (
    emit_research_debug_event,
    finding_source_refs_summary,
    summarize_values,
)
from jeff.cognitive.research.documents import (
    discover_document_sources,
    extract_document_source,
)
from jeff.cognitive.research.web import (
    discover_web_sources,
    extract_web_source,
)
from jeff.cognitive.research.contracts import ResearchFinding


def test_shared_debug_emitter_captures_events():
    """Test that shared emit_research_debug_event works correctly."""
    events: list[dict] = []

    def collect_event(event: dict) -> None:
        events.append(event)

    emit_research_debug_event(collect_event, "test_checkpoint", test_value="test_data")

    assert len(events) == 1
    assert events[0]["domain"] == "research"
    assert events[0]["checkpoint"] == "test_checkpoint"
    assert events[0]["payload"]["test_value"] == "test_data"


def test_shared_debug_emitter_handles_none():
    """Test that emit_research_debug_event safely ignores None emitter."""
    # Should not raise
    emit_research_debug_event(None, "test")


def test_summarize_values_within_limit():
    """Test summarize_values when values are under the limit."""
    values = ("a", "b", "c")
    result = summarize_values(values, limit=5)
    assert result == ["a", "b", "c"]


def test_summarize_values_exceeds_limit():
    """Test summarize_values when values exceed the limit."""
    values = tuple(f"item{i}" for i in range(10))
    result = summarize_values(values, limit=5)
    assert len(result) == 6
    assert result[:5] == [f"item{i}" for i in range(5)]
    assert result[5] == "+5 more"


def test_finding_source_refs_summary():
    """Test finding_source_refs_summary formatting."""
    findings = (
        ResearchFinding(text="Finding 1", source_refs=("src1", "src2")),
        ResearchFinding(text="Finding 2", source_refs=("src3",)),
    )
    result = finding_source_refs_summary(findings)
    assert result == ["src1,src2", "src3"]


def test_web_discovery_phase(tmp_path):
    """Test web source discovery produces discovered sources without fetching."""
    # This is a minimal test that discovery returns correct structure
    # without making actual network calls (would use mocked _search_web_query in real test)
    # For now, we just verify the function signature and error handling
    with pytest.raises(ValueError, match="web discovery requires explicit web_queries"):
        discover_web_sources(web_queries=(), max_results=10, max_pages=5)


def test_document_discovery_phase(tmp_path):
    """Test document source discovery enumerates paths without reading content."""
    document = tmp_path / "test.md"
    document.write_text("Test content", encoding="utf-8")

    discovered = discover_document_sources(
        document_paths=(str(tmp_path),),
        include_extensions=(".md",),
        max_files=10,
    )

    assert len(discovered) == 1
    assert discovered[0].path.name == "test.md"
    assert discovered[0].discovery_rank == 0


def test_document_extraction_phase(tmp_path):
    """Test document extraction reads and produces extracted source."""
    from jeff.cognitive.research.documents import _DiscoveredDocument

    document = tmp_path / "test.md"
    document.write_text("This is test content for extraction.", encoding="utf-8")

    discovered = _DiscoveredDocument(path=document, discovery_rank=0)
    extracted = extract_document_source(discovered, max_chars=1000)

    assert extracted is not None
    assert extracted.title == "test.md"
    assert extracted.source_id is not None
    assert "test content" in extracted.snippet


def test_document_extraction_handles_none():
    """Test that extract_document_source returns None for missing files."""
    from jeff.cognitive.research.documents import _DiscoveredDocument
    from pathlib import Path

    missing_document = _DiscoveredDocument(path=Path("/nonexistent/path.txt"), discovery_rank=0)
    extracted = extract_document_source(missing_document, max_chars=1000)

    assert extracted is None


def test_source_item_new_phase_02_fields():
    """Test that SourceItem accepts new Phase-02 optional fields."""
    from jeff.cognitive.research.contracts import SourceItem

    source = SourceItem(
        source_id="test-123",
        source_type="web",
        title="Test Source",
        locator="https://example.com",
        snippet="Test snippet",
        extractor_used="trafilatura",
        extraction_quality="good",
        domain="example.com",
        discovery_rank=1,
    )

    assert source.extractor_used == "trafilatura"
    assert source.extraction_quality == "good"
    assert source.domain == "example.com"
    assert source.discovery_rank == 1


def test_source_item_backwards_compatible():
    """Test that SourceItem without new fields still works."""
    from jeff.cognitive.research.contracts import SourceItem

    # Build source without new fields (like old code would)
    source = SourceItem(
        source_id="test-456",
        source_type="document",
        title="Old Style Source",
        locator="/path/to/file.md",
        snippet="Snippet",
    )

    # New fields should default to None
    assert source.extractor_used is None
    assert source.extraction_quality is None
    assert source.domain is None
    assert source.discovery_rank is None
    assert source.fetched_at is None


def test_source_item_discovery_rank_validation():
    """Test that discovery_rank must be non-negative integer."""
    from jeff.cognitive.research.contracts import SourceItem

    with pytest.raises(ValueError, match="discovery_rank must be non-negative"):
        SourceItem(
            source_id="test",
            source_type="web",
            discovery_rank=-1,
        )

    with pytest.raises(ValueError, match="discovery_rank must be an integer"):
        SourceItem(
            source_id="test",
            source_type="web",
            discovery_rank="not_an_int",  # type: ignore[arg-type]
        )
