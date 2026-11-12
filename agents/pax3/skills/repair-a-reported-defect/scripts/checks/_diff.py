"""Shared helper: the files the patch would contain, as submit_patch captures it."""
import subprocess

PROTECTED_NAMES = {"conftest.py", "pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg",
                   ".pytest.ini", "sitecustomize.py", "usercustomize.py"}
TEST_DIRS = {"tests", "test", "testing"}


def changed(filter_="ACDMR"):
    """Read-only: tracked changes against the baseline plus untracked files (what `git add -N` would add)."""
    files = []
    for base in ("_swegemma_baseline", "HEAD"):
        p = subprocess.run(["git", "diff", "--name-only", f"--diff-filter={filter_}", base],
                           capture_output=True, text=True)
        if p.returncode == 0:
            files = [line for line in p.stdout.splitlines() if line]
            break
    if "A" in filter_:
        p = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True)
        files += [line for line in p.stdout.splitlines() if line and line not in files]
    return files


def is_protected(path):
    parts = path.split("/")
    name = parts[-1]
    if name in PROTECTED_NAMES or name.endswith(".pth"):
        return True
    if name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py")
                                 or any(p in TEST_DIRS for p in parts[:-1])):
        return True
    return False
