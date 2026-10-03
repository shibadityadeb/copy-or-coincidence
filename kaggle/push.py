"""Send one experiment to Kaggle, wait for it, download its outputs.

python kaggle/push.py experiments/exp0_kaggle.json[,experiments/other.json] [--run-id run1[,run2]] [--no-wait]

The Kaggle job clones this repo at the current pushed commit, so commit + push first.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KAGGLE = str(Path.home() / ".local/bin/kaggle")
USER = "debshibaditya"


def sh(*args, capture=True) -> str:
    return subprocess.run(args, check=True, capture_output=capture, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment")
    ap.add_argument("--run-id", default="run1")
    ap.add_argument("--no-wait", action="store_true")
    a = ap.parse_args()

    commit = sh("git", "-C", str(ROOT), "rev-parse", "HEAD")
    if sh("git", "-C", str(ROOT), "status", "--porcelain", "--", "cep", "coc", "configs", "experiments",
          "prompts", "datasets"):
        raise SystemExit("uncommitted changes in code/configs: commit and push first")
    if not sh("git", "-C", str(ROOT), "branch", "-r", "--contains", commit):
        raise SystemExit(f"commit {commit[:8]} is not on GitHub yet: git push first")

    exp_ids = [json.loads((ROOT / e).read_text())["experiment_id"] for e in a.experiment.split(",")]
    slug = f"coc-{'-'.join(exp_ids)}-{a.run_id}".replace("_", "-").replace(",", "-").lower()[:50]
    job = ROOT / "kaggle" / "jobs" / slug
    job.mkdir(parents=True, exist_ok=True)
    src = (ROOT / "kaggle/layer0/layer0.py").read_text()
    env = json.loads((ROOT / "kaggle/env.json").read_text())
    src = src.replace("__COMMIT__", commit).replace("__EXPERIMENT__", a.experiment).replace("__RUN_ID__", a.run_id)
    src = src.replace("__VLLM__", env["vllm"]).replace("__PYTHON__", env["python"])
    (job / "job.py").write_text(src)
    (job / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{USER}/{slug}", "title": slug, "code_file": "job.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "machine_shape": "NvidiaTeslaT4", "dataset_sources": [], "competition_sources": [],
        "kernel_sources": [], "docker_image": env["docker_image"],
        "docker_image_pinning_type": env["docker_image_pinning_type"]}, indent=2))
    print(sh(KAGGLE, "kernels", "push", "-p", str(job)))
    if a.no_wait:
        return
    t0 = time.time()
    while True:
        time.sleep(60)
        status = sh(KAGGLE, "kernels", "status", f"{USER}/{slug}")
        print(f"[{(time.time() - t0) / 60:.0f} min] {status.split('status')[-1].strip()}", flush=True)
        if any(s in status.upper() for s in ("COMPLETE", "ERROR", "CANCEL")):
            break
    out = ROOT / "kaggle" / "jobs" / slug / "output"
    out.mkdir(exist_ok=True)
    print(sh(KAGGLE, "kernels", "output", f"{USER}/{slug}", "-p", str(out)))


if __name__ == "__main__":
    main()
