"""Layer 0: every agent answers every item K times, alone. Resumable, append-only JSONL.

python -m coc.runner --experiment experiments/exp0_dev.json
"""
import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from cep import normalize
from cep.checker import check_raw
from cep.schema import Item
from coc.backends import ANSWER_SCHEMA, Backend, Request
from coc.schema import Trial, stable_seed

ROOT = Path(__file__).resolve().parent.parent


def load_items(path: Path) -> list[Item]:
    return [Item.model_validate_json(l) for l in path.read_text().splitlines() if l.strip()]


def dev_slice(items: list[Item], n: int) -> list[Item]:
    """Round-robin over templates so a small slice still covers every question type."""
    by_t: dict[str, list[Item]] = {}
    for it in items:
        by_t.setdefault(it.template_id, []).append(it)
    out, i = [], 0
    while len(out) < n:
        for t in by_t:
            if i < len(by_t[t]) and len(out) < n:
                out.append(by_t[t][i])
        i += 1
    return out


def load_prompt(version: str) -> tuple[str, str]:
    text = (ROOT / "prompts" / f"{version}.txt").read_text()
    return text, hashlib.sha256(text.encode()).hexdigest()[:12]


def repair_tail(path: Path) -> None:
    """Drop a torn last line left by a crash, so new rows don't get glued onto it."""
    if not path.exists():
        return
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        path.write_bytes(data[: data.rfind(b"\n") + 1])


def done_ids(path: Path) -> set[str]:
    repair_tail(path)
    if not path.exists():
        return set()
    ids = set()
    for line in path.read_text().splitlines():
        try:
            ids.add(json.loads(line)["trial_id"])
        except (json.JSONDecodeError, KeyError):
            pass          # a half-written last line from a crash; that trial is simply redone
    return ids


def run_independent(items: list[Item], agent: dict, backend: Backend, k: int, out_path: Path,
                    experiment_id: str, run_id: str, batch_size: int = 64, log=print) -> int:
    system, prompt_hash = load_prompt(agent["prompt"])
    done = done_ids(out_path)
    todo = []
    for it in items:
        for s in range(k):
            tid = f"{experiment_id}:{agent['agent_id']}:{it.item_id}:independent:{s}"
            if tid not in done:
                todo.append((tid, it, s, stable_seed(agent["agent_id"], it.item_id, "independent", str(s))))
    log(f"{len(done)} trials already done, {len(todo)} to run")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    for b in range(0, len(todo), batch_size):
        chunk = todo[b:b + batch_size]
        batch_id = uuid.uuid4().hex[:10]
        reqs = [Request(system, it.question, seed, agent["temperature"], agent["top_p"],
                        agent["max_tokens"], agent["enable_thinking"],
                        ANSWER_SCHEMA if agent.get("structured_output") else None) for _, it, _, seed in chunk]
        gens = backend.generate(reqs)
        with out_path.open("a") as f:
            for pos, ((tid, it, s, seed), g) in enumerate(zip(chunk, gens)):
                graded = check_raw(it, g.text)
                row = Trial(
                    trial_id=tid, experiment_id=experiment_id, run_id=run_id, task_id=it.item_id,
                    sample_index=s, family=it.family, template_id=it.template_id,
                    error_cause_by_construction=it.error_cause_by_construction,
                    difficulty_param=it.difficulty_param, item_correct=it.correct, item_lure=it.lure,
                    agent_id=agent["agent_id"], model=agent["model"], model_revision=agent["revision"],
                    quantization=backend.quantization, dtype=backend.dtype, backend=backend.name,
                    framework_version=backend.framework_version, enable_thinking=agent["enable_thinking"],
                    structured_output=bool(agent.get("structured_output")) and backend.name != "mlx",
                    prompt_version=agent["prompt"], prompt_hash=prompt_hash, seed=seed,
                    temperature=agent["temperature"], top_p=agent["top_p"], max_tokens=agent["max_tokens"],
                    raw_output=g.text, normalizer_version=normalize.NORMALIZER_VERSION,
                    prompt_tokens=g.prompt_tokens, output_tokens=g.output_tokens, truncated=g.truncated,
                    latency_ms=round(g.latency_ms, 1), batch_id=batch_id, batch_position=pos,
                    timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    final=graded.pop("final"), **graded)
                f.write(row.model_dump_json() + "\n")
        written += len(chunk)
        log(f"  {len(done) + written}/{len(done) + len(todo)} trials")
    return written


def make_backend(agent: dict, backend: str) -> Backend:
    if backend == "mlx":
        from coc.backends import MLXBackend
        return MLXBackend(agent["mlx_repo"], agent["mlx_revision"], agent["mlx_quantization"])
    if backend == "vllm":
        from coc.backends import VLLMBackend
        return VLLMBackend(agent["model"], agent["revision"], **agent.get("vllm", {}))
    raise ValueError(backend)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--run-id", default="run1",
                    help="comma-separated; each run id reruns everything (run1,run2 = determinism check)")
    args = ap.parse_args()
    exp = json.loads((ROOT / args.experiment).read_text())
    items = load_items(ROOT / exp["items"])
    if exp.get("n_items"):
        items = dev_slice(items, exp["n_items"])
    backend = None
    for run_id in args.run_id.split(","):
        exp_id = f"{exp['experiment_id']}-{run_id}"
        for agent_file in exp["agents"]:
            agent = json.loads((ROOT / agent_file).read_text())
            backend = backend or make_backend(agent, exp["backend"])  # agents sharing weights share a backend
            out = ROOT / exp["out_dir"] / f"{exp_id}__{agent['agent_id']}.jsonl"
            print(f"{agent['agent_id']}: {len(items)} items x K={exp['k']} -> {out.relative_to(ROOT)}", flush=True)
            run_independent(items, agent, backend, exp["k"], out, exp_id, run_id, exp.get("batch_size", 64),
                            log=lambda *a: print(*a, flush=True))


if __name__ == "__main__":
    main()
