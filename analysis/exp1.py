"""Experiment 1 (pre-registered in prereg/exp1_independent_duplicates.md): independent duplicates.

python analysis/exp1.py outputs/layer0_olmo/layer0_olmo-run1__olmo3-7b-A.jsonl outputs/layer0_olmo/layer0_olmo-run1__olmo3-7b-B.jsonl
"""
import json
import sys

import pandas as pd

from coc.nulls import NA, ItemData, distribution, summarize

DIST, PAIRS = range(0, 10), range(10, 20)      # fixed split, see the pre-registration
EXCLUDED: set[str] = set()                     # item ids removed by the human audit, if any


def load(path_a: str, path_b: str) -> tuple[list[ItemData], pd.DataFrame]:
    rows = pd.concat([pd.read_json(p, lines=True) for p in (path_a, path_b)])
    rows["ans"] = rows.answer_norm.fillna(NA)
    rows["who"] = rows.agent_id.str[-1]                     # "A" / "B"
    items = []
    for item_id, g in rows.groupby("task_id"):
        if item_id in EXCLUDED:
            continue
        a, b = g[g.who == "A"].set_index("sample_index").ans, g[g.who == "B"].set_index("sample_index").ans
        lure = g.item_lure.iloc[0]
        items.append(ItemData(item_id, g.item_correct.iloc[0], lure if isinstance(lure, str) else None,
                              [a[s] for s in PAIRS], [b[s] for s in PAIRS],
                              distribution([a[s] for s in DIST]), distribution([b[s] for s in DIST])))
    return items, rows


def main(path_a, path_b):
    items, rows = load(path_a, path_b)
    fam = rows.groupby("task_id").family.first()
    report = {"overall": summarize(items)}
    for f in ("lure", "logic", "math"):
        report[f] = summarize([it for it in items if fam[it.item_id] == f])
    report["na_rate_by_family"] = rows.groupby("family").apply(lambda g: (g.ans == NA).mean()).round(4).to_dict()
    report["accuracy_by_family"] = rows.groupby("family").correct.mean().round(4).to_dict()

    passed = True
    for scope in ("overall", "lure", "logic", "math"):
        for m in ("joint_error", "same_answer", "same_wrong_answer", "both_lure"):
            r = report[scope][m]
            ok = r["ci95"][0] <= 0 <= r["ci95"][1] and abs(r["residual"]) < 0.02
            passed &= ok
            print(f"{scope:8s} {m:18s} obs {r['observed']:.3f} exp {r['expected']:.3f} "
                  f"residual {r['residual']:+.4f} [{r['ci95'][0]:+.4f}, {r['ci95'][1]:+.4f}] p={r['perm_p']:.3f} "
                  f"{'ok' if ok else 'FAIL'}")
        n = report[scope]["naive_global_joint_error"]
        print(f"{scope:8s} naive global excess (contrast only): {n['excess']:+.4f}")
    print("\nNA rate:", report["na_rate_by_family"], "\naccuracy:", report["accuracy_by_family"])
    print("\nEXPERIMENT 1:", "PASS" if passed else "FAIL")
    json.dump(report, open("outputs/layer0_olmo/exp1_report.json", "w"), indent=2, default=float)
    return passed


if __name__ == "__main__":
    sys.exit(0 if main(*sys.argv[1:3]) else 1)
