#!/usr/bin/env python
"""Build, push, watch and collect Kaggle evaluation kernels.

    tools/kernel.py build  <run_config.json>      -> kernels/ladder_eval/build/<run_id>/
    tools/kernel.py push   <run_id>
    tools/kernel.py status <run_id>
    tools/kernel.py pull   <run_id>                -> runs/<run_id>/

A run config is the single source of truth for a run and is committed under
runs/<run_id>/config.json before the kernel is pushed.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "kernels" / "ladder_eval" / "runner.py"
OWNER = os.environ.get("KAGGLE_OWNER", "d410qc")
DOCKER_IMAGE = ("gcr.io/kaggle-private-byod/python@sha256:"
                "37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461")


def _env() -> dict:
    env = dict(os.environ)
    envfile = ROOT / ".env"
    if envfile.exists():
        for line in envfile.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
    return env


def _kaggle(*args: str, check: bool = True) -> str:
    exe = ROOT / ".venv" / "bin" / "kaggle"
    p = subprocess.run([str(exe), *args], env=_env(), capture_output=True, text=True)
    out = "\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Warning" not in l)
    if check and p.returncode:
        raise SystemExit(f"kaggle {' '.join(args)} failed:\n{out}")
    return out


def slug(run_id: str) -> str:
    return f"g4-ladder-{run_id}".lower().replace("_", "-")


def build(config_path: str) -> Path:
    cfg = json.loads(Path(config_path).read_text())
    run_id = cfg["run_id"]
    bundles = {}
    for name in sorted({a["bundle"] for a in cfg["arms"]}):
        folder = ROOT / "agents" / name
        bundles[name] = {str(p.relative_to(folder)): p.read_text() for p in sorted(folder.rglob("*")) if p.is_file()}
    modules = {str(p.relative_to(ROOT / "src")): p.read_text()
               for p in sorted((ROOT / "src" / "ladder").glob("*.py"))}
    payload = {"config": cfg, "bundles": bundles, "modules": modules}
    blob = base64.b64encode(gzip.compress(json.dumps(payload, sort_keys=True).encode(), mtime=0)).decode()
    out = TEMPLATE.parent / "build" / run_id
    out.mkdir(parents=True, exist_ok=True)
    script = TEMPLATE.read_text().replace("__PAYLOAD__", blob)
    (out / "run.py").write_text(script)
    meta = {
        "id": f"{OWNER}/{slug(run_id)}", "title": slug(run_id), "code_file": "run.py",
        "language": "python", "kernel_type": "script", "is_private": True,
        "enable_gpu": True, "enable_tpu": False, "enable_internet": False,
        "dataset_sources": [
            "metric/gemma-4-developer-agent-wheelhouse",
            "zbigniewkirchner/gemma-4-agent-local-eval-wheels",
            "zbigniewkirchner/gemma-4-agent-local-eval-pythons",
            *sorted({a["dataset"] for a in cfg.get("adapters", [])}),
        ],
        "competition_sources": ["gemma-4-developer-agent"],
        "kernel_sources": [],
        "model_sources": [f"google/gemma-4/Other/{cfg['model']}/2"],
        "docker_image": DOCKER_IMAGE,
        "machine_shape": cfg.get("machine_shape", "NvidiaL4"),
    }
    (out / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.json").write_text(json.dumps(cfg, indent=1) + "\n")
    (run_dir / "build.json").write_text(json.dumps({
        "kernel": meta["id"], "script_sha256": hashlib.sha256(script.encode()).hexdigest(),
        "payload_sha256": hashlib.sha256(blob.encode()).hexdigest(),
        "bundles": {n: sorted(f) for n, f in bundles.items()},
    }, indent=1) + "\n")
    print(f"built {out} ({len(script) / 1024:.0f} KiB) -> {meta['id']}")
    return out


def main() -> None:
    cmd, arg = sys.argv[1], sys.argv[2]
    if cmd == "build":
        build(arg)
    elif cmd == "push":
        print(_kaggle("kernels", "push", "-p", str(TEMPLATE.parent / "build" / arg)))
    elif cmd == "status":
        print(_kaggle("kernels", "status", f"{OWNER}/{slug(arg)}", check=False))
    elif cmd == "pull":
        dest = ROOT / "runs" / arg / "output"
        dest.mkdir(parents=True, exist_ok=True)
        print(_kaggle("kernels", "output", f"{OWNER}/{slug(arg)}", "-p", str(dest), check=False)[-1500:])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
