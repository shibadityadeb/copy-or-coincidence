"""Experiment 7 analysis, exactly as pre-registered in prereg/exp7_sequential_exposure.md.

python analysis/exp7.py outputs/exp7_olmo [experiments/exp7_olmo.json]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from cep.schema import Item
from coc.nulls import NA, ItemData, distribution, item_bootstrap_ci, residuals, summarize, within_item_permutation
from coc.sequential import candidates, load_layer0

ROOT = Path(__file__).resolve().parent.parent
NULL_SAMPLES = range(0, 10)
N_PERM = 2000
EXCLUDED: set[str] = set()


def load_jsonl(p: Path) -> pd.DataFrame:
    return pd.read_json(p, lines=True)


def build(cond: dict, exp: dict, rows: pd.DataFrame, layer0: dict, items: dict, raw_l0: dict) -> list[ItemData]:
    """a = shown answer, b = receiver answer, per run r; nulls from Layer 0 samples 0-9."""
    receiver_agent = "A" if cond["receiver"].endswith("_A.json") else "B"
    out = []
    for item_id, g in rows.groupby("task_id"):
        if item_id in EXCLUDED:
            continue
        g = g.sort_values("sample_index")
        it = items[item_id]
        l0r = layer0[receiver_agent]
        dist_r = distribution([l0r.loc[(item_id, k), "ans"] for k in NULL_SAMPLES])
        if cond["sender"] == "random":
            # the exact candidate set the experiment drew from (same loader, so missing answers stay None)
            cand = candidates(it, [raw_l0[w][(item_id, k)] for w in raw_l0 for k in range(20)
                                   if (item_id, k) in raw_l0[w]])
            dist_s = {a: 1 / len(cand) for a in cand}
        else:
            l0s = layer0[cond["sender"]]
            dist_s = distribution([l0s.loc[(item_id, k), "ans"] for k in NULL_SAMPLES])
        out.append(ItemData(item_id, it.correct, it.lure, list(g.peer_answer_norm.fillna(NA)),
                            list(g.answer_norm.fillna(NA)), dist_s, dist_r))
    return out


def holm(pvals: dict[str, float]) -> dict[str, float]:
    order = sorted(pvals, key=pvals.get)
    m, running, adj = len(order), 0.0, {}
    for i, k in enumerate(order):
        running = max(running, min(1.0, (m - i) * pvals[k]))
        adj[k] = running
    return adj


def paired_difference(x: list[ItemData], y: list[ItemData], metric: str, seed: int = 0):
    """Per-item residual difference x - y (same items): bootstrap CI and one-sided sign-flip p."""
    ox, ex = residuals(x, metric)
    oy, ey = residuals(y, metric)
    d = (ox - ex) - (oy - ey)
    mean, lo, hi = item_bootstrap_ci(d)
    rng = np.random.default_rng(seed)
    null = np.array([(d * rng.choice([-1, 1], size=len(d))).mean() for _ in range(N_PERM)])
    p = (np.sum(null >= d.mean()) + 1) / (N_PERM + 1)
    return dict(n_items=len(d), residual_difference=mean, ci95=(lo, hi), perm_p=float(p))


def main(out_dir: str, exp_path: str = "experiments/exp7_olmo.json"):
    exp = json.loads((ROOT / exp_path).read_text())
    items = {i.item_id: i for i in (Item.model_validate_json(l) for l in (ROOT / exp["items"]).read_text().splitlines())}
    layer0 = {}
    for who, p in exp["layer0"].items():
        df = load_jsonl(ROOT / p)
        df["ans"] = df.answer_norm.fillna(NA)
        layer0[who] = df.set_index(["task_id", "sample_index"]).sort_index()
    raw_l0 = {who: load_layer0(ROOT / p) for who, p in exp["layer0"].items()}
    data, rows_by = {}, {}
    for cond in exp["conditions"]:
        f = next(Path(out_dir).glob(f"*__{cond['name']}__*.jsonl"))
        rows = load_jsonl(f)
        rows_by[cond["name"]] = rows
        data[cond["name"]] = build(cond, exp, rows, layer0, items, raw_l0)

    report = {"conditions": {}, "hypotheses": {}, "exploratory": {}}
    for name, its in data.items():
        report["conditions"][name] = summarize(its, n_perm=N_PERM)
        report["conditions"][name]["receiver_accuracy"] = float(rows_by[name].correct.mean())

    # primary hypotheses
    s = report["conditions"]
    raw = {
        "H1 seq_steps same-answer": (s["seq_steps"]["same_answer"]),
        "H3 random_answer same-answer": (s["random_answer"]["same_answer"]),
        "H4 seq_steps joint-error": (s["seq_steps"]["joint_error"]),
        "H5 seq_steps both-on-lure": (s["seq_steps"]["both_lure"]),
    }
    h2 = paired_difference(data["seq_steps"], data["seq_answer"], "same_answer")
    pvals = {k: v["perm_p"] for k, v in raw.items()} | {"H2 steps minus answer-only": h2["perm_p"]}
    adj = holm(pvals)
    for k, v in raw.items():
        report["hypotheses"][k] = dict(residual=v["residual"], ci95=v["ci95"], p=v["perm_p"], p_holm=adj[k],
                                       supported=adj[k] < 0.05 and v["ci95"][0] > 0)
    k = "H2 steps minus answer-only"
    report["hypotheses"][k] = dict(residual=h2["residual_difference"], ci95=h2["ci95"], p=h2["perm_p"],
                                   p_holm=adj[k], supported=adj[k] < 0.05 and h2["ci95"][0] > 0)

    # exploratory (labelled)
    fam = {i: items[i].family for i in items}
    for name, its in data.items():
        report["exploratory"][f"{name} by family"] = {
            f: summarize([x for x in its if fam[x.item_id] == f], n_perm=200) for f in ("lure", "logic", "math")}
    l0_acc = {w: float(layer0[w].correct.mean()) for w in layer0}
    report["exploratory"]["layer0 accuracy"] = l0_acc
    for name, rows in rows_by.items():
        shown_wrong = rows.peer_answer_norm.fillna(NA) != rows.item_correct
        report["exploratory"][f"{name} adoption"] = dict(
            receiver_gives_shown_answer=float((rows.answer_norm == rows.peer_answer_norm).mean()),
            accuracy_when_shown_right=float(rows[~shown_wrong].correct.mean()) if (~shown_wrong).any() else None,
            accuracy_when_shown_wrong=float(rows[shown_wrong].correct.mean()) if shown_wrong.any() else None,
            n_shown_wrong=int(shown_wrong.sum()))

    print("CONDITIONS (receiver vs shown answer; item-conditioned residuals, 95% CI, one-sided permutation p)")
    for name, r in s.items():
        print(f"\n[{name}] receiver accuracy {r['receiver_accuracy']:.3f} (Layer 0: A {l0_acc['A']:.3f}, B {l0_acc['B']:.3f})")
        for m in ("same_answer", "joint_error", "same_wrong_answer", "both_lure"):
            x = r[m]
            print(f"  {m:18s} obs {x['observed']:.3f} exp {x['expected']:.3f} residual {x['residual']:+.4f} "
                  f"[{x['ci95'][0]:+.4f}, {x['ci95'][1]:+.4f}] p={x['perm_p']:.4f}")
    print("\nPRE-REGISTERED HYPOTHESES (Holm-corrected across 5)")
    for k, v in report["hypotheses"].items():
        print(f"  {k:30s} {v['residual']:+.4f} [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] "
              f"p={v['p']:.4f} p_holm={v['p_holm']:.4f} -> {'SUPPORTED' if v['supported'] else 'not supported'}")
    print("\nEXPLORATORY: adoption of the shown answer")
    for name in rows_by:
        e = report["exploratory"][f"{name} adoption"]
        print(f"  {name:14s} gives shown answer {e['receiver_gives_shown_answer']:.3f} | accuracy when shown right "
              f"{e['accuracy_when_shown_right']} | when shown wrong {e['accuracy_when_shown_wrong']} (n={e['n_shown_wrong']})")
    Path(out_dir, "exp7_report.json").write_text(json.dumps(report, indent=2, default=float))
    print(f"\nreport: {Path(out_dir, 'exp7_report.json')}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
