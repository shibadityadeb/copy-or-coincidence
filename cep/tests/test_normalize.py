import pytest

from cep.normalize import FALSE, TRUE, UNANSWERABLE, canon_number, normalize


@pytest.mark.parametrize("raw,expected", [
    ("18", "18"), (18, "18"), (18.0, "18"), ("$18", "18"), ("$1,100", "1100"), ("18.", "18"),
    ("2.50", "2.5"), ("3/4", "0.75"), ("40%", "40"), ("2nd", "2"), ("second", "2"), ("2nd place", "2"),
    ("The answer is 18 dollars", "18"), ("**18**", "18"), ("-3", "-3"), ("0.0", "0"),
    ("16 - 3 - 4 = 9", None),           # several numbers: refuse to guess
    ("unanswerable", UNANSWERABLE), ("None", UNANSWERABLE),
    ("Cannot be determined from the given information", UNANSWERABLE),
    ("not enough information", UNANSWERABLE), ("", None), (None, None), ("banana", None),
])
def test_number(raw, expected):
    assert normalize(raw, "number") == expected


@pytest.mark.parametrize("raw,expected", [
    ("true", TRUE), ("False", FALSE), ("TRUE.", TRUE), (True, TRUE), (False, FALSE), ("A", TRUE),
    ("B", FALSE), ("yes", TRUE), ("The statement is false", FALSE), ("true or false", None),
    ("unknown", UNANSWERABLE), ("maybe", None),
])
def test_bool(raw, expected):
    assert normalize(raw, "bool") == expected


def test_canon_number_rounding():
    assert canon_number("40.00001") == "40"
    assert canon_number("33.33333333") == "33.3333"
