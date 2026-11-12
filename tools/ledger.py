#!/usr/bin/env python
"""Research ledger: one append-only, auditable record of what was planned,
done, decided, broken and claimed.

Storage: ledger/<kind>.jsonl. Every line is a full snapshot of one record at
one moment; the last line for an id is its current state and earlier lines are
its history. Nothing is ever edited or deleted in place.

Kinds and id prefixes
    task        T   unit of work           status: todo | doing | done | dropped
    experiment  E   hypothesis + runs      status: planned | running | done | failed | invalid
    decision    D   a choice and its why   status: active | superseded
    incident    I   something that broke   status: open | fixed
    claim       C   a statement the paper
                    makes                  status: pending | verified | retracted

Evidence is a list of files in the repo, each pinned by sha256 at the time it
was attached. `validate` fails if a file moved or changed, if a verified claim
or a finished experiment has no evidence, or if the paper cites a claim that is
not verified.

Usage
    tools/ledger.py add  <kind> title="..." [key=value ...] [evidence=path ...]
    tools/ledger.py set  <ID>   key=value ... [evidence=path ...]
    tools/ledger.py show [<ID>|<kind>]
    tools/ledger.py validate
    tools/ledger.py render            # rewrites the generated status page

`key:=<json>` stores a JSON value instead of a string.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "ledger"
PAPER = ROOT / "paper" / "writeup.md"
KINDS = {
    "task": ("T", ("todo", "doing", "done", "dropped")),
    "experiment": ("E", ("planned", "running", "done", "failed", "invalid")),
    "decision": ("D", ("active", "superseded")),
    "incident": ("I", ("open", "fixed")),
    "claim": ("C", ("pending", "verified", "retracted")),
}
PREFIX = {p: k for k, (p, _) in KINDS.items()}
NEEDS_EVIDENCE = {("claim", "verified"), ("experiment", "done"), ("incident", "fixed")}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(kind: str) -> dict[str, dict]:
    """Current state of every record of a kind, in creation order."""
    out: dict[str, dict] = {}
    f = LEDGER / f"{kind}.jsonl"
    if f.exists():
        for line in f.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                out[rec["id"]] = rec
    return out


def append(kind: str, rec: dict) -> None:
    LEDGER.mkdir(exist_ok=True)
    with open(LEDGER / f"{kind}.jsonl", "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def parse_fields(args: list[str]) -> tuple[dict, list[dict]]:
    fields, evidence = {}, []
    for a in args:
        if re.match(r"^\w+:=", a):
            k, v = a.split(":=", 1)
            fields[k] = json.loads(v)
        else:
            k, v = a.split("=", 1)
            if k == "evidence":
                path, _, locator = v.partition("#")
                p = ROOT / path
                if not p.is_file():
                    raise SystemExit(f"evidence not found: {path}")
                evidence.append({"path": path, "sha256": sha256(p), "locator": locator})
            else:
                fields[k] = v
    return fields, evidence


def cmd_add(kind: str, args: list[str]) -> str:
    prefix, statuses = KINDS[kind]
    fields, evidence = parse_fields(args)
    if "title" not in fields:
        raise SystemExit("title= is required")
    n = 1 + max((int(i[2:]) for i in load(kind)), default=0)
    rec = {"id": f"{prefix}-{n:03d}", "kind": kind, "status": statuses[0], "created": now(),
           "updated": now(), "evidence": evidence, **fields}
    check_status(kind, rec)
    append(kind, rec)
    return rec["id"]


def cmd_set(rid: str, args: list[str]) -> None:
    kind = PREFIX[rid.split("-")[0]]
    cur = load(kind).get(rid)
    if cur is None:
        raise SystemExit(f"unknown id {rid}")
    fields, evidence = parse_fields(args)
    rec = {**cur, **fields, "updated": now()}
    # attaching a path again re-pins it to the file's current hash; history keeps the old one
    fresh = {(e["path"], e["locator"]) for e in evidence}
    rec["evidence"] = [e for e in rec["evidence"] if (e["path"], e["locator"]) not in fresh] + evidence
    check_status(kind, rec)
    append(kind, rec)


def check_status(kind: str, rec: dict) -> None:
    if rec["status"] not in KINDS[kind][1]:
        raise SystemExit(f"{rec['id']}: status must be one of {KINDS[kind][1]}")


def paper_claims() -> set[str]:
    return set(re.findall(r"C-\d{3}", PAPER.read_text())) if PAPER.exists() else set()


def validate() -> list[str]:
    problems = []
    for kind in KINDS:
        for rid, rec in load(kind).items():
            if (kind, rec["status"]) in NEEDS_EVIDENCE and not rec["evidence"]:
                problems.append(f"{rid}: status {rec['status']} without evidence")
            for e in rec["evidence"]:
                p = ROOT / e["path"]
                if not p.is_file():
                    problems.append(f"{rid}: evidence missing: {e['path']}")
                elif sha256(p) != e["sha256"]:
                    problems.append(f"{rid}: evidence changed since it was attached: {e['path']}")
    claims = load("claim")
    for cid in sorted(paper_claims()):
        if cid not in claims:
            problems.append(f"paper cites unknown claim {cid}")
        elif claims[cid]["status"] != "verified":
            problems.append(f"paper cites {cid}, which is {claims[cid]['status']}")
    return problems


def render() -> str:
    lines = ["# Status", "",
             f"Generated by `tools/ledger.py render` at {now()}. Do not edit: change the ledger instead.", ""]
    titles = {"task": "Tasks", "experiment": "Experiments", "claim": "Claims",
              "decision": "Decisions", "incident": "Incidents"}
    order = {"doing": 0, "running": 0, "open": 0, "todo": 1, "planned": 1, "pending": 1}
    cited = paper_claims()
    for kind in ("task", "experiment", "claim", "decision", "incident"):
        recs = sorted(load(kind).values(), key=lambda r: (order.get(r["status"], 2), r["id"]))
        if not recs:
            continue
        tally = {}
        for r in recs:
            tally[r["status"]] = tally.get(r["status"], 0) + 1
        lines += [f"## {titles[kind]}", "", ", ".join(f"{v} {k}" for k, v in tally.items()), "",
                  "| ID | Status | What | Detail | Evidence |", "|---|---|---|---|---|"]
        for r in recs:
            detail = {
                "task": " ".join(x for x in (
                    f"[{r['owner']}]" if r.get("owner") else "", f"({r['wp']})" if r.get("wp") else "",
                    r.get("accept", ""), f"NEXT: {r['notes']}" if r.get("notes") else "") if x),
                "experiment": r.get("result") or r.get("hypothesis", ""),
                "claim": (r.get("value", "") + (" (in paper)" if r["id"] in cited else "")).strip(),
                "decision": r.get("why", ""),
                "incident": r.get("fix") or r.get("cause", ""),
            }[kind]
            ev = "<br>".join(f"`{e['path']}`" + (f" {e['locator']}" if e["locator"] else "") for e in r["evidence"])
            cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {r['id']} | {r['status']} | {cell(r['title'])} | {cell(detail)} | {ev} |")
        lines.append("")
    problems = validate()
    lines += ["## Ledger check", "", "Clean." if not problems else "\n".join(f"- {p}" for p in problems), ""]
    text = "\n".join(lines)
    (ROOT / "the generated status page").write_text(text)
    return text


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "add":
        print(cmd_add(args[0], args[1:]))
    elif cmd == "set":
        cmd_set(args[0], args[1:])
    elif cmd == "show":
        kinds = [PREFIX[args[0].split("-")[0]]] if args and "-" in args[0] else ([args[0]] if args else list(KINDS))
        for kind in kinds:
            for rid, rec in load(kind).items():
                if not args or "-" not in args[0] or rid == args[0]:
                    print(json.dumps(rec, indent=1, ensure_ascii=False))
    elif cmd == "validate":
        problems = validate()
        print("\n".join(problems) or "ledger clean")
        sys.exit(1 if problems else 0)
    elif cmd == "render":
        render()
        print("the generated status page written")
    else:
        raise SystemExit(__doc__)
    if cmd in ("add", "set"):
        render()


if __name__ == "__main__":
    main()
