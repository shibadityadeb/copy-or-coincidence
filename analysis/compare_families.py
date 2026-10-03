"""Experiment 7b summary across families + framing robustness (prereg/exp7b_peer_v2.md).

python analysis/compare_families.py
Needs analysis/exp7.py to have been run on each outputs/exp7b_<model> (and exp7_<model> for the framing check).
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
import exp7  # noqa: E402  (reuse its loaders so the comparison uses identical data handling)

from coc.nulls import item_bootstrap_ci, residuals  # noqa: E402

MODELS = ["olmo", "qwen", "nemotron"]
CONDS = ["seq_steps", "seq_answer", "random_answer", "seq_steps_rev"]
JUDGE = {"true", "false", "yes", "no", "correct", "incorrect"}


def judging_rate(path: str) -> float:
    d = pd.read_json(path, lines=True)
    num = d[~d.item_correct.isin(["TRUE", "FALSE"])]
    return float(num.final.astype(str).str.strip().str.lower().isin(JUDGE).mean())


def per_item(model: str, version: str, cond: str, metric: str):
    """Per-item residuals for one condition, keyed by item id (for paired v1-v2 differences)."""
    out_dir = ROOT / f"outputs/{version}_{model}"
    exp_path = f"experiments/{version}_{model}.json"
    e = json.loads((ROOT / exp_path).read_text())
    items = {i.item_id: i for i in (exp7.Item.model_validate_json(l) for l in (ROOT / e["items"]).read_text().splitlines())}
    layer0 = {}
    for who, p in e["layer0"].items():
        df = exp7.load_jsonl(ROOT / p)
        df["ans"] = df.answer_norm.fillna(exp7.NA)
        layer0[who] = df.set_index(["task_id", "sample_index"]).sort_index()
    raw_l0 = {who: exp7.load_layer0(ROOT / p) for who, p in e["layer0"].items()}
    c = next(x for x in e["conditions"] if x["name"] == cond)
    rows = exp7.load_jsonl(next(out_dir.glob(f"*__{cond}__*.jsonl")))
    data = exp7.build(c, e, rows, layer0, items, raw_l0)
    obs, ex = residuals(data, metric)
    use = [d for d in data if metric != "both_lure" or d.lure]
    return pd.Series(obs - ex, index=[d.item_id for d in use])


def main():
    print("=== Validity check: share of number items answered as a verdict on the peer (> 5% = invalid)")
    valid = {}
    for m in MODELS:
        cells = []
        for c in CONDS:
            f = glob.glob(str(ROOT / f"outputs/exp7b_{m}/*__{c}__*.jsonl"))
            r = judging_rate(f[0]) if f else float("nan")
            valid[(m, c)] = r <= 0.05
            cells.append(f"{c} {r:6.1%}{'' if r <= 0.05 else ' INVALID'}")
        print(f"  {m:9s} " + " | ".join(cells))

    print("\n=== Experiment 7b hypotheses per family (Holm within model)")
    rows = []
    for m in MODELS:
        rep = json.loads((ROOT / f"outputs/exp7b_{m}/exp7_report.json").read_text())
        for h, v in rep["hypotheses"].items():
            cond = {"H1": "seq_steps", "H2": "seq_answer", "H3": "random_answer", "H4": "seq_steps", "H5": "seq_steps"}[h[:2]]
            ok = valid[(m, cond)] and (h[:2] != "H2" or valid[(m, "seq_steps")])
            rows.append(dict(model=m, hypothesis=h, residual=round(v["residual"], 4),
                             ci=f"[{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]", p_holm=round(v["p_holm"], 4),
                             verdict=("SUPPORTED" if v["supported"] else "not supported") if ok else "invalid condition"))
    t = pd.DataFrame(rows)
    print(t.pivot(index="hypothesis", columns="model", values="verdict")[MODELS].to_string())
    print()
    print(t.to_string(index=False))

    print("\n=== Decomposition of joint error under seq_steps (observed = predicted by solo behaviour + interaction)")
    for m in MODELS:
        je = json.loads((ROOT / f"outputs/exp7b_{m}/exp7_report.json").read_text())["conditions"]["seq_steps"]["joint_error"]
        print(f"  {m:9s} {je['observed']:.3f} = {je['expected']:.3f} + {je['residual']:+.3f}  -> interaction share {je['residual'] / je['observed']:.0%}")

    print("\n=== Framing robustness (secondary): peer_v2 minus peer_v1, per-item paired, 95% item-bootstrap CI")
    for m in ("olmo", "nemotron"):
        for c in ("seq_steps", "seq_answer", "random_answer"):
            for metric in ("same_answer", "joint_error"):
                v1, v2 = per_item(m, "exp7", c, metric), per_item(m, "exp7b", c, metric)
                d = (v2 - v1.reindex(v2.index)).dropna().to_numpy()
                mean, lo, hi = item_bootstrap_ci(d)
                print(f"  {m:9s} {c:14s} {metric:12s} v1 {v1.mean():+.4f}  v2 {v2.mean():+.4f}  diff {mean:+.4f} [{lo:+.4f}, {hi:+.4f}]")


if __name__ == "__main__":
    main()
