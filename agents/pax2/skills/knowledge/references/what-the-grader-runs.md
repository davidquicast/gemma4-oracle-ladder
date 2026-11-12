---
description: 'What decides a task: hidden tests that must pass and tests that must keep passing'
section: definition-of-done
authority: research
sources:
  - id: B1
    label: Jimenez et al., SWE-bench - Can Language Models Resolve Real-World GitHub Issues?, arXiv:2310.06770 (FAIL_TO_PASS and PASS_TO_PASS; cited from the published paper)
    url: https://arxiv.org/abs/2310.06770
  - id: H1
    label: HARNESS_README.md, section 8.2 (authority official)
    url: https://www.kaggle.com/competitions/gemma-4-developer-agent/data
    read: '2026-11-12'
---

# What decides a task

## What holds
- A task is solved when the hidden tests that failed before the fix now pass, and the tests that passed still pass [B1, H1 §8.2].
- The hidden tests check the behaviour the statement describes. Names, messages, status codes and signatures the statement gives are what they assert on.
- The grader applies your patch to a fresh copy and runs those tests [H1 §8.2]; an empty patch, or one only touching protected files, cannot solve the task.
- Breaking behaviour elsewhere fails the task as surely as not fixing it: keep the change small.
