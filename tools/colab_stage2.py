"""Stage the inputs of a Colab A100 session for tools/colab.py payloads (run in a notebook cell).

One-time environment, from the Colab terminal (the harness wheels are cp312; Colab ships 3.13):

    apt-get install -y -qq python3.12-venv; pip install -q uv
    uv venv -q -p /usr/bin/python3.12 --seed /content/py312
    uv pip install -q -p /content/py312/bin/python vllm==0.19.1 litellm==1.82.4 "huggingface_hub>=1.5,<2.0"

Then, in a cell (the cell holds the Kaggle token, the terminal does not):

    import os; from google.colab import userdata
    os.environ["KAGGLE_API_TOKEN"] = userdata.get("KAGGLE_API_TOKEN")
    exec(open('/content/stage2.py').read())        # this file, copied to /content

/kaggle/input is read-only on Colab, so inputs go to /content/kinput and every payload's
run.py is rewritten to read from there. Launch a payload from the terminal with
`/content/py312/bin/python /content/payload/<run_id>/run.py` under nohup, and keep the
session alive with tools/colab_watch.py running in a cell (terminal processes do not count
as activity). The wheel and interpreter datasets are public datasets by another participant
(zbigniewkirchner), credited in the README.
"""
import glob
import pathlib
import subprocess
import zipfile

I = pathlib.Path("/content/kinput")
I.mkdir(parents=True, exist_ok=True)


def sh(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    print(" ".join(a[:4]), r.returncode, r.stderr[-300:])


if not (I / "comp").exists():
    sh("kaggle", "competitions", "download", "gemma-4-developer-agent", "-p", "/content/comp_zip")
    zipfile.ZipFile(glob.glob("/content/comp_zip/*.zip")[0]).extractall(I / "comp")
for ds in ["metric/gemma-4-developer-agent-wheelhouse",
           "zbigniewkirchner/gemma-4-agent-local-eval-wheels",
           "zbigniewkirchner/gemma-4-agent-local-eval-pythons"]:
    d = I / ds.split("/")[1]
    if not d.exists():
        sh("kaggle", "datasets", "download", ds, "-p", str(d), "--unzip")
m = I / "models" / "gemma-4-e4b-it-qat-w4a16-ct" / "2"
if not glob.glob(str(m / "**" / "config.json"), recursive=True):
    m.mkdir(parents=True, exist_ok=True)
    sh("kaggle", "models", "instances", "versions", "download",
       "google/gemma-4/other/gemma-4-e4b-it-qat-w4a16-ct/2", "-p", str(m), "--untar")
P = pathlib.Path("/content/payload")
sh("kaggle", "datasets", "download", "d410qc/g4-colab-payloads", "-p", str(P), "--unzip", "--force")
for rp in P.rglob("run.py"):
    rp.write_text(rp.read_text().replace("/kaggle/input", "/content/kinput"))
    print("patched", rp)
print("stage2 done")
