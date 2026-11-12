import importlib.util
from collections import Counter
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "label_failures", Path(__file__).resolve().parents[1] / "tools" / "label_failures.py")
lf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lf)

REF = "--- a/pkg/m.py\n+++ b/pkg/m.py\n@@ -1,2 +1,2 @@\n x = 1\n-y = 2\n+y = 3\n"
OK_EDIT = '{"status": "ok", "filepath": "pkg/m.py", "occurrences": 1}'
NOT_FOUND = '{"status": "error", "error_message": "Failed to replace: old_string not found."}'
MALFORMED = '{"error": "Invoking `edit_file()` failed as the following mandatory input parameters are not present:\\nold_string"}'


def ev(tool, obs, **args):
    return {"tool": tool, "args": args, "obs": obs}


def facts(events, nudges=None, patch="", level="L3"):
    return lf.episode_facts(events, Counter(nudges or {}), patch, REF, level)


def test_classify_edit():
    assert lf.classify_edit(OK_EDIT) == "ok"
    assert lf.classify_edit(NOT_FOUND) == "not_found"
    assert lf.classify_edit(MALFORMED) == "malformed"
    assert lf.classify_edit('{"error_message": "Target string occurs 3 times in a.py"}') == "ambiguous"
    assert lf.classify_edit('{"error_message": "No changes to apply. old_string and new_string are identical."}') == "identical"
    assert lf.classify_edit('{"error_message": "Source path /workspace/x.py not found"}') == "missing_file"


def test_solved_and_clipped_take_precedence():
    f = facts([])
    assert lf.label(True, True, True, "L3", f) == "solved"
    assert lf.label(False, True, True, "L3", f) == "oracle_clipped"


def test_empty_patch_labels_in_order():
    assert lf.label(False, False, True, "L0", facts([], {"token_limit_thinking": 1})) == "output_cut_off"
    assert lf.label(False, False, True, "L0", facts([ev("read_file", '{"status": "ok"}', filepath="a")])) == "no_edit_attempted"
    assert lf.label(False, False, True, "L0", facts([ev("edit_file", MALFORMED)])) == "malformed_call"
    mixed = [ev("edit_file", MALFORMED), ev("edit_file", NOT_FOUND, filepath="pkg/m.py", old_string="zz")]
    assert lf.label(False, False, True, "L0", facts(mixed)) == "edit_rejected"
    assert lf.label(False, False, True, "L0", facts([ev("edit_file", OK_EDIT, filepath="pkg/m.py", old_string="y = 2")])) == "empty_other"


def test_nonempty_labels():
    full = REF
    partial = "--- a/pkg/m.py\n+++ b/pkg/m.py\n@@ -1,2 +1,2 @@\n x = 1\n-y = 2\n+y = 4\n"
    assert lf.label(False, False, False, "L3", facts([], patch=full)) == "wrong_patch"
    assert lf.label(False, False, False, "L3", facts([], patch=partial)) == "incomplete_patch"
    assert lf.label(False, False, False, "L2", facts([], patch=partial, level="L2")) == "wrong_patch"
    big = "--- a/pkg/m.py\n+++ b/pkg/m.py\n@@ -1,30 +1,1 @@\n" + "".join(f"-l{i}\n" for i in range(30)) + "+y = 3\n"
    write = [ev("read_file", '{"status": "ok"}', filepath="pkg/m.py"),
             ev("write_file", '{"status": "ok", "filepath": "pkg/m.py", "size": 6}', filepath="pkg/m.py", content="y = 3")]
    f = facts(write, patch=big)
    assert f["write_file"]["overwrite_existing"] == 1
    assert lf.label(False, False, False, "L3", f) == "destructive_overwrite"


