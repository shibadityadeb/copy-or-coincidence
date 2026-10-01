"""Logic family, false-world half (PrOntoQA-OOD style). The rules contradict real-world knowledge, so
the lure is the common-sense answer and an error means the prior overrode the stated premises."""
from cep.normalize import FALSE, TRUE
from cep.schema import Item
from cep.sources.prontoqa import logic_question

# entity, false category, a broader category, property the rules assert (false in reality),
# property the rules deny (true in reality)
CASES = [
    ("whale", "fish", "animal", "cold-blooded", "warm-blooded"),
    ("penguin", "mammal", "animal", "furry", "feathered"),
    ("bat", "bird", "animal", "feathered", "furry"),
    ("spider", "insect", "creature", "six-legged", "eight-legged"),
    ("dolphin", "fish", "animal", "gilled", "air-breathing"),
    ("shark", "mammal", "animal", "warm-blooded", "cold-blooded"),
    ("snake", "mammal", "animal", "furry", "scaly"),
    ("eagle", "reptile", "animal", "cold-blooded", "warm-blooded"),
    ("cow", "carnivore", "animal", "meat-eating", "plant-eating"),
    ("lemon", "candy", "food", "sweet", "sour"),
    ("copper wire", "insulator", "material", "non-conductive", "conductive"),
    ("ice cube", "stove", "object", "hot", "cold"),
    ("crocodile", "bird", "animal", "feathered", "scaly"),
]
NAMES = ["Max", "Stella", "Sam", "Rex", "Wren", "Polly", "Fred", "Sally"]


def _a(noun: str) -> str:
    return ("an " if noun[0] in "aeiou" else "a ") + noun


def generate(n: int) -> list[Item]:
    items = []
    k = 0
    for depth in (1, 2):
        for negated in (False, True):
            for ci, (ent, cat, broad, fake_prop, real_prop) in enumerate(CASES):
                name = NAMES[k % len(NAMES)]
                other = CASES[(ci + 5) % len(CASES)]          # an unrelated true fact as a distractor
                carrier = cat if depth == 1 else broad
                rules = [f"Every {ent} is {_a(cat)}."]
                if depth == 2:
                    rules.append(f"Every {cat} is {_a(broad)}.")
                if negated:
                    rules.append(f"Every {carrier} is not {real_prop}.")
                    statement, correct, lure = f"{name} is {real_prop}.", FALSE, TRUE
                else:
                    rules.append(f"Every {carrier} is {fake_prop}.")
                    statement, correct, lure = f"{name} is {fake_prop}.", TRUE, FALSE
                rules.insert(1, f"Every {other[0]} is {other[4]}.")
                context = " ".join(rules + [f"{name} is {_a(ent)}."])
                items.append(Item(
                    item_id="", family="logic", source=f"false_ontology_gen:{ent}:{depth}:{int(negated)}",
                    template_id="false_ontology", question=logic_question(context, statement),
                    answer_type="bool", correct=correct, lure=lure,
                    error_cause_by_construction="prior_override", difficulty_param=depth,
                    meta={"ontology": "false", "entity": ent, "negated": negated}))
                k += 1
    return items[:n]
