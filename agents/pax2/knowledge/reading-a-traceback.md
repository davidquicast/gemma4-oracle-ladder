---
description: 'Reading a Python traceback to the line that raised'
section: foundations
authority: official
sources:
  - id: PY1
    label: Python documentation, Errors and Exceptions (tutorial section 8) (authority official, cited)
    url: https://docs.python.org/3/tutorial/errors.html
  - id: PY2
    label: Python documentation, traceback module (authority official, cited)
    url: https://docs.python.org/3/library/traceback.html
---

# Reading a traceback

## When to use it
When the statement or a check shows a traceback.

## The practice
- Read from the bottom: the last line is the exception type and message; the frame above it is where it was raised [PY1, PY2].
- The first frame inside the repository's own package, counted from the bottom, is usually where the change belongs; frames in the standard library or in tests are not.
- An exception type and message the statement asks for must be raised with exactly that type and wording.
