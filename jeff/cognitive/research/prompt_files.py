"""File-backed prompt loader and renderer for the research layer.

Prompts are stored as .md files under the repo-root PROMPTS/ directory.
Each runtime-wired file uses ---SYSTEM--- and ---PROMPT--- section markers.
Placeholder substitution uses {{UPPER_SNAKE_CASE}} syntax.
"""

from __future__ import annotations

import re
from pathlib import Path

_PROMPTS_ROOT = Path(__file__).parents[3] / "PROMPTS"

_SECTION_SYSTEM_MARKER = "---SYSTEM---"
_SECTION_PROMPT_MARKER = "---PROMPT---"

_UNRESOLVED_PLACEHOLDER = re.compile(r"\{\{[A-Z_]+\}\}")


class PromptFileNotFoundError(FileNotFoundError):
    """Raised when a required prompt file is not found at the expected path."""


class PromptFileMalformedError(ValueError):
    """Raised when a prompt file is missing required section markers."""


class PromptRenderError(ValueError):
    """Raised when a prompt template has unresolved placeholders after rendering."""


def load_prompt_file(relative_path: str) -> tuple[str, str]:
    """Load a prompt file and return (system_instructions, prompt_template).

    Args:
        relative_path: Path relative to PROMPTS/ (e.g. "research/STEP1_SYNTHESIS.md").

    Returns:
        Tuple of (system_instructions, prompt_template) — both plain text, trailing
        whitespace stripped.

    Raises:
        PromptFileNotFoundError: File does not exist at the resolved path.
        PromptFileMalformedError: File is missing ---SYSTEM--- or ---PROMPT--- section.
    """
    full_path = _PROMPTS_ROOT / relative_path
    if not full_path.is_file():
        raise PromptFileNotFoundError(f"prompt file not found: {full_path}")
    content = full_path.read_text(encoding="utf-8")
    return _parse_sections(content, path_hint=str(full_path))


def render_prompt(template: str, **values: str) -> str:
    """Substitute {{KEY}} placeholders in a prompt template.

    Args:
        template: Prompt template string containing {{PLACEHOLDER}} markers.
        **values: Placeholder names (UPPER_SNAKE_CASE) mapped to their string values.

    Returns:
        Rendered string with all placeholders substituted.

    Raises:
        PromptRenderError: Any {{PLACEHOLDER}} remains unresolved after substitution.
    """
    result = template
    for key, value in values.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    unresolved = _UNRESOLVED_PLACEHOLDER.findall(result)
    if unresolved:
        raise PromptRenderError(f"unresolved prompt placeholders: {sorted(set(unresolved))}")
    return result


def _parse_sections(content: str, *, path_hint: str) -> tuple[str, str]:
    system_marker = f"{_SECTION_SYSTEM_MARKER}\n"
    prompt_marker = f"{_SECTION_PROMPT_MARKER}\n"

    if system_marker not in content:
        raise PromptFileMalformedError(
            f"prompt file missing '{_SECTION_SYSTEM_MARKER}' section: {path_hint}"
        )
    if prompt_marker not in content:
        raise PromptFileMalformedError(
            f"prompt file missing '{_SECTION_PROMPT_MARKER}' section: {path_hint}"
        )

    after_system = content.split(system_marker, 1)[1]
    system_raw, prompt_raw = after_system.split(prompt_marker, 1)
    return system_raw.rstrip(), prompt_raw.rstrip()
