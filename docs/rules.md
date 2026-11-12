# Experimental design and pre-registered reading rules

Copied from the project's working plan. Each rule was written, and dated in the
ledger's decisions, before the data it reads existed.

- **Harness**: official `swegemma` 0.2.11, vLLM 0.19.1, scorer flags
  (32k context, gemma4 tool and reasoning parsers), subprocess sandbox with
  Z. Kirchner's scorer-like environment (reference patch passes on 127/129).
- **Tasks**: the public tasks whose reference patch passes in that sandbox.
- **Model**: `gemma-4-e2b-it-qat-w4a16-ct`. If compute allows, E4B on the same
  ladder as a second point (it is also eligible for the bonus).
- **Agent bundles** (`agents/`): `base` (official starter prompt, single agent),
  `lean` (650-character prompt, four tools), `nothink` (thinking off).
  Budget per episode: 24 tool calls, 5 minutes, 60 turns.
- **Wave 1 arms**: `base` at L0, L1, L2, L3, T; `lean` at L0 and L3; `nothink`
  at L0; `pax` at L0 and L2.
- **Personaxis ablation** (D-007). `pax` is `base` with one change: the
  instruction and skill are a Personaxis 2.0 persona. Same tools,
  sampling and budget. It runs at L0 (the competition condition) and at L2
  (where solve rates are high enough for a paired test to have power).
  Rule fixed before the data: with net = (tasks only `pax` solves) − (tasks only
  `base` solves), summed over L0 and L2, Personaxis is **adopted** (leaderboard
  bundle, later waves, reported as a positive result) if net ≥ +5 and it is not
  negative at either level; it is **rejected** if net ≤ −5; otherwise the paper
  reports "no detectable effect" with the counts. The counts are reported in
  every case.
  **Outcome**: net = −6, rejected (C-031, D-009). `pax` is not used further.
- **Analysis** (`tools/analyze.py`): solve rate with Wilson 95% intervals on the
  tasks common to all arms; exact McNemar on paired outcomes against `base_L0`;
  breakdown by repository and by reference-patch size; the three gaps.
- **Failure labels** (D-010; fixed after reading wave-1 traces). Every unsolved
  episode of every arm gets one label for the **patch state at grading**, first
  match wins:
  1. `oracle_clipped` — the arm's hint was clipped (`hint.truncated`). Reported
     separately and excluded from the shares.
  2. `output_cut_off` — empty patch and at least one token-limit continuation
     nudge (tool call cut off, or cut off while thinking).
  3. `no_edit_attempted` — empty patch, no `edit_file`/`write_file` call.
  4. `malformed_call` — empty patch; every edit/write call failed the tool
     schema (missing mandatory parameter).
  5. `edit_rejected` — empty patch; at least one well-formed edit/write call,
     none succeeded. (`empty_other` for an empty patch that fits none of 2–5.)
  6. `destructive_overwrite` — non-empty patch; a successful `write_file` on a
     file that already existed, and the patch removes at least 20 lines more
     than the reference patch does.
  7. `incomplete_patch` — L3 arms only: non-empty patch that lacks some of the
     reference's added lines (recall < 1 over stripped, non-blank added lines).
  8. `wrong_patch` — non-empty patch, tests fail (at L3: all reference lines
     present, yet lines were lost or added).

  Second axis, **how the episode ended**: `submit`, `timeout`, `tool_budget`,
  `turn_budget`, `stopped` (no submit, no budget hit). Budget exhaustion is this
  axis, not a label. Per-episode counters are kept beside the labels:
  `edit_file` calls by outcome (ok / old_string not found / ambiguous target /
  identical strings / missing file / malformed), `write_file` ok and
  overwrite-of-existing, token-limit nudges by kind, plain nudges, whether the
  last edit before `submit_patch` had failed, and for L2/L3 arms each
  not-found `old_string` classed as repeat of an already applied edit,
  verbatim in the hint's pre-image, verbatim in its post-image, or not verbatim.
- **Wave 2** (D-011, E-003; `runs/_configs/wave2.json`). Question: is the L3
  residual caused by the edit primitive or by the model's ability to copy?
  - `patch_L3`: bundle `patch` = `base` without `edit_file` and `write_file`;
    section 2 of the prompt tells the agent to apply one unified diff with
    `git apply --whitespace=nowarn <<'PATCH'` in `run_command`. Same oracle
    hint as `base_L3`. The apply is atomic and needs no old/new string pair.
  - `base_r2_L3`, `base_r2_L0`: unchanged reruns of wave-1 arms. The flip rate
    (tasks whose outcome differs between identical runs) is the noise floor for
    every paired comparison in the paper.
  - Reading rule, fixed now: with d = discordant tasks between `base_L3` and
    `base_r2_L3`, `patch_L3` "removes part of the residual" only if
    (only `patch_L3`) − (only `base_L3`) exceeds d and exact McNemar p < 0.01;
    otherwise the paper says the patch channel did not help and the residual is
    attributed to copying fidelity and the output budget.
  - **Outcome** (D-015): margin 23 − 10 = 13 ≤ d = 21, p = 0.035 (C-044, C-045,
    C-059). The patch channel is reported as not shown to help; the failures
    move to corrupt and cut-off diffs (C-054..C-056, `tools/patch_channel.py`).
  - Not run: `patch` at L0/L2 (measures diff authoring, a different question),
    skill scripts (need a code executor the scorer may not provide). The
    localization aid, E4B and the December edit interface are the work plan's.
  - If quota is short, drop `base_r2_L0` first, then `base_r2_L3`.
