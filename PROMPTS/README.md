# PROMPTS

Central prompt repository for Jeff.

Prompts are stored as `.md` files, organized by cognitive layer. This directory is the
editable source of truth for all prompt text — runtime code assembles and renders prompts
from these files rather than embedding large text blobs inline.

## Structure

```
PROMPTS/
  PROMPT_STANDARD.md          Prompt-writing standard and style guide
  README.md                   This file

  research/
    STEP1_SYNTHESIS.md        Step 1 bounded text synthesis (runtime-wired)
    STEP3_FORMATTER.md        Step 3 formatter fallback (runtime-wired)
    SHARED_RULES.md           Shared research epistemic rules (scaffold)

  proposal/
    STEP1_GENERATION.md       Proposal Step 1 generation contract (loadable, not runtime-called yet)
    GENERATION.md             Proposal generation legacy scaffold
    NORMALIZATION.md          Proposal normalization (scaffold)
    CRITIQUE.md               Proposal critique (scaffold)

  evaluation/
    JUDGMENT.md               Evaluation judgment (scaffold)
    SUMMARY.md                Evaluation summary (scaffold)

  planning/
    TASK_DECOMPOSITION.md     Task decomposition (scaffold)
    RISK_EXTRACTION.md        Risk extraction (scaffold)

  shared/
    EPISTEMIC_RULES.md        Cross-layer epistemic rules (scaffold)
    OUTPUT_CONTRACT_PATTERNS.md  Output shape patterns (scaffold)
    SENTINELS.md              Shared sentinel literals (scaffold)
```

## Runtime-wired files

Files marked **runtime-wired** are loaded at runtime by `jeff/cognitive/research/prompt_files.py`.
They use `---SYSTEM---` and `---PROMPT---` section markers, and `{{PLACEHOLDER}}` syntax for
dynamic values substituted at call time.

Proposal `STEP1_GENERATION.md` now follows the same file format and can be loaded/rendered by
the Proposal-local helper in `jeff/cognitive/proposal/prompt_files.py`, but it is not yet
connected to any model/runtime call path.

## Scaffold files

Files marked **scaffold** are created for structure and future work. They are not currently
loaded at runtime. They contain placeholder or candidate content for the next wiring slice.

## Prompt file format (runtime-wired)

```
---SYSTEM---
<system instructions — plain text, no placeholders>

---PROMPT---
<prompt template — may contain {{PLACEHOLDER}} markers>
QUESTION: {{QUESTION}}
...
```

Placeholders use `{{UPPER_SNAKE_CASE}}` syntax. Missing placeholders cause a hard failure
at render time — no silent fallback.
