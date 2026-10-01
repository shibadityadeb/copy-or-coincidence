"""One test question ("item") in the Correlated Error Probe."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

Family = Literal["lure", "logic", "math"]
AnswerType = Literal["number", "bool"]


class Item(BaseModel):
    item_id: str
    family: Family
    source: str                 # where it came from, e.g. "gsm_plus:test:1234" or "crt_gen:bat_ball:3"
    template_id: str            # items sharing a template share structure (used as a random effect later)
    question: str
    answer_type: AnswerType
    correct: str                # canonical answer (output of cep.normalize)
    lure: Optional[str]         # canonical tempting-wrong answer fixed in advance, or None
    error_cause_by_construction: str
    difficulty_param: Optional[float] = None
    meta: dict = Field(default_factory=dict)
