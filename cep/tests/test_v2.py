import re
import string

from cep.generators import math_word
from cep.normalize import FALSE, TRUE, UNANSWERABLE, canon_number
from cep.sources import rg_syllogism

ITEMS = math_word.generate(5, 5, seed=1)
TPL = {f"math_{t.name}": t for t in math_word.TEMPLATES}


def slot_vars(t, slot):
    return [f[1] for f in string.Formatter().parse(t.phrases[slot][0]) if f[1]]


def test_counts_unique_deterministic():
    assert len(ITEMS) == 100 and len({i.question for i in ITEMS}) == 100
    assert [i.model_dump() for i in ITEMS] == [i.model_dump() for i in math_word.generate(5, 5, seed=1)]
    assert sum(i.correct == UNANSWERABLE for i in ITEMS) == 50


def test_no_unfilled_slots_and_answers_positive_integers():
    for it in ITEMS:
        assert "{" not in it.question and "}" not in it.question
        key = it.meta["answer_if_complete"] if it.correct == UNANSWERABLE else it.correct
        assert re.fullmatch(r"\d+", key) and int(key) > 0, (it.template_id, key)


def test_complete_items_state_every_number():
    for it in ITEMS:
        if it.correct != UNANSWERABLE:
            t = TPL[it.template_id]
            for slot in t.phrases:
                for var in slot_vars(t, slot):
                    assert str(it.meta["variables"][var]) in it.question


def test_missing_premise_is_really_missing():
    """The hidden number is absent from the text, and changing it changes the answer (so it was needed)."""
    for it in ITEMS:
        if it.correct != UNANSWERABLE:
            continue
        t, v = TPL[it.template_id], dict(it.meta["variables"])
        slot = it.meta["removed_slot"]
        assert t.phrases[slot][1] in it.question
        for var in slot_vars(t, slot):
            changed = []
            for delta in (1, 2, 5, 10, 50, 100):
                w = dict(v, **{var: v[var] + delta})
                try:
                    changed.append(t.answer(w) != t.answer(v))
                except ZeroDivisionError:
                    pass
            assert any(changed), (it.template_id, var)
        assert it.lure is None and it.meta["answer_if_complete"] == canon_number(t.answer(v))


def test_syllogisms_balanced():
    s = rg_syllogism.generate(25, 25, seed=1)
    assert len(s) == 50 and sum(i.correct == TRUE for i in s) == 25 and sum(i.correct == FALSE for i in s) == 25


def test_syllogism_keys_hold_without_existential_import():
    for it in rg_syllogism.generate(25, 25, seed=1):
        if it.correct == TRUE:
            assert not it.meta["conclusion"].startswith("Some")


def test_every_cep_v2_key_confirmed_by_independent_solver(tmp_path):
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "analysis"))
    import verify_keys
    from cep.build import build
    build(tmp_path, "cep_v2")
    assert verify_keys.main(str(tmp_path / "items.jsonl")) == 0
