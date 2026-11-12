---
name: repair-a-reported-defect
description: >-
  Use for every task: locate the source code behind a reported defect, change
  it, check the change with a targeted test, and submit it as a patch.
metadata:
  personaxis:
    delivers:
      - the patch captured by submit_patch
    assertions:
      - id: fix-is-in-source
        says: The patch changes at least one non-test source file.
        evidence: [kept_code]
        check: scripts/checks/fix_is_in_source.py
    traps:
      - id: protected-files-in-patch
        says: >-
          Changes to test files and test runner configuration are stripped
          before grading, so a fix placed there is lost.
        source: HARNESS_README.md section 8.2, anti-tampering test and config reset
        check: scripts/checks/no_protected_files.py
      - id: scratch-file-in-patch
        says: >-
          An untracked file left under /workspace is captured into the patch.
        source: HARNESS_README.md section 10, item 3
        check: scripts/checks/no_scratch_files.py
    release:
      control: autonomous
---

# Repair a reported defect

## Steps

1. From the problem statement, write down the names it gives: files,
   functions, classes, error messages, exception types, status codes.
2. Locate the code. If a file path is named, `read_file` it at the relevant
   lines. If only a symbol or message is named, use `search_similar_code` or
   one `run_command` with `grep -rn "<name>" --include=*.py .` limited to the
   package directory. Do not read files the defect does not touch.
3. Read the exact lines you will change, then apply the smallest change with
   `edit_file`, copying `old_string` from what you read. Keep each edit small;
   if an edit is rejected, read the lines again before retrying.
4. Check the change: run the one test file or test function that covers it
   (`python3 -m pytest <file> -k <name> -q`), or an inline
   `python3 -c "..."` assertion. Scratch scripts go in `/tmp`. If an existing
   test fails for a reason unrelated to the defect, ignore it.
5. Run the guarantee below, fix what fails, then call `submit_patch` and
   confirm `patch_size > 0` and `files_changed > 0`.
6. End with one or two lines: what changed, and what the check printed.

## Guarantee: run these before `submit_patch`

The harness does not run the checks in `scripts/checks/`; you run their
equivalent with one command:

```
git add -N . && git diff --stat _swegemma_baseline 2>/dev/null || git diff --stat HEAD
```

- **fix-is-in-source**: the list names at least one `.py` file that is not a
  test file. If it is empty, the work is not done.
- **protected-files-in-patch**: the list names no `test_*.py`, `*_test.py`,
  file under `tests/`, `test/` or `testing/`, `conftest.py`, `pytest.ini`,
  `pyproject.toml`, `tox.ini` or `setup.cfg`. Revert any that appear with
  `git checkout -- <file>`.
- **scratch-file-in-patch**: the list names no file you created only to
  reproduce or debug. Delete it with `rm <file>`.
