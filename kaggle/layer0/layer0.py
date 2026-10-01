# Kaggle runner: clone the repo at a pinned commit, install vLLM, run one experiment config.
# Pushed by `python kaggle/push.py <experiment.json> <commit>`; outputs land in /kaggle/working/outputs.
import os, subprocess, sys, json, shutil

REPO = "https://github.com/shibadityadeb/copy-or-coincidence.git"
COMMIT = "__COMMIT__"
EXPERIMENT = "__EXPERIMENT__"
RUN_ID = "__RUN_ID__"

def sh(cmd):
    print("+", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)

sh(f"git clone -q {REPO} /kaggle/working/repo && cd /kaggle/working/repo && git checkout -q {COMMIT}")
sh("pip install -q vllm pydantic datasets 2>&1 | tail -3")
sh("cd /kaggle/working/repo && pip install -q -e . --no-deps")
sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
os.chdir("/kaggle/working/repo")
os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"
sh(f"python -m coc.runner --experiment {EXPERIMENT} --run-id {RUN_ID}")
exp = json.load(open(EXPERIMENT))
shutil.copytree(exp["out_dir"], "/kaggle/working/outputs", dirs_exist_ok=True)
shutil.rmtree("/kaggle/working/repo")
