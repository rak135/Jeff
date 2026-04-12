# RESEARCH_V2_ROADMAP.md

Status: proposed v2 roadmap for Jeff Research  
Authority: subordinate to `ARCHITECTURE.md`, `PLANNING_AND_RESEARCH_SPEC.md`, `MEMORY_SPEC.md`, `CONTEXT_SPEC.md`, `HANDOFF_STRUCTURE.md`, and current Cognitive/Research handoffs  
Purpose: define the next-stage hybrid research direction for Jeff after the current v1 research backbone

---

## 1. Why this document exists

Jeff now has a usable v1 research backbone:

- prepared-evidence synthesis
- document source acquisition
- web source acquisition
- research artifact persistence
- selective research-to-memory handoff
- CLI entry through `/research docs` and `/research web`

That is enough to be useful.

It is not enough to be strong across many topics, source qualities, and web conditions.

The next step is not to replace the current architecture.
The next step is to strengthen the weakest part of the current system:

- source discovery
- main-content extraction
- source ranking
- evidence quality
- source presentation

This document defines the v2 direction for that upgrade.

---

## 2. Core v2 principle

Jeff Research v2 remains:

`request -> plan -> discovery -> extraction -> ranking -> evidence -> synthesis -> artifact -> optional memory handoff`

This does **not** become:
- one black-box browsing agent
- one giant autonomous loop
- memory-as-archive
- truth-by-web-scrape
- interface-owned research logic

Jeff keeps:
- evidence-first research
- explicit provenance
- bounded source acquisition
- bounded synthesis
- persisted support artifacts
- selective memory handoff

---

## 3. What v2 is trying to fix

The current v1 weakness is not mainly the LLM.

The main weaknesses are:

1. candidate source discovery is too shallow
2. fetched source text quality is uneven
3. snippets and excerpts are often noisy
4. source ranking is still primitive
5. evidence extraction is too close to raw snippets
6. operator source presentation is weaker than the backend provenance
7. deep multi-pass research does not exist yet

So v2 should focus on **source and evidence quality first**.

---

## 4. Hybrid design sources of inspiration

Jeff should not copy a single vendor product.

Jeff should take the strongest patterns from multiple directions.

### From OpenAI-style research
Take:
- clear split between quick search and deep research
- stronger operator controllability
- trusted-source / bounded-domain restrictions
- explicit progress and plan visibility
- connector-friendly future shape

### From Gemini-style research
Take:
- iterative planning and search refinement
- multi-pass research loops
- combining web and owned documents
- gap-finding and follow-up search

### From Perplexity-style research
Take:
- search-native posture
- strong citation and source presentation
- relevance-first result shaping
- source-linked summaries

### From open-source tooling
Take:
- SearXNG for candidate discovery
- Trafilatura for main-content extraction and metadata
- Crawl4AI for stronger fallback extraction/crawling
- Playwright fallback for hard dynamic pages only
- Unstructured for richer document ingestion later

The rule is:
**Jeff owns semantics. External tools provide bounded capability.**

---

## 5. Target operating modes

Jeff Research v2 should have two explicit modes.

### 5.1 Quick Search
Purpose:
- fast bounded answer
- low latency
- smaller source budget
- smaller evidence pack
- short artifact

Good for:
- quick factual checks
- narrow comparisons
- short market/topic summaries
- first-pass scouting

### 5.2 Deep Research
Purpose:
- broader source discovery
- iterative refinement
- stronger extraction and ranking
- richer evidence pack
- more detailed artifact

Good for:
- project research
- technical comparisons
- academic or documentation research
- complex market or industry synthesis

These are not separate architectures.
They are two operating profiles on the same pipeline.

---

## 6. Target v2 pipeline

## 6.1 Research request
Input should include:
- question
- scope
- mode: `quick` or `deep`
- source modes: `documents`, `web`, or `hybrid`
- optional domain constraints
- optional recency or freshness bias
- optional output depth/profile

