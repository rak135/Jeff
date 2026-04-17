import os
import sys
os.chdir(r"c:\DATA\PROJECTS\JEFF")
sys.path.insert(0, r"c:\DATA\PROJECTS\JEFF")
import pytest
sys.exit(pytest.main(["tests/unit/cognitive/test_research_synthesis.py", "tests/unit/cognitive/test_research_bounded_syntax.py", "tests/unit/cognitive/test_research_deterministic_transformer.py", "-q"]))
