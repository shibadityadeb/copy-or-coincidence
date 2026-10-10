import json

from cep.normalize import FALSE, TRUE, UNANSWERABLE
from coc.runner import ROOT, load_items
from coc.sequential import MASK, MESSAGE_SAMPLES, build_specs, load_layer0, mask_answer

EXP = json.loads((ROOT / "experiments/exp8_olmo.json").read_text())
ITEMS = load_items(ROOT / EXP["items"])
LAYER0 = {who: load_layer0(ROOT / p) for who, p in EXP["layer0"].items()}
TEMPLATE = (ROOT / "prompts/peer_v2.txt").read_text()
B = json.loads((ROOT / "configs/agents/olmo3_7b_B.json").read_text())
SUB = ITEMS[:40] + ITEMS[200:230] + ITEMS[400:430]


def specs(name):
    cond = next(c for c in EXP["conditions"] if c["name"] == name)
    return build_specs(cond, SUB, B, LAYER0, "t", TEMPLATE, EXP["R"], pool_items=ITEMS)


def test_mask_answer():
    assert mask_answer("so x = 30, total 130", "30") == f"so x = {MASK}, total 130"
    assert mask_answer("2.5 hours", "2.5") == f"{MASK} hours"
    assert mask_answer("it costs $1,100 in total", "1100") == f"it costs ${MASK} in total"
    assert MASK in mask_answer("Therefore the statement is true.", TRUE)
    assert "follow" not in mask_answer("It does not logically follow.", FALSE)
    assert "determined" not in mask_answer("It cannot be determined.", UNANSWERABLE)


def test_redacted_has_no_final_answer_line():
    for sp in specs("steps_redacted"):
        assert "Its final answer" not in sp.user_text and "Its reasoning:" in sp.user_text
        assert sp.trial_fields["peer_answer_norm"] == sp.trial_fields["peer_argued_answer_norm"]


def test_flipped_shows_a_different_answer_than_argued():
    for sp in specs("steps_flipped"):
        f = sp.trial_fields
        assert f["peer_answer_norm"] != f["peer_argued_answer_norm"]
        assert "Its reasoning:" in sp.user_text and "Its final answer:" in sp.user_text
    assert [s.user_text for s in specs("steps_flipped")] == [s.user_text for s in specs("steps_flipped")]


def test_mismatched_steps_come_from_another_item_of_same_template():
    for sp in specs("steps_mismatched"):
        f = sp.trial_fields
        assert len(f["peer_trial_ids"]) == 2
        other_item = f["peer_trial_ids"][1].split(":")[2]
        assert other_item != sp.item.item_id
        assert other_item in {i.item_id for i in ITEMS if i.template_id == sp.item.template_id}
        assert f["peer_answer_norm"] == (LAYER0["A"][(sp.item.item_id, MESSAGE_SAMPLES[sp.sample_index])]["answer_norm"] or "NA")


def test_seeds_unique_across_new_conditions():
    seeds = [sp.seed for n in ("steps_redacted", "steps_flipped", "steps_mismatched") for sp in specs(n)]
    assert len(seeds) == len(set(seeds))


def test_flip_fallbacks():
    from coc.sequential import flip_target
    it = SUB[0]
    assert flip_target(it, TRUE, [TRUE], 1) == FALSE
    assert flip_target(it, "30", ["30"], 1) == "60"
    assert flip_target(it, "30", ["30", "60", "20"], 1) in ("60", "20")
