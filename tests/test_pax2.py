"""The rebuilt Personaxis bundle (pax2): spec layout, schema, compiled PERSONA.md, knowledge copies."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAX = ROOT / "agents" / "pax2"
SPEC = ROOT / "private" / "personaxis-spec-2.0" / "spec" / "schema"
yaml = pytest.importorskip("yaml")

LAYERS = ["identity", "character", "personality", "values_and_drives", "affect", "cognition",
          "memory", "metacognition", "self_regulation", "presentation"]
HEADINGS = ["## What you do and what you do not", "## What you keep, whoever asks",
            "## How you speak, and what you adapt to each person", "## Hard limits (never overridden)",
            "## Your work", "## Your resources"]


def frontmatter(path):
    return yaml.safe_load(path.read_text().split("---", 2)[1])


def test_definition_has_all_ten_layers_in_order():
    keys = list(frontmatter(PAX / "personaxis.md"))
    assert [k for k in keys if k in LAYERS] == LAYERS


def test_compiled_persona_follows_the_template():
    text = (PAX / "PERSONA.md").read_text()
    assert [l for l in text.splitlines() if l.startswith("## ")] == HEADINGS
    body = text.split("---", 2)[2]
    assert "{" not in body and "}" not in body  # ADK would template them from session state
    fm = frontmatter(PAX / "personaxis.md")
    for rule in fm["self_regulation"]["hard_limits"] + fm["character"]["prohibited_behaviors"]:
        assert rule in text
    for item in fm["identity"]["scope"]["does"] + fm["identity"]["scope"]["does_not"]:
        assert f"- {item}" in text
    assert fm["self_regulation"]["correction_rule"].split()[0] in text


def test_agent_reads_persona_md_and_loads_both_skills():
    agent = (PAX / "agent.yaml").read_text()
    assert "instruction: !include PERSONA.md" in agent
    assert "skills/repair-a-reported-defect" in agent and "skills/knowledge" in agent


def test_knowledge_copies_match_their_home():
    home = sorted(p.name for p in (PAX / "knowledge").glob("*.md"))
    refs = PAX / "skills" / "knowledge" / "references"
    assert sorted(p.name for p in refs.glob("*.md")) == home
    for name in home:
        assert (refs / name).read_text() == (PAX / "knowledge" / name).read_text()
    for name in home:
        if name != "INDEX.md":
            assert f"({name})" in (PAX / "knowledge" / "INDEX.md").read_text()


def test_e4b_copy_differs_only_in_the_model_line():
    other = ROOT / "agents" / "pax2_e4b"
    a = {str(p.relative_to(PAX)): p.read_text() for p in PAX.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    b = {str(p.relative_to(other)): p.read_text() for p in other.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    assert set(a) == set(b)
    for rel in a:
        if rel == "agent.yaml":
            assert a[rel].replace("gemma-4-e2b-it-qat-w4a16-ct", "gemma-4-e4b-it-qat-w4a16-ct") == b[rel]
        else:
            assert a[rel] == b[rel], rel


@pytest.mark.skipif(not SPEC.exists(), reason="private Personaxis spec not present")
def test_definition_and_guarantee_validate_against_the_spec_schema():
    jsonschema = pytest.importorskip("jsonschema")
    def errors(schema_file, inst):
        schema = json.loads((SPEC / schema_file).read_text())
        return [e.message for e in jsonschema.Draft7Validator(schema).iter_errors(json.loads(json.dumps(inst, default=str)))]
    assert errors("persona.schema.json", frontmatter(PAX / "personaxis.md")) == []
    for skill in ("repair-a-reported-defect", "knowledge"):
        meta = frontmatter(PAX / "skills" / skill / "SKILL.md")["metadata"]["personaxis"]
        assert errors("skill.schema.json", meta) == []
