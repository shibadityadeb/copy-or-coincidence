"""Lure family: classic trick-question structures (CRT, Alice-in-Wonderland, harmonic mean, fencepost)
re-instantiated with fresh numbers and wording, so the answer can't be recalled and the intuitive
wrong answer (the lure) is known exactly."""
import random
from fractions import Fraction

from cep.normalize import canon_number
from cep.schema import Item

ORD = {1: "1st", 2: "2nd", 3: "3rd"}


def ordinal(k: int) -> str:
    return ORD.get(k, f"{k}th")


def bat_ball(r: random.Random):
    a, b = r.choice([("laptop", "laptop case"), ("bicycle", "helmet"), ("phone", "charger"),
                     ("guitar", "guitar strap"), ("camera", "camera bag"), ("sofa", "cushion"),
                     ("tent", "sleeping mat"), ("drone", "spare battery"), ("printer", "ink pack")])
    diff = r.choice([100, 200, 500, 1000])
    x = r.randrange(5, 100, 5)
    q = (f"A {a} and a {b} cost ${diff + 2 * x} in total. The {a} costs ${diff} more than the {b}. "
         f"How much does the {b} cost, in dollars?")
    return q, x, 2 * x, dict(diff=diff)


def widgets(r: random.Random):
    n, m = r.randint(3, 12), r.randint(40, 250)
    who, thing = r.choice([("machines", "widgets"), ("printers", "posters"), ("bakers", "cakes"),
                           ("robots", "boxes"), ("looms", "rugs")])
    q = (f"If {n} {who} take {n} minutes to make {n} {thing}, how many minutes would it take "
         f"{m} {who} to make {m} {thing}?")
    return q, n, m, dict(n=n, m=m)


def doubling(r: random.Random):
    days = r.randrange(12, 62, 2)
    what, where = r.choice([("A patch of lily pads", "lake"), ("A patch of algae", "pond"),
                            ("A colony of mould", "slice of bread"), ("A bacteria culture", "petri dish")])
    q = (f"{what} doubles in size every day. It takes {days} days to cover the whole {where}. "
         f"How many days does it take to cover half of the {where}?")
    return q, days - 1, days // 2, dict(days=days)


def overtaking(r: random.Random):
    k = r.randint(2, 11)
    race = r.choice(["a running race", "a swimming race", "a cycling race", "a marathon"])
    q = (f"In {race}, you overtake the person in {ordinal(k)} place. What place are you in now? "
         f"Answer with the place as a number.")
    return q, k, k - 1, dict(k=k)


def siblings(r: random.Random):
    name = r.choice(["Alice", "Priya", "Maria", "Aiko", "Fatima", "Chloe", "Nadia", "Elena"])
    brothers, sisters = r.randint(1, 6), r.randint(1, 6)
    b_word = "brother" if brothers == 1 else "brothers"
    s_word = "sister" if sisters == 1 else "sisters"
    q = f"{name} has {brothers} {b_word} and {sisters} {s_word}. How many sisters does {name}'s brother have?"
    return q, sisters + 1, sisters, dict(brothers=brothers, sisters=sisters)


def percent_round_trip(r: random.Random):
    price, p = r.choice([200, 400, 500, 800, 1000, 1600]), r.choice([10, 20, 30, 40, 50])
    item = r.choice(["jacket", "watch", "chair", "lamp", "backpack", "kettle"])
    q = (f"A {item} costs ${price}. Its price is increased by {p}%, and then the new price is "
         f"decreased by {p}%. What is the final price, in dollars?")
    return q, Fraction(price) * (1 - Fraction(p, 100) ** 2), price, dict(price=price, p=p)


HM_PAIRS = [(30, 60), (20, 60), (40, 60), (12, 24), (60, 90), (45, 90), (40, 120), (36, 45),
            (60, 120), (15, 30), (30, 45), (70, 105), (24, 40), (50, 75)]


def average_speed(r: random.Random):
    v1, v2 = r.choice(HM_PAIRS)
    if r.random() < 0.5:
        v1, v2 = v2, v1
    who = r.choice(["A car", "A cyclist", "A bus", "A delivery van"])
    q = (f"{who} travels from town A to town B at {v1} km/h and returns along the same road at "
         f"{v2} km/h. What is the average speed for the whole round trip, in km/h?")
    return q, Fraction(2 * v1 * v2, v1 + v2), Fraction(v1 + v2, 2), dict(v1=v1, v2=v2)


def fence_posts(r: random.Random):
    gap = r.choice([2, 3, 4, 5, 10])
    length = gap * r.randint(6, 40)
    thing, unit = r.choice([("fence", "posts"), ("row of trees", "trees"), ("street", "lamp posts")])
    q = (f"A straight {thing} is {length} meters long, with {unit} placed every {gap} meters, "
         f"including one at each end. How many {unit} are there?")
    return q, length // gap + 1, length // gap, dict(length=length, gap=gap)


def stairs(r: random.Random):
    while True:  # keep the proportional-thinking lure a whole number so it is a crisp target
        per_floor, k, m = r.randint(6, 20), r.randint(3, 5), r.randint(6, 12)
        t = per_floor * (k - 1)
        if (t * m) % k == 0:
            break
    q = (f"It takes {t} seconds to walk up the stairs from the 1st floor to the {ordinal(k)} floor. "
         f"At the same pace, how many seconds does it take to walk from the 1st floor to the "
         f"{ordinal(m)} floor?")
    return q, per_floor * (m - 1), Fraction(t * m, k), dict(per_floor=per_floor, k=k, m=m)


def clock_strikes(r: random.Random):
    while True:  # whole-number lure, as in stairs()
        a, gap, b = r.randint(3, 6), r.randint(1, 4), r.randint(7, 12)
        t = gap * (a - 1)
        if (t * b) % a == 0:
            break
    q = (f"A clock strikes once for each hour, with equal pauses between strikes. It takes {t} seconds "
         f"to strike {a} o'clock (from the first strike to the last). How many seconds does it take "
         f"to strike {b} o'clock?")
    return q, gap * (b - 1), Fraction(t * b, a), dict(a=a, gap=gap, b=b)


TEMPLATES = [bat_ball, widgets, doubling, overtaking, siblings, percent_round_trip, average_speed,
             fence_posts, stairs, clock_strikes]


def generate(per_template: int, seed: int) -> list[Item]:
    items = []
    for ti, fn in enumerate(TEMPLATES):
        r = random.Random(seed * 1000 + ti)
        seen: set[str] = set()
        while len(seen) < per_template:
            q, correct, lure, params = fn(r)
            c, l = canon_number(correct), canon_number(lure)
            if q in seen or c == l:
                continue
            seen.add(q)
            items.append(Item(
                item_id="", family="lure", source=f"crt_gen:{fn.__name__}:{len(seen)}",
                template_id=fn.__name__, question=q, answer_type="number", correct=c, lure=l,
                error_cause_by_construction="intuitive_lure", difficulty_param=None, meta=params))
    return items