- **Wave 3** (D-018, E-004; `runs/_configs/wave3.json`). Question: does an edit
  protocol built from the wave-2 failure counts recover part of 1 − Solve(L3)?
  - Bundle `hunk` = `patch` with section 2 of the prompt rewritten;
    `max_output_tokens` 8,192 as in `patch` and `base` (D-019: 16,384 was
    planned, but on the 32,768-token context it kills any request whose prompt
    passes 16,384 tokens, I-011). The agent sends one command per file:
    `git apply --recount --reject --unidiff-zero --ignore-whitespace --whitespace=nowarn <<'PATCH'`.
    `--recount` ignores the hunk-header counts (the 73 "corrupt patch" calls);
    `--reject` applies each hunk on its own and names the rejected ones;
    `--unidiff-zero` lets a hunk whose trailing context was dropped apply away
    from the end of the file; `--ignore-whitespace` tolerates indentation
    errors in context lines. One file per command is required: the L3 hint has
    no `diff --git` lines, and with `--recount` the next file's `--- a/` line
    is read as a removed line. Checked on a toy repository, git 2.34.1.
    Nothing here is a harness change: the scorer accepts the bundle as is.
  - Arms: `hunk_L3`, `hunk_r2_L3` (two runs of one arm), `hunk_L2`, `hunk_L0`.
    Controls are the existing runs `base_L3`, `base_r2_L3`, `base_L2`,
    `base_L0`, `base_r2_L0`. If quota is short, drop `hunk_L0`, then
    `hunk_L2`, then `hunk_r2_L3`.
  - **Primary rule, fixed now.** For each of the 127 tasks, d = (solves in the
    `hunk` L3 runs) − (solves in the two `base` L3 runs), D = Σd. Exact
    two-sided sign-flip test: every non-zero d keeps or flips its sign with
    probability ½; p = P(|D*| ≥ |D|). Under "the bundle makes no difference"
    the four runs of a task are exchangeable, so the test is exact and already
    contains the run-to-run flips. The protocol "removes part of the transfer
    residual" iff D > 0 and p < 0.01. With a single `hunk` L3 run: iff exact
    McNemar p < 0.01 against `base_L3` and against `base_r2_L3`, both with a
    positive net. Otherwise the paper says it was not shown.
  - Why not the D-011 rule again: it compared a net margin with the gross
    count d = 21. Between identical runs the net has a standard deviation of
    about √21 ≈ 4.6, so "net > 21" asked for 4.6 standard deviations on top of
    p < 0.01. The D-011 outcome is still reported for every new pairing, and
    the new test applied to `patch_L3` is reported as post hoc.
  - **Carry-over rule, fixed now.** `hunk_L2` against `base_L2`, and `hunk_L0`
    against `base_L0` and `base_r2_L0`: an effect is claimed at a level only
    if exact McNemar p < 0.01 in every pairing at that level, with the same
    sign. Prediction recorded before the data: no effect at L2 or L0.
  - Reported in every case: solve rates with intervals, discordant counts,
    `git apply` call outcomes (ok / partial / rejected / corrupt), token-limit
    nudges, labels, rates by patch size, and the ladder recomputed under
    `hunk`: Solve(`hunk` L3) − Solve(`hunk` L2) and 1 − Solve(`hunk` L3).
  - **Wave 3b, only if quota and time allow**: `base` and `hunk` at L3 on E4B
    (bundles `base_e4b`, `hunk_e4b`: identical except the `model:` line). It
    answers whether "handed the fix, still failing" is specific to the 2.3B
    model. Descriptive only, no rule; drop `hunk_e4b_L3` first.
- **Wave 4** (D-020, E-006; `runs/_configs/wave4.json`). `base_e4b` at L0 and
  L2, the two levels missing from the E4B ladder. Descriptive, no rule. It is
  also the dev-set number for the E4B leaderboard bundle (D-021). Drop
  `base_e4b_L2` if less than 4.0 h of quota is left. `deadline_minutes` 100
  keeps the run inside the quota; rows cut by it are `skipped_deadline`.
- **LoRA** (D-008) is built, not optional. Two steps: a plumbing proof that an
  adapter trained outside loads in the official harness on the W4A16
  checkpoint (starts now), then the real adapter, whose training
  target is the stage the ladder shows is lost. Constraints fixed now: an
  adapter evaluated on the public tasks is trained on no data from those tasks
  or their reference patches; an adapter trained on everything is for the
  leaderboard only and no dev-set number is reported for it. Training data is
  built from real commits and real traces, never from model-invented tasks.
  LoRA enters the paper only if a valid result exists at G3; otherwise it is
  December-track work.
- **Threats recorded up front**: single seed at temperature 0.2 (repeat L0 and
  L3 once if compute allows, report the flip rate); public tasks are four
  repositories, mostly fastapi; oracle hints change prompt length as well as
  information; grading sandbox is scorer-like, not the scorer.
  Added after wave 1: the L3 hint is clipped at 16,000 characters for 8 tasks
  (reported with and without them); the `patch` bundle and the failure labels
  were designed on wave-1 traces of the same 127 tasks (behaviour, never task
  content), so wave 2 is not a held-out test of the intervention; the `patch`
  prompt is 1,141 characters longer than `base`.
