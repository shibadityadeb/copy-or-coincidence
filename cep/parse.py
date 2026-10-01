"""Extract {"steps": [...], "final": ..., "confidence": ...} from raw model output."""
import json
import re
from typing import Any, Optional

PARSER_VERSION = "1"

_THINK_RE = re.compile(r"<think>.*?</think>", re.S | re.I)
_FINAL_RE = re.compile(r'"final"\s*:\s*("(?:[^"\\]|\\.)*"|-?[\d.]+|true|false|null)', re.I)
_PROSE_RE = re.compile(r"final answer\s*(?:is)?\s*[:=]?\s*(.+)", re.I)


def _json_objects(text: str):
    """Yield balanced {...} substrings, last one first."""
    spans, stack = [], []
    in_str = esc = False
    for i, ch in enumerate(text):
        if in_str:
            esc = (ch == "\\") and not esc
            if ch == '"' and not esc:
                in_str = False
            continue
        if ch == '"' and stack:
            in_str = True
        elif ch == "{":
            stack.append(i)
        elif ch == "}" and stack:
            start = stack.pop()
            if not stack:
                spans.append((start, i + 1))
    for s, e in reversed(spans):
        yield text[s:e]


def parse_output(raw: str) -> dict[str, Any]:
    """Returns dict(parse_ok, how, final, confidence, steps). parse_ok is True only for real JSON."""
    text = _THINK_RE.sub("", raw or "")
    # an unterminated <think> means the model ran out of tokens while thinking
    if "<think>" in text.lower():
        text = text[text.lower().rfind("</think>") + 8:] if "</think>" in text.lower() else ""
    for cand in _json_objects(text):
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "final" in obj:
            steps = obj.get("steps")
            return dict(parse_ok=True, how="json", final=obj.get("final"),
                        confidence=_conf(obj.get("confidence")),
                        steps=steps if isinstance(steps, list) else None)
    m = _FINAL_RE.search(text)
    if m:
        v = m.group(1)
        final = json.loads(v) if v[0] == '"' or v in ("true", "false", "null") else v
        return dict(parse_ok=False, how="regex_final", final=final, confidence=None, steps=None)
    m = _PROSE_RE.search(text)
    if m:
        return dict(parse_ok=False, how="prose", final=m.group(1).strip(), confidence=None, steps=None)
    return dict(parse_ok=False, how="none", final=None, confidence=None, steps=None)


def _conf(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if 1 < f <= 100:
        f /= 100
    return f if 0 <= f <= 1 else None
