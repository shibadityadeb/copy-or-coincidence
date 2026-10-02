"""Programmatic grading. No LLM judge anywhere in the label path (field guide §3)."""
import hashlib
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

from cep.normalize import FALSE, UNANSWERABLE, normalize
from cep.parse import parse_output
from cep.schema import Item

ErrorClass = Literal["correct", "lure", "unanswerable_answered", "false_unanswerable",
                     "other_wrong", "format_error"]

_HERE = Path(__file__).parent
CHECKER_VERSION = hashlib.sha256(
    b"".join((_HERE / f).read_bytes() for f in ("normalize.py", "parse.py", "checker.py"))
).hexdigest()[:12]


class Check(BaseModel):
    answer_norm: Optional[str]
    correct: bool
    lure_hit: bool
    error_class: ErrorClass


# "Does it logically follow?": a conclusion that cannot be determined from the premises does not follow,
# so "unanswerable" means "No". Decided 2026-10-02 after Layer 0 showed the model using it that way
# (1,042 of 2,000 replies on invalid syllogisms); see docs/RESEARCH_LOG.md. Not applied to other bool items,
# where every needed fact is stated and "unanswerable" is a real error.
FOLLOWS_TEMPLATES = {"rg_syllogism"}


def check_final(item: Item, final) -> Check:
    ans = normalize(final, item.answer_type)
    if ans == UNANSWERABLE and item.template_id in FOLLOWS_TEMPLATES:
        ans = FALSE
    if ans is None:
        return Check(answer_norm=None, correct=False, lure_hit=False, error_class="format_error")
    if ans == item.correct:
        return Check(answer_norm=ans, correct=True, lure_hit=False, error_class="correct")
    lure_hit = item.lure is not None and ans == item.lure
    if lure_hit:
        cls = "lure"
    elif item.correct == UNANSWERABLE:
        cls = "unanswerable_answered"
    elif ans == UNANSWERABLE:
        cls = "false_unanswerable"
    else:
        cls = "other_wrong"
    return Check(answer_norm=ans, correct=False, lure_hit=lure_hit, error_class=cls)


def check_raw(item: Item, raw_output: str) -> dict:
    """Parse + grade one raw model output; returns the fields that go on a JSONL trial row."""
    p = parse_output(raw_output)
    c = check_final(item, p["final"])
    return dict(parse_ok=p["parse_ok"], parse_how=p["how"], final=p["final"],
                confidence=p["confidence"], n_steps=len(p["steps"]) if p["steps"] else None,
                checker_version=CHECKER_VERSION, **c.model_dump())
