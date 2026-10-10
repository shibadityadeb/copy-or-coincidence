"""Experiments 7/8: a receiver agent answers after seeing a sender's answer.

Senders are Layer 0 samples (already graded), so every shown answer is a real independent answer whose
agent's distribution is known; the random-answer control shows a uniformly drawn candidate instead.
Experiment 8 (prereg/exp8_mechanism.md) adds three message types that pull reasoning and conclusion apart:
  steps_redacted   the sender's steps with its final answer masked and no final-answer line
  steps_flipped    the sender's real steps, followed by a different final answer
  steps_mismatched steps from another item of the same template, followed by the sender's real answer
"""
import json
import random
import re
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


MASK = "[...]"
_BOOL_WORDS = re.compile(r"\b(true|false|yes|no)\b|\b(does not|doesn't|do not)?\s*(logically\s+)?follows?\b", re.I)
_UNANS_WORDS = re.compile(r"unanswerable|cannot be (determined|answered|calculated)|can't be determined|"
                          r"not enough (info|information)|insufficient (info|information|data)|missing (info|information)", re.I)


def mask_answer(text: str, answer_norm: str | None, raw_final=None) -> str:
    """Hide the sender's final answer wherever it is stated in a reasoning step."""
    if answer_norm in (TRUE, FALSE):
        return _BOOL_WORDS.sub(MASK, text)
    if answer_norm == UNANSWERABLE:
        return _UNANS_WORDS.sub(MASK, text)
    if answer_norm and answer_norm != NA:
        num = re.escape(answer_norm)
        text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)          # 1,100 -> 1100 (thousands separators only)
        text = re.sub(rf"(?<![\d.]){num}(\.0+)?(?![\d])", MASK, text)
        if raw_final not in (None, ""):
            text = text.replace(str(raw_final), MASK)
    return text


def steps_of(row: dict) -> list[str]:
    return parse_output(row["raw_output"])["steps"] or []


def peer_text(row: dict | None, show: str, answer_norm: str | None = None, final_override: str | None = None,
              steps_row: dict | None = None) -> str:
    """The text appended after the question. `row` is the sender's Layer 0 row (None for the random-answer
    control). final_override replaces the shown final answer (steps_flipped); steps_row supplies the steps
    (steps_mismatched)."""
    if row is None:
        return f"Its final answer: {display(answer_norm)}"
    final = display(final_override) if final_override else display(row["answer_norm"], row.get("final"))
    if show == "answer":
        return f"Its final answer: {final}"
    steps = steps_of(steps_row or row)
    if show == "steps_redacted":
        steps = [mask_answer(st, row["answer_norm"], row.get("final")) for st in steps]
        return "\n".join(["Its reasoning:"] + [f"{i}. {st}" for i, st in enumerate(steps, 1)])
    lines = ["Its reasoning:"] + [f"{i}. {st}" for i, st in enumerate(steps, 1)] + [f"Its final answer: {final}"]
    return "\n".join(lines)


def candidates(item: Item, layer0_rows: list[dict]) -> list[str]:
    """Answer set for the random-answer control: every readable Layer 0 answer, plus the key and the lure."""
    c = {r["answer_norm"] for r in layer0_rows if r["answer_norm"]}
    c.add(item.correct)
    if item.lure:
        c.add(item.lure)
    return sorted(c)


def flip_target(item: Item, argued: str, cand: list[str], seed: int) -> str:
    """A different final answer to attach to the sender's steps (steps_flipped). Uniform over the item's other
    candidate answers; if there are none: true <-> false, the complete-problem answer for a missing-premise item,
    otherwise twice the argued number."""
    others = [a for a in cand if a != argued]
    if others:
        return random.Random(seed).choice(others)
    if argued in (TRUE, FALSE):
        return FALSE if argued == TRUE else TRUE
    if argued == UNANSWERABLE and item.meta.get("answer_if_complete"):
        return item.meta["answer_if_complete"]
    from cep.normalize import canon_number
    try:
        return canon_number(2 * float(argued))
    except ValueError:
        return UNANSWERABLE


def build_specs(cond: dict, items: list[Item], receiver: dict, layer0: dict, experiment_id: str,
                template: str, r_runs: int, pool_items: list[Item] | None = None) -> list[Spec]:
    """pool_items: the full item set, used to pick another item of the same template (steps_mismatched)."""
    specs = []
    sender = cond["sender"]
    show = cond["show"]
    same_template: dict[str, list[str]] = {}
    for it in pool_items or items:
        same_template.setdefault(it.template_id, []).append(it.item_id)
    for it in items:
        cand = None
        if sender == "random" or show == "steps_flipped":
            cand = candidates(it, [layer0[s][(it.item_id, k)] for s in layer0 for k in range(20)
                                   if (it.item_id, k) in layer0[s]])
        for r in range(r_runs):
            seed = stable_seed(receiver["agent_id"], it.item_id, cond["name"], str(r))
            if sender == "random":
                shown = random.Random(stable_seed("random_answer", it.item_id, str(r))).choice(cand)
                text, peer_ids, argued = peer_text(None, "answer", shown), [], None
            else:
                row = layer0[sender][(it.item_id, MESSAGE_SAMPLES[r])]
                argued = row["answer_norm"] or NA
                shown, peer_ids, extra = argued, [row["trial_id"]], {}
                if show == "steps_flipped":
                    shown = flip_target(it, argued, cand, stable_seed("flip", it.item_id, str(r)))
                    extra = dict(final_override=shown)
                elif show == "steps_mismatched":
                    pool = [i for i in same_template[it.template_id] if i != it.item_id]
                    other = random.Random(stable_seed("mismatch", it.item_id, str(r))).choice(pool)
                    other_row = layer0[sender][(other, MESSAGE_SAMPLES[r])]
                    peer_ids = peer_ids + [other_row["trial_id"]]
                    extra = dict(steps_row=other_row)
                text = peer_text(row, show, **extra)
            message = template.format(peer=text).strip()
            specs.append(Spec(
                trial_id=f"{experiment_id}:{receiver['agent_id']}:{it.item_id}:{cond['name']}:{r}",
                item=it, sample_index=r, seed=seed, user_text=f"{it.question}\n\n{message}",
                trial_fields=dict(protocol=cond["name"], condition="C" if sender == "random" else "B",
                                  interaction_round=1, previous_agent_output_available=True,
                                  peer_trial_ids=peer_ids, peer_content_shown=message, peer_answer_norm=shown,
                                  peer_argued_answer_norm=None if sender == "random" else argued)))
    return specs


def run_conditions(exp: dict, items: list[Item], run_id: str, make_backend, log=print) -> None:
    experiment_id = f"{exp['experiment_id']}-{run_id}"
    layer0 = {who: load_layer0(ROOT / p) for who, p in exp["layer0"].items()}
    template = (ROOT / "prompts" / f"{exp['peer_prompt']}.txt").read_text()
    backend = None
    for cond in exp["conditions"]:
        receiver = json.loads((ROOT / cond["receiver"]).read_text())
        backend = backend or make_backend(receiver, exp["backend"])
        specs = build_specs(cond, items, receiver, layer0, experiment_id, template, exp["R"], pool_items=items)
        out = ROOT / exp["out_dir"] / f"{experiment_id}__{cond['name']}__{receiver['agent_id']}.jsonl"
        log(f"{cond['name']}: {receiver['agent_id']} sees {cond['sender']} ({cond['show']}), "
            f"{len(specs)} answers -> {out}")
        execute(specs, receiver, backend, out, experiment_id, run_id, exp.get("batch_size", 64), log)
