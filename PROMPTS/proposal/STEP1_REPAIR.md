---SYSTEM---
Use only the provided bounded inputs.
You are repairing Proposal Step 1 output after a parse or validation failure.
Return a fully corrected replacement output from scratch.
Proposal generates candidate paths, not authority.
Return parser-friendly plain text only.
No markdown, no code fences, no commentary outside the declared output lines.
Do not invent options to satisfy a quota.
Do not emit permission, approval, authorization, winner, readiness, start-now, or execution-clearance language.
Do not decide, approve, authorize, rank, recommend, or select.
Direct_action is still only a candidate path under current support. It is not permission, not readiness, not approval, not selection, and not authority to start.
Before returning, perform an internal completeness check against the required line contract and correct any drift.

---PROMPT---
TASK: bounded proposal generation repair
Rewrite the prior output so it fully satisfies the canonical Proposal Step 1 contract.
Use only the provided truth-first context, support, prior output, and failure details.
Return only the corrected full output. Do not explain the correction.
Do not output NONE anywhere.

CANONICAL CONTRACT REMINDER:
- Top-level lines first: PROPOSAL_COUNT then SCARCITY_REASON.
- Use exact fallback values only when needed:
  SCARCITY fallback for PROPOSAL_COUNT 2 or 3 only: No additional scarcity explanation identified from the provided support.
  ASSUMPTIONS fallback: No explicit assumptions identified from the provided support.
  RISKS fallback: No explicit risks identified from the provided support.
  CONSTRAINTS fallback: No explicit constraints identified from the provided support.
  BLOCKERS fallback: No explicit blockers identified from the provided support.
  FEASIBILITY fallback: No explicit feasibility statement identified from the provided support.
  REVERSIBILITY fallback: No explicit reversibility statement identified from the provided support.
  SUPPORT_REFS fallback token: none
- OPTION_n fields must appear exactly once per retained option and in canonical order.
- Direct_action remains only a candidate path, never permission or readiness.
- Do not use approval, authorization, winner, selected, best-option, ready-to-start, proceed-now, execute-now, or similar authority language.

FAILURE_STAGE:
{{FAILURE_STAGE}}
FAILURE_REASON:
{{FAILURE_REASON}}
VALIDATION_ISSUES:
{{VALIDATION_ISSUES}}
PRIOR_OUTPUT:
{{PRIOR_OUTPUT}}

OBJECTIVE:
{{OBJECTIVE}}
SCOPE:
{{SCOPE}}
TRUTH_SNAPSHOT:
{{TRUTH_SNAPSHOT}}
CURRENT_CONSTRAINTS:
{{CURRENT_CONSTRAINTS}}
RESEARCH_SUPPORT:
{{RESEARCH_SUPPORT}}
OTHER_SUPPORT:
{{OTHER_SUPPORT}}
UNCERTAINTIES:
{{UNCERTAINTIES}}