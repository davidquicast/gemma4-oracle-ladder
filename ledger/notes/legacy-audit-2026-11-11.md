# Audit of the inherited workspace (2026-11-11)

The workspace inherited on 2026-11-11 was archived unchanged (minus the virtualenv)
to an archive outside the repository and then removed from
the repository. Paths below are relative to that archive. None of its results are
used anywhere in this repository.

## Findings

1. **Reference-solution leakage in the headline result ("50% Pass@1", EXP-005).**
   `experiments/exp05_iterative_trial_error/run_live_gpu_exp05.py`:
   - line 131: the prompt contains the target file and the exact line windows to
     edit, computed from the reference patch (`task["patch"]`);
   - line 153: the "v3" arm adds the hidden tests from `test_patch`;
   - lines 239-256: when an attempt fails, the "closed-loop diagnostic" returns the
     reference replacement text ("Required `new_replacement`").
   The arm therefore measured copying the answer, not solving the task. EXP-004
   has the same oracle localization (`run_live_gpu_exp04.py` line 367).
2. **No run used the official harness.** All GPU numbers came from a custom loop
   over 14 tasks; none went through `swegemma`.
3. **Statistics.** The reported p = 0.0029 compared against a 0/14 prose arm. The
   log's own comparison against a 1/14 arm gave p = 0.052; against the 2/14
   baseline it is weaker still.
4. **"89% decode speed-up" (EXP-006) is a measurement artefact.** Per-token decode
   time was computed as total generation time minus a separately measured prefill,
   floored at 1 ms; it fell from 91 ms to 3 ms as context grew, which is not
   physical. The LoRA (36 steps, 30 samples) scored 7/14, identical to no LoRA, on
   the leaked benchmark.
5. **Uncredited prior work.** The chat-template `dictsort` argument-order finding
   and the calibration CSVs came from other participants' public notebooks
   (notably davorjerkovic/gemma-4-agent-harness-calibration) and were not cited.
6. **Secret in plaintext.** A Kaggle API token was written into a handoff document
   and a notebook.

## Consequence

The project restarted from an empty repository. Every number in the paper must
come from a run recorded under `runs/` and be registered as a claim in the ledger.
