# Kaggle runner: clone the repo at a pinned commit, install vLLM, run one experiment config.
# Pushed by `python kaggle/push.py <experiment.json> <commit>`; outputs land in /kaggle/working/outputs.
import os, subprocess, sys, json, shutil

REPO = "https://github.com/shibadityadeb/copy-or-coincidence.git"
COMMIT = "__COMMIT__"
EXPERIMENT = "__EXPERIMENT__"
RUN_ID = "__RUN_ID__"
VLLM = "__VLLM__"          # pinned in kaggle/env.json
PYTHON = "__PYTHON__"

def sh(cmd):
    print("+", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)

sh(f"git clone -q {REPO} /kaggle/working/repo && cd /kaggle/working/repo && git checkout -q {COMMIT}")
import platform
if not platform.python_version().startswith(PYTHON):
    raise SystemExit(f"STOP: Kaggle image has Python {platform.python_version()}, expected {PYTHON}. Image pin not honoured.")
sh(f"pip install -q vllm=={VLLM} pydantic datasets 2>&1 | tail -3")
sh("pip uninstall -y -q torchaudio 2>&1 | tail -1")     # unused; a mismatched build breaks vLLM's import
import importlib.metadata as md
versions = {p: md.version(p) for p in ("vllm", "torch", "transformers")}
print("VERSIONS", platform.python_version(), versions, flush=True)
if versions["vllm"] != VLLM:
    raise SystemExit(f"STOP: vLLM {versions['vllm']} installed, expected {VLLM}")
sh("cd /kaggle/working/repo && pip install -q -e . --no-deps")
sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
os.chdir("/kaggle/working/repo")
os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"
failed = []
for e in EXPERIMENT.split(","):            # several experiments per job amortise the GPU session
    try:
        sh(f"python -m coc.runner --experiment {e} --run-id {RUN_ID}")
    except subprocess.CalledProcessError:
        failed.append(e)
        print(f"!!! {e} failed, continuing", flush=True)
    out = json.load(open(e))["out_dir"]
    if os.path.isdir(out):
        shutil.copytree(out, f"/kaggle/working/outputs/{os.path.basename(out)}", dirs_exist_ok=True)
shutil.rmtree("/kaggle/working/repo")
print("FAILED:", failed, flush=True)
