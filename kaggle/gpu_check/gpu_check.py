# Smoke test: confirm Kaggle GPUs and the libraries we'll need.
import subprocess, sys, json, platform
print(subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout)
info = {"python": platform.python_version()}
try:
    import torch
    info["torch"] = torch.__version__
    info["cuda"] = torch.cuda.is_available()
    info["gpus"] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
except Exception as e:
    info["torch_error"] = repr(e)
for mod in ["transformers", "vllm"]:
    try:
        info[mod] = __import__(mod).__version__
    except Exception as e:
        info[mod] = f"not installed ({type(e).__name__})"
print(json.dumps(info, indent=2))
json.dump(info, open("gpu_check.json", "w"), indent=2)
