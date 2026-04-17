import os
import sys
os.chdir(r"c:\DATA\PROJECTS\JEFF")
sys.path.insert(0, r"c:\DATA\PROJECTS\JEFF")
import pytest
sys.exit(pytest.main(["tests/unit", "tests/integration", "-q"]))
