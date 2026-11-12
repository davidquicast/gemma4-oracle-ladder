"""Minimal unified-diff parsing for the oracle ladder.

Only what the ladder needs: which files a reference patch touches, and for each
hunk the pre-image line range and the pre-image text. Standard library only so
the same module runs inside the Kaggle kernel.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import PurePosixPath

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

# Mirrors the harness rule (HARNESS_README section 8.1): these paths are stripped
# from any agent patch, so they are never part of what an agent has to edit.
_PROTECTED_NAMES = (
    "conftest.py", "pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg",
    ".pytest.ini", "sitecustomize.py", "usercustomize.py", "_swegemma_stubs.py",
)
_TEST_DIRS = {"tests", "test", "testing"}


def is_protected(path: str) -> bool:
    p = PurePosixPath(path)
    name = p.name
    if name in _PROTECTED_NAMES or name.endswith(".pth"):
        return True
    if fnmatch(name, "test_*.py") or fnmatch(name, "*_test.py"):
        return True
    return name.endswith(".py") and any(part in _TEST_DIRS for part in p.parts[:-1])


@dataclass
class Hunk:
    old_start: int
    old_len: int
    new_start: int
    new_len: int
    lines: list[str] = field(default_factory=list)  # raw body lines incl. prefix

    @property
    def old_text(self) -> str:
        return "\n".join(l[1:] for l in self.lines if l[:1] in (" ", "-"))

    @property
    def new_text(self) -> str:
        return "\n".join(l[1:] for l in self.lines if l[:1] in (" ", "+"))

    @property
    def old_end(self) -> int:
        return self.old_start + max(self.old_len, 1) - 1 if self.old_start else 0


@dataclass
class FileDiff:
    path: str            # post-image path (pre-image path for deletions)
    is_new: bool
    is_deleted: bool
    raw: str             # the file's section of the diff, verbatim
    hunks: list[Hunk] = field(default_factory=list)


def _strip_prefix(p: str) -> str:
    p = p.strip().split("\t")[0]
    return p[2:] if p.startswith(("a/", "b/")) else p


def parse_patch(patch: str) -> list[FileDiff]:
    """Split a unified diff into per-file sections with parsed hunks.

    Accepts both `git diff` output and the header-less form used by the
    competition's tasks.jsonl (sections start directly at `--- a/path`).
    """
    lines = (patch or "").split("\n")
    starts = [
        i for i in range(len(lines) - 1)
        if lines[i].startswith("--- ") and lines[i + 1].startswith("+++ ")
    ]
    files: list[FileDiff] = []
    for k, i in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        # a preceding "diff --git"/"index" preamble belongs to the next section
        while end > i + 2 and k + 1 < len(starts) and not (
            lines[end - 1][:1] in (" ", "+", "-", "\\") or lines[end - 1] == ""
        ):
            end -= 1
        old_path, new_path = lines[i][4:], lines[i + 1][4:]
        hunks: list[Hunk] = []
        cur: Hunk | None = None
        remaining_old = remaining_new = 0
        for ln in lines[i + 2:end]:
            m = _HUNK_RE.match(ln)
            if m:
                cur = Hunk(int(m[1]), int(m[2]) if m[2] is not None else 1,
                           int(m[3]), int(m[4]) if m[4] is not None else 1)
                remaining_old, remaining_new = cur.old_len, cur.new_len
                hunks.append(cur)
            elif cur is not None and (remaining_old > 0 or remaining_new > 0):
                tag = ln[:1]
                if tag == "\\":          # "\ No newline at end of file"
                    continue
                if tag == "":             # blank context line with stripped space
                    ln, tag = " ", " "
                if tag not in (" ", "+", "-"):
                    continue
                cur.lines.append(ln)
                remaining_old -= tag in (" ", "-")
                remaining_new -= tag in (" ", "+")
        is_deleted = new_path.strip() == "/dev/null"
        is_new = old_path.strip() == "/dev/null" or (
            bool(hunks) and all(h.old_start == 0 and h.old_len == 0 for h in hunks)
        )
        path = _strip_prefix(old_path if is_deleted else new_path)
        raw = "\n".join(lines[i:end]).rstrip("\n") + "\n"
        files.append(FileDiff(path, is_new, is_deleted, raw, hunks))
    return files


def source_files(patch: str) -> list[FileDiff]:
    """File sections an agent actually has to produce (protected paths removed)."""
    return [f for f in parse_patch(patch) if not is_protected(f.path)]
