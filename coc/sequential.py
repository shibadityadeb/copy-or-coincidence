"""Experiment 7: a receiver agent answers after seeing a sender's answer (prereg/exp7_sequential_exposure.md).

Senders are Layer 0 samples (already graded), so every shown answer is a real independent answer whose
agent's distribution is known; the random-answer control shows a uniformly drawn candidate instead.
"""
import json
import random
from pathlib import Path

from cep.normalize import FALSE, TRUE, UNANSWERABLE
from cep.parse import parse_output
from cep.schema import Item
from coc.runner import ROOT, Spec, execute
from coc.schema import stable_seed

MESSAGE_SAMPLES = range(10, 15)      # Layer 0 samples shown as messages; samples 0-9 estimate the nulls
NA = "NA"


def load_layer0(path: Path) -> dict[tuple[str, int], dict]:
    """(item_id, sample_index) -> Layer 0 row."""
    rows = {}
    for line in path.read_text().splitlines():
        r = json.loads(line)
        rows[(r["task_id"], r["sample_index"])] = r
    return rows


def display(answer_norm: str | None, raw_final=None) -> str:
    """How a final answer is written in the message: the sender's own text if it gave one."""
    if raw_final not in (None, ""):
        return str(raw_final)
    return {TRUE: "true", FALSE: "false", UNANSWERABLE: "unanswerable"}.get(answer_norm, answer_norm or "(none given)")


def peer_text(row: dict | None, show: str, answer_norm: str | None = None) -> str:
    """The text appended after the question. `row` is a Layer 0 row (or None for the random-answer control)."""
    if row is None:
        return f"Its final answer: {display(answer_norm)}"
    final = display(row["answer_norm"], row.get("final"))
    if show == "answer":
        return f"Its final answer: {final}"
    steps = parse_output(row["raw_output"])["steps"] or []
    lines = ["Its reasoning:"] + [f"{i}. {st}" for i, st in enumerate(steps, 1)] + [f"Its final answer: {final}"]
    return "\n".join(lines)


def candidates(item: Item, layer0_rows: list[dict]) -> list[str]:
    """Answer set for the random-answer control: every readable Layer 0 answer, plus the key and the lure."""
    c = {r["answer_norm"] for r in layer0_rows if r["answer_norm"]}
    c.add(item.correct)
    if item.lure:
        c.add(item.lure)
    return sorted(c)


def build_specs(cond: dict, items: list[Item], receiver: dict, layer0: dict, experiment_id: str,
                template: str, r_runs: int) -> list[Spec]:
    specs = []
    sender = cond["sender"]
    for it in items:
        cand = None
        if sender == "random":
            cand = candidates(it, [layer0[s][(it.item_id, k)] for s in layer0 for k in range(20)
                                   if (it.item_id, k) in layer0[s]])
        for r in range(r_runs):
            seed = stable_seed(receiver["agent_id"], it.item_id, cond["name"], str(r))
            if sender == "random":
                shown = random.Random(stable_seed("random_answer", it.item_id, str(r))).choice(cand)
                text, peer_ids = peer_text(None, "answer", shown), []
            else:
                row = layer0[sender][(it.item_id, MESSAGE_SAMPLES[r])]
                shown = row["answer_norm"] or NA
                text, peer_ids = peer_text(row, cond["show"]), [row["trial_id"]]
            message = template.format(peer=text).strip()
            specs.append(Spec(
                trial_id=f"{experiment_id}:{receiver['agent_id']}:{it.item_id}:{cond['name']}:{r}",
                item=it, sample_index=r, seed=seed, user_text=f"{it.question}\n\n{message}",
                trial_fields=dict(protocol=cond["name"], condition="C" if sender == "random" else "B",
                                  interaction_round=1, previous_agent_output_available=True,
                                  peer_trial_ids=peer_ids, peer_content_shown=message, peer_answer_norm=shown)))
    return specs


def run_conditions(exp: dict, items: list[Item], run_id: str, make_backend, log=print) -> None:
    experiment_id = f"{exp['experiment_id']}-{run_id}"
    layer0 = {who: load_layer0(ROOT / p) for who, p in exp["layer0"].items()}
    template = (ROOT / "prompts" / f"{exp['peer_prompt']}.txt").read_text()
    backend = None
    for cond in exp["conditions"]:
        receiver = json.loads((ROOT / cond["receiver"]).read_text())
        backend = backend or make_backend(receiver, exp["backend"])
        specs = build_specs(cond, items, receiver, layer0, experiment_id, template, exp["R"])
        out = ROOT / exp["out_dir"] / f"{experiment_id}__{cond['name']}__{receiver['agent_id']}.jsonl"
        log(f"{cond['name']}: {receiver['agent_id']} sees {cond['sender']} ({cond['show']}), "
            f"{len(specs)} answers -> {out}")
        execute(specs, receiver, backend, out, experiment_id, run_id, exp.get("batch_size", 64), log)
