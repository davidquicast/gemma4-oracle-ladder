"""Keep a Colab session active while a campaign runs, then upload its outputs.

Run inside a Colab notebook cell (not the terminal: a terminal process does not
count as activity and the session is disconnected after a while):

    RUN = "colab_e4b_L0_r2"; exec(open("/content/colab_watch.py").read())

Polls the runner every 120 s, prints the number of graded episodes, and when the
runner exits copies /kaggle/working outputs to /content/out/<RUN> and uploads them
as the private Kaggle dataset <owner>/g4-colab-out-<run> for tools/colab.py pull.
Needs the KAGGLE_API_TOKEN Colab secret.
"""
import json
import os
import pathlib
import shutil
import subprocess
import time

from google.colab import userdata  # noqa: E402  (Colab only)

os.environ["KAGGLE_API_TOKEN"] = userdata.get("KAGGLE_API_TOKEN")
RUN = globals().get("RUN") or os.environ["RUN"]
OWNER = os.environ.get("KAGGLE_OWNER", "d410qc")
W = pathlib.Path("/kaggle/working")


def alive() -> bool:
    return subprocess.run(["pgrep", "-f", RUN + "/run.py"], capture_output=True).returncode == 0


while alive():
    log = W / (RUN + ".log")
    print(time.strftime("%H:%M:%S"), log.read_text().count("resolved=") if log.exists() else 0, "episodes", flush=True)
    time.sleep(120)
d = pathlib.Path("/content/out") / RUN
d.mkdir(parents=True, exist_ok=True)
for f in ["results.jsonl", "manifest.json", "eval.zip", "vllm.log", RUN + ".log"]:
    if (W / f).exists():
        shutil.copy(W / f, d / f)
slug = "g4-colab-out-" + RUN.replace("_", "-").lower()
(d / "dataset-metadata.json").write_text(json.dumps({"title": slug, "id": f"{OWNER}/{slug}", "licenses": [{"name": "other"}]}))
r = subprocess.run(["kaggle", "datasets", "create", "-p", str(d), "--dir-mode", "zip"], capture_output=True, text=True)
print("upload", r.returncode, r.stdout[-200:], r.stderr[-200:])
