import json
from pathlib import Path

import pytest

from ladder.oracle import LEVELS, MAX_HINT_CHARS, apply_level, build_hint
from ladder.patches import is_protected, parse_patch, source_files

PATCH = """--- a/pkg/core.py
+++ b/pkg/core.py
@@ -10,3 +10,4 @@ def f(x):
     a = 1
-    return a
+    b = 2
+    return a + b
 
--- a/pkg/new_mod.py
+++ b/pkg/new_mod.py
@@ -0,0 +1,2 @@
+def g():
+    return 1
--- a/tests/test_core.py
+++ b/tests/test_core.py
@@ -1,1 +1,2 @@
 import pkg
+assert pkg
"""
TASKS = Path(__file__).resolve().parents[1] / "data" / "competition_files" / "tasks.jsonl"


def test_parse_splits_files_and_hunks():
    files = parse_patch(PATCH)
    assert [f.path for f in files] == ["pkg/core.py", "pkg/new_mod.py", "tests/test_core.py"]
    h = files[0].hunks[0]
    assert (h.old_start, h.old_len, h.new_start, h.new_len) == (10, 3, 10, 4)
    assert h.old_text == "    a = 1\n    return a\n"
    assert h.new_text == "    a = 1\n    b = 2\n    return a + b\n"
    assert files[1].is_new and not files[0].is_new
    assert "".join(f.raw for f in files) == PATCH


def test_protected_paths_follow_the_harness_rule():
    assert is_protected("tests/test_core.py") and is_protected("pkg/conftest.py")
    assert is_protected("pkg/foo_test.py") and is_protected("pyproject.toml")
    assert not is_protected("pkg/core.py") and not is_protected("docs_src/tutorial001.py")
    assert [f.path for f in source_files(PATCH)] == ["pkg/core.py", "pkg/new_mod.py"]


def test_levels_are_nested_in_information():
    l0, l1, l2, l3 = (build_hint(lv, PATCH)[0] for lv in ("L0", "L1", "L2", "L3"))
    assert l0 == ""
    assert "pkg/core.py" in l1 and "return a" not in l1
    assert "lines 10-12" in l2 and "return a" in l2 and "return a + b" not in l2
    assert "return a + b" in l3
    assert all("tests/test_core.py" not in h for h in (l1, l2, l3))


def test_test_oracle_shows_only_the_test_patch():
    hint, meta = build_hint("T", PATCH, "--- a/tests/t.py\n+++ b/tests/t.py\n@@ -0,0 +1 @@\n+assert f(1) == 3\n")
    assert "assert f(1) == 3" in hint and "return a + b" not in hint and meta["level"] == "T"


def test_existing_hints_are_kept_and_long_hints_are_clipped():
    text, _ = apply_level("maintainer note", "L1", PATCH)
    assert text.startswith("maintainer note\n\nOracle hint")
    big = "--- a/x.py\n+++ b/x.py\n@@ -0,0 +1,3000 @@\n" + "+line of filler text\n" * 3000
    hint, meta = build_hint("L3", big)
    assert meta["truncated"] and len(hint) <= MAX_HINT_CHARS + 40


@pytest.mark.skipif(not TASKS.exists(), reason="competition data not present")
def test_every_public_task_parses_exactly():
    for line in TASKS.read_text().splitlines():
        t = json.loads(line)
        files = parse_patch(t["patch"])
        assert "".join(f.raw for f in files).strip() == t["patch"].strip(), t["instance_id"]
        for f in files:
            for h in f.hunks:
                assert sum(l[:1] in " -" for l in h.lines) == h.old_len, t["instance_id"]
                assert sum(l[:1] in " +" for l in h.lines) == h.new_len, t["instance_id"]
        assert source_files(t["patch"]), t["instance_id"]
        for lv in LEVELS:
            build_hint(lv, t["patch"], t["test_patch"])


def test_statistics_match_known_values():
    from ladder.stats import mcnemar_exact, paired, wilson
    lo, hi = wilson(7, 14)
    assert abs(lo - 0.2680) < 1e-3 and abs(hi - 0.7320) < 1e-3
    assert wilson(0, 10)[0] == 0.0 and wilson(0, 0) == (0.0, 1.0)
    assert mcnemar_exact(0, 0) == 1.0
    assert abs(mcnemar_exact(0, 5) - 0.0625) < 1e-12
    assert abs(mcnemar_exact(2, 8) - 0.109375) < 1e-12
    r = paired({"a": True, "b": False, "c": True}, {"a": True, "b": True, "c": False, "d": True})
    assert (r["n"], r["both"], r["only_a"], r["only_b"]) == (3, 1, 1, 1)
