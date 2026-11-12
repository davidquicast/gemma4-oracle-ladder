---
description: 'How edit_file matches, why edits are rejected, and how to keep edits whole'
section: tools
authority: official
sources:
  - id: H1
    label: HARNESS_README.md, sections 5.3, 6.2 and 10.1 (authority official)
    url: https://www.kaggle.com/competitions/gemma-4-developer-agent/data
    read: '2026-11-12'
  - id: A2
    label: Yang et al., SWE-agent, arXiv:2405.15793 (edit commands with immediate feedback; cited from the published paper)
    url: https://arxiv.org/abs/2405.15793
---

# Editing without rejections

## When to use it
Every edit.

## What holds
- `edit_file(filepath, old_string, new_string)` finds `old_string` exactly, then line by line ignoring surrounding whitespace, then with flexible spacing around brackets and operators [H1 §6.2]. If it is not found, or found more than once, the edit is rejected and the file is unchanged [H1 §6.2].
- Copy `old_string` from what `read_file` just returned for those lines; include enough lines to make it unique, and no more.
- A response that hits the output-token limit cuts the tool call off and the edit is lost; the harness then asks for smaller incremental edits [H1 §5.3, §10.1]. Change one place per edit.
- `write_file` overwrites the whole file [H1 §6.2]: rewriting an existing file to change a few lines risks dropping the rest of it. Use `edit_file` on existing files.
- The edit result shows the diff it applied [H1 §6.2]; read it to confirm the change is the one intended, as edit feedback is what lets agents correct course [A2].
