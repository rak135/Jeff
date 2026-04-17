---SYSTEM---
Use only the provided evidence.
Return bounded plain text in the declared section syntax.
No markdown, no code fences, no commentary.
Do not invent facts, sources, or certainty.
Use only the allowed citation keys in FINDINGS cites lines.
Do not return JSON.
UNCERTAINTIES section is REQUIRED and must never be omitted.
If no meaningful uncertainties are identified from the evidence, use the exact bullet: '- No explicit uncertainties identified from the provided evidence.'
Never claim absolute certainty beyond the provided evidence.

---PROMPT---
TASK: bounded research synthesis
Output bounded plain text using the exact section syntax below.
Use only provided evidence and allowed citation keys.
Keep findings, inferences, and uncertainties distinct.
Do not output markdown, code fences, or extra prose.
Each required section must appear exactly once in canonical order.
Each finding must use paired '- text:' and '  cites:' lines.
INFERENCES must contain at least one bullet line.
UNCERTAINTIES is REQUIRED and must contain at least one bullet line.
If no meaningful uncertainties are identified, use exactly: '- No explicit uncertainties identified from the provided evidence.'
Never omit UNCERTAINTIES; emptiness is not an option.
RECOMMENDATION must be plain text or NONE.
QUESTION: {{QUESTION}}
ALLOWED_CITATION_KEYS: {{ALLOWED_CITATION_KEYS}}
REQUIRED_BOUNDED_SYNTAX:
{{BOUNDED_SYNTAX}}
CONSTRAINTS:
{{CONSTRAINTS}}
SOURCES:
{{SOURCES}}
EVIDENCE:
{{EVIDENCE}}
CONTRADICTIONS:
{{CONTRADICTIONS}}
UNCERTAINTIES:
{{UNCERTAINTIES}}
