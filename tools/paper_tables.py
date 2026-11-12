"""Print the paper's tables from the analysis files under runs/.

    python tools/paper_tables.py

Reads only files that tools/analyze.py, tools/label_failures.py and
tools/patch_channel.py write, so it runs without a GPU and without the
competition data.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def rate(c: dict) -> str:
    return f"{c['k']}/{c['n']} = {100 * c['rate']:.1f}% ({100 * c['ci95'][0]:.1f}-{100 * c['ci95'][1]:.1f})"


def pair(p: dict) -> str:
    return f"{p['only_arm']} vs {p['only_reference']}, p = {p['p_mcnemar']}"


def main() -> None:
    w1, w1_l2, w1_l3 = (load(f"runs/wave1/{f}.json") for f in ("analysis", "analysis_vs_L2", "analysis_vs_L3"))
    w2, w2_l3, w2_l0 = (load(f"runs/wave2/{f}.json") for f in ("analysis", "analysis_vs_L3", "analysis_vs_L0"))
    lab1, lab2 = load("runs/wave1/failure_labels.json")["summary"], load("runs/wave2/failure_labels.json")["summary"]

    print("Table 1. Ladder on base (wave 1)")
    for lv in ("L0", "L1", "L2", "L3", "T"):
        arm = f"base_{lv}"
        vs = {"L1": ("L0", w1), "L2": ("L0", w1), "T": ("L0", w1), "L3": ("L2", w1_l2)}.get(lv)
        extra = f"   vs {vs[0]}: {pair(vs[1]['paired_vs_reference'][arm])}" if vs else ""
        print(f"  {lv:<3} {rate(w1['arms'][arm])}{extra}")
    print("  gaps:", {k: v for k, v in w1["ladder"].items() if k != "rates"})

    print("\nOther arms")
    for arm in ("lean_L0", "nothink_L0", "pax_L0"):
        print(f"  {arm:<11} {rate(w1['arms'][arm])}   vs base_L0: {pair(w1['paired_vs_reference'][arm])}")
    print(f"  pax_L2      {rate(w1['arms']['pax_L2'])}   vs base_L2: {pair(w1_l2['paired_vs_reference']['pax_L2'])}")
    print(f"  lean_L3     {rate(w1['arms']['lean_L3'])}   vs base_L3: {pair(w1_l3['paired_vs_reference']['lean_L3'])}")
    for arm in ("patch_L3", "base_r2_L3", "base_r2_L0"):
        ref, src = ("base_L0", w2_l0) if arm.endswith("L0") else ("base_L3", w2_l3)
        print(f"  {arm:<11} {rate(w2['arms'][arm])}   vs {ref}: {pair(src['paired_vs_reference'][arm])}")
    print(f"  patch_L3 vs base_r2_L3: {pair(w2['paired_vs_reference']['patch_L3'])}")

    print("\nTable 2. Patch state at grading, L3 arms, complete-hint tasks")
    cols = [("base_L3", lab1), ("base_r2_L3", lab2), ("lean_L3", lab1), ("patch_L3", lab2)]
    rows = [("solved", ("solved",)),
            ("empty", ("output_cut_off", "no_edit_attempted", "malformed_call", "edit_rejected", "empty_other")),
            ("destructive overwrite", ("destructive_overwrite",)), ("incomplete", ("incomplete_patch",)),
            ("complete but failing", ("wrong_patch",)), ("(hint clipped)", ("oracle_clipped",))]
    print(f"  {'':<22}" + "".join(f"{a:>12}" for a, _ in cols))
    for name, keys in rows:
        print(f"  {name:<22}" + "".join(f"{sum(src[a]['labels'][k] for k in keys):>12}" for a, src in cols))

    print("\nSolve rate at L3 by reference-patch size")
    for b in ("1 file, 1 hunk", "1 file, 2+ hunks", "2+ files"):
        print(f"  {b:<17} base_L3 {rate(w1['by_patch_size'][b]['base_L3'])} | base_r2_L3 "
              f"{rate(w2['by_patch_size'][b]['base_r2_L3'])} | patch_L3 {rate(w2['by_patch_size'][b]['patch_L3'])}")

    print("\nEdit calls")
    for arm in ("base_L3", "base_L0"):
        e = lab1[arm]["edit_file"]
        print(f"  {arm} edit_file: {sum(e.values())} calls, {e}")
    print("  base_L3 not-found classes:", lab1["base_L3"]["not_found_classes"])
    print("  base_L3 write_file:", lab1["base_L3"]["write_file"], "| unsolved by end:", lab1["base_L3"]["end_unsolved"])
    pc = load("runs/wave2/patch_channel_patch_L3.json")
    print("  patch_L3 git apply:", pc["calls"])
    print("  patch_L3 unsolved, complete hints:", pc["unsolved_complete_hint"])

    if (ROOT / "runs/wave3/analysis.json").exists():
        wave3(rows)


def wave3(rows) -> None:
    w3 = load("runs/wave3/analysis.json")
    lab3 = load("runs/wave3/failure_labels.json")["summary"]
    print("\nTable 2, wave-3 columns (same rows)")
    cols = ("hunk_L3", "hunk_r2_L3")
    print(f"  {'':<22}" + "".join(f"{a:>12}" for a in cols))
    for name, keys in rows:
        print(f"  {name:<22}" + "".join(f"{sum(lab3[a]['labels'].get(k, 0) for k in keys):>12}" for a in cols))

    print("\nWave 3 solve rates")
    for arm in ("hunk_L3", "hunk_r2_L3", "hunk_L2", "hunk_L0"):
        if arm in w3["arms"]:
            print(f"  {arm:<11} {rate(w3['arms'][arm])}")

    print("\nWave 3 pairings (only treat vs only control, net, exact McNemar p, D-011 outcome)")
    for path, title in (("runs/wave3/protocol_test.json", "primary, L3"),
                        ("runs/wave3/protocol_test_patch_posthoc.json", "post hoc, patch_L3")):
        if not (ROOT / path).exists():
            continue
        t = load(path)
        print(f"  {title}:")
        for name, q in t["pairings"].items():
            print(f"    {name}: {q['only_treat']} vs {q['only_control']}, net {q['net']}, p = {q['p_mcnemar']:.6g}, "
                  f"D-011 {q['d011_outcome']}")
        if t.get("signflip"):
            sf = t["signflip"]
            print(f"    sign-flip: D = {sf['D']}, non-zero d = {sf['n_nonzero']}, p = {sf['p_two_sided']:.6g}; "
                  f"verdict: {t['verdict']}")
    if (ROOT / "runs/wave3/carryover_test.json").exists():
        for level, t in load("runs/wave3/carryover_test.json").items():
            print(f"  carry-over, {level}:")
            for name, q in t["pairings"].items():
                print(f"    {name}: {q['only_treat']} vs {q['only_control']}, net {q['net']}, p = {q['p_mcnemar']:.6g}")
            print(f"    verdict: {t['verdict']}")


if __name__ == "__main__":
    main()
