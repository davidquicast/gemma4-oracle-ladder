# Oracle Ladder for small SWE agents

Where does a 2.3B-parameter model lose a software-engineering task: finding the
code, writing the fix, or getting the fix through the tool interface?

This repository measures that for **Gemma 4 E2B** inside the official
`swegemma` harness of the Kaggle *Gemma 4 Developer Agent* competition. The same
agent is run on the same public tasks while the harness's own `hints` channel is
given graded amounts of reference information:

| Level | Added to the task | What it removes |
|---|---|---|
| L0 | nothing | — (the real task) |
| L1 | which files change | file-level localization |
| L2 | + line ranges and the current code there | localization |
| L3 | the full reference diff | synthesis; only transcription is left |
| T | the hidden tests | ambiguity about what "fixed" means |

Levels above L0 use information an agent never has at test time. They are
diagnostic upper bounds, not methods.

## Layout

```
src/ladder/        diff parsing and hint construction (standard library only)
agents/            agent bundles in the competition's submission format
kernels/           Kaggle kernel template that runs a campaign
tools/kernel.py    build / push / status / pull for a run
tools/ledger.py    the research ledger (tasks, experiments, decisions, incidents, claims)
tools/analyze.py, label_failures.py, patch_channel.py, paper_tables.py, figures.py
                   run outputs -> analysis files, failure labels, tables, figures
runs/<run_id>/     config, build hashes and raw outputs of every run
ledger/            append-only records; the generated status page is generated from them
paper/             the write-up and its figures
tests/             unit tests
```

## Reproduce a run

Requirements: a Kaggle account that has joined the competition, and the Kaggle
CLI with `KAGGLE_API_TOKEN` set in `.env`.

```bash
python tools/kernel.py build runs/_configs/<run>.json   # embeds bundles + src into one script
python tools/kernel.py push  <run_id>                   # GPU L4x4, internet off
python tools/kernel.py status <run_id>
python tools/kernel.py pull  <run_id>                   # -> runs/<run_id>/output/
```

Competition data is not redistributed here; the kernel reads it from the
attached competition dataset. The trace archives under `runs/` do contain task
statements, oracle hints and repository excerpts of the public tasks, as the
agent saw them (competition data licence: Apache-2.0).

## Traceability

`the generated status page` shows what is done, in progress and planned. Every number in the
paper is a claim in `ledger/claim.jsonl` that points to a file under `runs/`
pinned by SHA-256; `python tools/ledger.py validate` fails if any evidence file
changed or if the paper cites a claim that is not verified.

## Credits

- Harness, tasks, wheelhouse and starter prompt: the competition hosts
  (Google / Kaggle), Apache-2.0.
- Scorer-like sandbox used for grading inside Kaggle notebooks: adapted from
  Zbigniew Kirchner, *Gemma 4 Agent: Run Your Agent Locally* (Apache-2.0).

## License

Apache-2.0.
