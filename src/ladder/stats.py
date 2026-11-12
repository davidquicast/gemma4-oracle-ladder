"""Small-sample statistics used in the paper. Standard library only."""
from __future__ import annotations

from math import comb, sqrt


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar test on the discordant pairs.

    b = pairs solved only by A, c = pairs solved only by B. Under the null the
    discordant pairs split as Binomial(b + c, 1/2).
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def paired(a: dict[str, bool], b: dict[str, bool]) -> dict:
    """Paired comparison of two arms over the tasks both ran."""
    common = sorted(set(a) & set(b))
    both = sum(a[t] and b[t] for t in common)
    only_a = sum(a[t] and not b[t] for t in common)
    only_b = sum(b[t] and not a[t] for t in common)
    return {
        "n": len(common), "a": both + only_a, "b": both + only_b, "both": both,
        "only_a": only_a, "only_b": only_b, "p_mcnemar": mcnemar_exact(only_a, only_b),
    }


def signflip_exact(diffs: list[int]) -> dict:
    """Exact two-sided sign-flip (permutation) test on paired integer differences.

    Under the null each difference is equally likely to carry either sign, so
    the sum S = sum(±|d_i|) has the distribution of the convolution of the
    two-point laws {-|d_i|, +|d_i|}. p = P(|S| >= |D|), D the observed sum.
    """
    nonzero = [abs(int(d)) for d in diffs if d]
    dist: dict[int, int] = {0: 1}
    for a in nonzero:
        nxt: dict[int, int] = {}
        for s, w in dist.items():
            nxt[s + a] = nxt.get(s + a, 0) + w
            nxt[s - a] = nxt.get(s - a, 0) + w
        dist = nxt
    d_obs = int(sum(diffs))
    total = 2 ** len(nonzero)
    extreme = sum(w for s, w in dist.items() if abs(s) >= abs(d_obs))
    return {"D": d_obs, "n_nonzero": len(nonzero), "p_two_sided": min(1.0, extreme / total)}
