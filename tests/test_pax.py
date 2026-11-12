"""The pax bundle's persona validates against the Personaxis 2.0 schema (skipped without the unpublished spec)."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "private" / "personaxis-spec-2.0" / "spec" / "schema"
PAX = ROOT / "agents" / "pax"

pytestmark = pytest.mark.skipif(not SPEC.exists(), reason="private Personaxis spec not present")
jsonschema = pytest.importorskip("jsonschema")
yaml = pytest.importorskip("yaml")


def frontmatter(path):
    return yaml.safe_load(path.read_text().split("---", 2)[1])


def errors(schema_file, instance):
    schema = json.loads((SPEC / schema_file).read_text())
    return [f"{list(e.path)}: {e.message}" for e in jsonschema.Draft7Validator(schema).iter_errors(instance)]


def test_persona_validates():
    persona = json.loads(json.dumps(frontmatter(PAX / "persona" / "personaxis.md"), default=str))
    assert errors("persona.schema.json", persona) == []


def test_persona_carries_universal_hard_limits():
    limits = frontmatter(PAX / "persona" / "personaxis.md")["self_regulation"]["hard_limits"]
    for rule in ("No claim of subjective consciousness.", "No persistent memory write without policy pass.",
                 "No unauthorized identity change."):
        assert rule in limits


def test_skill_guarantee_validates():
    skill = PAX / "skills" / "repair-a-reported-defect" / "SKILL.md"
    meta = frontmatter(skill)["metadata"]["personaxis"]
    assert errors("skill.schema.json", meta) == []
    for entry in meta.get("assertions", []) + meta.get("traps", []):
        assert (skill.parent / entry["check"]).is_file()


def test_compiled_prompt_matches_template_headings():
    text = (PAX / "prompts" / "system.md").read_text()
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    assert headings == ["## What you do and what you do not", "## What you keep, whoever asks",
                        "## How you speak, and what you adapt to each person",
                        "## Hard limits (never overridden)", "## Your work", "## Your resources"]
    assert 3000 <= len(text) <= 4500
    assert "{" not in text and "}" not in text  # ADK would template them from session state