def test_not_found_classes_and_last_edit():
    events = [
        ev("edit_file", OK_EDIT, filepath="pkg/m.py", old_string="y = 2", new_string="y = 3"),
        ev("edit_file", NOT_FOUND, filepath="pkg/m.py", old_string="y = 2", new_string="y = 3"),
        ev("edit_file", NOT_FOUND, filepath="pkg/m.py", old_string="x = 1", new_string="x = 0"),
        ev("edit_file", NOT_FOUND, filepath="pkg/m.py", old_string="y = 3", new_string="y = 4"),
        ev("edit_file", NOT_FOUND, filepath="pkg/m.py", old_string="nope", new_string="z"),
        ev("submit_patch", '{"status": "ok", "patch_size": 10}'),
    ]
    f = facts(events, patch=REF)
    assert f["not_found_classes"] == {"repeat_of_applied": 1, "in_preimage": 1, "in_postimage": 1, "not_verbatim": 1}
    assert f["last_edit_failed_before_submit"] is True
    assert f["submitted"] is True
    assert facts(events, level="L0")["not_found_classes"] is None


def test_end_reason():
    assert lf.end_reason("Agent exceeded session timeout (5.0 min)", True) == "timeout"
    assert lf.end_reason("Agent exceeded tool call budget (24 calls)", False) == "tool_budget"
    assert lf.end_reason("Agent exceeded turn budget", False) == "turn_budget"
    assert lf.end_reason(None, True) == "submit"
    assert lf.end_reason("Agent completed execution without calling submit_patch.", False) == "stopped"


def test_nudge_kinds():
    trace = {"steps": [
        {"extra": {"event_type": "continuation_nudge"}, "message": "Your previous response reached the token limit while thinking before"},
        {"extra": {"event_type": "continuation_nudge"}, "message": "Your previous response reached the token limit before the tool call finished"},
        {"extra": {"event_type": "continuation_nudge"}, "message": "Please continue your work"},
    ]}
    _, n = lf.tool_events(trace)
    assert n == Counter({"token_limit_thinking": 1, "token_limit_tool_call": 1, "plain": 1})


def test_git_apply_outcomes():
    import importlib.util
    spec = importlib.util.spec_from_file_location("patch_channel", Path(__file__).resolve().parents[1] / "tools" / "patch_channel.py")
    pc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pc)
    assert pc.classify_apply('{"status": "ok", "exit_code": 0}') == "ok"
    assert pc.classify_apply('{"status": "error", "error_message": "error: corrupt patch at line 12"}') == "corrupt_patch"
    assert pc.classify_apply('{"status": "error", "error_message": "error: patch failed: a.py:3"}') == "context_mismatch"
    assert pc.classify_apply('{"status": "error", "error_message": "error: patch fragment without header at line 2"}') == "no_header"
    assert pc.classify_apply('{"status": "error", "error_message": "boom"}') == "other_error"


def test_strip_rej_drops_only_reject_files():
    patch = ("diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n"
             "diff --git a/x.py.rej b/x.py.rej\nnew file mode 100644\n--- /dev/null\n+++ b/x.py.rej\n@@ -0,0 +1 @@\n+junk\n")
    kept, n = lf.strip_rej(patch)
    assert n == 1 and "x.py.rej" not in kept and kept.startswith("diff --git a/x.py b/x.py")
    assert lf.strip_rej("diff --git a/y b/y\n") == ("diff --git a/y b/y\n", 0)
    only_rej = "diff --git a/z.rej b/z.rej\n+++ b/z.rej\n"
    assert lf.strip_rej(only_rej) == ("", 1)


def test_patch_channel_hunk_outcomes():
    spec = importlib.util.spec_from_file_location("patch_channel", Path(__file__).parents[1] / "tools" / "patch_channel.py")
    pc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pc)
    assert pc.classify_apply('{"status": "ok"}') == "ok"
    partial = "Checking patch a.py...\nApplying patch a.py with 1 reject...\nHunk #1 applied cleanly.\nRejected hunk #2."
    assert pc.classify_apply(partial) == "partial" and pc.hunk_counts(partial) == (1, 1)
    assert pc.classify_apply("Rejected hunk #1.\nRejected hunk #2.") == "rejected"
    assert pc.classify_apply("error: corrupt patch at line 9") == "corrupt_patch"
    assert pc.classify_apply("Hunk #1 succeeded at 40 (offset 2 lines).\nRejected hunk #2.") == "partial"
