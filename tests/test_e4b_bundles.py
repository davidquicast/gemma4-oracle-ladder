from pathlib import Path

AGENTS = Path(__file__).resolve().parents[1] / "agents"


def _files(d: Path) -> dict[str, str]:
    return {str(p.relative_to(d)): p.read_text() for p in sorted(d.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def test_e4b_bundles_differ_only_in_the_model_line():
    for name in ("base", "hunk"):
        a, b = _files(AGENTS / name), _files(AGENTS / f"{name}_e4b")
        assert set(a) == set(b)
        for rel in a:
            if rel == "agent.yaml":
                assert a[rel].replace("model: gemma-4-e2b-it-qat-w4a16-ct", "model: gemma-4-e4b-it-qat-w4a16-ct") == b[rel]
                assert "model: gemma-4-e4b-it-qat-w4a16-ct" in b[rel]
            else:
                assert a[rel] == b[rel], rel
