"""Experiment 8 analysis, as pre-registered in prereg/exp8_mechanism.md.

python analysis/exp8.py            # all three models
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
import exp7  # noqa: E402
from compare_families import JUDGE  # noqa: E402

from coc.nulls import item_bootstrap_ci, residuals, summarize  # noqa: E402

N_PERM = 2000
EXP8_OUT = Path(os.environ.get("EXP8_OUT_ROOT", ROOT / "outputs"))   # override only for dry runs on fake data
NULL = range(0, 10)
rng = np.random.default_rng(0)


def context(version: str, model: str):
    e = json.loads((ROOT / f"experiments/{version}_{model}.json").read_text())
    items = {i.item_id: i for i in (exp7.Item.model_validate_json(l) for l in (ROOT / e["items"]).read_text().splitlines())}
    layer0 = {}
    for who, p in e["layer0"].items():
        df = exp7.load_jsonl(ROOT / p)
        df["ans"] = df.answer_norm.fillna(exp7.NA)
        layer0[who] = df.set_index(["task_id", "sample_index"]).sort_index()
    raw = {who: exp7.load_layer0(ROOT / p) for who, p in e["layer0"].items()}
    return e, items, layer0, raw


def condition(version, model, name, ctx=None):
    e, items, layer0, raw = ctx or context(version, model)
    c = next(x for x in e["conditions"] if x["name"] == name)
    base = EXP8_OUT if version == "exp8" else ROOT / "outputs"
    rows = exp7.load_jsonl(next((base / f"{version}_{model}").glob(f"*__{name}__*.jsonl")))
    return rows, exp7.build(c, e, rows, layer0, items, raw)


def per_item_same(data) -> pd.Series:
    obs, ex = residuals(data, "same_answer")
    return pd.Series(obs - ex, index=[d.item_id for d in data])


def paired(x: pd.Series, y: pd.Series):
    d = (x - y.reindex(x.index)).dropna().to_numpy()
    mean, lo, hi = item_bootstrap_ci(d)
    null = np.array([(d * rng.choice([-1, 1], size=len(d))).mean() for _ in range(N_PERM)])
    return dict(estimate=mean, ci95=(lo, hi), perm_p=float((np.sum(null >= d.mean()) + 1) / (N_PERM + 1)), n_items=len(d))


def _signflip(d: np.ndarray):
    mean, lo, hi = item_bootstrap_ci(d)
    null = np.array([(d * rng.choice([-1, 1], size=len(d))).mean() for _ in range(N_PERM)])
    return dict(estimate=mean, ci95=(lo, hi), perm_p=float((np.sum(null >= d.mean()) + 1) / (N_PERM + 1)), n_items=len(d))


def h2_flipped(rows: pd.DataFrame, layer0_b: pd.DataFrame):
    """Amendment 1: H2a = mean [1(y=s) - p_B(s)] (follows the attached conclusion, primary);
    H2b = mean [p_B(argued) - 1(y=argued)] (abandons the argued answer); combined = H2a + H2b."""
    a_vals, b_vals = [], []
    for item, g in rows.groupby("task_id"):
        solo = [layer0_b.loc[(item, k), "ans"] for k in NULL]
        pb = lambda a: sum(x == a for x in solo) / len(solo)
        trip = list(zip(g.peer_answer_norm, g.peer_argued_answer_norm.fillna(exp7.NA), g.answer_norm.fillna(exp7.NA)))
        a_vals.append(np.mean([float(y == s) - pb(s) for s, a, y in trip]))
        b_vals.append(np.mean([pb(a) - float(y == a) for s, a, y in trip]))
    h2a, h2b = _signflip(np.array(a_vals)), _signflip(np.array(b_vals))
    combined = _signflip(np.array(a_vals) + np.array(b_vals))
    return dict(**h2a, H2b_abandons_argued=h2b, combined=combined,
                receiver_gives_shown=float((rows.answer_norm == rows.peer_answer_norm).mean()),
                receiver_gives_argued=float((rows.answer_norm == rows.peer_argued_answer_norm).mean()))


def judging(rows):
    num = rows[~rows.item_correct.isin(["TRUE", "FALSE"])]
    return float(num.final.astype(str).str.strip().str.lower().isin(JUDGE).mean())


def holm(p: dict) -> dict:
    order, m, run, out = sorted(p, key=p.get), len(p), 0.0, {}
    for i, k in enumerate(order):
        run = max(run, min(1.0, (m - i) * p[k]))
        out[k] = run
    return out


def main():
    report = {}
    for model in ("olmo", "qwen", "nemotron"):
        if not list((EXP8_OUT / f"exp8_{model}").glob("*.jsonl")):
            print(f"{model}: no Experiment 8 output yet"); continue
        ctx8 = context("exp8", model)
        red_rows, red = condition("exp8", model, "steps_redacted", ctx8)
        flip_rows, _ = condition("exp8", model, "steps_flipped", ctx8)
        mis_rows, mis = condition("exp8", model, "steps_mismatched", ctx8)
        ctx7 = context("exp7b", model)
        _, steps7 = condition("exp7b", model, "seq_steps", ctx7)
        ans_rows7, ans7 = condition("exp7b", model, "seq_answer", ctx7)
        receiver = "A" if ctx8[0]["conditions"][0]["receiver"].endswith("_A.json") else "B"

        validity = {"steps_redacted": judging(red_rows), "steps_flipped": judging(flip_rows),
                    "steps_mismatched": judging(mis_rows), "exp7b seq_answer": judging(ans_rows7)}
        s_red = summarize(red, n_perm=N_PERM)["same_answer"]
        h = {"H1 argument alone (redacted)": dict(estimate=s_red["residual"], ci95=s_red["ci95"], perm_p=s_red["perm_p"]),
             "H2a follows attached conclusion (flipped)": h2_flipped(flip_rows, ctx8[2][receiver]),
             "H3 form persuades (mismatched - answer only)": paired(per_item_same(mis), per_item_same(ans7)),
             "H4 content persuades (real steps - mismatched)": paired(per_item_same(steps7), per_item_same(mis))}
        valid = {"H1 argument alone (redacted)": validity["steps_redacted"] <= 0.05,
                 "H2a follows attached conclusion (flipped)": validity["steps_flipped"] <= 0.05,
                 "H3 form persuades (mismatched - answer only)": validity["steps_mismatched"] <= 0.05 and validity["exp7b seq_answer"] <= 0.05,
                 "H4 content persuades (real steps - mismatched)": validity["steps_mismatched"] <= 0.05}
        adj = holm({k: v["perm_p"] for k, v in h.items() if valid[k]})
        for k, v in h.items():
            v["valid"] = valid[k]
            v["p_holm"] = adj.get(k)
            v["supported"] = bool(valid[k] and adj[k] < 0.05 and v["ci95"][0] > 0)
        acc = {n: float(r.correct.mean()) for n, r in (("steps_redacted", red_rows), ("steps_flipped", flip_rows),
                                                      ("steps_mismatched", mis_rows))}
        report[model] = dict(validity=validity, hypotheses=h, receiver_accuracy=acc)

        print(f"\n######## {model}")
        print("  validity (judging replies):", {k: f"{v:.1%}" for k, v in validity.items()})
        print("  receiver accuracy:", {k: round(v, 3) for k, v in acc.items()})
        for k, v in h.items():
            verdict = "SUPPORTED" if v["supported"] else ("not supported" if v["valid"] else "invalid condition")
            extra = (f"  (gives shown {v['receiver_gives_shown']:.3f}, gives argued {v['receiver_gives_argued']:.3f}; "
                     f"H2b abandons argued {v['H2b_abandons_argued']['estimate']:+.4f} "
                     f"[{v['H2b_abandons_argued']['ci95'][0]:+.4f}, {v['H2b_abandons_argued']['ci95'][1]:+.4f}])"
                     if "receiver_gives_shown" in v else "")
            print(f"  {k:48s} {v['estimate']:+.4f} [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] p={v['perm_p']:.4f} "
                  f"p_holm={v['p_holm'] if v['p_holm'] is None else round(v['p_holm'], 4)} -> {verdict}{extra}")
    (EXP8_OUT / "exp8_report.json").write_text(json.dumps(report, indent=2, default=float))
    print(f"\nreport: {EXP8_OUT / 'exp8_report.json'}")


if __name__ == "__main__":
    main()
