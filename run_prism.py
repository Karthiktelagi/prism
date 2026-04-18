"""
run_prism.py — Quick-start entry point for PRISM (delegates to main.py logic)
"""
import sys
import subprocess

if __name__ == "__main__":
    # Just forward to main.py with any args passed here
    result = subprocess.run(
        [sys.executable, "main.py"] + sys.argv[1:],
        cwd="."
    )
    sys.exit(result.returncode)
