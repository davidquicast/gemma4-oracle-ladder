#!/usr/bin/env python
"""Run a campaign on Google Colab (one GPU) with the same runner as the Kaggle kernels.

    tools/colab.py payload <config.json>   build the run script and upload it to the
                                           private dataset <owner>/g4-colab-payloads
    tools/colab.py pull <run_id>           download the outputs the Colab notebook
                                           uploaded to <owner>/g4-colab-out-<run_id>

The notebook kernels/colab/ladder_eval.ipynb downloads the competition data, the
harness wheelhouses and the model with the Kaggle API into /kaggle/input, so the
runner finds every input where it does on Kaggle, runs the payload, and uploads
/kaggle/working as a private dataset. Hardware differs from Kaggle's 4x L4, so a
Colab arm is compared only with arms run on Colab.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from kernel import OWNER, _kaggle, build  # noqa: E402

PAYLOADS = f"{OWNER}/g4-colab-payloads"


def payload(config: str) -> None:
    out = build(config)
    run_id = json.loads(Path(config).read_text())["run_id"]
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        existing = _kaggle("datasets", "list", "--mine", "-s", "g4-colab-payloads", check=False)
        if "g4-colab-payloads" in existing:
            _kaggle("datasets", "download", PAYLOADS, "-p", str(d), "--unzip", check=False)
        (d / run_id).mkdir(exist_ok=True)
        shutil.copy(out / "run.py", d / run_id / "run.py")
        (d / "dataset-metadata.json").write_text(json.dumps(
            {"title": "g4-colab-payloads", "id": PAYLOADS, "licenses": [{"name": "other"}]}))
        if "g4-colab-payloads" in existing:
            print(_kaggle("datasets", "version", "-p", str(d), "-m", run_id, "--dir-mode", "zip"))
        else:
            print(_kaggle("datasets", "create", "-p", str(d), "--dir-mode", "zip"))
    print(f"payload {run_id} uploaded to {PAYLOADS}")


def pull(run_id: str) -> None:
    dest = ROOT / "runs" / run_id / "output"
    dest.mkdir(parents=True, exist_ok=True)
    print(_kaggle("datasets", "download", f"{OWNER}/g4-colab-out-{run_id.replace('_', '-').lower()}",
                  "-p", str(dest), "--unzip", "--force")[-500:])
    print(sorted(p.name for p in dest.iterdir()))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("payload", "pull"):
        raise SystemExit(__doc__)
    {"payload": payload, "pull": pull}[sys.argv[1]](sys.argv[2])
