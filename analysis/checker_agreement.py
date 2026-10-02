"""Agreement between the checker and a human reading of 150 Layer 0 replies.

python analysis/checker_agreement.py validation/checker_label_sheet.md [labels.txt]
Reader answers come from the `answer:` lines of the sheet, or from a labels file with lines "n: answer"
(e.g. validation/llm_reader_labels.txt from the blind LLM reader). Each human answer goes through the same normaliser, and its error class is derived with the
same rules, so what is tested is the checker's reading of the reply (parsing + normalisation), not the rules.
Targets (field guide §3): correct/incorrect >= 0.95, error class >= 0.85.
"""
import json
import re
import sys
from pathlib import Path

from cep.checker import check_final
from cep.schema import Item

ROOT = Path(__file__).resolve().parent.parent


def human_answers(sheet: Path, labels_file: str | None = None) -> dict[int, str]:
    out = {}
    extra = Path(labels_file) if labels_file else ROOT / "validation/human_labels.txt"
    if extra.exists():
        for line in extra.read_text().splitlines():
            if m := re.match(r"\s*(\d+)\s*[:.)-]\s*(.+)", line):
                out[int(m.group(1))] = m.group(2).strip()
    for n, ans in re.findall(r"^## (\d+)\n.*?^answer:[ \t]*([^\n]*)$", sheet.read_text(), re.S | re.M):
        if ans.strip():
            out.setdefault(int(n), ans.strip())
    return out


def main(sheet_path: str, labels_file: str | None = None):
    key = json.loads((ROOT / "validation/checker_label_key.json").read_text())
    items = {i.item_id: i for i in (Item.model_validate_json(l) for l in
                                    (ROOT / "datasets/cep_v2/items.jsonl").read_text().splitlines())}
    human = human_answers(Path(sheet_path), labels_file)
    done, agree_c, agree_cls, disagreements = 0, 0, 0, []
    for k in key:
        if k["n"] not in human:
            continue
        h = human[k["n"]]
        hc = check_final(items[k["task_id"]], None if h.lower() == "unclear" else h)
        done += 1
        same_c = hc.correct == k["checker_correct"]
        same_cls = hc.error_class == k["checker_error_class"]
        agree_c += same_c
        agree_cls += same_cls
        if not (same_c and same_cls):
            disagreements.append((k["n"], k["template_id"], h, hc.answer_norm, k["checker_answer_norm"],
                                  hc.error_class, k["checker_error_class"]))
    if not done:
        print("no human answers yet")
        return
    print(f"labelled {done}/{len(key)}")
    print(f"correct/incorrect agreement: {agree_c}/{done} = {agree_c / done:.3f}  (target >= 0.95)")
    print(f"error-class agreement:       {agree_cls}/{done} = {agree_cls / done:.3f}  (target >= 0.85)")
    for d in disagreements:
        print(f"  #{d[0]} {d[1]}: human '{d[2]}' -> {d[3]} ({d[5]}) | checker {d[4]} ({d[6]})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "validation/checker_label_sheet.md",
         sys.argv[2] if len(sys.argv) > 2 else None)
