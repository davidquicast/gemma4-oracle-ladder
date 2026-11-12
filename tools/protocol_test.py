#!/usr/bin/env python
"""Pre-registered tests of an arm against controls (docs/rules.md, wave 3).

    tools/protocol_test.py <out.json> --treat <run:arm>... --control <run:arm>...
                           [--pairs-only | --mcnemar-rule] [--key NAME]

Per task d = (solves in the treat arms) - (solves in the control arms) over
the tasks every listed arm graded. With as many treat as control arms the
primary rule applies: exact two-sided sign-flip test on d; the verdict is
"shown" iff D > 0 and p < 0.01. With one treat arm and several controls the
fallback applies: exact McNemar p < 0.01 in every treat x control pairing,
all with the same non-zero sign of the net. Every pairing also carries its
discordant counts, exact McNemar p and the D-011 outcome (net > 21 and
p < 0.01). --mcnemar-rule applies the McNemar rule whatever the arm counts
(the carry-over rule of the project plan). --pairs-only writes the pairings without a rule. --key stores the
result under that key of <out.json>, keeping the other keys (used to put
several levels in one file). The verdict is printed as data.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ladder.stats import mcnemar_exact, signflip_exact  # noqa: E402

D011_MARGIN = 21
ALPHA = 0.01


def load_arm(spec: str) -> dict[str, bool]:
    run, arm = spec.split(":", 1)
    solved = {}
    for line in (ROOT / "runs" / run / "output" / "results.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r["arm"] == arm and r["status"] == "done" and r.get("gradable", True):
            solved[r["task"]] = bool(r["resolved"])
    if not solved:
        raise SystemExit(f"no graded rows for {spec}")
    return solved


def pairing(t: dict[str, bool], c: dict[str, bool], tasks: list[str]) -> dict:
    only_t = sum(t[k] and not c[k] for k in tasks)
    only_c = sum(c[k] and not t[k] for k in tasks)
    p = mcnemar_exact(only_t, only_c)
    net = only_t - only_c
    return {"n": len(tasks), "treat_solved": sum(t[k] for k in tasks), "control_solved": sum(c[k] for k in tasks),
            "only_treat": only_t, "only_control": only_c, "net": net, "p_mcnemar": p,
            "d011_outcome": bool(net > D011_MARGIN and p < ALPHA)}


def run(treat: list[str], control: list[str], pairs_only: bool = False,
        arms: dict[str, dict[str, bool]] | None = None, mcnemar_rule: bool = False) -> dict:
    arms = arms or {s: load_arm(s) for s in treat + control}
    tasks = sorted(set.intersection(*(set(arms[s]) for s in treat + control)))
    out: dict = {"treat": treat, "control": control, "n_tasks": len(tasks),
                 "pairings": {f"{t} vs {c}": pairing(arms[t], arms[c], tasks) for t in treat for c in control}}
    if pairs_only:
        out["rule"] = None
        return out
    if len(treat) == len(control) and not mcnemar_rule:
        diffs = [sum(arms[t][k] for t in treat) - sum(arms[c][k] for c in control) for k in tasks]
        sf = signflip_exact(diffs)
        out["rule"] = "signflip: D > 0 and p < 0.01"
        out["signflip"] = sf
        out["verdict"] = "shown" if sf["D"] > 0 and sf["p_two_sided"] < ALPHA else "not shown"
    elif len(treat) == 1 or mcnemar_rule:
        ps = list(out["pairings"].values())
        signs = {(p["net"] > 0) - (p["net"] < 0) for p in ps}
        ok = all(p["p_mcnemar"] < ALPHA for p in ps) and len(signs) == 1 and 0 not in signs
        out["rule"] = "mcnemar in every pairing: p < 0.01, same non-zero sign"
        out["verdict"] = ("shown, positive" if signs == {1} else "shown, negative") if ok else "not shown"
    else:
        raise SystemExit("sign-flip test needs as many treat as control arms")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--treat", nargs="+", required=True)
    ap.add_argument("--control", nargs="+", required=True)
    ap.add_argument("--pairs-only", action="store_true")
    ap.add_argument("--mcnemar-rule", action="store_true")
    ap.add_argument("--key")
    a = ap.parse_args()
    res = run(a.treat, a.control, a.pairs_only, mcnemar_rule=a.mcnemar_rule)
    path = ROOT / a.out if not Path(a.out).is_absolute() else Path(a.out)
    if a.key:
        doc = json.loads(path.read_text()) if path.exists() else {}
        doc[a.key] = res
    else:
        doc = res
    path.write_text(json.dumps(doc, indent=1) + "\n")
    for name, p in res["pairings"].items():
        print(f"{name}: only_treat {p['only_treat']}, only_control {p['only_control']}, net {p['net']}, "
              f"p {p['p_mcnemar']:.6g}, d011 {p['d011_outcome']}")
    if res.get("signflip"):
        s = res["signflip"]
        print(f"signflip: D {s['D']}, n_nonzero {s['n_nonzero']}, p {s['p_two_sided']:.6g}")
    if res["rule"]:
        print(f"rule: {res['rule']}\nverdict: {res['verdict']}")


if __name__ == "__main__":
    main()
