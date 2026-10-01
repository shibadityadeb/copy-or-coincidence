"""Turn a model's free-text final answer into a canonical string.

Two answers are "the same" for every metric in this project iff their canonical strings are equal,
so this file decides what counts as a shared wrong answer. Be conservative: when unsure, return None
(unparsed) rather than guess; a guessed merge would manufacture agreement.
"""
import re
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Optional

NORMALIZER_VERSION = "1"
UNANSWERABLE = "UNANSWERABLE"
TRUE, FALSE = "TRUE", "FALSE"

_UNANSWERABLE_RE = re.compile(
    r"\b(unanswerable|cannot be (determined|answered|calculated|computed|known)|"
    r"can(?:no|')t be (determined|answered|calculated|computed)|"
    r"(not|insufficient|missing) (enough )?(info|information|data)|"
    r"undetermined|indeterminate|unknown|none|n/a)\b",
    re.I,
)

_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
    "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12,
}
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?")


def canon_number(x) -> str:
    """Canonical text for a number: rounded to 4 decimals, no trailing zeros ('18', '2.5', '-0.75')."""
    q = Fraction(Decimal(str(x))) if not isinstance(x, Fraction) else x
    d = Decimal(q.numerator) / Decimal(q.denominator)
    d = d.quantize(Decimal("0.0001"))
    s = format(d.normalize(), "f")
    return "0" if s in ("-0", "") else s


def _to_number(tok: str) -> Optional[Fraction]:
    try:
        if "/" in tok:
            a, b = tok.split("/")
            return Fraction(Decimal(a)) / Fraction(Decimal(b)) if Decimal(b) != 0 else None
        return Fraction(Decimal(tok))
    except (InvalidOperation, ValueError, ZeroDivisionError):
        return None


def _clean(s: str) -> str:
    s = s.strip().strip("*`'\" ").rstrip(".")
    s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", s)          # 1,100 -> 1100
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s, flags=re.I)  # 2nd -> 2
    return s


def parse_number(s: str) -> Optional[str]:
    s = _clean(s)
    nums = _NUM_RE.findall(s)
    if not nums:
        words = [w for w in re.findall(r"[a-z]+", s.lower()) if w in _WORDS]
        return canon_number(_WORDS[words[0]]) if len(set(words)) == 1 else None
    values = {canon_number(v) for v in (_to_number(n) for n in nums) if v is not None}
    # Several different numbers ("16 - 3 - 4 = 9") is not a final answer: refuse to pick one.
    return values.pop() if len(values) == 1 else None


def parse_bool(s: str) -> Optional[str]:
    t = _clean(s).lower()
    if t in ("a", "a)", "(a)"):
        return TRUE
    if t in ("b", "b)", "(b)"):
        return FALSE
    has_t = re.search(r"\b(true|yes)\b", t) is not None
    has_f = re.search(r"\b(false|no)\b", t) is not None
    if has_t != has_f:
        return TRUE if has_t else FALSE
    return None


def normalize(final, answer_type: str) -> Optional[str]:
    """Canonical answer, UNANSWERABLE, or None when the text can't be read as an answer."""
    if final is None:
        return None
    if isinstance(final, bool):
        return TRUE if final else FALSE
    if isinstance(final, (int, float)) and answer_type == "number":
        return canon_number(final)
    s = str(final).strip()
    if not s:
        return None
    if answer_type == "bool":
        b = parse_bool(s)
        if b is not None:
            return b
        return UNANSWERABLE if _UNANSWERABLE_RE.search(s) else None
    # number: a clean number wins; otherwise an explicit "can't be answered"; otherwise one number in prose
    if _NUM_RE.fullmatch(_clean(s).lstrip("$").rstrip("%")):
        return parse_number(s)
    if _UNANSWERABLE_RE.search(s):
        return UNANSWERABLE
    return parse_number(s)
