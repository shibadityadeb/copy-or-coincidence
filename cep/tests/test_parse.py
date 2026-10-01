from cep.parse import parse_output


def test_clean_json():
    p = parse_output('{"steps": ["a", "b"], "final": "18", "confidence": 0.9}')
    assert p["parse_ok"] and p["final"] == "18" and p["confidence"] == 0.9 and len(p["steps"]) == 2


def test_json_in_fence_after_prose():
    raw = 'Sure! Here you go:\n```json\n{"steps": ["x {y}"], "final": 7, "confidence": 80}\n```'
    p = parse_output(raw)
    assert p["parse_ok"] and p["final"] == 7 and p["confidence"] == 0.8


def test_think_block_removed():
    raw = '<think>maybe {"final": "WRONG"}</think>{"steps": [], "final": "true", "confidence": 1}'
    assert parse_output(raw)["final"] == "true"


def test_unfinished_think_is_no_answer():
    assert parse_output('<think>still thinking... {"final": "3"}')["final"] is None


def test_broken_json_falls_back_to_regex():
    p = parse_output('{"steps": ["a", ], "final": "12", "confidence": 0.5')
    assert not p["parse_ok"] and p["how"] == "regex_final" and p["final"] == "12"


def test_prose_fallback():
    p = parse_output("Working... Final answer: 42")
    assert p["how"] == "prose" and p["final"] == "42"


def test_nothing():
    assert parse_output("I don't know")["final"] is None
