"""Item-conditioned null models and residuals (field guide §4-5).

Data shape used everywhere: for each item, an (R,) array of A's answers and an (R,) array of B's answers,
where run r of A is paired with run r of B. Answers are canonical strings (cep.normalize); an unreadable
answer is the token NA, which counts as wrong and never as "the same answer" as anything.

Expected (null) rates come from each agent's own per-item answer distribution, estimated on samples that
are NOT used for the observed pairs (never estimate observed and expected from the same samples).
"""
from collections import Counter
from dataclasses import dataclass
from typing import Optional

import numpy as np

NA = "NA"


@dataclass
class ItemData:
    item_id: str
    correct: str
    lure: Optional[str]
    pairs_a: list[str]          # observed: A's answer in run r ...
    pairs_b: list[str]          # ... paired with B's answer in run r
    dist_a: dict[str, float]    # A's per-item answer distribution (from held-out samples)
    dist_b: dict[str, float]


def distribution(answers: list[str]) -> dict[str, float]:
    c = Counter(answers)
    n = sum(c.values())
    return {a: k / n for a, k in c.items()}


# ---------- per-item expected rates under item-conditioned independence (N2/N3) ----------
def p_wrong(d: dict, correct: str) -> float:
    return 1.0 - d.get(correct, 0.0)


def expected_same(da: dict, db: dict) -> float:
    return sum(p * db.get(a, 0.0) for a, p in da.items() if a != NA)


def expected_same_wrong(da: dict, db: dict, correct: str) -> float:
    return sum(p * db.get(a, 0.0) for a, p in da.items() if a not in (NA, correct))


def expected_both_wrong(da: dict, db: dict, correct: str) -> float:
    return p_wrong(da, correct) * p_wrong(db, correct)


def expected_both_lure(da: dict, db: dict, lure: Optional[str]) -> float:
    return da.get(lure, 0.0) * db.get(lure, 0.0) if lure else 0.0


# ---------- observed rates on paired runs ----------
def obs_same(a, b, correct=None):
    return np.mean([x == y and x != NA for x, y in zip(a, b)])


def obs_same_wrong(a, b, correct):
    return np.mean([x == y and x not in (NA, correct) for x, y in zip(a, b)])


def obs_both_wrong(a, b, correct):
    return np.mean([x != correct and y != correct for x, y in zip(a, b)])


def obs_both_lure(a, b, lure):
    return np.mean([x == y == lure for x, y in zip(a, b)]) if lure else 0.0


METRICS = {
    # name: (observed fn, expected fn, which item field the fns need)
    "joint_error": (obs_both_wrong, expected_both_wrong, "correct"),
    "same_answer": (obs_same, lambda da, db, _: expected_same(da, db), "correct"),
    "same_wrong_answer": (obs_same_wrong, expected_same_wrong, "correct"),
    "both_lure": (obs_both_lure, expected_both_lure, "lure"),
}


def residuals(items: list[ItemData], metric: str) -> tuple[np.ndarray, np.ndarray]:
    """Per-item observed and expected rates for one metric (items without a lure are skipped for both_lure)."""
    obs_fn, exp_fn, field = METRICS[metric]
    use = [it for it in items if metric != "both_lure" or it.lure]
    obs = np.array([obs_fn(it.pairs_a, it.pairs_b, getattr(it, field)) for it in use])
    exp = np.array([exp_fn(it.dist_a, it.dist_b, getattr(it, field)) for it in use])
    return obs, exp


def global_naive_excess(items: list[ItemData]) -> tuple[float, float]:
    """N1, the confounded baseline: observed joint error vs product of dataset-average error rates."""
    a_wrong = np.mean([x != it.correct for it in items for x in it.pairs_a])
    b_wrong = np.mean([y != it.correct for it in items for y in it.pairs_b])
    obs = np.mean([obs_both_wrong(it.pairs_a, it.pairs_b, it.correct) for it in items])
    return obs, a_wrong * b_wrong


# ---------- inference: the item is the unit ----------
def within_item_permutation(items: list[ItemData], metric: str, n_perm: int = 1000, seed: int = 0):
    """Shuffle B's runs within each item: keeps every per-item distribution, destroys only the A/B pairing.
    Returns (observed mean, one-sided p for observed > null, null draws)."""
    rng = np.random.default_rng(seed)
    obs_fn, _, field = METRICS[metric]
    use = [it for it in items if metric != "both_lure" or it.lure]
    stat = lambda pb: np.mean([obs_fn(it.pairs_a, b, getattr(it, field)) for it, b in zip(use, pb)])
    observed = stat([it.pairs_b for it in use])
    null = np.array([stat([list(rng.permutation(it.pairs_b)) for it in use]) for _ in range(n_perm)])
    return observed, (np.sum(null >= observed) + 1) / (n_perm + 1), null


def item_bootstrap_ci(values: np.ndarray, n_boot: int = 2000, seed: int = 0, level: float = 0.95):
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(values, size=len(values), replace=True).mean() for _ in range(n_boot)])
    lo, hi = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(values.mean()), float(lo), float(hi)


def summarize(items: list[ItemData], n_perm: int = 1000) -> dict:
    out = {}
    for m in METRICS:
        obs, exp = residuals(items, m)
        mean, lo, hi = item_bootstrap_ci(obs - exp)
        _, p, _ = within_item_permutation(items, m, n_perm=n_perm)
        out[m] = dict(n_items=len(obs), observed=float(obs.mean()), expected=float(exp.mean()),
                      residual=mean, ci95=(lo, hi), perm_p=float(p))
    o, e = global_naive_excess(items)
    out["naive_global_joint_error"] = dict(observed=float(o), expected=float(e), excess=float(o - e))
    return out
