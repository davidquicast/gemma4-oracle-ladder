"""Failure labels for every episode of a run (docs/rules.md, D-010).

    python tools/label_failures.py label <run_id>             -> runs/<run_id>/failure_labels.json
    python tools/label_failures.py show <run_id> <arm> <task>  bounded view of one trace

Inputs: runs/<id>/output/results.jsonl, and the traces and patches inside
runs/<id>/output/eval.zip (read in place, nothing extracted). Reference patches
come from data/competition_files/tasks.jsonl through ladder.patches.source_files.

Patch-state label of an unsolved episode, first match wins:
  oracle_clipped, output_cut_off, no_edit_attempted, malformed_call,
  edit_rejected (empty_other), destructive_overwrite, incomplete_patch, wrong_patch.
Solved episodes get `solved`. How the episode ended is a second axis:
  submit, timeout, tool_budget, turn_budget, stopped.
"""
from __future__ import annotations

import ast
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ladder.patches import parse_patch, source_files  # noqa: E402

TASKS = ROOT / "data" / "competition_files" / "tasks.jsonl"
EDIT_TOOLS = ("edit_file", "write_file")
DESTRUCTIVE_EXTRA_REMOVED = 20

LABELS = (
    "solved", "oracle_clipped", "output_cut_off", "no_edit_attempted", "malformed_call",
    "edit_rejected", "empty_other", "destructive_overwrite", "incomplete_patch", "wrong_patch",
)
ENDS = ("submit", "timeout", "tool_budget", "turn_budget", "stopped")
EDIT_OUTCOMES = ("ok", "not_found", "ambiguous", "identical", "missing_file", "malformed", "other_error")
NOT_FOUND_CLASSES = ("repeat_of_applied", "in_preimage", "in_postimage", "not_verbatim")


# ---------------------------------------------------------------- trace parsing

def _args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        try:
            return ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return {}


def _obs_text(step: dict) -> str:
    ob = step.get("observation")
    if not ob:
        return ""
    if isinstance(ob, dict):
        c = ob.get("content")
        if c is None and ob.get("results") is not None:
            c = ob["results"]
        return c if isinstance(c, str) else json.dumps(c)
    return str(ob)


def classify_edit(obs: str) -> str:
    """Outcome of one edit_file call from its observation text."""
    if obs.startswith('{"error": "Invoking'):
        return "malformed"
    if '"status": "ok"' in obs:
        return "ok"
    if "old_string not found" in obs:
        return "not_found"
    if "Target string occurs" in obs or "flexibly matches" in obs:
        return "ambiguous"
    if "old_string and new_string are identical" in obs:
        return "identical"
    if "Source path" in obs and "not" in obs:
        return "missing_file"
    return "other_error"


def tool_events(trace: dict) -> tuple[list[dict], Counter]:
    """Ordered tool calls with their outcome, and nudge counts by kind.

    A step's tool_calls are paired with the step's observation; the harness
    issues one call per step, so one observation per step is assumed.
    """
    events, nudges = [], Counter()
    for step in trace.get("steps", []):
        if (step.get("extra") or {}).get("event_type") == "continuation_nudge":
            msg = step.get("message") or ""
            if "token limit while thinking" in msg:
                nudges["token_limit_thinking"] += 1
            elif "token limit" in msg:
                nudges["token_limit_tool_call"] += 1
            else:
                nudges["plain"] += 1
            continue
        calls = step.get("tool_calls") or []
        obs = _obs_text(step)
        for tc in calls:
            events.append({"tool": tc.get("function_name"), "args": _args(tc.get("arguments")), "obs": obs})
    return events, nudges


# ---------------------------------------------------------------- patch facts

def _added(files) -> Counter:
    return Counter(
        l[1:].strip() for f in files for h in f.hunks for l in h.lines
        if l[:1] == "+" and l[1:].strip()
    )


def _removed_count(files) -> int:
    return sum(1 for f in files for h in f.hunks for l in h.lines if l[:1] == "-")


def recall_of_reference(agent_patch: str, ref_patch: str) -> float | None:
    ref = _added(source_files(ref_patch))
    if not ref:
        return None
    got = _added(source_files(agent_patch))
    return sum(min(n, got[line]) for line, n in ref.items()) / sum(ref.values())


# ---------------------------------------------------------------- episode label

def end_reason(error: str | None, submitted: bool) -> str:
    e = (error or "").lower()
    if "timeout" in e:
        return "timeout"
    if "tool call budget" in e:
        return "tool_budget"
    if "turn" in e and ("budget" in e or "limit" in e):
        return "turn_budget"
    return "submit" if submitted else "stopped"


