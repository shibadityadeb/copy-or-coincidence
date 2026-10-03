"""N4 tipping test, deference models, three-way error decomposition (prereg/why1_n4_tipping.md).

python analysis/n4_tipping.py            # Experiment 7b, all three families (primary)
python analysis/n4_tipping.py exp7       # Experiment 7 (peer_v1), robustness
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
import exp7  # noqa: E402

NA = exp7.NA
EPS = 0.01
CONTESTED = 0.7
VALID = {"olmo": ["seq_steps", "seq_answer", "random_answer"], "qwen": ["seq_steps"],
         "nemotron": ["seq_steps", "seq_answer", "random_answer"]}
rng = np.random.default_rng(0)


def load(version: str, model: str) -> dict:
    """condition -> list of ItemData (a = shown answer, b = receiver answer, dist_a = sender, dist_b = receiver)."""
    e = json.loads((ROOT / f"experiments/{version}_{model}.json").read_text())
    items = {i.item_id: i for i in (exp7.Item.model_validate_json(l) for l in (ROOT / e["items"]).read_text().splitlines())}
    layer0 = {}
    for who, p in e["layer0"].items():
        df = exp7.load_jsonl(ROOT / p)
        df["ans"] = df.answer_norm.fillna(NA)
        layer0[who] = df.set_index(["task_id", "sample_index"]).sort_index()
    raw = {who: exp7.load_layer0(ROOT / p) for who, p in e["layer0"].items()}
    out = {}
    for c in e["conditions"]:
        if c["name"] not in VALID[model]:
            continue
        rows = exp7.load_jsonl(next((ROOT / f"outputs/{version}_{model}").glob(f"*__{c['name']}__*.jsonl")))
        out[c["name"]] = exp7.build(c, e, rows, layer0, items, raw)
    return out


def joint_mode(d):
    q = {a: p * d.dist_b.get(a, 0.0) for a, p in d.dist_a.items() if a != NA}
    z = sum(q.values())
    if z == 0:
        return None, None, None
    q = {a: v / z for a, v in q.items()}
    top = max(q.values())
    modes = [a for a, v in q.items() if v == top]
    return (modes[0] if len(modes) == 1 else None), top, q


def boot(values: np.ndarray, weights: np.ndarray | None = None, n: int = 2000):
    """Mean (or weighted ratio) with item-bootstrap 95% CI. values/weights are per-item sums."""
    idx = rng.integers(0, len(values), size=(n, len(values)))
    if weights is None:
        stats = values[idx].mean(axis=1)
        point = values.mean()
    else:
        stats = values[idx].sum(axis=1) / np.maximum(weights[idx].sum(axis=1), 1e-12)
        point = values.sum() / weights.sum()
    return float(point), float(np.quantile(stats, 0.025)), float(np.quantile(stats, 0.975))


def analysis1(data):
    """Informative runs: contested item, shown answer != joint mode."""
    shown_r, mode_r, base_shown, base_mode, diff = [], [], [], [], []
    for d in data:
        m, top, _ = joint_mode(d)
        if m is None or top >= CONTESTED:
            continue
        runs = [(a, b) for a, b in zip(d.pairs_a, d.pairs_b) if a != m and a != NA]
        if not runs:
            continue
        s = np.mean([b == a for a, b in runs])
        md = np.mean([b == m for a, b in runs])
        shown_r.append(s); mode_r.append(md); diff.append(s - md)
        base_shown.append(np.mean([d.dist_b.get(a, 0.0) for a, _ in runs]))
        base_mode.append(d.dist_b.get(m, 0.0))
    f = lambda x: boot(np.array(x))
    return dict(n_items=len(diff), receiver_gives_shown=f(shown_r), receiver_gives_joint_mode=f(mode_r),
                paired_shown_minus_mode=f(diff), solo_rate_of_shown=f(base_shown), solo_rate_of_mode=f(base_mode))


def analysis2(data):
    """Log-likelihood per answer of five receiver models; deference weight alpha by grid MLE + item bootstrap."""
    per_item = []      # arrays per item: p_R(y), p_mix(y), 1[y=m*], 1[y=shown], uniform smoothing 1/|U|
    for d in data:
        m, _, _ = joint_mode(d)
        U = set(d.dist_a) | set(d.dist_b) | set(d.pairs_a) | set(d.pairs_b) | {NA}
        u = 1.0 / len(U)
        rows = [(d.dist_b.get(y, 0.0), 0.5 * (d.dist_a.get(y, 0.0) + d.dist_b.get(y, 0.0)),
                 float(m is not None and y == m), float(y == a and a != NA), u)
                for a, y in zip(d.pairs_a, d.pairs_b)]
        per_item.append(np.array(rows))
    allr = np.vstack(per_item)
    pr, mix, mode, shown, u = allr.T
    smooth = lambda p: np.log((1 - EPS) * p + EPS * u)
    n = len(allr)
    ll = {"independent (N3)": smooth(pr).sum(), "mixture": smooth(mix).sum(), "mode-finding (N4)": smooth(mode).sum(),
          "pure copy": smooth(shown).sum()}
    grid = np.linspace(0, 1, 1001)

    def fit(block):
        p, s, uu = block[:, 0], block[:, 3], block[:, 4]
        lls = [np.log((1 - EPS) * ((1 - g) * p + g * s) + EPS * uu).sum() for g in grid]
        k = int(np.argmax(lls))
        return grid[k], lls[k]

    alpha, ll_a = fit(allr)
    ll["deference weight"] = ll_a
    boots = []
    for _ in range(300):
        pick = rng.integers(0, len(per_item), size=len(per_item))
        boots.append(fit(np.vstack([per_item[i] for i in pick]))[0])
    aic = {k: -2 * v + (2 if k == "deference weight" else 0) for k, v in ll.items()}
    return dict(n_answers=n, ll_per_answer={k: v / n for k, v in ll.items()}, aic=aic,
                alpha=(float(alpha), float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))))


def analysis3(steps, random_cond):
    """Three-way decomposition of receiver errors under seq_steps."""
    def counts(data, item_ids=None):
        out = {}
        for d in data:
            mode_r = max((a for a in d.dist_b if a != NA), key=lambda a: d.dist_b[a], default=None)
            wrong = [(a, b) for a, b in zip(d.pairs_a, d.pairs_b) if b != d.correct]
            shared = sum(mode_r != d.correct for _ in wrong)
            created = sum(mode_r == d.correct and a != d.correct for a, _ in wrong)
            out[d.item_id] = (len(wrong), shared, created, len(d.pairs_b))
        return out
    cs = counts(steps)
    ids = list(cs)
    W = np.array([cs[i][0] for i in ids], float)
    res = dict(n_wrong=int(W.sum()),
               shared_share=boot(np.array([cs[i][1] for i in ids], float), W),
               created_share=boot(np.array([cs[i][2] for i in ids], float), W),
               created_rate_per_answer=boot(np.array([cs[i][2] for i in ids], float), np.array([cs[i][3] for i in ids], float)))
    if random_cond is not None:
        cr = counts(random_cond)
        res["created_rate_per_answer_random"] = boot(np.array([cr[i][2] for i in ids if i in cr], float),
                                                     np.array([cr[i][3] for i in ids if i in cr], float))
    amp = []
    for d in steps:
        m, top, q = joint_mode(d)
        if d.lure is None or q is None or top >= CONTESTED:
            continue
        amp.append(np.mean([b == d.lure for b in d.pairs_b]) - q.get(d.lure, 0.0))
    res["lure_amplification_contested"] = boot(np.array(amp)) if amp else None
    res["n_contested_lure_items"] = len(amp)
    return res


def fmt(t):
    return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]" if isinstance(t, tuple) else str(t)


def main(version="exp7b"):
    report = {}
    for model in ("olmo", "qwen", "nemotron"):
        if not (ROOT / f"experiments/{version}_{model}.json").exists():
            continue
        data = load(version, model)
        r = report[model] = {}
        print(f"\n######## {model} ({version})")
        a1 = r["tipping_vs_transmission"] = analysis1(data["seq_steps"])
        print(f"[1] informative items {a1['n_items']}: receiver gives SHOWN {fmt(a1['receiver_gives_shown'])} "
              f"vs JOINT MODE {fmt(a1['receiver_gives_joint_mode'])}; paired shown−mode {fmt(a1['paired_shown_minus_mode'])}")
        print(f"    solo baselines: shown {fmt(a1['solo_rate_of_shown'])}, joint mode {fmt(a1['solo_rate_of_mode'])}")
        for cond, d in data.items():
            a2 = r[f"models_{cond}"] = analysis2(d)
            best = min(a2["aic"], key=a2["aic"].get)
            print(f"[2] {cond:14s} LL/answer: " + "  ".join(f"{k} {v:.3f}" for k, v in a2["ll_per_answer"].items())
                  + f"  | best (AIC): {best} | alpha {fmt(a2['alpha'])}")
        a3 = r["decomposition"] = analysis3(data["seq_steps"], data.get("random_answer"))
        print(f"[3] wrong answers {a3['n_wrong']}: shared {fmt(a3['shared_share'])}, interaction-created "
              f"{fmt(a3['created_share'])} | created per answer: steps {fmt(a3['created_rate_per_answer'])}"
              + (f", random {fmt(a3['created_rate_per_answer_random'])}" if "created_rate_per_answer_random" in a3 else "")
              + f" | lure amplification beyond N4 on {a3['n_contested_lure_items']} contested lure items: "
              f"{fmt(a3['lure_amplification_contested'])}")
    out = ROOT / f"outputs/why1_n4_tipping_{version}.json"
    out.write_text(json.dumps(report, indent=2, default=float))
    print(f"\nreport: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
