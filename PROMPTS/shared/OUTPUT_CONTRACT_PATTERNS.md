# Output Contract Patterns

Shared output contract patterns for all Jeff prompts.
Not yet runtime-wired. Documents repeating structural patterns across layers.

## Bounded text pattern (Step 1 research)

Used for first-pass synthesis where the output is plain text with a fixed section structure.
Parsed deterministically by the transformer. Falls back to Step 3 formatter on failure.

## JSON schema pattern (Step 3 formatter, evaluation, planning)

Used where structured output is required. Schema is provided inline in the prompt.
No markdown, no code fences, exactly one JSON object.
