"""Math family from GSM-Plus (CC-BY-SA-4.0): missing-premise and distractor perturbations of GSM8K."""
import random

from datasets import load_dataset

from cep.normalize import UNANSWERABLE, canon_number
from cep.schema import Item

DATASET = "qintongli/GSM-Plus"
REVISION = "3b708db57b96a16e8e3368ed2956990c0809440e"


def _n_ops(solution: str) -> int:
    return solution.count("<<")  # GSM8K marks each calculation as <<a*b=c>>


def load(n_missing: int, n_distractor: int, seed: int) -> list[Item]:
    ds = load_dataset(DATASET, split="test", revision=REVISION)
    rows = list(enumerate(ds))
    random.Random(seed).shuffle(rows)
    want = {"critical thinking": n_missing, "distraction insertion": n_distractor}
    used_seeds: set[str] = set()          # never take two perturbations of the same original problem
    items: list[Item] = []
    for idx, r in rows:
        kind = r["perturbation_type"]
        if want.get(kind, 0) == 0 or r["seed_question"] in used_seeds or r["question"] == r["seed_question"]:
            continue
        if kind == "critical thinking":
            # The question has a fact deleted. Making that fact up reproduces the original answer: the lure.
            items.append(Item(
                item_id="", family="math", source=f"gsm_plus:test:{idx}", template_id="gsm_missing_premise",
                question=r["question"], answer_type="number", correct=UNANSWERABLE,
                lure=canon_number(r["seed_answer"]), error_cause_by_construction="missing_premise",
                difficulty_param=_n_ops(r["seed_solution"]),
                meta={"seed_question": r["seed_question"]}))
        else:
            # An irrelevant sentence was inserted; the answer is unchanged. No single pre-specifiable lure.
            items.append(Item(
                item_id="", family="math", source=f"gsm_plus:test:{idx}", template_id="gsm_distractor",
                question=r["question"], answer_type="number", correct=canon_number(r["answer"]),
                lure=None, error_cause_by_construction="distractor",
                difficulty_param=_n_ops(r["solution"]),
                meta={"seed_question": r["seed_question"]}))
        want[kind] -= 1
        used_seeds.add(r["seed_question"])
        if not any(want.values()):
            break
    assert not any(want.values()), f"not enough GSM-Plus rows: {want}"
    return items
