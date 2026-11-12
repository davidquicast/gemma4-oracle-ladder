---
description: 'From the statement to the lines: file, then function, then lines'
section: patterns
authority: research
sources:
  - id: A1
    label: Xia et al., Agentless - Demystifying LLM-based Software Engineering Agents, arXiv:2407.01489 (cited from the published paper, authority research)
    url: https://arxiv.org/abs/2407.01489
  - id: A2
    label: Yang et al., SWE-agent - Agent-Computer Interfaces Enable Automated Software Engineering, arXiv:2405.15793 (cited from the published paper, authority research)
    url: https://arxiv.org/abs/2405.15793
  - id: H1
    label: HARNESS_README.md, section 6 (tool reference, authority official)
    url: https://www.kaggle.com/competitions/gemma-4-developer-agent/data
    read: '2026-11-12'
---

# Localizing a defect: file, then function, then lines

## When to use it
Before the first edit.

## The practice
1. Collect the names the statement gives: file paths, functions, classes, error messages, exception types, status codes [A1].
2. Narrow in steps: first the file, then the class or function, then the lines [A1]. Do not read whole files the defect does not touch.
3. Search with the exact strings: `grep -rn "<message or name>" --include=*.py <package_dir>`, or `search_similar_code` with the statement's words [H1 §6.3]. An error message quoted in the statement is usually raised in one place.
4. Read a narrow window with `read_file(path, start_line, end_line)`; the tool returns at most 150 lines or 10,000 characters [H1 §6.2]. Search, then view a window, then edit, is the cycle that works for language-model agents [A2].

## Why it works
Hierarchical localization keeps the context small and points the edit at the code that decides the behaviour [A1].
