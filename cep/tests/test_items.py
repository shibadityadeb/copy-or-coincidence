from fractions import Fraction

from cep.generators import crt, false_ontology
from cep.normalize import FALSE, TRUE, canon_number


def test_crt_counts_and_uniqueness():
    items = crt.generate(per_template=10, seed=0)
    assert len(items) == 100 and len({i.question for i in items}) == 100
    assert all(i.correct != i.lure for i in items)


def test_crt_deterministic():
    a = [i.model_dump() for i in crt.generate(10, seed=0)]
    b = [i.model_dump() for i in crt.generate(10, seed=0)]
    assert a == b


def test_crt_answers_recomputed_independently():
    """Brute-force / closed-form checks that don't reuse the generator's own arithmetic."""
    for it in crt.generate(10, seed=0):
        p = it.meta
        if it.template_id == "bat_ball":
            total = p["diff"] + 2 * int(it.correct)
            cheap = next(x for x in range(0, total + 1) if x + (x + p["diff"]) == total)
            assert canon_number(cheap) == it.correct
        elif it.template_id == "fence_posts":
            assert len(range(0, p["length"] + 1, p["gap"])) == int(it.correct)
        elif it.template_id == "average_speed":
            d = 1  # any distance
            t = Fraction(d, p["v1"]) + Fraction(d, p["v2"])
            assert canon_number(Fraction(2 * d) / t) == it.correct
        elif it.template_id == "siblings":
            assert int(it.correct) == p["sisters"] + 1
        elif it.template_id == "doubling":
            size, day = 1, 0
            full = 2 ** p["days"]
            while size < full / 2:
                size, day = size * 2, day + 1
            assert day == int(it.correct)


def test_false_ontology():
    items = false_ontology.generate(50)
    assert len(items) == 50 and len({i.question for i in items}) == 50
    for it in items:
        assert {it.correct, it.lure} == {TRUE, FALSE}
        assert "Assume every statement above is true" in it.question


def test_lures_are_whole_numbers():
    for it in crt.generate(10, seed=0):
        if it.template_id in ("stairs", "clock_strikes", "widgets", "doubling", "fence_posts"):
            assert "." not in it.lure, (it.template_id, it.lure)
