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


def test_v2_extra_templates():
    items = crt.generate(10, seed=1, extra=True)
    assert len(items) == 200 and len({i.question for i in items}) == 200
    assert [i.model_dump() for i in crt.generate(10, seed=0)] == [i.model_dump() for i in crt.generate(10, seed=0, extra=False)]
    for it in items:
        p = it.meta
        assert it.correct != it.lure, (it.template_id, it.lure)
        if it.template_id == "handshakes":
            assert int(it.correct) == len([(i, j) for i in range(p["n"]) for j in range(i + 1, p["n"])])
        elif it.template_id == "snail_well":
            h, day = 0, 0
            while True:
                day += 1
                h += p["up"]
                if h >= p["depth"]:
                    break
                h -= p["down"]
            assert day == int(it.correct)
        elif it.template_id == "pipes_together":
            assert Fraction(1, p["a"]) + Fraction(1, p["b"]) == 1 / Fraction(it.correct)
        elif it.template_id == "inclusive_days":
            assert len(range(p["a"], p["b"] + 1)) == int(it.correct)
        elif it.template_id == "stacked_discount":
            price = Fraction(100) * (100 - p["a"]) / 100 * (100 - p["b"]) / 100
            assert canon_number(100 - price) == it.correct


def test_false_ontology_v2():
    items = false_ontology.generate(100, extra=True)
    assert len(items) == 100 and len({i.question for i in items}) == 100
    v1 = false_ontology.generate(50)
    assert all("goldfish" not in i.question for i in v1)           # cep_v1 unchanged by the extra cases
    for it in items:
        text = it.question.split("\n\n")[0]
        assert " is not " not in text                                # no scope-ambiguous negation
        asked = it.question.rsplit(" is ", 1)[1].rstrip(".")
        facts = [f for f in text.split(". ") if not f.startswith(("Every " + it.meta["entity"], "No "))]
        distractor = facts[0]                                        # the unrelated fact comes second
        assert asked not in distractor or it.meta["entity"] in distractor, (asked, distractor)
