"""File-backed prompt loader and renderer for proposal prompt contracts."""

from __future__ import annotations

import re
from pathlib import Path

_PROMPTS_ROOT = Path(__file__).parents[3] / "PROMPTS" / "proposal"

_SECTION_SYSTEM_MARKER = "---SYSTEM---"
_SECTION_PROMPT_MARKER = "---PROMPT---"

_UNRESOLVED_PLACEHOLDER = re.compile(r"\{\{[A-Z_]+\}\}")


class PromptFileNotFoundError(FileNotFoundError):
    """Raised when a required proposal prompt file is not found."""


class PromptFileMalformedError(ValueError):
    """Raised when a proposal prompt file is missing required sections."""


class PromptRenderError(ValueError):
    """Raised when a rendered proposal prompt still has unresolved placeholders."""


def load_prompt_file(file_name: str) -> tuple[str, str]:
    """Load a proposal prompt file and return (system_instructions, prompt_template)."""
    full_path = _PROMPTS_ROOT / file_name
    if not full_path.is_file():
        raise PromptFileNotFoundError(f"prompt file not found: {full_path}")
    content = full_path.read_text(encoding="utf-8")
    return _parse_sections(content, path_hint=str(full_path))


def render_prompt(template: str, **values: str) -> str:
    """Substitute {{KEY}} placeholders in a proposal prompt template."""
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
