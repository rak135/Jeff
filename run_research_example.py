import os
import sys
os.chdir(r"c:\DATA\PROJECTS\JEFF")
sys.path.insert(0, r"c:\DATA\PROJECTS\JEFF")

# Run a research command
import subprocess
print("Running research command...")
result = subprocess.run(
    [sys.executable, "-m", "jeff", "--command", r'/research docs "What is Jeff?" README.md'],
    cwd=r"c:\DATA\PROJECTS\JEFF",
    text=True,
)
print("Command completed with return code:", result.returncode)
