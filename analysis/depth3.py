"""Depth 3: which training stage creates deference? (prereg/depth3_training_stages.md)

python analysis/depth3.py
Every stage saw byte-identical Exp 7b messages; only the receiver differs. Final = OLMo-3-7B-Instruct, whose
data are the Exp 7b `olmo` runs (receiver agent B).
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
import exp7  # noqa: E402
from why2_rational import fit, rows_for  # noqa: E402

from coc.nulls import NA, residuals  # noqa: E402

STAGES = ["base", "sft", "dpo", "final"]
CONDS = ["seq_steps", "seq_answer", "random_answer"]
N_BOOT = 1000
rng = np.random.default_rng(0)


def stage_paths(stage: str):
    """(experiment config, exposure output dir, receiver Layer 0 file)."""
    if stage == "final":
        e = "experiments/exp7b_olmo.json"
        return e, "outputs/exp7b_olmo", json.loads((ROOT / e).read_text())["layer0"]["B"]
    e = f"experiments/depth3_{stage}.json"
    return e, f"outputs/depth3_{stage}", json.loads((ROOT / e).read_text())["receiver_layer0"]


def load_stage(stage: str) -> dict:
    exp_file, out_dir, recv_l0 = stage_paths(stage)
    e = json.loads((ROOT / exp_file).read_text())
    items = {i.item_id: i for i in (exp7.Item.model_validate_json(l) for l in (ROOT / e["items"]).read_text().splitlines())}
    raw = {who: exp7.load_layer0(ROOT / p) for who, p in e["layer0"].items()}      # message source (as generated)
    frames = {}
    for who, p in (("A", e["layer0"]["A"]), ("B", recv_l0)):                         # B = this receiver's own solo answers
        df = exp7.load_jsonl(ROOT / p)
        df["ans"] = df.answer_norm.fillna(NA)
        frames[who] = df.set_index(["task_id", "sample_index"]).sort_index()
    out = {}
    for c in e["conditions"]:
        if c["name"] not in CONDS:
            continue
        rows = exp7.load_jsonl(next((ROOT / out_dir).glob(f"*__{c['name']}__*.jsonl")))
        cond = c                                                                       # receiver = agent B
        out[c["name"]] = {d.item_id: d for d in exp7.build(cond, e, rows, frames, items, raw)}
    return out


def blocks(data: dict, ids, keep):
    return [rows_for(data[i], keep(data[i])) for i in ids if i in data]


def alpha(data, ids):
    return fit([b for b in blocks(data, ids, lambda d: (lambda s: True)) if b])


def discrimination(data, ids):
    mixed = [i for i in ids if i in data and 0 < data[i].dist_b.get(data[i].correct, 0.0) < 1]
    right = [b for b in blocks(data, mixed, lambda d: (lambda s, c=d.correct: s == c)) if b]
    wrong = [b for b in blocks(data, mixed, lambda d: (lambda s, c=d.correct: s != c and s != NA)) if b]
    return fit(right) - fit(wrong)


def contrast(stat, x, y, ids, larger: bool):
    """stat(x) - stat(y) with a joint item bootstrap; one-sided p for the predicted direction."""
    point = stat(x, ids) - stat(y, ids)
    boots = []
    for _ in range(N_BOOT):
        pick = [ids[j] for j in rng.integers(0, len(ids), len(ids))]
        boots.append(stat(x, pick) - stat(y, pick))
    boots = np.array(boots)
    p = float(np.mean(boots <= 0) if larger else np.mean(boots >= 0))
    return dict(estimate=float(point), ci95=tuple(float(v) for v in np.quantile(boots, [0.025, 0.975])), p=max(p, 1 / N_BOOT))


def holm(p: dict) -> dict:
    order, m, run, out = sorted(p, key=p.get), len(p), 0.0, {}
    for i, k in enumerate(order):
        run = max(run, min(1.0, (m - i) * p[k]))
        out[k] = run
    return out


def main():
    data = {s: load_stage(s) for s in STAGES}
    ids = sorted(set.intersection(*(set(data[s]["seq_steps"]) for s in STAGES)))
    report = {"n_items": len(ids), "curves": {}, "hypotheses": {}}

    print(f"items: {len(ids)}\n\nDEFERENCE WEIGHT α by training stage (exploratory curves; point estimates)")
    print(f"  {'condition':14s} " + " ".join(f"{s:>7s}" for s in STAGES))
    for c in CONDS:
        vals = [alpha(data[s][c], ids) for s in STAGES]
        report["curves"][f"alpha_{c}"] = dict(zip(STAGES, vals))
        print(f"  {c:14s} " + " ".join(f"{v:7.2f}" for v in vals))
    for c in CONDS:
        vals = [discrimination(data[s][c], ids) for s in STAGES]
        report["curves"][f"D_{c}"] = dict(zip(STAGES, vals))
        print(f"  D {c:12s} " + " ".join(f"{v:+7.2f}" for v in vals))
    for s in STAGES:
        d = list(data[s]["seq_steps"].values())
        obs, ex = residuals(d, "joint_error")
        report["curves"].setdefault("joint_error_seq_steps", {})[s] = dict(observed=float(obs.mean()), expected=float(ex.mean()),
                                                                          interaction_share=float((obs - ex).mean() / obs.mean()))

    st = "seq_steps"
    h = {"H1 alpha Final > Base": contrast(alpha, data["final"][st], data["base"][st], ids, True),
         "H2 alpha SFT > Base": contrast(alpha, data["sft"][st], data["base"][st], ids, True),
         "H3 alpha DPO > SFT": contrast(alpha, data["dpo"][st], data["sft"][st], ids, True),
         "H4 D Final < Base": contrast(discrimination, data["final"][st], data["base"][st], ids, False)}
    adj = holm({k: v["p"] for k, v in h.items()})
    print("\nPRE-REGISTERED HYPOTHESES (seq_steps; Holm across 4)")
    for k, v in h.items():
        sup = adj[k] < 0.05 and (v["ci95"][0] > 0 if "<" not in k else v["ci95"][1] < 0)
        v.update(p_holm=adj[k], supported=bool(sup))
        print(f"  {k:24s} {v['estimate']:+.3f} [{v['ci95'][0]:+.3f}, {v['ci95'][1]:+.3f}] p={v['p']:.3f} "
              f"p_holm={adj[k]:.3f} -> {'SUPPORTED' if sup else 'not supported'}")
    report["hypotheses"] = h
    print("\nInteraction share of joint error (seq_steps):",
          {s: f"{v['interaction_share']:.0%}" for s, v in report["curves"]["joint_error_seq_steps"].items()})
    (ROOT / "outputs/depth3_report.json").write_text(json.dumps(report, indent=2, default=float))
    print("report: outputs/depth3_report.json")


if __name__ == "__main__":
    main()
