import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ledger_tool", ROOT / "tools" / "ledger.py")


def make(tmp_path):
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT, mod.LEDGER, mod.PAPER = tmp_path, tmp_path / "ledger", tmp_path / "paper" / "writeup.md"
    return mod


def test_history_is_append_only_and_latest_wins(tmp_path):
    L = make(tmp_path)
    tid = L.cmd_add("task", ["title=do it"])
    L.cmd_set(tid, ["status=done"])
    assert L.load("task")[tid]["status"] == "done"
    assert len((tmp_path / "ledger" / "task.jsonl").read_text().splitlines()) == 2


def test_verified_claim_needs_unchanged_evidence(tmp_path):
    L = make(tmp_path)
    cid = L.cmd_add("claim", ["title=x solves y", "value=3/10"])
    L.cmd_set(cid, ["status=verified"])
    assert any("without evidence" in p for p in L.validate())
    ev = tmp_path / "runs" / "r.json"
    ev.parent.mkdir()
    ev.write_text("{}")
    L.cmd_set(cid, ["evidence=runs/r.json#summary"])
    assert L.validate() == []
    ev.write_text('{"changed": 1}')
    assert any("changed since" in p for p in L.validate())


def test_paper_may_only_cite_verified_claims(tmp_path):
    L = make(tmp_path)
    cid = L.cmd_add("claim", ["title=pending thing"])
    L.PAPER.parent.mkdir()
    L.PAPER.write_text(f"We find a thing <!--{cid}--> and C-999.")
    problems = L.validate()
    assert any(f"cites {cid}, which is pending" in p for p in problems)
    assert any("unknown claim C-999" in p for p in problems)
