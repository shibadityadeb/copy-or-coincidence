"""Logic family: syllogisms from Reasoning Gym (Apache-2.0, first released Feb 2025), generated fresh from a seed.
Real-world words in nonsense relations ("All engineers are whales") pit the stated logic against common sense."""
import reasoning_gym

from cep.normalize import FALSE, TRUE
from cep.schema import Item

PACKAGE_VERSION = "0.1.25"


def generate(n_valid: int, n_invalid: int, seed: int) -> list[Item]:
    pool = reasoning_gym.create_dataset("syllogism", size=20 * (n_valid + n_invalid), seed=seed)
    want = {True: n_valid, False: n_invalid}
    items, seen = [], set()
    for e in pool:
        valid = bool(e["metadata"]["is_valid"])
        assert (e["answer"] == "Yes") == valid
        if want[valid] == 0 or e["question"] in seen:
            continue
        # "Some X are Y" drawn from All/No premises is valid only if X exists (Aristotelian existential import);
        # modern logic says it does not follow. Drop those so every answer key holds under both conventions.
        if valid and e["metadata"]["conclusion"].startswith("Some"):
            continue
        seen.add(e["question"])
        want[valid] -= 1
        items.append(Item(
            item_id="", family="logic", source=f"reasoning_gym:syllogism:{seed}:{e['metadata']['source_index']}",
            template_id="rg_syllogism", question=e["question"], answer_type="bool",
            correct=TRUE if valid else FALSE, lure=None, error_cause_by_construction="deduction_slip",
            difficulty_param=None, meta={"type": e["metadata"]["type"], "conclusion": e["metadata"]["conclusion"]}))
        if not any(want.values()):
            break
    assert not any(want.values()), f"not enough syllogisms: {want}"
    return items