def episode_facts(events: list[dict], nudges: Counter, agent_patch: str, ref_patch: str, level: str) -> dict:
    ref_files = source_files(ref_patch)
    pre = [h.old_text for f in ref_files for h in f.hunks]
    post = [h.new_text for f in ref_files for h in f.hunks]
    agent_files = {f.path: f for f in parse_patch(agent_patch)}

    edit = Counter({k: 0 for k in EDIT_OUTCOMES})
    write = Counter({"ok": 0, "overwrite_existing": 0, "malformed": 0, "other_error": 0})
    not_found = Counter({k: 0 for k in NOT_FOUND_CLASSES})
    seen_paths, applied_old = set(), set()
    edits_wellformed = edits_ok = edits_total = 0
    last_edit_failed = None
    submitted = saw_submit = False
    failed_before_submit = None
    for ev in events:
        tool, a, obs = ev["tool"], ev["args"], ev["obs"]
        path = str(a.get("filepath") or a.get("path") or "").lstrip("/")
        if path.startswith("workspace/"):
            path = path[len("workspace/"):]
        if tool == "read_file" and '"status": "ok"' in obs:
            seen_paths.add(path)
        elif tool == "edit_file":
            out = classify_edit(obs)
            edit[out] += 1
            edits_total += 1
            edits_wellformed += out != "malformed"
            edits_ok += out == "ok"
            last_edit_failed = out != "ok"
            old = str(a.get("old_string") or "")
            if out == "ok":
                applied_old.add((path, old.strip()))
                seen_paths.add(path)
            elif out == "not_found" and level in ("L2", "L3"):
                key = old.strip("\n")
                if (path, old.strip()) in applied_old:
                    not_found["repeat_of_applied"] += 1
                elif key and any(key in t for t in pre):
                    not_found["in_preimage"] += 1
                elif key and level == "L3" and any(key in t for t in post):
                    not_found["in_postimage"] += 1
                else:
                    not_found["not_verbatim"] += 1
        elif tool == "write_file":
            edits_total += 1
            if obs.startswith('{"error": "Invoking'):
                write["malformed"] += 1
                last_edit_failed = True
                continue
            edits_wellformed += 1
            if '"status": "ok"' in obs:
                write["ok"] += 1
                edits_ok += 1
                last_edit_failed = False
                f = agent_files.get(path)
                existed = path in seen_paths or (f is not None and not f.is_new)
                write["overwrite_existing"] += existed
                seen_paths.add(path)
            else:
                write["other_error"] += 1
                last_edit_failed = True
        elif tool == "submit_patch":
            if '"status": "ok"' in obs:
                submitted = True
            if not saw_submit:  # the first submit is the one graded
                saw_submit, failed_before_submit = True, last_edit_failed
    return {
        "edit_file": dict(edit),
        "write_file": dict(write),
        "edit_calls_total": edits_total,
        "edit_calls_wellformed": edits_wellformed,
        "edit_calls_ok": edits_ok,
        "not_found_classes": dict(not_found) if level in ("L2", "L3") else None,
        "nudges": {k: nudges.get(k, 0) for k in ("token_limit_thinking", "token_limit_tool_call", "plain")},
        "submitted": submitted,
        "last_edit_failed_before_submit": failed_before_submit,
        "patch_removed_lines": _removed_count(source_files(agent_patch)),
        "reference_removed_lines": _removed_count(ref_files),
        "reference_recall": recall_of_reference(agent_patch, ref_patch) if agent_patch.strip() else 0.0,
    }


def label(resolved: bool, truncated: bool, empty_patch: bool, level: str, facts: dict) -> str:
    """Patch-state label, first match wins (docs/rules.md)."""
    if resolved:
        return "solved"
    if truncated:
        return "oracle_clipped"
    tl = facts["nudges"]["token_limit_thinking"] + facts["nudges"]["token_limit_tool_call"]
    if empty_patch:
        if tl > 0:
            return "output_cut_off"
        if facts["edit_calls_total"] == 0:
            return "no_edit_attempted"
        if facts["edit_calls_wellformed"] == 0:
            return "malformed_call"
        if facts["edit_calls_ok"] == 0:
            return "edit_rejected"
        return "empty_other"
    if facts["write_file"]["overwrite_existing"] > 0 and (
        facts["patch_removed_lines"] - facts["reference_removed_lines"] >= DESTRUCTIVE_EXTRA_REMOVED
    ):
        return "destructive_overwrite"
    if level == "L3" and facts["reference_recall"] is not None and facts["reference_recall"] < 1:
        return "incomplete_patch"
    return "wrong_patch"


# ---------------------------------------------------------------- run level

def load_reference() -> dict[str, str]:
    out = {}
    for line in TASKS.read_text().splitlines():
        if line.strip():
            t = json.loads(line)
            out[t["instance_id"]] = t["patch"]
    return out


