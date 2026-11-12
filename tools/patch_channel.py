"""`git apply` outcomes of a patch-channel arm, counted from its traces.

    python tools/patch_channel.py <run_id> <arm>   -> runs/<run_id>/patch_channel_<arm>.json

The D-010 labels count only edit_file/write_file as edit attempts, so an arm
whose bundle edits through `git apply` in run_command needs its own counter.
Reads runs/<id>/output/eval.zip in place and runs/<id>/failure_labels.json
for the episode labels. A call is a run_command whose command contains
`git apply`; its outcome is read from the observation:
  ok                 status ok
  partial            some hunks applied, some rejected (`git apply --reject`:
                     "Rejected hunk" with "applied cleanly" or "succeeded at")
  rejected           only "Rejected hunk" lines
  corrupt_patch      git: "corrupt patch at line N" (hunk header and body disagree)
  context_mismatch   git: "patch failed" / "does not apply" (context lines differ from the file)
  no_header          git: "patch fragment without header"
  other_error        anything else
partial and rejected are tested before the error classes. Arms whose commands
use `--reject` also get per-episode counts of hunks applied and rejected, and
there `apply_ok` means at least one call was ok or partial. Arms without
`--reject` keep the original output format byte for byte.
`unterminated_heredoc` is counted separately (bash: here-document delimited by
end-of-file), because it co-occurs with the outcomes above.
"""
from __future__ import annotations

import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from label_failures import tool_events  # noqa: E402

OUTCOMES = ("ok", "corrupt_patch", "context_mismatch", "no_header", "other_error")
HUNK_OUTCOMES = ("ok", "partial", "rejected", "corrupt_patch", "context_mismatch", "no_header", "other_error")


def hunk_counts(obs: str) -> tuple[int, int]:
    """(hunks applied, hunks rejected) reported by `git apply --reject`."""
    return obs.count("applied cleanly") + obs.count("succeeded at"), obs.count("Rejected hunk")


def classify_apply(obs: str) -> str:
    if '"status": "ok"' in obs:
        return "ok"
    applied, rejected = hunk_counts(obs)
    if rejected:
        return "partial" if applied else "rejected"
    if "corrupt patch" in obs:
        return "corrupt_patch"
    if "patch failed" in obs or "does not apply" in obs:
        return "context_mismatch"
    if "patch fragment without header" in obs:
        return "no_header"
    return "other_error"


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    run_id, arm = sys.argv[1:3]
    run = ROOT / "runs" / run_id
    labels = {e["task"]: e for e in json.loads((run / "failure_labels.json").read_text())["episodes"] if e["arm"] == arm}
    zf = zipfile.ZipFile(run / "output" / "eval.zip")
    episodes, calls, heredoc, hunk_mode = [], Counter(), 0, False
    for task, lab in sorted(labels.items()):
        events, _ = tool_events(json.loads(zf.read(f"{arm}/traces/trace_{task}.json")))
        outcome, applied, rejected = Counter(), 0, 0
        for e in events:
            cmd = str(e["args"].get("command", ""))
            if e["tool"] == "run_command" and "git apply" in cmd:
                kind = classify_apply(e["obs"])
                outcome[kind] += 1
                heredoc += "here-document" in e["obs"]
                hunk_mode |= "--reject" in cmd or kind in ("partial", "rejected")
                a, r = hunk_counts(e["obs"])
                applied, rejected = applied + a, rejected + r
        calls.update(outcome)
        episodes.append({"task": task, "label": lab["label"], "resolved": lab["resolved"],
                         "apply_calls": sum(outcome.values()), **{k: outcome[k] for k in HUNK_OUTCOMES},
                         "hunks_applied": applied, "hunks_rejected": rejected})
    kinds = HUNK_OUTCOMES if hunk_mode else OUTCOMES
    if not hunk_mode:
        for ep in episodes:
            for k in ("partial", "rejected", "hunks_applied", "hunks_rejected"):
                del ep[k]

    def any_ok(ep: dict) -> bool:
        return bool(ep["ok"] or ep.get("partial", 0))

    by_label: dict[str, dict] = {}
    for ep in episodes:
        s = by_label.setdefault(ep["label"], {"episodes": 0, "no_apply_call": 0, "apply_ok": 0, "apply_never_ok": 0})
        s["episodes"] += 1
        s["no_apply_call" if not ep["apply_calls"] else ("apply_ok" if any_ok(ep) else "apply_never_ok")] += 1
    unsolved = [ep for ep in episodes if not ep["resolved"] and ep["label"] != "oracle_clipped"]
    out = {
        "run_id": run_id, "arm": arm, "n_episodes": len(episodes),
        "calls": {"total": sum(calls.values()), **{k: calls[k] for k in kinds}, "unterminated_heredoc": heredoc},
        "episodes_with_apply_call": sum(1 for ep in episodes if ep["apply_calls"]),
        "episodes_with_apply_ok": sum(1 for ep in episodes if any_ok(ep)),
        "by_label": dict(sorted(by_label.items())),
        "unsolved_complete_hint": {
            "episodes": len(unsolved),
            "apply_never_ok": sum(1 for ep in unsolved if not any_ok(ep)),
            "apply_ok": sum(1 for ep in unsolved if any_ok(ep)),
            "saw_corrupt_patch": sum(1 for ep in unsolved if ep["corrupt_patch"]),
            "saw_context_mismatch": sum(1 for ep in unsolved if ep["context_mismatch"]),
        },
        "episodes": episodes,
    }
    if hunk_mode:
        out["hunks"] = {"applied": sum(ep["hunks_applied"] for ep in episodes),
                        "rejected": sum(ep["hunks_rejected"] for ep in episodes)}
    path = run / f"patch_channel_{arm}.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "episodes"}, indent=1))


if __name__ == "__main__":
    main()
