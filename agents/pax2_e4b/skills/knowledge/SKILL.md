---
name: knowledge
description: >-
  The persona's sourced knowledge, one topic per file. Load a topic with
  load_skill_resource when a step of repair-a-reported-defect points to it.
metadata:
  personaxis:
    origin: genesis
    compiled_from: knowledge/
---

# Knowledge

Each topic is a reference file of this skill. Read one with
`load_skill_resource(skill_name="knowledge", file_path="references/<topic>.md")`.

- `references/harness-environment.md`: the workspace, the budget, what becomes the patch.
- `references/reading-a-traceback.md`: from a traceback to the line that raised.
- `references/localizing-a-defect.md`: file, then function, then lines.
- `references/checking-a-fix.md`: one test or an inline assertion, within the budget.
- `references/editing-without-rejections.md`: how `edit_file` matches and why edits are rejected.
- `references/what-the-grader-runs.md`: hidden tests that must pass and tests that must keep passing.

These files are compiled copies of `knowledge/` at the persona's root, which
is their only home; edit them there.
