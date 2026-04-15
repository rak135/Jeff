from __future__ import annotations

from typing import Any


def bounded_research_text_from_payload(
    payload: dict[str, Any],
    *,
    default_inference: str = "No additional inference beyond the cited findings.",
    default_uncertainty: str = "No additional uncertainty was provided.",
) -> str:
    findings_value = payload.get("findings") or ()
    finding_lines: list[str] = []
    for finding in findings_value:
        text = str(finding["text"])
        source_refs = ",".join(str(source_ref) for source_ref in finding["source_refs"])
        finding_lines.extend([f"- text: {text}", f"  cites: {source_refs}"])

    inferences_value = payload.get("inferences") or [default_inference]
    uncertainties_value = payload.get("uncertainties") or [default_uncertainty]
    recommendation_value = payload.get("recommendation")
    recommendation_text = "NONE" if recommendation_value is None else str(recommendation_value)

    return "\n".join(
        [
            "SUMMARY:",
            str(payload["summary"]),
            "",
            "FINDINGS:",
            *finding_lines,
            "",
            "INFERENCES:",
            *(f"- {value}" for value in inferences_value),
            "",
            "UNCERTAINTIES:",
            *(f"- {value}" for value in uncertainties_value),
            "",
            "RECOMMENDATION:",
            recommendation_text,
        ]
    )
