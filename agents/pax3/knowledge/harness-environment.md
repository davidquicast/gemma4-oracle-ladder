---
description: 'The workspace you work in: offline, budgeted, and what becomes the patch'
section: foundations
authority: official
sources:
  - id: H1
    label: HARNESS_README.md, sections 5.3, 6, 8.1 and 10 (the competition's harness guide, read in full, authority official)
    url: https://www.kaggle.com/competitions/gemma-4-developer-agent/data
    read: '2026-11-12'
---

# The workspace: offline, budgeted, and what becomes the patch

## When to use it
At the start of every task, and before `submit_patch`.

## What holds
- The repository is at `/workspace`, offline: nothing can be installed or downloaded [H1 §6].
- Every `read_file`, `edit_file`, `write_file` and `run_command` counts toward the tool-call budget; `submit_patch` and `get_status` are free [H1 §10.5].
- The patch is `git add -N . && git diff` of `/workspace` against the baseline commit, so **any untracked file you create there becomes part of the patch** [H1 §8.1]. Scratch scripts go in `/tmp` [H1 §10.3].
- Changes to test files (`test_*.py`, `*_test.py`, files under `tests/`, `test/`, `testing/`) and to `conftest.py`, `pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg` are stripped from the patch before grading: a fix placed there is lost [H1 §8.1].
- When you call `submit_patch`, the session ends at the end of that turn [H1 §5.3]. Call it last.
- If the session ends without `submit_patch`, the harness still extracts the diff, but only of what is in the working tree [H1 §8.1].

## Why it works
The grader applies only your diff to a fresh copy of the repository and runs hidden tests; nothing else you did is seen.
