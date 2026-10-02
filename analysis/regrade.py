"""Re-grade stored replies with the current checker, without touching the original files.

python analysis/regrade.py outputs/layer0_olmo/layer0_olmo-run1__olmo3-7b-A.jsonl ...
Writes <name>.regraded-<checker_version>.jsonl next to each input. The previous grading fields are kept
as prev_* columns, so both scorings can be reported (field guide: bump checker_version, keep old columns).
"""
import json
import sys
from pathlib import Path

from cep.checker import CHECKER_VERSION, check_raw
from cep.schema import Item

ROOT = Path(__file__).resolve().parent.parent
GRADED = ["answer_norm", "correct", "lure_hit", "error_class", "checker_version"]


def main(paths):
    items = {}
    for v in ("cep_v1", "cep_v2"):
        for line in (ROOT / "datasets" / v / "items.jsonl").read_text().splitlines():
            it = Item.model_validate_json(line)
            items[it.item_id] = it
    for p in (Path(x).resolve() for x in paths):
        out = p.with_name(p.stem + f".regraded-{CHECKER_VERSION}.jsonl")
        changed = 0
        with out.open("w") as f:
            for line in p.read_text().splitlines():
                row = json.loads(line)
                new = check_raw(items[row["task_id"]], row["raw_output"])
                for k in GRADED:
                    row[f"prev_{k}"] = row[k]
                    row[k] = new[k]
                changed += row["prev_correct"] != row["correct"]
                f.write(json.dumps(row) + "\n")
        print(f"{out.relative_to(ROOT)}: {changed} answers changed correct/incorrect")


if __name__ == "__main__":
    main(sys.argv[1:])
