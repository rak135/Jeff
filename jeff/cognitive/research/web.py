"""Bounded web source acquisition for research."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from html import unescape
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
_PUBLISHED_META_KEYS = frozenset(
    {
        "article:published_time",
        "og:published_time",
        "datepublished",
        "publishdate",
        "pubdate",
        "dc.date",
        "dc.date.issued",
        "parsely-pub-date",
    }
)
_PUBLISHED_AT_CACHE: dict[tuple[str, int], str | None] = {}


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

            _PUBLISHED_AT_CACHE.pop((normalized_url, research_request.max_chars_per_page), None)
            fetched_excerpt = _fetch_web_page_excerpt(normalized_url, max_chars=research_request.max_chars_per_page)
            cleaned_fetched_excerpt = (
                _clean_web_excerpt_text(fetched_excerpt, max_chars=research_request.max_chars_per_page)
                if fetched_excerpt
                else None
            )
            search_snippet = _clean_web_excerpt_text(result.snippet or "", max_chars=research_request.max_chars_per_page)
            snippet = _snippet_from_text(cleaned_fetched_excerpt or search_snippet or "", max_chars=280)
            if not snippet:
                continue
            sources.append(
                SourceItem(
                    source_id=_stable_web_source_id(normalized_url),
                    source_type="web",
                    title=result.title or normalized_url,
                    locator=normalized_url,
                    snippet=snippet,
                    published_at=_PUBLISHED_AT_CACHE.get((normalized_url, research_request.max_chars_per_page)),
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
    debug_emitter=None,
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
        debug_emitter=debug_emitter,
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

    published_at = _extract_published_at(raw_text, content_type=content_type)
    _PUBLISHED_AT_CACHE[(url, max_chars)] = published_at

    if "html" in content_type.lower():
        text = _clean_html_excerpt(raw_text, max_chars=max_chars)
    elif "json" in content_type.lower():
        text = _clean_web_excerpt_text(_json_excerpt(raw_text), max_chars=max_chars)
    else:
        text = _clean_web_excerpt_text(raw_text, max_chars=max_chars)

    if not text:
        return None
    return text[:max_chars]


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
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "template", "svg"} and self._ignored_depth > 0:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0:
            self._parts.append(data)

    @classmethod
    def extract(cls, html: str) -> str:
        parser = cls()
        parser.feed(html)
        return " ".join(parser._parts)


class _HTMLMetadataExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta_candidates: list[str] = []
        self.json_ld_blocks: list[str] = []
        self._capturing_json_ld = False
        self._json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value for key, value in attrs if value is not None}
        if tag == "meta":
            content = attributes.get("content")
            key_candidates = (
                attributes.get("property"),
                attributes.get("name"),
                attributes.get("itemprop"),
            )
            if content is not None and any((key or "").lower() in _PUBLISHED_META_KEYS for key in key_candidates):
                self.meta_candidates.append(content)
        elif tag == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self._capturing_json_ld = True
            self._json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._capturing_json_ld:
            block = "".join(self._json_ld_parts).strip()
            if block:
                self.json_ld_blocks.append(block)
            self._capturing_json_ld = False
            self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        if self._capturing_json_ld:
            self._json_ld_parts.append(data)


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


def _clean_html_excerpt(html_text: str, *, max_chars: int) -> str | None:
    extracted = _HTMLTextExtractor.extract(html_text)
    cleaned = _clean_web_excerpt_text(extracted, max_chars=max_chars)
    if cleaned:
        return cleaned
    fallback = _clean_web_excerpt_text(_strip_obvious_markup(html_text), max_chars=max_chars)
    return fallback or None


def _clean_web_excerpt_text(text: str, *, max_chars: int) -> str:
    normalized = unescape(text).replace("\xa0", " ")
    normalized = re.sub(r"<!--.*?-->", " ", normalized, flags=re.DOTALL)
    parts = re.split(r"[\r\n]+|(?<=[.!?])\s+", normalized)
    cleaned_parts: list[str] = []
    for part in parts:
        compact = re.sub(r"\s+", " ", part).strip(" \t|:-")
        if not compact:
            continue
        if _looks_like_web_sludge(compact):
            continue
        cleaned_parts.append(compact)

    cleaned = re.sub(r"\s+", " ", " ".join(cleaned_parts)).strip()
    if not cleaned:
        cleaned = re.sub(r"\s+", " ", normalized).strip()
    return cleaned[:max_chars]


def _looks_like_web_sludge(text: str) -> bool:
    lowered = text.lower()
    if "<" in text and ">" in text:
        return True
    if ("{" in text and "}" in text and ";" in text) or lowered.startswith("@media"):
        return True
    if any(token in lowered for token in ("function(", "window.", "document.", "var ", "let ", "const ")):
        return True
    if re.fullmatch(r"[.#a-z0-9_\-\s,:;{}()%/]+", lowered) and ("{" in text or "}" in text):
        return True
    return False


def _strip_obvious_markup(text: str) -> str:
    without_blocks = re.sub(
        r"(?is)<(script|style|noscript|template|svg)[^>]*>.*?</\1>",
        " ",
        text,
    )
    without_tags = re.sub(r"(?is)<[^>]+>", " ", without_blocks)
    return unescape(without_tags)


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


def _extract_published_at(text: str, *, content_type: str) -> str | None:
    if "html" in content_type.lower():
        return _extract_published_at_from_html(text)
    if "json" in content_type.lower():
        return _extract_published_at_from_json_ld(text)
    return None


def _extract_published_at_from_html(html_text: str) -> str | None:
    parser = _HTMLMetadataExtractor()
    parser.feed(html_text)
    candidates = [_normalize_published_at(item) for item in parser.meta_candidates]
    for block in parser.json_ld_blocks:
        candidates.append(_extract_published_at_from_json_ld(block))
    normalized = sorted({item for item in candidates if item is not None})
    if len(normalized) != 1:
        return None
    return normalized[0]


def _extract_published_at_from_json_ld(text: str) -> str | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    candidates = [_normalize_published_at(value) for value in _find_date_published_values(parsed)]
    normalized = sorted({item for item in candidates if item is not None})
    if len(normalized) != 1:
        return None
    return normalized[0]


def _find_date_published_values(node: object) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "datePublished" and isinstance(value, str):
                values.append(value)
            values.extend(_find_date_published_values(value))
    elif isinstance(node, list):
        for item in node:
            values.extend(_find_date_published_values(item))
    return tuple(values)


def _normalize_published_at(value: str) -> str | None:
    candidate = value.strip()
    if not candidate:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", candidate):
        return candidate

    iso_candidate = candidate.replace("Z", "+00:00") if candidate.endswith("Z") else candidate
    try:
        parsed = datetime.fromisoformat(iso_candidate)
    except ValueError:
        return None

    if parsed.microsecond:
        parsed = parsed.replace(microsecond=0)
    return parsed.isoformat()
