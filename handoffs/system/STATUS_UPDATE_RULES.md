# STATUS_UPDATE_RULES.md

Purpose: rules for Codex to create one short standalone `.md` status-update file after a meaningful implementation step.  
Recommended repo location: `handoffs/system/STATUS_UPDATE_RULES.md`

---

## Rules for Codex

- Do not update any growing history document.
- Do not create multiple progress files for the same completed step.
- After a meaningful implementation step, create exactly one new short `.md` file.
- The file must contain only one status entry.
- Keep it short and factual.
- Record only what was actually done.
- Do not include long explanations, diffs, logs, stack traces, or copied spec text.
- If nothing meaningful was completed, do not create a status file.
- If work is partial or failed, say so clearly.

---

## Filename rule

Use this filename format:

```text
WORK_STATUS_UPDATE_YYYY-MM-DD_HHMM.md
```

Example:

```text
WORK_STATUS_UPDATE_2026-04-10_1940.md
```

---

## Required file content

Use exactly this structure:

```md
## YYYY-MM-DD HH:MM — <short title>

- Scope:
- Done:
- Validation:
- Current state:
- Next step:
- Files:
```

---

## Field rules

- `Scope:` one short line saying what area was worked on
- `Done:` 2–5 short bullets with what was actually completed
- `Validation:` short note about tests, checks, or `not run yet`
- `Current state:` one short line describing where things now stand
- `Next step:` one short line only
- `Files:` short list of the most relevant files only

---

## Writing constraints

- Prefer concrete facts over explanations.
- Prefer short bullets over paragraphs.
- Do not restate architecture or canonical rules unless implementation changed.
- Do not write intentions as if they were completed work.
- Do not claim full completion without evidence.
- Do not include low-value noise edits.

---

## Example output

```md
## 2026-04-10 19:40 — Added transition validation skeleton

- Scope: core transition layer
- Done:
  - added transition request model
  - added validation skeleton for scope and basis checks
  - wired initial reject path for invalid requests
- Validation: unit tests for model parsing passed
- Current state: transition layer now has a minimal typed entry point with basic rejection behavior
- Next step: implement candidate-state construction and commit path
- Files:
  - jeff/core/transition/models.py
  - jeff/core/transition/validator.py
  - tests/test_transition_models.py
```
