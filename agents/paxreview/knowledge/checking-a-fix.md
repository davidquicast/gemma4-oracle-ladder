---
description: 'Running one test, or an inline assertion, within the budget'
section: patterns
authority: official
sources:
  - id: P1
    label: pytest documentation, How to invoke pytest (node ids, -k, -x, -q) (authority official, cited)
    url: https://docs.pytest.org/en/stable/how-to/usage.html
  - id: H1
    label: HARNESS_README.md, sections 7 and 10 (authority official)
    url: https://www.kaggle.com/competitions/gemma-4-developer-agent/data
    read: '2026-11-12'
---

# Checking a fix within the budget

## When to use it
After the edit, before `submit_patch`.

## The practice
- Run one test: `python3 -m pytest path/to/test_file.py::test_name -q -x`, or select by name with `-k "<expression>"` [P1].
- When no test covers the behaviour, check it inline: `python3 -c "import pkg; assert pkg.f(x) == expected"`.
- Never run the whole suite; the session has a time limit per task [H1 §7].
- A reproduction script, if needed, goes in `/tmp` [H1 §10.3].
- A failure in a test unrelated to the reported behaviour is not yours to fix.
