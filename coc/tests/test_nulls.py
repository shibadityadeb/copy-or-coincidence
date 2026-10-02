"""The null-model code must (1) give zero residual when agents are independent, even with strong
difficulty heterogeneity, where the naive global baseline shows a large spurious excess, and
(2) recover a known copying rate c. Guide gate, month 2: "nulls.py recovers known c"."""
import numpy as np
import pytest

from coc.nulls import ItemData, distribution, global_naive_excess, residuals, summarize

ANSWERS = ["right", "lure", "w1", "w2"]


def simulate(n_items=400, k_dist=10, r=10, copy=0.0, seed=0):
    """Each item has its own answer distribution (hard items put mass on the lure). B copies A with prob `copy`."""
    rng = np.random.default_rng(seed)
    items = []
    for i in range(n_items):
        difficulty = rng.beta(0.6, 0.6)                       # many easy and many hard items
        p = np.array([1 - difficulty, 0.6 * difficulty, 0.25 * difficulty, 0.15 * difficulty])
        draw = lambda n: list(rng.choice(ANSWERS, size=n, p=p))
        a_runs = draw(r)
        b_runs = [a if rng.random() < copy else b for a, b in zip(a_runs, draw(r))]
        items.append(ItemData(f"i{i}", "right", "lure", a_runs, b_runs,
                              distribution(draw(k_dist)), distribution(draw(k_dist))))
    return items


def test_independent_agents_give_zero_residual_but_naive_baseline_does_not():
    items = simulate(copy=0.0)
    s = summarize(items, n_perm=300)
    for m in ("joint_error", "same_answer", "same_wrong_answer", "both_lure"):
        lo, hi = s[m]["ci95"]
        assert lo <= 0 <= hi, (m, s[m])
        assert s[m]["perm_p"] > 0.01, (m, s[m])
    naive = s["naive_global_joint_error"]
    assert naive["excess"] > 0.05      # difficulty heterogeneity alone fakes a big "excess"


@pytest.mark.parametrize("c", [0.05, 0.10, 0.20])
def test_recovers_known_copying_rate(c):
    items = simulate(copy=c, seed=1)
    obs, exp = residuals(items, "same_answer")
    # under copying with prob c: P(same) = c + (1-c) * expected  =>  residual = c * (1 - expected)
    predicted = c * (1 - exp).mean()
    assert abs((obs - exp).mean() - predicted) < 0.03
    s = summarize(items, n_perm=300)
    assert s["same_answer"]["perm_p"] < 0.01 and s["same_answer"]["ci95"][0] > 0


def test_na_answers_never_count_as_agreement():
    it = ItemData("x", "1", None, ["NA", "NA"], ["NA", "NA"], {"NA": 1.0}, {"NA": 1.0})
    obs, exp = residuals([it], "same_answer")
    assert obs[0] == 0 and exp[0] == 0
