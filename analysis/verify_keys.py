"""Second, independent solver for every cep_v2 answer key.

Each question is re-solved from its text (or its stored parameters) by code written separately from the
generators: brute force over set models for syllogisms, forward chaining for false-world rules, simulation
for trick questions, separately written formulas for math. Any disagreement with the stored key is printed.

python analysis/verify_keys.py datasets/cep_v2/items.jsonl
"""
import itertools
import json
import re
import sys
from fractions import Fraction

from cep.normalize import FALSE, TRUE, UNANSWERABLE, canon_number

# ---------- syllogisms: enumerate every possible world over 3 terms ----------
STMT = re.compile(r"^(All|No|Some) (.+?) are (not )?(.+?)\??$")


def parse_stmt(s):
    m = STMT.match(s.strip())
    q, x, neg, y = m.group(1), m.group(2), bool(m.group(3)), m.group(4)
    return q + (" not" if neg else ""), x, y


def holds(stmt, world, idx):
    q, x, y = stmt
    xs = [r for r in world if r[idx[x]]]
    if q == "All":
        return all(r[idx[y]] for r in xs)
    if q == "No":
        return not any(r[idx[y]] for r in xs)
    if q == "Some":
        return any(r[idx[y]] for r in xs)
    if q == "Some not":
        return any(not r[idx[y]] for r in xs)
    raise ValueError(q)


def syllogism_valid(premises, conclusion, existential_import: bool) -> bool:
    stmts = [parse_stmt(p) for p in premises] + [parse_stmt(conclusion)]
    terms = sorted({t for s in stmts for t in s[1:]})
    idx = {t: i for i, t in enumerate(terms)}
    regions = list(itertools.product([False, True], repeat=len(terms)))
    for k in range(len(regions) + 1):
        for world in itertools.combinations(regions, k):          # world = set of non-empty regions
            if existential_import and not all(any(r[i] for r in world) for i in range(len(terms))):
                continue
            if all(holds(s, world, idx) for s in stmts[:-1]) and not holds(stmts[-1], world, idx):
                return False
    return True


def check_syllogism(it):
    lines = [l.strip() for l in it["question"].splitlines() if l.strip()]
    premises = [re.sub(r"^\d+\.\s*", "", l) for l in lines if re.match(r"^\d+\.", l)]
    conclusion = lines[lines.index("Does it logically follow that:") + 1]
    modern = syllogism_valid(premises, conclusion, existential_import=False)
    aristotle = syllogism_valid(premises, conclusion, existential_import=True)
    if modern != aristotle:
        return f"key depends on logic convention (modern={modern}, with existential import={aristotle})"
    expect = TRUE if modern else FALSE
    return None if expect == it["correct"] else f"solver says {expect}, key says {it['correct']}"


# ---------- false-world rules: forward chaining from the stated facts ----------
def check_false_world(it):
    text, _, tail = it["question"].partition("\n\nAssume")
    facts = [f.strip() for f in text.split(".") if f.strip()]
    isa, props, negs = {}, {}, {}
    entity_of = {}
    for f in facts:
        if m := (re.match(r"Every (.+?) is not (.+)$", f) or re.match(r"No (.+?) is (.+)$", f)):
            negs.setdefault(m.group(1), set()).add(m.group(2))
        elif m := re.match(r"Every (.+?) is an? (.+)$", f):
            isa.setdefault(m.group(1), set()).add(m.group(2))
        elif m := re.match(r"Every (.+?) is (.+)$", f):
            props.setdefault(m.group(1), set()).add(m.group(2))
        elif m := re.match(r"(\w+) is an? (.+)$", f):
            entity_of[m.group(1)] = m.group(2)
    statement = tail.split("true or false?")[1].strip().rstrip(".")
    name, prop = re.match(r"(\w+) is (.+)$", statement).groups()
    cats, frontier = set(), [entity_of[name]]
    while frontier:
        c = frontier.pop()
        if c not in cats:
            cats.add(c)
            frontier += list(isa.get(c, ()))
    has = set().union(*(props.get(c, set()) for c in cats))
    lacks = set().union(*(negs.get(c, set()) for c in cats))
    if prop in has and prop not in lacks:
        expect = TRUE
    elif prop in lacks and prop not in has:
        expect = FALSE
    else:
        return f"rules don't determine '{prop}'"
    return None if expect == it["correct"] else f"solver says {expect}, key says {it['correct']}"


