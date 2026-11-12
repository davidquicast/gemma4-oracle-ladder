from ladder.stats import signflip_exact


def test_signflip_all_zero_is_p_one():
    r = signflip_exact([0] * 127)
    assert r == {"D": 0, "n_nonzero": 0, "p_two_sided": 1.0}


def test_signflip_ten_plus_ones():
    r = signflip_exact([1] * 10 + [0] * 5)
    assert r["D"] == 10 and r["n_nonzero"] == 10
    assert r["p_two_sided"] == 2 / 1024


def test_signflip_symmetric_under_negation():
    d = [2, 1, -1, 0, 1, 2, -2, 1, 1, 0, 1]
    a, b = signflip_exact(d), signflip_exact([-x for x in d])
    assert a["p_two_sided"] == b["p_two_sided"] and a["D"] == -b["D"]


def test_signflip_matches_sign_test_for_unit_diffs():
    from ladder.stats import mcnemar_exact
    d = [1] * 9 + [-1] * 2
    assert abs(signflip_exact(d)["p_two_sided"] - mcnemar_exact(9, 2)) < 1e-12


def _proto():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("protocol_test", Path(__file__).parents[1] / "tools" / "protocol_test.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_protocol_signflip_rule_on_synthetic_arms():
    m = _proto()
    tasks = [f"t{i}" for i in range(40)]
    base = {k: i < 5 for i, k in enumerate(tasks)}
    treat = {k: i < 25 for i, k in enumerate(tasks)}
    arms = {"r:t1": treat, "r:t2": treat, "r:c1": base, "r:c2": base}
    out = m.run(["r:t1", "r:t2"], ["r:c1", "r:c2"], arms=arms)
    assert out["signflip"]["D"] == 40 and out["signflip"]["n_nonzero"] == 20
    assert out["verdict"] == "shown"
    p = out["pairings"]["r:t1 vs r:c1"]
    assert (p["only_treat"], p["only_control"], p["net"], p["d011_outcome"]) == (20, 0, 20, False)


def test_protocol_null_and_fallback_rules():
    m = _proto()
    tasks = [f"t{i}" for i in range(20)]
    a = {k: i % 2 == 0 for i, k in enumerate(tasks)}
    b = {k: i % 2 == 1 for i, k in enumerate(tasks)}
    out = m.run(["r:a"], ["r:b"], arms={"r:a": a, "r:b": b})
    assert out["signflip"]["D"] == 0 and out["verdict"] == "not shown"
    out = m.run(["r:a"], ["r:b", "r:b2"], arms={"r:a": a, "r:b": b, "r:b2": b})
    assert out["verdict"] == "not shown" and out["rule"].startswith("mcnemar")
    out = m.run(["r:a"], ["r:b"], pairs_only=True, arms={"r:a": a, "r:b": b})
    assert out["rule"] is None and "verdict" not in out


def test_protocol_mcnemar_rule_forced_on_one_to_one():
    m = _proto()
    tasks = [f"t{i}" for i in range(30)]
    a = {k: i < 2 for i, k in enumerate(tasks)}
    b = {k: i < 20 for i, k in enumerate(tasks)}
    out = m.run(["r:a"], ["r:b"], arms={"r:a": a, "r:b": b}, mcnemar_rule=True)
    assert out["rule"].startswith("mcnemar") and out["verdict"] == "shown, negative" and "signflip" not in out
