"""
Tests for chatbot.validators — gibberish detection.
Run with:  python -m pytest tests/test_validators.py -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot.validators import validate_query


# ── Should PASS (valid questions) ────────────────────────────────────────────
VALID = [
    "What are the admission requirements?",
    "How much are the school fees?",
    "Is hostel accommodation available on campus?",
    "When does the first semester begin?",
    "How do I check my results on the portal?",
    "Where is the admissions office located?",
    "What courses does NAUB offer?",
    "Can I apply for a scholarship?",
    "Tell me about SIWES",
    "What is the CGPA requirement for graduation?",
    "hi",                      # too short but passes length gate —
                               # actually 2 chars, will fail — expected False
]

# ── Should FAIL (gibberish / invalid) ────────────────────────────────────────
INVALID = [
    "utuwrky fguf",
    "asdfgh qwerty",
    "sdfghjkl",
    "zzzzxxx",
    "1234567",
    "!!!???",
    "   ",
    "",
    "ab",
    "kkkkkk tttttt",
    "xkcd zprq",
]


def test_valid_questions():
    legit = [q for q in VALID if len(q.strip()) >= 3]
    for q in legit:
        result = validate_query(q)
        # "hi" (2 chars stripped) will legitimately fail; skip it
        if len(q.strip()) < 3:
            continue
        assert result.valid, f"Expected VALID but got INVALID for: {q!r}\n  → {result.message}"


def test_invalid_inputs():
    for q in INVALID:
        result = validate_query(q)
        assert not result.valid, f"Expected INVALID but got VALID for: {q!r}"
        assert result.message, f"Expected a helpful message for: {q!r}"


def test_message_is_helpful():
    """Invalid queries must return a non-empty, user-friendly message."""
    result = validate_query("utuwrky fguf")
    assert not result.valid
    assert len(result.message) > 20, "Message should be descriptive"


if __name__ == "__main__":
    test_valid_questions()
    test_invalid_inputs()
    test_message_is_helpful()
    print("All validator tests passed ✓")
