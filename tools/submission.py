#!/usr/bin/env python
"""Package an agent bundle as a leaderboard submission.

    tools/submission.py build  <bundle> <name>   -> kernels/submission/build/<name>/
    tools/submission.py push   <name>            run the packaging kernel on Kaggle
    tools/submission.py submit <name> <kernel_version> "<message>"   (version printed by push)

The competition scores the `submission.zip` written by a notebook, so a
submission is a tiny CPU kernel that writes the bundle's files and zips them.
The bundle is validated locally with the official validator before building.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from kernel import OWNER, _kaggle  # noqa: E402

COMPETITION = "gemma-4-developer-agent"
BUILD = ROOT / "kernels" / "submission" / "build"

SCRIPT = '''# Writes submission.zip for the Gemma 4 Developer Agent competition.
import json, zipfile
from pathlib import Path

FILES = json.loads({files!r})
with zipfile.ZipFile("/kaggle/working/submission.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for rel in sorted(FILES):
        z.writestr(rel, FILES[rel])
print("submission.zip:", sorted(FILES))
'''


def slug(name: str) -> str:
    return f"g4-submission-{name}".lower().replace("_", "-")


def build(bundle: str, name: str) -> None:
    from adk_submission import validate_directory
    from swegemma.config import build_submission_limits

    folder = ROOT / "agents" / bundle
    validate_directory(folder, limits=build_submission_limits()[0])
    files = {str(p.relative_to(folder)): p.read_text() for p in sorted(folder.rglob("*")) if p.is_file()}
    out = BUILD / name
    out.mkdir(parents=True, exist_ok=True)
    script = SCRIPT.format(files=json.dumps(files, sort_keys=True))
    (out / "run.py").write_text(script)
    (out / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{OWNER}/{slug(name)}", "title": slug(name), "code_file": "run.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
        "enable_internet": False, "dataset_sources": [], "competition_sources": [COMPETITION],
        "kernel_sources": [], "model_sources": [],
    }, indent=1))
    record = ROOT / "runs" / "submissions" / f"{name}.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({
        "name": name, "bundle": bundle, "kernel": f"{OWNER}/{slug(name)}",
        "bundle_sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
        "files": sorted(files),
    }, indent=1) + "\n")
    print(f"built {out} from agents/{bundle} ({len(files)} files)")


def main() -> None:
    cmd = sys.argv[1]
    if cmd == "build":
        build(sys.argv[2], sys.argv[3])
    elif cmd == "push":
        print(_kaggle("kernels", "push", "-p", str(BUILD / sys.argv[2])))
    elif cmd == "status":
        print(_kaggle("kernels", "status", f"{OWNER}/{slug(sys.argv[2])}", check=False))
    elif cmd == "submit":
        print(_kaggle("competitions", "submit", COMPETITION, "-k", f"{OWNER}/{slug(sys.argv[2])}",
                      "-v", sys.argv[3], "-f", "submission.zip", "-m", sys.argv[4], check=False))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
