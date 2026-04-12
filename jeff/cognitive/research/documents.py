"""Bounded local-document source acquisition for research."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from jeff.infrastructure import InfrastructureServices

from .contracts import EvidenceItem, EvidencePack, ResearchArtifact, ResearchRequest, SourceItem
from .errors import ResearchSynthesisValidationError
from .synthesis import synthesize_research_with_runtime

SUPPORTED_DOCUMENT_EXTENSIONS = frozenset(
    {
        ".md",
        ".txt",
        ".rst",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".csv",
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".go",
        ".rs",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".html",
        ".css",
        ".xml",
        ".sql",
    }
)

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


def collect_document_sources(research_request: ResearchRequest) -> tuple[SourceItem, ...]:
    if not research_request.document_paths:
        raise ValueError("document source collection requires explicit document_paths")

    allowed_extensions = (
        set(SUPPORTED_DOCUMENT_EXTENSIONS).intersection(research_request.include_extensions)
        if research_request.include_extensions
        else set(SUPPORTED_DOCUMENT_EXTENSIONS)
    )

    collected: list[SourceItem] = []
    for raw_path in research_request.document_paths:
        if len(collected) >= research_request.max_files:
            break

        for candidate in _expand_explicit_path(Path(raw_path)):
            if len(collected) >= research_request.max_files:
                break
            if candidate.suffix.lower() not in allowed_extensions:
                continue
            text = _read_document_text(candidate, max_chars=research_request.max_chars_per_file)
            if text is None:
                continue
            collected.append(
                SourceItem(
                    source_id=_stable_source_id(candidate),
                    source_type="document",
                    title=candidate.name,
                    locator=str(candidate.resolve()),
                    snippet=_snippet_from_text(text),
                )
            )

    return tuple(collected)


def build_document_evidence_pack(
    research_request: ResearchRequest,
    document_sources: tuple[SourceItem, ...],
) -> EvidencePack:
    if not document_sources:
        raise ValueError("document evidence pack requires at least one document source")

    query_tokens = _query_tokens(research_request.question, research_request.constraints)
    scored_segments: list[tuple[int, int, int, str, str]] = []
    contradictions: list[str] = []

    for source_index, source in enumerate(document_sources):
        source_text = _text_for_source(source, max_chars=research_request.max_chars_per_file)
        segments = _extract_segments(source_text or source.snippet or "")
        for segment_index, segment in enumerate(segments):
            score = _segment_score(segment, query_tokens)
            if score > 0:
                scored_segments.append((score, source_index, segment_index, source.source_id, segment))
            if _has_contradiction_marker(segment, query_tokens):
                contradictions.append(f"{source.source_id}: {segment}")

    scored_segments.sort(key=lambda item: (-item[0], item[1], item[2], item[3], item[4]))
    evidence_items = tuple(
        EvidenceItem(text=segment, source_refs=(source_id,))
        for _, _, _, source_id, segment in scored_segments[: research_request.max_evidence_items]
    )

    uncertainties: list[str] = []
    if not evidence_items:
        uncertainties.append("No strong evidence found in the provided documents for the research question.")

    return EvidencePack(
        question=research_request.question,
        sources=document_sources,
        evidence_items=evidence_items,
        contradictions=tuple(contradictions),
        uncertainties=tuple(uncertainties),
        constraints=research_request.constraints,
    )


def run_document_research(
    research_request: ResearchRequest,
    infrastructure_services: InfrastructureServices,
    adapter_id: str | None = None,
    debug_emitter=None,
) -> ResearchArtifact:
    sources = collect_document_sources(research_request)
    if not sources:
        raise ResearchSynthesisValidationError("no supported document sources were collected")

    evidence_pack = build_document_evidence_pack(research_request, sources)
    if not evidence_pack.evidence_items:
        raise ResearchSynthesisValidationError("no evidence items were extracted from collected documents")

    return synthesize_research_with_runtime(
        research_request=research_request,
        evidence_pack=evidence_pack,
        infrastructure_services=infrastructure_services,
        adapter_id=adapter_id,
        debug_emitter=debug_emitter,
    )


def _expand_explicit_path(path: Path) -> tuple[Path, ...]:
    resolved = path.expanduser()
    if resolved.is_file():
        return (resolved,)
    if resolved.is_dir():
        return tuple(sorted((child for child in resolved.rglob("*") if child.is_file()), key=lambda item: str(item)))
    return ()


def _read_document_text(path: Path, *, max_chars: int) -> str | None:
    try:
        with path.open("rb") as handle:
            probe = handle.read(min(max_chars, 4096))
        if b"\x00" in probe:
            return None
        with path.open("r", encoding="utf-8") as handle:
            text = handle.read(max_chars)
    except (OSError, UnicodeDecodeError):
        return None

    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return None
    return normalized


def _stable_source_id(path: Path) -> str:
    normalized = str(path.resolve()).replace("\\", "/").lower()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"document-{digest}"


def _snippet_from_text(text: str, *, max_chars: int = 280) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:max_chars]


def _text_for_source(source: SourceItem, *, max_chars: int) -> str | None:
    if source.locator is None:
        return source.snippet
    return _read_document_text(Path(source.locator), max_chars=max_chars) or source.snippet


def _extract_segments(text: str) -> tuple[str, ...]:
    if not text.strip():
        return ()

    paragraph_candidates = [segment.strip() for segment in re.split(r"\n\s*\n", text) if segment.strip()]
    raw_segments = (
        paragraph_candidates
        if len(paragraph_candidates) > 1
        else [line.strip() for line in text.splitlines() if line.strip()]
    )

    segments: list[str] = []
    for segment in raw_segments:
        compact = re.sub(r"\s+", " ", segment).strip()
        if compact:
            segments.append(compact[:400])
    return tuple(segments)


def _query_tokens(question: str, constraints: tuple[str, ...]) -> tuple[str, ...]:
    combined = " ".join((question, *constraints)).lower()
    tokens = []
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