Output:
- `ResearchRequest`

## 6.2 Research planning
A bounded planning layer should create:
- query variants
- source profile
- search budget
- fetch budget
- extraction budget
- ranking posture
- trusted-source rules when requested

Output:
- `ResearchPlan`

This planner does not decide truth.
It decides how the research pass should proceed.

## 6.3 Discovery layer
Default direction:
- SearXNG-backed candidate discovery

Responsibilities:
- execute bounded search queries
- return candidate result metadata
- preserve source provenance from the start
- support deterministic or near-deterministic bounded result sets

Output:
- `DiscoveredSource[]`

Each discovered source should include at least:
- url
- title
- domain
- source preview text if available
- rank/order from discovery
- optional published date if available at discovery time

## 6.4 Fetch and extraction layer
This layer must be a fallback stack.

### Default extractor
- Trafilatura

Responsibilities:
- extract main text
- extract useful metadata
- avoid raw HTML sludge
- support title / date / content cleanliness

### Stronger fallback
- Crawl4AI

Use when:
- default extraction is weak
- pages are more complex
- bounded crawling or stronger extraction logic is justified

### Hard fallback
- Playwright-based fetch

Use only when:
- the page is too dynamic for normal extraction
- bounded browser automation is worth the cost

Playwright is fallback, not default.

Output:
- `FetchedSource[]`

Each fetched source should include:
- source_id
- url
- title
- domain
- published_at
- fetched_at
- extractor_used
- cleaned_text
- bounded snippet
- extraction quality flags

## 6.5 Document ingestion layer
For documents and hybrid mode:

### Default
- text-like files already supported by v1

### Later upgrade
- Unstructured for PDF, DOCX, HTML, and richer formats

Output should converge to the same logical shape as web sources:
- one shared source model
- one shared evidence path

That is critical.
Documents and web must not become two unrelated research engines.

## 6.6 Ranking and source selection
After discovery and extraction, Jeff should rank sources using bounded support signals such as:
- question relevance
- profile fit
- domain trust hints
- freshness
- extraction quality
- duplication penalty

This is not truth scoring.
It is bounded source selection for better evidence.

Output:
- `SelectedSource[]`

## 6.7 Chunking and evidence extraction
This is a major v2 improvement area.

Instead of leaning on poor raw snippets:
- chunk the cleaned source text
- score chunks against the research goal
- retain the strongest bounded chunks
- preserve exact source references

Recommended shape:
- deterministic prefilter first
- optional model-assisted rerank only in deeper mode

Output:
- `EvidencePack`
  - source_items
  - evidence_items
  - contradiction markers
  - uncertainty markers
  - provenance map

## 6.8 Synthesis
The synthesis layer remains bounded and explicit.

Input:
- question
- selected sources
- evidence items
- contradiction markers
- uncertainty markers

Output:
- summary
- findings
- inferences
- uncertainties
- recommendation

Requirements:
- findings remain source-backed
- inferences remain labeled inference
- uncertainty remains explicit
- source references remain valid
- fail closed on bad structure or provenance mismatch

## 6.9 Artifact persistence
Persist research as support artifacts, not truth.

Persist:
- question
- mode
- source profile
- scope
- source items
- evidence items
- findings
- inferences
- uncertainties
- recommendation
- timestamps
- bounded metadata

Artifact is:
- audit trail
- history
- future support object
- later reuse surface

Artifact is not:
- truth
- memory
- permission
- hidden workflow authority

## 6.10 Memory handoff
Memory handoff remains selective.

Research may propose:
- durable conclusions
- reusable patterns
- cautions
- directional lessons
- semantic conclusions

Memory still decides:
- write
- reject
- defer

Research does not become memory.

---

## 7. Source profiles

Jeff should move toward explicit source profiles.

Initial target profiles:

- `general_web`
- `news_market`
- `technical_docs`
- `academic`
- `product_compare`

