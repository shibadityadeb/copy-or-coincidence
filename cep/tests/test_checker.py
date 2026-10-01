from cep.checker import check_final, check_raw
from cep.normalize import FALSE, TRUE, UNANSWERABLE
from cep.schema import Item


def item(correct, lure, answer_type="number"):
    return Item(item_id="t", family="math", source="t", template_id="t", question="q",
                answer_type=answer_type, correct=correct, lure=lure, error_cause_by_construction="t")


def test_classes_numeric_with_lure():
    it = item("50", "100")
    assert check_final(it, "50").error_class == "correct"
    c = check_final(it, "$100")
    assert c.error_class == "lure" and c.lure_hit and not c.correct
    assert check_final(it, "75").error_class == "other_wrong"
    assert check_final(it, "unanswerable").error_class == "false_unanswerable"
    assert check_final(it, "1 or 2").error_class == "format_error"


def test_missing_premise_item():
    it = item(UNANSWERABLE, "18")
    assert check_final(it, "Not enough information").correct
    assert check_final(it, 18).error_class == "lure"
    assert check_final(it, 20).error_class == "unanswerable_answered"


def test_bool_item():
    it = item(TRUE, FALSE, "bool")
    assert check_final(it, "true").correct
    assert check_final(it, "false").lure_hit


def test_check_raw_row_fields():
    row = check_raw(item("7", None), '{"steps": ["a"], "final": "7", "confidence": 0.6}')
    assert row["correct"] and row["parse_ok"] and row["n_steps"] == 1 and len(row["checker_version"]) == 12
