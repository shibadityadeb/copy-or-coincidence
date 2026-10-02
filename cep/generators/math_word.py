"""Math family: multi-step word problems with exact answers, plus missing-premise variants.

Every template uses every quantity it states, so replacing one with a vague phrase ("some boxes") makes
the problem genuinely unanswerable. Missing-premise items have no lure: the hidden number is random, so no
single wrong answer is tempting (unlike GSM-Plus, where it came from a well-known original problem). The
error that matters there is answering at all, which the checker labels `unanswerable_answered`.
"""
import random
from dataclasses import dataclass
from typing import Callable

from cep.normalize import UNANSWERABLE, canon_number
from cep.schema import Item


@dataclass
class Template:
    name: str
    text: str                                    # slots in {Braces} are quantity phrases
    phrases: dict[str, tuple[str, str]]          # slot -> (exact phrase with {var}, vague phrase)
    sample: Callable[[random.Random], dict]      # draws variables; returns None to redraw
    answer: Callable[[dict], int]
    n_ops: int


def _shop(r):
    a, b, c = r.randint(6, 20), r.choice([12, 24, 36, 48]), r.randint(10, 60)
    return dict(a=a, b=b, c=c) if a * b > 3 * c else None


def _fuel(r):
    a, p = r.randint(5, 9), r.randint(2, 4)
    b = r.randrange(100, 500, 50)
    c = r.randrange(100, 500, 50)
    return dict(a=a, b=b, c=c, p=p) if (b + c) % 100 == 0 else None


def _savings(r):
    a, p, w = r.choice([200, 250, 300, 400, 500]), r.choice([10, 20, 25, 40]), r.randint(4, 12)
    s = r.randrange(50, 400, 10)
    if (a * p) % 100:            # weekly saving must be whole dollars (250 x 25% = 62.50 was floored before)
        return None
    return dict(a=a, p=p, w=w, s=s) if a * p // 100 * w > s else None


def _buses(r):
    k, n, p, c = r.randint(3, 8), r.randint(20, 32), r.choice([25, 50, 75]), r.choice([20, 30, 40, 50])
    return dict(k=k, n=n, p=p, c=c) if (k * n * p) % 100 == 0 else None


def _bakery(r):
    t, m, b = r.randint(3, 9), r.choice([12, 18, 24]), r.choice([4, 6])
    k = r.randrange(b, 3 * b + 1, b) + (t * m) % b
    return dict(t=t, m=m, k=k, b=b) if t * m > k and (t * m - k) % b == 0 else None


def _fence(r):
    return dict(l=r.randint(8, 40), w=r.randint(5, 25), c=r.randint(3, 15))


def _reading(r):
    a, d, b = r.randint(10, 30), r.randint(3, 7), r.randint(20, 40)
    rest = b * r.randint(2, 6)
    return dict(p=a * d + rest, a=a, d=d, b=b)


def _tickets(r):
    a, c, x, y = r.randint(12, 30), r.randint(5, 11), r.randint(1, 4), r.randint(1, 5)
    m = r.choice([100, 150, 200, 250])
    return dict(a=a, c=c, x=x, y=y, m=m) if m > a * x + c * y else None


def _tank(r):
    rate, leak = r.randint(8, 20), r.randint(1, 6)
    if rate <= leak:
        return None
    return dict(v=(rate - leak) * r.randint(10, 40), r=rate, l=leak)


def _pay(r):
    return dict(h=r.randint(20, 40), w=r.randint(12, 30), o=r.randint(2, 10), m=2)


