from jeff.cognitive import (
    build_web_evidence_pack,
    collect_web_sources,
)
from jeff.cognitive.research.contracts import ResearchRequest
from jeff.cognitive.research import web as web_module


def test_collect_web_sources_uses_only_explicit_queries(monkeypatch) -> None:
    seen_queries: list[str] = []

    def fake_search(query: str, *, max_results: int):
        seen_queries.append(query)
        return (
            web_module._WebSearchResult(
                title="Bounded Result",
                url="https://example.com/a",
                snippet="Bounded plan support text.",
            ),
        )

    monkeypatch.setattr(web_module, "_search_web_query", fake_search)
    monkeypatch.setattr(web_module, "_fetch_web_page_excerpt", lambda url, *, max_chars: "Bounded plan support text.")

    sources = collect_web_sources(
        ResearchRequest(
            question="What does the bounded plan support?",
            web_queries=("bounded plan", "ignored due to page cap"),
            max_web_pages=1,
        )
    )

    assert seen_queries == ["bounded plan"]
    assert len(sources) == 1


def test_collect_web_sources_respects_result_and_page_limits(monkeypatch) -> None:
    def fake_search(query: str, *, max_results: int):
        return (
            web_module._WebSearchResult(title="One", url="https://example.com/1", snippet="one"),
            web_module._WebSearchResult(title="Two", url="https://example.com/2", snippet="two"),
            web_module._WebSearchResult(title="Three", url="https://example.com/3", snippet="three"),
        )[:max_results]

    monkeypatch.setattr(web_module, "_search_web_query", fake_search)
    monkeypatch.setattr(web_module, "_fetch_web_page_excerpt", lambda url, *, max_chars: f"excerpt:{url}")

    sources = collect_web_sources(
        ResearchRequest(
            question="What is bounded?",
            web_queries=("bounded",),
            max_web_results=2,
            max_web_pages=1,
        )
    )

    assert len(sources) == 1
    assert sources[0].locator == "https://example.com/1"


def test_collect_web_sources_preserves_provenance_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        web_module,
        "_search_web_query",
        lambda query, *, max_results: (
            web_module._WebSearchResult(
                title="Bounded Result",
                url="https://example.com/path#fragment",
                snippet="Snippet text",
            ),
        ),
    )
    monkeypatch.setattr(web_module, "_fetch_web_page_excerpt", lambda url, *, max_chars: "Fetched excerpt text.")

    source = collect_web_sources(
        ResearchRequest(question="What is bounded?", web_queries=("bounded",))
    )[0]

    assert source.source_type == "web"
    assert source.source_id.startswith("web-")
    assert source.title == "Bounded Result"
    assert source.locator == "https://example.com/path"
    assert source.snippet == "Fetched excerpt text."


def test_collect_web_sources_respects_max_chars_per_page(monkeypatch) -> None:
    observed_max_chars: list[int] = []

    monkeypatch.setattr(
        web_module,
        "_search_web_query",
        lambda query, *, max_results: (
            web_module._WebSearchResult(title="Bounded Result", url="https://example.com/a", snippet="short"),
        ),
    )

    def fake_fetch(url: str, *, max_chars: int):
        observed_max_chars.append(max_chars)
        return "x" * max_chars

    monkeypatch.setattr(web_module, "_fetch_web_page_excerpt", fake_fetch)

    source = collect_web_sources(
        ResearchRequest(
            question="What is bounded?",
            web_queries=("bounded",),
            max_chars_per_page=123,
        )
    )[0]

    assert observed_max_chars == [123]
    assert len(source.snippet) == 123 if 123 < 280 else 280


def test_collect_web_sources_keeps_deterministic_order(monkeypatch) -> None:
    def fake_search(query: str, *, max_results: int):
        return (
            web_module._WebSearchResult(title="A", url="https://example.com/a", snippet="a"),
            web_module._WebSearchResult(title="B", url="https://example.com/b", snippet="b"),
        )

    monkeypatch.setattr(web_module, "_search_web_query", fake_search)
    monkeypatch.setattr(web_module, "_fetch_web_page_excerpt", lambda url, *, max_chars: url.rsplit("/", 1)[-1])

    sources = collect_web_sources(
        ResearchRequest(
            question="What is bounded?",
            web_queries=("first", "second"),
            max_web_pages=3,
        )
    )

    assert tuple(source.locator for source in sources) == (
        "https://example.com/a",
        "https://example.com/b",
    )


def test_build_web_evidence_pack_produces_bounded_evidence_tied_to_real_source_refs() -> None:
    request = ResearchRequest(
        question="What does the bounded plan support?",
        web_queries=("bounded plan",),
        max_web_evidence_items=1,
    )
    sources = (
        web_module.SourceItem(
            source_id="web-1",
            source_type="web",
            title="A",
            locator="https://example.com/a",
            snippet="The bounded plan supports a stable rollout. It remains narrow.",
        ),
        web_module.SourceItem(
            source_id="web-2",
            source_type="web",
            title="B",
            locator="https://example.com/b",
            snippet="General unrelated chatter.",
        ),
    )

    evidence_pack = build_web_evidence_pack(request, sources)

    assert len(evidence_pack.evidence_items) == 1
    assert evidence_pack.evidence_items[0].source_refs == ("web-1",)


def test_build_web_evidence_pack_does_not_invent_evidence_when_query_is_unsupported() -> None:
    request = ResearchRequest(
        question="What database migration risk exists?",
        web_queries=("database migration risk",),
    )
    sources = (
        web_module.SourceItem(
            source_id="web-1",
            source_type="web",
            title="A",
            locator="https://example.com/a",
            snippet="Apples and oranges are discussed here.",
        ),
    )

    evidence_pack = build_web_evidence_pack(request, sources)

    assert evidence_pack.evidence_items == ()
    assert any("No strong evidence found" in item for item in evidence_pack.uncertainties)


def test_build_web_evidence_pack_surfaces_uncertainty_when_no_strong_evidence() -> None:
    request = ResearchRequest(
        question="What contradiction exists in the current plan?",
        web_queries=("current plan contradiction",),
    )
    sources = (
        web_module.SourceItem(
            source_id="web-1",
            source_type="web",
            title="A",
            locator="https://example.com/a",
            snippet="Contradiction: the current plan conflicts with the published constraint.",
        ),
    )

    evidence_pack = build_web_evidence_pack(request, sources)

    assert evidence_pack.contradictions
    assert evidence_pack.contradictions[0].startswith("web-1:")
