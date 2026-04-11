"""Bounded web source acquisition for research."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib import parse, request

from jeff.infrastructure import InfrastructureServices

from .contracts import EvidenceItem, EvidencePack, ResearchArtifact, ResearchRequest, SourceItem
from .errors import ResearchSynthesisValidationError
from .synthesis import synthesize_research_with_runtime

_SEARCH_ENDPOINT = "https://html.duckduckgo.com/html/"
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "which",
    "with",
}
_CONTRADICTION_MARKERS = ("contradiction", "contradicts", "conflict", "conflicts", "inconsistent")


@dataclass(frozen=True, slots=True)
class _WebSearchResult:
    title: str
    url: str
    snippet: str | None = None


def collect_web_sources(research_request: ResearchRequest) -> tuple[SourceItem, ...]:
    if not research_request.web_queries:
        raise ValueError("web source collection requires explicit web_queries")

    sources: list[SourceItem] = []
    seen_urls: set[str] = set()
    remaining_results = research_request.max_web_results

    for query in research_request.web_queries:
        if remaining_results <= 0 or len(sources) >= research_request.max_web_pages:
            break

        for result in _search_web_query(query, max_results=remaining_results):
            if len(sources) >= research_request.max_web_pages or remaining_results <= 0:
                break
            normalized_url = _normalize_url(result.url)
            if normalized_url is None:
                continue
            if normalized_url in seen_urls:
                continue
            seen_urls.add(normalized_url)
            remaining_results -= 1

            fetched_excerpt = _fetch_web_page_excerpt(normalized_url, max_chars=research_request.max_chars_per_page)
            snippet = _snippet_from_text(fetched_excerpt or result.snippet or "", max_chars=280)
            if not snippet:
                continue
            sources.append(
                SourceItem(
                    source_id=_stable_web_source_id(normalized_url),
                    source_type="web",
                    title=result.title or normalized_url,
                    locator=normalized_url,
                    snippet=snippet,
                )
            )

    return tuple(sources)


def build_web_evidence_pack(
    research_request: ResearchRequest,
    web_sources: tuple[SourceItem, ...],
) -> EvidencePack:
    if not web_sources:
        raise ValueError("web evidence pack requires at least one web source")

    query_tokens = _query_tokens(research_request.question, research_request.constraints, research_request.web_queries)
    scored_segments: list[tuple[int, int, int, str, str]] = []
    contradictions: list[str] = []

    for source_index, source in enumerate(web_sources):
        segments = _extract_segments(source.snippet or "")
        for segment_index, segment in enumerate(segments):
            score = _segment_score(segment, query_tokens)
            if score > 0:
                scored_segments.append((score, source_index, segment_index, source.source_id, segment))
            if _has_contradiction_marker(segment, query_tokens):
                contradictions.append(f"{source.source_id}: {segment}")

    scored_segments.sort(key=lambda item: (-item[0], item[1], item[2], item[3], item[4]))
    evidence_limit = research_request.max_web_evidence_items or research_request.max_evidence_items
    evidence_items = tuple(
        EvidenceItem(text=segment, source_refs=(source_id,))
        for _, _, _, source_id, segment in scored_segments[:evidence_limit]
    )

    uncertainties: list[str] = []
    if not evidence_items:
        uncertainties.append("No strong evidence found in the fetched web sources for the research question.")

    return EvidencePack(
        question=research_request.question,
        sources=web_sources,
        evidence_items=evidence_items,
        contradictions=tuple(contradictions),
        uncertainties=tuple(uncertainties),
        constraints=research_request.constraints,
    )


def run_web_research(
    research_request: ResearchRequest,
    infrastructure_services: InfrastructureServices,
    adapter_id: str | None = None,
) -> ResearchArtifact:
    sources = collect_web_sources(research_request)
    if not sources:
        raise ResearchSynthesisValidationError("no supported web sources were collected")

    evidence_pack = build_web_evidence_pack(research_request, sources)
    if not evidence_pack.evidence_items:
        raise ResearchSynthesisValidationError("no evidence items were extracted from collected web sources")

    return synthesize_research_with_runtime(
        research_request=research_request,
        evidence_pack=evidence_pack,
        infrastructure_services=infrastructure_services,
        adapter_id=adapter_id,
    )


def _search_web_query(query: str, *, max_results: int) -> tuple[_WebSearchResult, ...]:
    payload = parse.urlencode({"q": query})
    http_request = request.Request(
        f"{_SEARCH_ENDPOINT}?{payload}",
        headers={"User-Agent": "JeffResearch/0.1"},
        method="GET",
    )
    with request.urlopen(http_request, timeout=10) as response:
        html = response.read().decode("utf-8", errors="replace")
    parser = _DuckDuckGoResultParser()
    parser.feed(html)
    return tuple(parser.results[:max_results])


def _fetch_web_page_excerpt(url: str, *, max_chars: int) -> str | None:
    http_request = request.Request(
        url,
        headers={"User-Agent": "JeffResearch/0.1"},
        method="GET",
    )
    try:
        with request.urlopen(http_request, timeout=10) as response:
            content_type = response.headers.get("Content-Type", "")
            raw_text = response.read(max_chars * 3).decode("utf-8", errors="replace")
    except OSError:
        return None

    if "html" in content_type.lower():
        text = _HTMLTextExtractor.extract(raw_text)
    elif "json" in content_type.lower():
        text = _json_excerpt(raw_text)
    else:
        text = raw_text

    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return None
    return compact[:max_chars]


class _DuckDuckGoResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[_WebSearchResult] = []
        self._current_link: str | None = None
        self._current_title: list[str] = []
        self._capturing_title = False
        self._pending_result: _WebSearchResult | None = None
        self._capturing_snippet = False
        self._current_snippet: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class", "") or ""
        if tag == "a" and "result__a" in classes and attributes.get("href"):
            self._current_link = attributes["href"]
            self._current_title = []
            self._capturing_title = True
        elif tag in {"a", "div"} and "result__snippet" in classes:
            self._capturing_snippet = True
            self._current_snippet = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capturing_title and self._current_link:
            title = re.sub(r"\s+", " ", "".join(self._current_title)).strip()
            if title:
                self._pending_result = _WebSearchResult(title=title, url=self._current_link, snippet=None)
                self.results.append(self._pending_result)
            self._capturing_title = False
            self._current_link = None
            self._current_title = []
        elif tag in {"a", "div"} and self._capturing_snippet:
            snippet = re.sub(r"\s+", " ", "".join(self._current_snippet)).strip()
            if snippet and self._pending_result is not None and self._pending_result.snippet is None:
                self.results[-1] = _WebSearchResult(
                    title=self._pending_result.title,
                    url=self._pending_result.url,
                    snippet=snippet,
                )
                self._pending_result = self.results[-1]
            self._capturing_snippet = False
            self._current_snippet = []

    def handle_data(self, data: str) -> None:
        if self._capturing_title:
            self._current_title.append(data)
        if self._capturing_snippet:
            self._current_snippet.append(data)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    @classmethod
    def extract(cls, html: str) -> str:
        parser = cls()
        parser.feed(html)
        return " ".join(parser._parts)


def _normalize_url(url: str) -> str | None:
    parsed = parse.urlparse(url.strip())
    if parsed.scheme in {"", "http", "https"} and parsed.path.startswith("/l/"):
        uddg = parse.parse_qs(parsed.query).get("uddg")
        if uddg:
            parsed = parse.urlparse(uddg[0])
    if parsed.scheme not in {"http", "https"}:
        return None
    return parse.urlunparse(parsed._replace(fragment=""))


def _stable_web_source_id(url: str) -> str:
    normalized = _normalize_url(url)
    if normalized is None:
        raise ValueError("web source id requires an http or https URL")
    normalized = normalized.lower()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"web-{digest}"


def _snippet_from_text(text: str, *, max_chars: int) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:max_chars]


def _extract_segments(text: str) -> tuple[str, ...]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return ()
    return tuple(segment.strip()[:400] for segment in re.split(r"(?<=[.!?])\s+", compact) if segment.strip())


def _query_tokens(question: str, constraints: tuple[str, ...], web_queries: tuple[str, ...]) -> tuple[str, ...]:
    combined = " ".join((question, *constraints, *web_queries)).lower()
    tokens: list[str] = []
    for token in re.findall(r"[a-z0-9_]+", combined):
        if token in _STOP_WORDS:
            continue
        if len(token) < 3 and not token.isdigit():
            continue
        if token not in tokens:
            tokens.append(token)
    return tuple(tokens)


def _segment_score(segment: str, query_tokens: tuple[str, ...]) -> int:
    lowered = segment.lower()
    return sum(1 for token in query_tokens if token in lowered)


def _has_contradiction_marker(segment: str, query_tokens: tuple[str, ...]) -> bool:
    lowered = segment.lower()
    if not any(marker in lowered for marker in _CONTRADICTION_MARKERS):
        return False
    if not query_tokens:
        return True
    return any(token in lowered for token in query_tokens)


def _json_excerpt(text: str) -> str:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(parsed, ensure_ascii=True)
