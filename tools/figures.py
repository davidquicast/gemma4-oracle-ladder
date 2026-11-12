"""Figures of the paper, drawn only from analysis files under runs/.

    python tools/figures.py        -> paper/figures/fig1_ladder.png, fig2_patch_size.png

fig1: solve rate of the base bundle at each oracle level (wave 1), Wilson 95%.
fig2: solve rate at L3 by reference-patch size for the two identical edit-tool
      runs, the git-apply arm (waves 1 and 2) and, once wave 3 exists, the mean
      of the two hunk-protocol runs (pooled over both runs), Wilson 95%.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#7a5bd1"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": GRID, "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def _axes(ax, ymax: float) -> None:
    ax.set_ylim(0, ymax)
    ax.set_ylabel("tasks solved (%)")
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)


def _pool(a: dict, b: dict) -> dict:
    """Two runs of one arm pooled: k and n summed, Wilson 95% on the pool, shown as a per-run mean."""
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from ladder.stats import wilson
    k, n = a["k"] + b["k"], a["n"] + b["n"]
    lo, hi = wilson(k, n)
    mean = k / 2
    return {"k": int(mean) if mean == int(mean) else mean, "n": a["n"], "rate": k / n, "ci95": [lo, hi]}


def _bars(ax, xs, cells, color, width, label=None):
    rates = [100 * c["rate"] for c in cells]
    lo = [100 * (c["rate"] - c["ci95"][0]) for c in cells]
    hi = [100 * (c["ci95"][1] - c["rate"]) for c in cells]
    ax.bar(xs, rates, width=width, color=color, label=label, edgecolor=SURFACE, linewidth=2)
    ax.errorbar(xs, rates, yerr=[lo, hi], fmt="none", ecolor=INK, elinewidth=1, capsize=3)
    for x, c, h in zip(xs, cells, hi):
        ax.text(x, 100 * c["rate"] + h + 1.5, f"{c['k']}/{c['n']}", ha="center", va="bottom", fontsize=9, color=INK)


def fig1() -> None:
    arms = _load("runs/wave1/analysis.json")["arms"]
    levels = [("L0", "L0\nthe task"), ("L1", "L1\n+ files"), ("L2", "L2\n+ lines and code"),
              ("L3", "L3\n+ reference diff"), ("T", "T\n+ hidden tests")]
    fig, ax = plt.subplots(figsize=(7.2, 3.9), dpi=200)
    _bars(ax, range(len(levels)), [arms[f"base_{lv}"] for lv, _ in levels], BLUE, 0.56)
    ax.set_xticks(range(len(levels)), [name for _, name in levels])
    _axes(ax, 62)
    ax.set_title("Gemma 4 E2B, official starter agent, 127 public tasks", loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_ladder.png")
    plt.close(fig)


def fig2() -> None:
    w1 = _load("runs/wave1/analysis.json")["by_patch_size"]
    w2 = _load("runs/wave2/analysis.json")["by_patch_size"]
    bins = ["1 file, 1 hunk", "1 file, 2+ hunks", "2+ files"]
    series = [("edit tools, run 1", BLUE, [w1[b]["base_L3"] for b in bins]),
              ("edit tools, run 2", ORANGE, [w2[b]["base_r2_L3"] for b in bins]),
              ("one git apply", AQUA, [w2[b]["patch_L3"] for b in bins])]
    w3_path = ROOT / "runs/wave3/analysis.json"
    if w3_path.exists():
        w3 = json.loads(w3_path.read_text())["by_patch_size"]
        series.append(("hunk protocol, mean of 2 runs", VIOLET,
                       [_pool(w3[b]["hunk_L3"], w3[b]["hunk_r2_L3"]) for b in bins]))
    fig, ax = plt.subplots(figsize=(7.2, 3.9), dpi=200)
    width = 0.78 / len(series)
    mid = (len(series) - 1) / 2
    for i, (name, color, cells) in enumerate(series):
        _bars(ax, [x + (i - mid) * width for x in range(len(bins))], cells, color, width, name)
    ax.set_xticks(range(len(bins)), [f"{b}\n({w1[b]['base_L3']['n']} tasks)" for b in bins])
    _axes(ax, 100)
    ax.set_title("Solve rate with the reference diff given (L3), by size of that diff", loc="left", fontsize=11)
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_patch_size.png")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fig1()
    fig2()
    print("wrote", *(p.name for p in sorted(OUT.glob("*.png"))))
