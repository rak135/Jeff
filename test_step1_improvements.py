"""Test Step 1 bounded text with direct in-memory test."""

import sys
sys.path.insert(0, r"c:\DATA\PROJECTS\JEFF")

from jeff.cognitive.research.synthesis import _build_primary_synthesis_prompt, _primary_synthesis_system_instructions
from jeff.cognitive import EvidencePack, EvidenceItem, SourceItem, ResearchRequest, synthesize_research
from jeff.infrastructure import FakeModelAdapter

# Test 1: Check if the system instructions include the new sentinel language
system_instructions = _primary_synthesis_system_instructions()
print("=== System Instructions ===")
print(system_instructions)
print()

# Test 2: Check if the prompt includes the new sentinel language
request = ResearchRequest(
    question="What is the current state?",
    project_id="test-project",
    work_unit_id="test-wu",
    run_id="test-run",
)
evidence_pack = EvidencePack(
    question="What is the current state?",
    sources=(
        SourceItem(
            source_id="source-1",
            source_type="document",
            title="Test Doc",
            locator="test://1",
            snippet="Test content",
        ),
    ),
    evidence_items=(
        EvidenceItem(
            text="Test evidence",
            source_refs=("source-1",),
        ),
    ),
)

from jeff.cognitive.research.synthesis import build_research_model_request
model_request = build_research_model_request(request, evidence_pack)
print("=== Prompt (first 1500 chars) ===")
print(model_request.prompt[:1500])
print()

# Test 3: Test with sentinel uncertainty
test_bounded_text_with_sentinel = """SUMMARY:
The evidence provides basic information.

FINDINGS:
- text: The evidence shows a basic state.
  cites: S1

INFERENCES:
- The conclusion follows from the evidence.

UNCERTAINTIES:
- No explicit uncertainties identified from the provided evidence.

RECOMMENDATION:
NONE"""

print("=== Testing Bounded Text with Sentinel Uncertainty ===")
try:
    artifact = synthesize_research(
        research_request=request,
        evidence_pack=evidence_pack,
        adapter=FakeModelAdapter(
            adapter_id="test-adapter",
            default_text_response=test_bounded_text_with_sentinel,
        ),
    )
    print("SUCCESS: Synthesis completed with sentinel uncertainty")
    print(f"Uncertainties: {artifact.uncertainties}")
except Exception as e:
    print(f"FAILED: {e}")

print("\nTest completed!")
