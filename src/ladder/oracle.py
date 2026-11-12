"""The oracle ladder: graded amounts of reference information, injected through
the harness's own `hints_text` channel (rendered to the agent as "## Hints:").

Every level above L0 uses information an agent never has at test time. The
levels are diagnostic upper bounds, not methods:

  L0  nothing added           -> the real task
  L1  which files change      -> removes file-level localization
  L2  + line ranges and the
        current code there    -> removes localization entirely
  L3  the full reference diff -> removes synthesis; only transcription is left
  T   the hidden tests        -> removes ambiguity about what "fixed" means

Solve(L3) - Solve(L0) is then split into localization (L0->L2), synthesis
(L2->L3) and an interface residual (1 - L3).
"""
from __future__ import annotations

from .patches import source_files

LEVELS = ("L0", "L1", "L2", "L3", "T")
MAX_HINT_CHARS = 16000


def _clip(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n[... truncated ...]", True


def _l1(files) -> str:
    out = ["Oracle hint (files). The correct fix changes exactly these source files:"]
    for f in files:
        tag = " (new file to create)" if f.is_new else (" (file to delete)" if f.is_deleted else "")
        out.append(f"- {f.path}{tag}")
    return "\n".join(out)


def _l2(files) -> str:
    out = [_l1(files), "", "Oracle hint (locations). The lines that must change, with their current content:"]
    for f in files:
        if f.is_new:
            out.append(f"\n{f.path}: new file, no current content.")
            continue
        for h in f.hunks:
            out.append(f"\n{f.path}, lines {h.old_start}-{h.old_end}:\n```\n{h.old_text}\n```")
    return "\n".join(out)


def _l3(files) -> str:
    diff = "".join(f.raw for f in files)
    return (
        "Oracle hint (reference fix). The following diff is the correct fix. "
        "Apply exactly this change to the files in /workspace, then call submit_patch.\n"
        f"```diff\n{diff}```"
    )


def _t(test_patch: str) -> str:
    return (
        "Oracle hint (tests). Your change is graded by the tests added in this diff. "
        "Test files are reset before grading, so do not create or edit them; "
        "make the source code satisfy them.\n"
        f"```diff\n{test_patch.rstrip()}\n```"
    )


def build_hint(level: str, patch: str, test_patch: str = "") -> tuple[str, dict]:
    """Return (hint_text, meta). meta records size and truncation for the manifest."""
    if level not in LEVELS:
        raise ValueError(f"unknown ladder level {level!r}")
    if level == "L0":
        return "", {"level": level, "chars": 0, "truncated": False, "n_files": 0, "n_hunks": 0}
    files = source_files(patch)
    meta = {"level": level, "n_files": len(files), "n_hunks": sum(len(f.hunks) for f in files)}
    if level == "T":
        text = _t(test_patch)
    elif not files:
        text = ""  # nothing an agent could be told; behaves as L0 and is flagged
        meta["empty_source_patch"] = True
    else:
        text = {"L1": _l1, "L2": _l2, "L3": _l3}[level](files)
    text, truncated = _clip(text, MAX_HINT_CHARS)
    meta.update(chars=len(text), truncated=truncated)
    return text, meta


def apply_level(existing_hints: str, level: str, patch: str, test_patch: str = "") -> tuple[str, dict]:
    """Combine a task's own hints with the oracle hint for `level`."""
    hint, meta = build_hint(level, patch, test_patch)
    parts = [p for p in ((existing_hints or "").strip(), hint) if p]
    return "\n\n".join(parts), meta
