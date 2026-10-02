import json

from coc.backends import FakeBackend
from coc.runner import ROOT, load_items
from coc.sequential import MESSAGE_SAMPLES, build_specs, candidates, load_layer0, run_conditions

EXP = json.loads((ROOT / "experiments/exp7_olmo.json").read_text())
ITEMS = load_items(ROOT / EXP["items"])[:12] + load_items(ROOT / EXP["items"])[300:306]
LAYER0 = {who: load_layer0(ROOT / p) for who, p in EXP["layer0"].items()}
TEMPLATE = (ROOT / "prompts/peer_v1.txt").read_text()
B = json.loads((ROOT / "configs/agents/olmo3_7b_B.json").read_text())


def specs(name):
    cond = next(c for c in EXP["conditions"] if c["name"] == name)
    return build_specs(cond, ITEMS, B, LAYER0, "t", TEMPLATE, EXP["R"])


def test_shown_answers_are_layer0_message_samples():
    for sp in specs("seq_steps"):
        row = LAYER0["A"][(sp.item.item_id, MESSAGE_SAMPLES[sp.sample_index])]
        assert sp.trial_fields["peer_trial_ids"] == [row["trial_id"]]
        assert sp.trial_fields["peer_answer_norm"] == (row["answer_norm"] or "NA")
        assert sp.user_text.startswith(sp.item.question)
        assert "Another agent solved this problem independently." in sp.user_text
        assert "Its reasoning:" in sp.user_text and "Its final answer:" in sp.user_text


def test_answer_only_shows_no_reasoning_and_same_answers_as_steps():
    a, s = specs("seq_answer"), specs("seq_steps")
    assert all("Its reasoning:" not in sp.user_text for sp in a)
    assert [x.trial_fields["peer_answer_norm"] for x in a] == [x.trial_fields["peer_answer_norm"] for x in s]


def test_messages_never_use_null_samples():
    assert min(MESSAGE_SAMPLES) >= 10       # samples 0-9 estimate the null distributions


def test_random_answers_come_from_candidates_and_are_reproducible():
    one, two = specs("random_answer"), specs("random_answer")
    assert [x.user_text for x in one] == [x.user_text for x in two]
    for sp in one:
        rows = [LAYER0[w][(sp.item.item_id, k)] for w in "AB" for k in range(20)]
        assert sp.trial_fields["peer_answer_norm"] in candidates(sp.item, rows)
        assert sp.trial_fields["condition"] == "C" and sp.trial_fields["peer_trial_ids"] == []


def test_seeds_differ_across_conditions_and_runs():
    seeds = [sp.seed for n in ("seq_steps", "seq_answer", "random_answer") for sp in specs(n)]
    assert len(set(seeds)) == len(seeds)


def test_end_to_end_with_fake_backend(tmp_path):
    exp = dict(EXP, out_dir=str(tmp_path))      # an absolute out_dir overrides the ROOT prefix
    run_conditions(exp, ITEMS, "r1", lambda agent, backend: FakeBackend(), log=lambda *a: None)
    files = sorted(tmp_path.glob("*.jsonl"))
    assert len(files) == 4
    for f in files:
        rows = [json.loads(l) for l in f.read_text().splitlines()]
        assert len(rows) == len(ITEMS) * EXP["R"]
        assert all(r["previous_agent_output_available"] and r["interaction_round"] == 1 for r in rows)
        assert all(r["peer_answer_norm"] for r in rows)
