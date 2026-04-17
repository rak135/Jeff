---SYSTEM---
Format the provided bounded text artifact into exactly one JSON object that matches json_schema.
No markdown, no code fences, no commentary.
Do not add claims, citations, evidence, or certainty.
Preserve only content already materially present in the bounded artifact.

---PROMPT---
TASK: formatter fallback over bounded research text
Use only the provided bounded text artifact.
Do not use or reconstruct the original evidence pack.
Reformat only the content already present.
Do not add claims, citations, evidence, or certainty.
Output exactly one JSON object matching json_schema.
Do not output markdown, code fences, or extra prose.
QUESTION: {{QUESTION}}
ALLOWED_CITATION_KEYS: {{ALLOWED_CITATION_KEYS}}
TRANSFORM_FAILURE: {{TRANSFORM_FAILURE}}
JSON_SCHEMA: {{JSON_SCHEMA}}
BOUNDED_CONTENT:
{{BOUNDED_CONTENT}}
