"""Logic family, fictional half: ProntoQA (MIT) as packaged by Logic-LM. Made-up words, so errors are
reasoning slips rather than real-world priors; no lure."""
import random

from datasets import load_dataset

from cep.normalize import FALSE, TRUE
from cep.schema import Item

DATASET = "renma/ProntoQA"
REVISION = "6f3e03863ce763efd1f9cd11aacf4caff1b7af02"
ASSUME = "Assume every statement above is true, even if it seems false in the real world."


def logic_question(context: str, statement: str) -> str:
    return f"{context}\n\n{ASSUME}\nIs the following statement true or false? {statement}"


def load(n: int, seed: int) -> list[Item]:
    ds = load_dataset(DATASET, split="validation", revision=REVISION)
    idx = list(range(len(ds)))
    random.Random(seed).shuffle(idx)
    items = []
    for i in idx[:n]:
        r = ds[i]
        statement = r["question"].split("true or false?", 1)[1].strip()
        items.append(Item(
            item_id="", family="logic", source=f"prontoqa:{r['id']}", template_id="prontoqa_fictional",
            question=logic_question(r["context"], statement), answer_type="bool",
            correct=TRUE if r["answer"] == "A" else FALSE, lure=None,
            error_cause_by_construction="deduction_slip",
            difficulty_param=r["context"].count("."),   # number of rules, a rough size proxy
            meta={"ontology": "fictional"}))
    return items
