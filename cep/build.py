"""Build and freeze the item set: python -m cep.build  (writes datasets/cep_v1/)."""
import argparse
import collections
import hashlib
import json
import random
from pathlib import Path

from cep import checker, normalize, parse
from cep.generators import crt, false_ontology
from cep.sources import gsm_plus, prontoqa

VERSION = "cep_v1"
SEED = 0


def build(out_dir: Path, seed: int = SEED) -> dict:
    groups = [
        crt.generate(per_template=10, seed=seed),                    # 100 lure items
        prontoqa.load(n=50, seed=seed),                              # 50 fictional logic
        false_ontology.generate(n=50),                               # 50 false-world logic
        gsm_plus.load(n_missing=50, n_distractor=50, seed=seed),     # 100 math
    ]
    items = [it for g in groups for it in g]
    counters = collections.Counter()
    for it in items:
        counters[it.family] += 1
        it.item_id = f"{VERSION}-{it.family}-{counters[it.family]:03d}"

    assert len({it.question for it in items}) == len(items), "duplicate questions"
    assert all(it.correct != it.lure for it in items), "lure equals correct answer"

    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [it.model_dump_json() for it in items]
    body = ("\n".join(lines) + "\n").encode()
    (out_dir / "items.jsonl").write_bytes(body)

    manifest = dict(
        version=VERSION, seed=seed, n_items=len(items),
        items_sha256=hashlib.sha256(body).hexdigest(),
        normalizer_version=normalize.NORMALIZER_VERSION, parser_version=parse.PARSER_VERSION,
        checker_version=checker.CHECKER_VERSION,
        sources={gsm_plus.DATASET: gsm_plus.REVISION, prontoqa.DATASET: prontoqa.REVISION},
        by_family=dict(collections.Counter(it.family for it in items)),
        by_template=dict(collections.Counter(it.template_id for it in items)),
        by_cause=dict(collections.Counter(it.error_cause_by_construction for it in items)),
        with_lure=sum(it.lure is not None for it in items),
    )
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    _write_audit(items, out_dir / "audit_sample.md", seed)
    return manifest


def _write_audit(items, path: Path, seed: int):
    """30 items (10 per family) for a human to check the answer key and lure by hand."""
    r = random.Random(seed)
    out = ["# cep_v1 hand audit (30 items)\n",
           "For each item tick: answer key correct? lure sensible? question unambiguous? "
           "Note any problem under the item.\n"]
    for fam in ("lure", "logic", "math"):
        pool = [it for it in items if it.family == fam]
        for it in r.sample(pool, 10):
            out += [f"\n## {it.item_id}  ·  {it.template_id}  ·  {it.source}\n",
                    "```text", it.question, "```",
                    f"- correct: **{it.correct}**  ·  lure: **{it.lure}**  ·  cause: {it.error_cause_by_construction}",
                    "- [ ] key correct  - [ ] lure sensible  - [ ] unambiguous", "- notes: "]
    path.write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=f"datasets/{VERSION}")
    m = build(Path(ap.parse_args().out))
    print(json.dumps(m, indent=2))
