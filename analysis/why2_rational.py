"""Is deference rational? (prereg/why2_rational_deference.md)

python analysis/why2_rational.py           # Experiment 7b (primary)
python analysis/why2_rational.py exp7      # Experiment 7 (robustness)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
from n4_tipping import NA, load  # noqa: E402

EPS = 0.01
GRID = np.linspace(0, 1, 1001)
N_BOOT = 500
rng = np.random.default_rng(0)


def rows_for(d, keep):
    """Per-run arrays (p_R(y), 1[y = shown], 1/|U|) for runs where keep(shown) is true."""
    U = set(d.dist_a) | set(d.dist_b) | set(d.pairs_a) | set(d.pairs_b) | {NA}
    u = 1.0 / len(U)
    return [(d.dist_b.get(y, 0.0), float(y == s and s != NA), u) for s, y in zip(d.pairs_a, d.pairs_b) if keep(s)]


def fit(blocks):
    """MLE of alpha over a list of per-item arrays."""
    rows = [r for b in blocks for r in b]
    if not rows:
        return float("nan")
    a = np.array(rows)
    p, s, u = a[:, 0][:, None], a[:, 1][:, None], a[:, 2][:, None]
    ll = np.log((1 - EPS) * ((1 - GRID) * p + GRID * s) + EPS * u).sum(axis=0)
    return float(GRID[int(np.argmax(ll))])


def alpha_ci(per_item):
    """per_item: list of per-item row lists. Point estimate + item-bootstrap CI."""
    per_item = [b for b in per_item if b]
    point = fit(per_item)
    n = len(per_item)
    boots = [fit([per_item[i] for i in rng.integers(0, n, n)]) for _ in range(N_BOOT)] if n else []
    lo, hi = (np.nanquantile(boots, [0.025, 0.975]) if boots else (float("nan"), float("nan")))
    return dict(alpha=point, ci=(float(lo), float(hi)), n_items=n, n_runs=sum(len(b) for b in per_item))


def paired_discrimination(right, wrong):
    """D = alpha_right - alpha_wrong with a paired item bootstrap over items present in either set."""
    ids = sorted(set(right) | set(wrong))
    d_point = fit([right[i] for i in ids if i in right]) - fit([wrong[i] for i in ids if i in wrong])
    boots = []
    for _ in range(N_BOOT):
        pick = [ids[j] for j in rng.integers(0, len(ids), len(ids))]
        boots.append(fit([right[i] for i in pick if i in right]) - fit([wrong[i] for i in pick if i in wrong]))
    return dict(D=d_point, ci=tuple(float(x) for x in np.nanquantile(boots, [0.025, 0.975])))


def entropy(dist):
    return -sum(p * math.log2(p) for p in dist.values() if p > 0)


def analyse(data):
    out = {}
    mixed = [d for d in data if 0 < d.dist_b.get(d.correct, 0.0) < 1]
    right = {d.item_id: rows_for(d, lambda s, c=d.correct: s == c) for d in mixed}
    wrong = {d.item_id: rows_for(d, lambda s, c=d.correct: s != c and s != NA) for d in mixed}
    right = {k: v for k, v in right.items() if v}
    wrong = {k: v for k, v in wrong.items() if v}
    out["n_mixed_items"] = len(mixed)
    out["alpha_right"] = alpha_ci(list(right.values()))
    out["alpha_wrong"] = alpha_ci(list(wrong.values()))
    out["discrimination"] = paired_discrimination(right, wrong)
    bins = {"certain (H=0)": lambda h: h == 0, "some doubt (0<H<=1)": lambda h: 0 < h <= 1, "very unsure (H>1)": lambda h: h > 1}
    out["by_certainty_wrong_shown"] = {
        name: alpha_ci([rows_for(d, lambda s, c=d.correct: s != c and s != NA) for d in data if test(entropy(d.dist_b))])
        for name, test in bins.items()}
    out["by_plausibility_wrong_shown"] = {
        "never gives it alone": alpha_ci([rows_for(d, lambda s, d=d: s != d.correct and s != NA and d.dist_b.get(s, 0) == 0) for d in data]),
        "sometimes gives it alone": alpha_ci([rows_for(d, lambda s, d=d: s != d.correct and s != NA and d.dist_b.get(s, 0) > 0) for d in data]),
    }
    return out


def f(x):
    return f"{x['alpha']:.2f} [{x['ci'][0]:.2f}, {x['ci'][1]:.2f}] (items {x['n_items']}, runs {x['n_runs']})"


def main(version="exp7b"):
    report = {}
    for model in ("olmo", "qwen", "nemotron"):
        data = load(version, model)
        for cond, d in data.items():
            r = report[f"{model}/{cond}"] = analyse(d)
            print(f"\n#### {model} / {cond}  ({version}; mixed items: {r['n_mixed_items']})")
            print(f"  [1] alpha right peer {f(r['alpha_right'])}")
            print(f"      alpha wrong peer {f(r['alpha_wrong'])}")
            print(f"      discrimination D = {r['discrimination']['D']:+.2f} [{r['discrimination']['ci'][0]:+.2f}, {r['discrimination']['ci'][1]:+.2f}]")
            for k, v in r["by_certainty_wrong_shown"].items():
                print(f"  [2] {k:22s} alpha (wrong shown) {f(v)}")
            for k, v in r["by_plausibility_wrong_shown"].items():
                print(f"  [3] {k:24s} alpha (wrong shown) {f(v)}")
    out = ROOT / f"outputs/why2_rational_{version}.json"
    out.write_text(json.dumps(report, indent=2, default=float))
    print(f"\nreport: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