TEMPLATES = [
    Template("shop_restock",
             "A shop has {A} with {B}. It sells {C} on Monday and twice as many on Tuesday. "
             "How many pens are left?",
             {"A": ("{a} boxes of pens", "several boxes of pens"), "B": ("{b} pens in each box", "some pens in each box"),
              "C": ("{c} pens", "some pens")},
             _shop, lambda v: v["a"] * v["b"] - 3 * v["c"], 3),
    Template("fuel_cost",
             "A car uses {A} for every 100 km. It drives {B} on Saturday and {C} on Sunday. Fuel costs {D}. "
             "How much does the fuel for the weekend cost, in dollars?",
             {"A": ("{a} liters of fuel", "a certain amount of fuel"), "B": ("{b} km", "some distance"),
              "C": ("{c} km", "a further distance"), "D": ("${p} per liter", "a fixed price per liter")},
             _fuel, lambda v: v["a"] * (v["b"] + v["c"]) // 100 * v["p"], 3),
    Template("savings",
             "Maya earns {A} and saves {B} of it. After {C} she spends {D} of her savings on a bike. "
             "How many dollars of savings does she have left?",
             {"A": ("${a} per week", "a weekly wage"), "B": ("{p}%", "part"), "C": ("{w} weeks", "some weeks"),
              "D": ("${s}", "some")},
             _savings, lambda v: v["a"] * v["p"] // 100 * v["w"] - v["s"], 4),
    Template("school_buses",
             "A school has {A} with {B}. {C} of all the students go on a trip. Each bus holds {D}. "
             "How many buses are needed?",
             {"A": ("{k} classes", "several classes"), "B": ("{n} students each", "a number of students each"),
              "C": ("{p}%", "Some"), "D": ("{c} students", "a fixed number of students")},
             _buses, lambda v: -(-(v["k"] * v["n"] * v["p"] // 100) // v["c"]), 4),
    Template("bakery_boxes",
             "A baker bakes {A} of {B}. She keeps {C} for the shop window and packs the rest into boxes of {D}. "
             "How many boxes does she fill?",
             {"A": ("{t} trays", "several trays"), "B": ("{m} muffins", "muffins"), "C": ("{k} muffins", "some muffins"),
              "D": ("{b}", "equal size")},
             _bakery, lambda v: (v["t"] * v["m"] - v["k"]) // v["b"], 3),
    Template("garden_fence",
             "A rectangular garden is {A} long and {B}. Fencing costs {C}. "
             "How much does it cost, in dollars, to fence the whole garden?",
             {"A": ("{l} meters", "some meters"), "B": ("{w} meters wide", "a bit narrower than that"),
              "C": ("${c} per meter", "a fixed price per meter")},
             _fence, lambda v: 2 * (v["l"] + v["w"]) * v["c"], 3),
    Template("reading_days",
             "A book has {A}. Leo reads {B} a day for {C}, then speeds up to {D} a day. "
             "How many more days does he need to finish the book after he speeds up?",
             {"A": ("{p} pages", "a number of pages"), "B": ("{a} pages", "some pages"), "C": ("{d} days", "a few days"),
              "D": ("{b} pages", "more pages")},
             _reading, lambda v: (v["p"] - v["a"] * v["d"]) // v["b"], 3),
    Template("ticket_change",
             "Adult tickets cost {A} and child tickets cost {B}. A family buys {C} and {D}, "
             "and pays with {E}. How much change do they get, in dollars?",
             {"A": ("${a}", "a set price"), "B": ("${c}", "less"), "C": ("{x} adult tickets", "some adult tickets"),
              "D": ("{y} child tickets", "some child tickets"), "E": ("${m}", "a large banknote")},
             _tickets, lambda v: v["m"] - v["a"] * v["x"] - v["c"] * v["y"], 4),
    Template("tank_fill",
             "An empty tank holds {A}. Water flows in at {B} while a crack leaks {C}. "
             "How many minutes does it take to fill the tank?",
             {"A": ("{v} liters", "a certain number of liters"), "B": ("{r} liters per minute", "a steady rate"),
              "C": ("{l} liters per minute", "a little water every minute")},
             _tank, lambda v: v["v"] // (v["r"] - v["l"]), 2),
    Template("weekly_pay",
             "Ana works {A} a week at {B}. She also works {C} of overtime, paid at twice her normal rate. "
             "How many dollars does she earn in the week?",
             {"A": ("{h} regular hours", "regular hours"), "B": ("${w} per hour", "an hourly wage"),
              "C": ("{o} hours", "some hours")},
             _pay, lambda v: v["h"] * v["w"] + v["o"] * v["w"] * v["m"], 3),
]


def _render(t: Template, v: dict, vague_slot=None) -> str:
    fills = {s: (vague if s == vague_slot else exact.format(**v)) for s, (exact, vague) in t.phrases.items()}
    text = t.text.format(**fills)
    return text[0].upper() + text[1:]


def generate(per_template_complete: int, per_template_missing: int, seed: int) -> list[Item]:
    items = []
    for ti, t in enumerate(TEMPLATES):
        r = random.Random(seed * 1000 + 500 + ti)
        seen: set[str] = set()
        made = {"complete": 0, "missing": 0}
        while made["complete"] < per_template_complete or made["missing"] < per_template_missing:
            v = t.sample(r)
            if v is None:
                continue
            ans = t.answer(v)
            if made["complete"] < per_template_complete:
                kind, slot = "complete", None
            else:
                kind, slot = "missing", r.choice(sorted(t.phrases))
            q = _render(t, v, slot)
            if q in seen:
                continue
            seen.add(q)
            made[kind] += 1
            common = dict(item_id="", family="math", template_id=f"math_{t.name}", question=q, answer_type="number",
                          difficulty_param=t.n_ops, meta=dict(variables=v, removed_slot=slot))
            if kind == "complete":
                items.append(Item(source=f"math_gen:{t.name}:c{made['complete']}", correct=canon_number(ans),
                                  lure=None, error_cause_by_construction="multi_step", **common))
            else:
                common["meta"]["answer_if_complete"] = canon_number(ans)
                items.append(Item(source=f"math_gen:{t.name}:m{made['missing']}", correct=UNANSWERABLE,
                                  lure=None, error_cause_by_construction="missing_premise", **common))
    return items
