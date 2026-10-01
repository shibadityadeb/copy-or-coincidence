import json
from pathlib import Path

from coc.backends import FakeBackend
from coc.runner import ROOT, dev_slice, load_items, run_independent
from coc.schema import stable_seed

ITEMS = load_items(ROOT / "datasets/cep_v1/items.jsonl")
AGENT = json.loads((ROOT / "configs/agents/qwen35_4b_A.json").read_text())


def rows(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines()]


def test_dev_slice_covers_every_template():
    s = dev_slice(ITEMS, 20)
    assert len(s) == 20 and len({i.template_id for i in s}) == 14


def test_seeds_stable_and_distinct():
    assert stable_seed("a", "b") == stable_seed("a", "b") != stable_seed("a", "c")


def test_rows_graded_and_complete(tmp_path):
    out = tmp_path / "t.jsonl"
    run_independent(ITEMS[:5], AGENT, FakeBackend(), k=3, out_path=out, experiment_id="t", run_id="r",
                    log=lambda *_: None)
    r = rows(out)
    assert len(r) == 15 and len({x["trial_id"] for x in r}) == 15
    assert all(x["parse_ok"] and x["checker_version"] and x["answer_norm"] for x in r)
    assert len({x["seed"] for x in r}) == 15


def test_resume_after_crash(tmp_path):
    out = tmp_path / "t.jsonl"
    be = FakeBackend()
    run_independent(ITEMS[:4], AGENT, be, k=2, out_path=out, experiment_id="t", run_id="r", log=lambda *_: None)
    lines = out.read_text().splitlines()
    out.write_text("\n".join(lines[:5]) + "\n" + lines[5][:30])        # lose 3 rows, leave a torn line
    be2 = FakeBackend()
    run_independent(ITEMS[:4], AGENT, be2, k=2, out_path=out, experiment_id="t", run_id="r", log=lambda *_: None)
    good = rows(out)
    assert be2.calls == 3 and len({x["trial_id"] for x in good}) == 8


def test_same_seeds_give_same_outputs(tmp_path):
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    for p in (a, b):
        run_independent(ITEMS[:6], AGENT, FakeBackend(), k=2, out_path=p, experiment_id="t", run_id="r",
                        log=lambda *_: None)
    assert [x["raw_output"] for x in rows(a)] == [x["raw_output"] for x in rows(b)]