# ---------- trick questions: simulate from stored parameters ----------
def sim_trick(t, p):
    if t == "widgets":
        return p["n"]                       # each machine makes one item in n minutes, in parallel
    if t == "doubling":
        return p["days"] - 1
    if t == "overtaking":
        return p["k"]
    if t == "siblings":
        return p["sisters"] + 1
    if t == "percent_round_trip":
        return Fraction(p["price"]) * Fraction(100 + p["p"], 100) * Fraction(100 - p["p"], 100)
    if t == "average_speed":
        d = 120
        return Fraction(2 * d) / (Fraction(d, p["v1"]) + Fraction(d, p["v2"]))
    if t == "fence_posts":
        return len(range(0, p["length"] + 1, p["gap"]))
    if t == "stairs":
        return Fraction(p["per_floor"] * (p["k"] - 1), p["k"] - 1) * (p["m"] - 1)
    if t == "clock_strikes":
        return p["gap"] * (p["b"] - 1)
    if t == "stacked_discount":
        return 100 - 100 * Fraction(100 - p["a"], 100) * Fraction(100 - p["b"], 100)
    if t == "reverse_percent":
        return Fraction(p["after"]) / Fraction(100 + p["p"], 100)
    if t == "cut_log":
        return (p["n"] - 1) * p["m"]
    if t == "pills":
        return (p["n"] - 1) * p["gap"]
    if t == "inclusive_days":
        return len(range(p["a"], p["b"] + 1))
    if t == "snail_well":
        h, day = 0, 0
        while True:
            day += 1
            h += p["up"]
            if h >= p["depth"]:
                return day
            h -= p["down"]
    if t == "weighted_average":
        scores = [p["a"]] * p["n1"] + [p["b"]] * p["n2"]
        return Fraction(sum(scores), len(scores))
    if t == "pipes_together":
        return 1 / (Fraction(1, p["a"]) + Fraction(1, p["b"]))
    if t == "handshakes":
        return sum(1 for _ in itertools.combinations(range(p["n"]), 2))
    if t == "all_but":
        return p["keep"]
    raise KeyError(t)


def check_trick(it):
    t, p = it["template_id"], it["meta"]
    if t == "bat_ball":   # re-solve from the text: x + (x + diff) = total
        total, diff = map(int, re.findall(r"\$(\d+)", it["question"])[:2])
        sol = next((x for x in range(total + 1) if x + x + diff == total), None)
        expect = canon_number(sol)
    else:
        expect = canon_number(sim_trick(t, p))
    return None if expect == it["correct"] else f"solver says {expect}, key says {it['correct']}"


# ---------- math: separately written formulas + the vague phrase really hides a quantity ----------
MATH = {
    "shop_restock": lambda v: v["a"] * v["b"] - v["c"] - 2 * v["c"],
    "fuel_cost": lambda v: Fraction(v["b"] + v["c"], 100) * v["a"] * v["p"],
    "savings": lambda v: Fraction(v["a"] * v["p"], 100) * v["w"] - v["s"],
    "school_buses": lambda v: -(-Fraction(v["k"] * v["n"] * v["p"], 100) // v["c"]),
    "bakery_boxes": lambda v: Fraction(v["t"] * v["m"] - v["k"], v["b"]),
    "garden_fence": lambda v: (v["l"] + v["w"] + v["l"] + v["w"]) * v["c"],
    "reading_days": lambda v: Fraction(v["p"] - v["a"] * v["d"], v["b"]),
    "ticket_change": lambda v: v["m"] - (v["a"] * v["x"] + v["c"] * v["y"]),
    "tank_fill": lambda v: Fraction(v["v"], v["r"] - v["l"]),
    "weekly_pay": lambda v: v["h"] * v["w"] + v["o"] * 2 * v["w"],
}


def check_math(it):
    name = it["template_id"].removeprefix("math_")
    v = it["meta"]["variables"]
    val = MATH[name](v)
    if val != int(val) or val <= 0:
        return f"answer {val} is not a positive whole number"
    expect = canon_number(val)
    if it["correct"] == UNANSWERABLE:
        if expect != it["meta"]["answer_if_complete"]:
            return f"complete-version answer {expect} != stored {it['meta']['answer_if_complete']}"
        return None if it["meta"]["removed_slot"] else "missing-premise item has no removed slot"
    return None if expect == it["correct"] else f"solver says {expect}, key says {it['correct']}"


def main(path):
    items = [json.loads(l) for l in open(path)]
    problems, by_group = [], {}
    for it in items:
        t = it["template_id"]
        if t == "rg_syllogism":
            err, g = check_syllogism(it), "syllogism"
        elif t == "false_ontology":
            err, g = check_false_world(it), "false_world"
        elif t.startswith("math_"):
            err, g = check_math(it), "math"
        else:
            err, g = check_trick(it), "trick"
        by_group.setdefault(g, [0, 0])
        by_group[g][0] += 1
        if err:
            by_group[g][1] += 1
            problems.append((it["item_id"], t, err))
    for g, (n, bad) in by_group.items():
        print(f"{g:12s} {n - bad}/{n} keys confirmed")
    for p in problems:
        print("  DISAGREE", *p)
    return len(problems)


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1]) else 0)