def strip_rej(patch: str) -> tuple[str, int]:
    """Drop the file sections of a unified diff whose path ends in `.rej`.

    `git apply --reject` leaves `<file>.rej` beside each file with a rejected
    hunk; the harness diff then lists them as new files. They are residue of
    the edit tool, not part of the agent's fix.
    """
    if ".rej" not in patch:
        return patch, 0
    parts = re.split(r"(?m)^(?=diff --git )", patch)
    keep, dropped = [], 0
    for part in parts:
        head = part.split("\n", 1)[0]
        if head.startswith("diff --git ") and head.rstrip().endswith(".rej"):
            dropped += 1
        else:
            keep.append(part)
    return "".join(keep), dropped


def label_run(run_id: str) -> dict:
    out_dir = ROOT / "runs" / run_id / "output"
    refs = load_reference()
    zf = zipfile.ZipFile(out_dir / "eval.zip")
    names = set(zf.namelist())
    episodes = []
    for line in (out_dir / "results.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("status") != "done" or not r.get("gradable", True):
            continue
        arm, task, level = r["arm"], r["task"], r["level"]
        tpath = f"{arm}/traces/trace_{task}.json"
        ppath = f"{arm}/patches/{task}.patch"
        trace = json.loads(zf.read(tpath)) if tpath in names else {"steps": []}
        agent_patch = zf.read(ppath).decode("utf-8", "replace") if ppath in names else ""
        agent_patch, rej_files = strip_rej(agent_patch)
        events, nudges = tool_events(trace)
        facts = episode_facts(events, nudges, agent_patch, refs.get(task, ""), level)
        empty = (r.get("patch_chars") or 0) == 0 or (rej_files > 0 and not agent_patch.strip())
        lab = label(bool(r["resolved"]), bool((r.get("hint") or {}).get("truncated")), empty, level, facts)
        episodes.append({
            "arm": arm, "task": task, "level": level, "resolved": bool(r["resolved"]),
            "label": lab, "end": end_reason((r.get("result") or {}).get("error"), facts["submitted"]),
            "empty_patch": empty, "has_trace": tpath in names, **facts,
        })
    return {"run_id": run_id, "scheme": "docs/rules.md (D-010)", "episodes": episodes, "summary": summarise(episodes)}


def summarise(episodes: list[dict]) -> dict:
    by_arm = defaultdict(list)
    for e in episodes:
        by_arm[e["arm"]].append(e)
    out = {}
    for arm, eps in sorted(by_arm.items()):
        labels = Counter(e["label"] for e in eps)
        cross = defaultdict(Counter)
        for e in eps:
            cross[e["label"]][e["end"]] += 1
        unsolved = [e for e in eps if not e["resolved"]]
        edit, write, nf, nud = Counter(), Counter(), Counter(), Counter()
        for e in eps:
            edit.update(e["edit_file"])
            write.update(e["write_file"])
            nud.update(e["nudges"])
            if e["not_found_classes"]:
                nf.update(e["not_found_classes"])
        out[arm] = {
            "n": len(eps),
            "labels": {k: labels.get(k, 0) for k in LABELS},
            "label_x_end": {k: {x: cross[k].get(x, 0) for x in ENDS} for k in LABELS if labels.get(k)},
            "end_unsolved": {x: sum(e["end"] == x for e in unsolved) for x in ENDS},
            "n_unsolved": len(unsolved),
            "edit_file": {k: edit.get(k, 0) for k in EDIT_OUTCOMES},
            "write_file": dict(write),
            "nudges": dict(nud),
            "not_found_classes": {k: nf.get(k, 0) for k in NOT_FOUND_CLASSES} if eps and eps[0]["level"] in ("L2", "L3") else None,
            "last_edit_failed_before_submit": sum(bool(e["last_edit_failed_before_submit"]) for e in unsolved),
        }
    return out


def show(run_id: str, arm: str, task: str, width: int = 200) -> None:
    zf = zipfile.ZipFile(ROOT / "runs" / run_id / "output" / "eval.zip")
    trace = json.loads(zf.read(f"{arm}/traces/trace_{task}.json"))
    for step in trace.get("steps", []):
        ev = (step.get("extra") or {}).get("event_type")
        if ev == "continuation_nudge":
            print(f"[nudge] {(step.get('message') or '')[:width]!r}")
            continue
        obs = _obs_text(step)
        for tc in step.get("tool_calls") or []:
            a = _args(tc.get("arguments"))
            print(f"> {tc.get('function_name')}")
            for k, v in a.items():
                print(f"    {k}: {str(v)[:width]!r}")
            print(f"  = {obs[:width]!r}")


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "label":
        res = label_run(sys.argv[2])
        dest = ROOT / "runs" / sys.argv[2] / "failure_labels.json"
        dest.write_text(json.dumps(res, indent=1) + "\n")
        for arm, s in res["summary"].items():
            print(arm, {k: v for k, v in s["labels"].items() if v})
        print("wrote", dest.relative_to(ROOT))
    elif len(sys.argv) == 5 and sys.argv[1] == "show":
        show(*sys.argv[2:5])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
