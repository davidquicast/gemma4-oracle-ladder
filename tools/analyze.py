#!/usr/bin/env python
"""Turn raw run outputs into the tables the paper cites.

    tools/analyze.py <run_id> [<run_id> ...] [--out runs/<name>/analysis.json]

Reads runs/<run_id>/output/results.jsonl (one row per arm x task), keeps the
tasks whose reference patch passes in the grading sandbox, and writes one JSON
file with per-arm solve rates (Wilson 95% intervals), paired exact McNemar
tests against a reference arm, the ladder decomposition and breakdowns by
repository and by reference-patch size. Rows from several runs are pooled;
a (arm, task) pair that appears twice is an error unless --allow-repeats.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ladder.stats import paired, wilson  # noqa: E402


def load_rows(run_ids: list[str]) -> list[dict]:
    rows = []
    for rid in run_ids:
        path = ROOT / "runs" / rid / "output" / "results.jsonl"
        for line in path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                row["run_id"] = rid
                rows.append(row)
    return rows


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": [round(lo, 4), round(hi, 4)]}


def analyse(rows: list[dict], reference: str, allow_repeats: bool = False) -> dict:
    status = defaultdict(lambda: defaultdict(int))
    for r in rows:
        status[r["arm"]][r["status"]] += 1
    done = [r for r in rows if r["status"] == "done" and r.get("gradable", True)]
    solved: dict[str, dict[str, bool]] = defaultdict(dict)
    by_key = {}
    for r in done:
        key = (r["arm"], r["task"])
        if key in by_key and not allow_repeats:
            raise SystemExit(f"duplicate row for {key}")
        by_key[key] = r
        solved[r["arm"]][r["task"]] = bool(r["resolved"])
    arms = sorted(solved)
    common = sorted(set.intersection(*(set(solved[a]) for a in arms))) if arms else []

    out = {
        "reference_arm": reference, "n_rows": len(rows), "status_counts": {a: dict(s) for a, s in status.items()},
        "n_common_tasks": len(common), "arms": {}, "paired_vs_reference": {}, "by_repo": {}, "by_patch_size": {},
    }
    for a in arms:
        rs = [by_key[(a, t)] for t in common]
        k = sum(solved[a][t] for t in common)
        secs = sorted(r["seconds"] for r in rs)
        calls = [r.get("tool_calls") or 0 for r in rs]
        out["arms"][a] = {
            **rate(k, len(common)),
            "all_tasks_run": rate(sum(solved[a].values()), len(solved[a])),
            "no_patch": sum(1 for r in rs if not r.get("patch_chars")),
            "median_seconds": secs[len(secs) // 2] if secs else None,
            "total_hours": round(sum(secs) / 3600, 2),
            "mean_tool_calls": round(sum(calls) / len(calls), 2) if calls else None,
            "level": rs[0]["level"] if rs else None, "bundle": rs[0]["bundle"] if rs else None,
        }
        if reference in solved and a != reference:
            p = paired({t: solved[a][t] for t in common}, {t: solved[reference][t] for t in common})
            out["paired_vs_reference"][a] = {
                "n": p["n"], "arm": p["a"], "reference": p["b"], "both": p["both"],
                "only_arm": p["only_a"], "only_reference": p["only_b"], "p_mcnemar": round(p["p_mcnemar"], 6),
            }
    # breakdowns over the common tasks
    repo_of = {r["task"]: r["repo"] for r in done}
    hunks_of = {}
    for r in done:
        h = (r.get("hint") or {})
        if r["level"] in ("L1", "L2", "L3") and "n_hunks" in h:
            hunks_of[r["task"]] = (h["n_files"], h["n_hunks"])
    def size_bin(t):
        if t not in hunks_of:
            return "unknown"
        files, hunks = hunks_of[t]
        return "1 file, 1 hunk" if (files, hunks) == (1, 1) else ("1 file, 2+ hunks" if files == 1 else "2+ files")
    for name, keyfn in (("by_repo", lambda t: repo_of[t]), ("by_patch_size", size_bin)):
        groups = defaultdict(list)
        for t in common:
            groups[keyfn(t)].append(t)
        out[name] = {g: {a: rate(sum(solved[a][t] for t in ts), len(ts)) for a in arms} for g, ts in sorted(groups.items())}
    # ladder decomposition on the reference bundle
    ladder = {}
    for a in arms:
        info = out["arms"][a]
        # only the canonical arm of each level (named <bundle>_<level>): a rerun arm must not overwrite it
        if (info["bundle"] == out["arms"].get(reference, {}).get("bundle") and info["level"] in ("L0", "L1", "L2", "L3")
                and a == f"{info['bundle']}_{info['level']}"):
            ladder[info["level"]] = info["rate"]
    if all(lv in ladder for lv in ("L0", "L2", "L3")):
        out["ladder"] = {
            "rates": ladder,
            "localization_gap": round(ladder["L2"] - ladder["L0"], 4),
            "synthesis_gap": round(ladder["L3"] - ladder["L2"], 4),
            "interface_residual": round(1 - ladder["L3"], 4),
        }
    out["solved_tasks"] = {a: sorted(t for t in common if solved[a][t]) for a in arms}
    out["common_tasks"] = common
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_ids", nargs="+")
    ap.add_argument("--reference", default="base_L0")
    ap.add_argument("--out")
    ap.add_argument("--allow-repeats", action="store_true")
    ap.add_argument("--complete-hints", metavar="ARM",
                    help="keep only tasks whose oracle hint in ARM was not clipped (sensitivity analysis)")
    args = ap.parse_args()
    rows = load_rows(args.run_ids)
    dropped: list[str] = []
    if args.complete_hints:
        dropped = sorted({r["task"] for r in rows
                          if r["arm"] == args.complete_hints and r.get("hint", {}).get("truncated")})
        rows = [r for r in rows if r["task"] not in dropped]
    result = analyse(rows, args.reference, args.allow_repeats)
    result["run_ids"] = args.run_ids
    if args.complete_hints:
        result["complete_hints_arm"] = args.complete_hints
        result["dropped_tasks"] = dropped
    out = (ROOT / args.out).resolve() if args.out else ROOT / "runs" / args.run_ids[0] / "analysis.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1) + "\n")
    print(f"{result['n_common_tasks']} common tasks -> {out.relative_to(ROOT)}")
    for a, info in result["arms"].items():
        pv = result["paired_vs_reference"].get(a, {})
        extra = f"  vs {args.reference}: +{pv['only_arm']}/-{pv['only_reference']} p={pv['p_mcnemar']}" if pv else ""
        print(f"  {a:<16} {info['k']:>3}/{info['n']:<3} {100 * info['rate']:5.1f}%  "
              f"[{100 * info['ci95'][0]:.1f}, {100 * info['ci95'][1]:.1f}]  no_patch={info['no_patch']} "
              f"med={info['median_seconds']}s calls={info['mean_tool_calls']}{extra}")
    if "ladder" in result:
        print("  ladder:", result["ladder"])


if __name__ == "__main__":
    main()
