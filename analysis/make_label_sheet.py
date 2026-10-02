"""Draw 150 Layer 0 answers for human labelling of the checker (guide §3: >= 0.95 correct/incorrect,
>= 0.85 error class). Stratified: 50 per family; within each family 15 'unusual' replies (not clean JSON, or
a final answer whose text differs from its canonical form), 15 the checker marked wrong, 20 at random.
The human sees the question and the raw reply only, never the checker's label.

python analysis/make_label_sheet.py
"""
import json
import random
from pathlib import Path

import pandas as pd

from cep.normalize import FALSE, TRUE, UNANSWERABLE

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "validation"
QUOTA = {"unusual": 15, "checker_wrong": 15, "random": 20}


def canonical_text(a):
    return {TRUE: "true", FALSE: "false", UNANSWERABLE: "unanswerable"}.get(a, a)


def main():
    rows = pd.concat([pd.read_json(ROOT / f"outputs/layer0_olmo/layer0_olmo-run1__olmo3-7b-{x}.jsonl", lines=True)
                      for x in "AB"], ignore_index=True)
    items = {json.loads(l)["item_id"]: json.loads(l) for l in (ROOT / "datasets/cep_v2/items.jsonl").read_text().splitlines()}
    rows["final_text"] = rows.final.astype(str).str.strip().str.lower()
    rows["unusual"] = (~rows.parse_ok) | (rows.final_text != rows.answer_norm.map(canonical_text).astype(str).str.lower())
    rng = random.Random(0)
    picked, used = [], set()
    for fam in ("lure", "logic", "math"):
        f = rows[rows.family == fam]
        pools = {"unusual": f[f.unusual], "checker_wrong": f[~f.correct & ~f.unusual], "random": f}
        for stratum, n in QUOTA.items():
            idx = [i for i in pools[stratum].index if i not in used]
            take = rng.sample(idx, min(n, len(idx)))
            used.update(take)
            picked += [(i, stratum) for i in take]
    rng.shuffle(picked)          # mixed order, so strata can't be guessed from position

    sheet = ["# Checker validation: label 150 model answers",
             "",
             "For each entry, read the question and the model's reply, then write **what the model's final answer is**,",
             "in your own words: a number (`30`), `yes` / `no`, `true` / `false`, `unanswerable`, or `unclear` if you",
             "can't tell what it answered. You are judging what the model *said*, not whether it is right.",
             "Fill in the `answer:` line, or reply in chat as `1: 30, 2: no, ...`. Please don't open `checker_label_key.json`.",
             ""]
    key = []
    for n, (i, stratum) in enumerate(picked, 1):
        r = rows.loc[i]
        it = items[r.task_id]
        sheet += [f"## {n}", "", "**Question**", "", "```text", it["question"], "```", "",
                  "**Model reply**", "", "```text", r.raw_output.strip(), "```", "", "answer: ", ""]
        key.append(dict(n=n, trial_id=r.trial_id, task_id=r.task_id, family=r.family, template_id=r.template_id,
                        stratum=stratum, item_correct=it["correct"], item_lure=it["lure"],
                        checker_answer_norm=r.answer_norm, checker_correct=bool(r.correct),
                        checker_error_class=r.error_class, checker_version=r.checker_version))
    OUT.mkdir(exist_ok=True)
    (OUT / "checker_label_sheet.md").write_text("\n".join(sheet) + "\n")
    (OUT / "checker_label_key.json").write_text(json.dumps(key, indent=1))
    s = pd.DataFrame(key)
    print(s.groupby(["family", "stratum"]).size().unstack(), "\n")
    print("checker marked wrong in sample:", int((~s.checker_correct).sum()), "/", len(s))


if __name__ == "__main__":
    main()