Profiles can shape:
- query expansion
- source preferences
- freshness weighting
- ranking hints
- extraction posture
- evidence density expectations

Profiles are important because “one universal research behavior” will underperform across topics.

---

## 8. Module design direction

### 8.1 Cognitive ownership
Suggested research package shape:

```text
jeff/cognitive/research/
  __init__.py
  contracts.py
  planning.py
  discovery.py
  extraction.py
  ranking.py
  evidence.py
  synthesis.py
  persistence.py
  memory_handoff.py
  profiles.py
  web.py
  documents.py
  legacy.py
```

### 8.2 Infrastructure ownership
Suggested support tooling package shape:

```text
jeff/infrastructure/research_sources/
  __init__.py
  searxng_client.py
  trafilatura_extractor.py
  crawl4ai_extractor.py
  playwright_fetcher.py
  unstructured_loader.py
```

Rule:
- Cognitive owns research meaning
- Infrastructure owns external tooling and provider plumbing

---

## 9. What v2 should explicitly avoid

Do not turn Jeff Research into:
- one giant autonomous crawler
- one LLM-only browse-and-summarize loop
- memory archive of all research
- browser automation as the default path
- one flat module blob again
- interface-owned semantics
- silent cross-project retrieval
- “deep research” branding without deep evidence quality

---

## 10. Priority roadmap

## Phase 1 — repair current v1 weak points
Before bigger upgrades, fix:
- source transparency in CLI output
- provenance consistency bugs
- source rendering with title + URL + date
- cleaner snippets/excerpts
- stronger source-item validation

## Phase 2 — discovery and extraction upgrade
Implement:
- SearXNG-backed discovery
- Trafilatura-backed default extraction
- better publish-date handling
- domain metadata
- cleaner main-content extraction

## Phase 3 — evidence quality upgrade
Implement:
- cleaned-text chunking
- stronger bounded evidence extraction
- ranking improvements
- optional deep-mode rerank
- contradiction surfacing improvements

## Phase 4 — hard-page fallback
Implement:
- Crawl4AI fallback
- Playwright fallback only where truly needed

## Phase 5 — richer document ingestion
Implement:
- Unstructured-backed non-trivial document ingestion
- shared source model across web and documents

## Phase 6 — true deep research mode
Implement:
- iterative planning
- query refinement
- gap detection
- trusted-source constraints
- stronger operator progress visibility

---

## 11. Near-term implementation recommendation

The next practical implementation order should be:

1. research source transparency + provenance consistency repair
2. SearXNG discovery integration
3. Trafilatura extraction integration
4. cleaned-text chunking + evidence extraction upgrade
5. publish date support in source model and operator output
6. Crawl4AI fallback
7. Playwright fallback
8. Unstructured documents expansion
9. deep research mode

This keeps the roadmap grounded.
Do not jump to deep loops before fixing source quality.

---

## 12. Success criteria for v2 direction

Jeff Research v2 is succeeding when:

- sources are easier to trust and inspect
- operator output shows real sources, not internal IDs
- evidence packs come from cleaned main content, not web garbage
- different topics degrade later and more gracefully
- quick mode is fast and useful
- deep mode is stronger without becoming opaque
- artifacts remain audit-friendly
- memory stays selective
- architecture remains bounded and truthful

---

## 13. Final direction

The v2 direction is:

- OpenAI-style controllability
- Gemini-style iterative planning
- Perplexity-style search-native relevance and citation UX
- SearXNG discovery
- Trafilatura default extraction
- Crawl4AI stronger fallback
- Playwright hard-page fallback
- Unstructured later for richer documents
- Jeff-owned evidence-first semantics over all of it

That is the correct hybrid direction.

Jeff should not become a wrapper around one vendor or one open-source crawler.
Jeff should become a disciplined research system that composes the best tools while keeping truth, memory, evidence, and operator trust intact.
