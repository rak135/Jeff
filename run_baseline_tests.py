#!/usr/bin/env python
"""Run baseline tests for research modules."""

import subprocess
import sys

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/cognitive/test_research_synthesis.py",
        "tests/unit/cognitive/test_research_bounded_syntax.py",
        "tests/unit/cognitive/test_research_deterministic_transformer.py",
        "-q",
    ],
    cwd=r"c:\DATA\PROJECTS\JEFF",
)
sys.exit(result.returncode)
