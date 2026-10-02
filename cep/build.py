"""Build and freeze the item set: python -m cep.build  (writes datasets/cep_v1/)."""
import argparse
import collections
import hashlib
import json
import random
from pathlib import Path

from cep import checker, normalize, parse
from cep.generators import crt, false_ontology, math_word

# cep_v1 (frozen, superseded): drew 150 items from public datasets (ProntoQA 2022, GSM-Plus 2024).
# cep_v2: every item generated fresh, so no model's training data can contain it.
VERSIONS = {"cep_v1": 0, "cep_v2": 1}       # version -> seed


def make_items(version: str, seed: int) -> list:
    if version == "cep_v1":
        from cep.sources import gsm_plus, prontoqa
        return [*crt.generate(per_template=10, seed=seed), *prontoqa.load(n=50, seed=seed),
                *false_ontology.generate(n=50), *gsm_plus.load(n_missing=50, n_distractor=50, seed=seed)]
    from cep.sources import rg_syllogism
    return [
        *crt.generate(per_template=10, seed=seed, extra=True),                            # 200 trick (20 templates)
        *false_ontology.generate(n=100, extra=True),                                      # 100 false-world logic
        *rg_syllogism.generate(n_valid=50, n_invalid=50, seed=seed),                      # 100 syllogisms
        *math_word.generate(per_template_complete=10, per_template_missing=10, seed=seed), # 200 math
    ]


def build(out_dir: Path, version: str) -> dict:
    seed = VERSIONS[version]
    VERSION = version
    items = make_items(version, seed)
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
        sources=_sources(version),
        by_family=dict(collections.Counter(it.family for it in items)),
        by_template=dict(collections.Counter(it.template_id for it in items)),
        by_cause=dict(collections.Counter(it.error_cause_by_construction for it in items)),
        with_lure=sum(it.lure is not None for it in items),
    )
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    _write_audit(items, out_dir / "audit_sample.md", seed)
    return manifest


def _sources(version: str) -> dict:
    if version == "cep_v1":
        from cep.sources import gsm_plus, prontoqa
        return {gsm_plus.DATASET: gsm_plus.REVISION, prontoqa.DATASET: prontoqa.REVISION}
    from cep.sources import rg_syllogism
    return {"reasoning-gym (pip)": rg_syllogism.PACKAGE_VERSION, "generators": "cep/generators/*.py (this commit)"}


def _write_audit(items, path: Path, seed: int):
    """30 items (10 per family) for a human to check the answer key and lure by hand."""
    r = random.Random(seed)
    out = [f"# {items[0].item_id.rsplit('-', 2)[0]} hand audit (30 items)\n",
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
    ap.add_argument("--version", default="cep_v2", choices=sorted(VERSIONS))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    m = build(Path(a.out or f"datasets/{a.version}"), a.version)
    print(json.dumps(m, indent=2))
