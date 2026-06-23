"""
NAUB Chatbot — Input Validator
Detects gibberish / non-question text and rejects it before
any DB write or engine call.
"""

import re

# ── Tuning constants ──────────────────────────────────────────────────────────
MIN_REAL_WORDS          = 2    # need at least 2 clearly real words
MIN_KNOWN_WORDS         = 1    # at least 1 word must be in the known dictionary
MAX_CONSONANT_RUN       = 4    # "sdfgh" → 5 → rejected; "pply" counts y as vowel
MIN_VOWEL_RATIO_WORD    = 0.20 # individual word vowel ratio to be considered real
MIN_VOWEL_RATIO_QUERY   = 0.18 # whole-query vowel ratio
MIN_QUERY_LENGTH        = 3    # stripped query must be ≥ 3 chars

VOWELS = set("aeiouAEIOUyY")  # treat y/Y as vowel for consonant-run purposes

# Known real words — checked against each individual token
KNOWN_WORDS = {
    # discourse
    "hi","hello","hey","good","morning","afternoon","evening","please",
    "thanks","thank","help","can","what","when","where","how","who","why",
    "which","is","are","does","do","will","tell","show","give","get","find",
    "need","want","know","about","much","many","cost","price","long","far",
    "any","all","my","me","i","you","us","our","your","its","their",
    "a","an","the","of","for","in","on","at","to","by","from","with",
    # NAUB-specific
    "admission","admissions","fee","fees","course","courses","department",
    "faculty","hostel","accommodation","portal","result","results","jamb",
    "utme","post","clearance","registration","semester","session","calendar",
    "schedule","exam","exams","cgpa","gpa","carryover","graduation",
    "convocation","matriculation","siwes","ijmb","naub","university","biu",
    "borno","army","military","student","students","lecturer","professor",
    "rector","vc","registrar","bursar","library","ict","directorate",
    "contact","email","phone","address","scholarship","bursary","sport",
    "health","medical","screening","form","forms","application","apply",
    "deadline","date","payment","bank","slip","school","campus","office",
    "program","programmes","programs","department","departments","faculty",
    "faculties","number","location","available","require","requirement",
    "requirements","process","procedure","duration","years","year","month",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _alpha_chars(text: str) -> str:
    return "".join(c for c in text if c.isalpha())


def _vowel_ratio(text: str) -> float:
    alpha = _alpha_chars(text)
    if not alpha:
        return 0.0
    return sum(1 for c in alpha if c in VOWELS) / len(alpha)


def _max_consonant_run(text: str) -> int:
    """Longest run of consecutive consonants in a string."""
    run = max_run = 0
    for c in text.lower():
        if c.isalpha() and c not in VOWELS:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return max_run


def _is_pronounceable_word(word: str) -> bool:
    """
    Heuristic: a word is 'pronounceable' (and therefore likely real) if:
      - it has a healthy vowel ratio, AND
      - its max consonant run is short
    """
    if len(word) < 2:
        return False
    return (
        _vowel_ratio(word) >= MIN_VOWEL_RATIO_WORD
        and _max_consonant_run(word) <= MAX_CONSONANT_RUN
    )


def _score_tokens(tokens: list[str]) -> tuple[int, int]:
    """
    Returns (known_count, pronounceable_count).
    'known' = in KNOWN_WORDS dictionary.
    'pronounceable' = passes the vowel/consonant heuristic.
    """
    known = 0
    pronounceable = 0
    for tok in tokens:
        low = tok.lower()
        if low in KNOWN_WORDS:
            known += 1
            pronounceable += 1          # known words are inherently pronounceable
        elif _is_pronounceable_word(tok):
            pronounceable += 1
    return known, pronounceable


# ── Public API ────────────────────────────────────────────────────────────────

class ValidationResult:
    __slots__ = ("valid", "message")

    def __init__(self, valid: bool, message: str = ""):
        self.valid   = valid
        self.message = message

    def __bool__(self):
        return self.valid


def validate_query(raw: str) -> ValidationResult:
    """
    Returns a ValidationResult.
    If .valid is False, show .message to the user and DO NOT log to DB.
    If .valid is True, proceed with engine + DB logging.
    """
    text = raw.strip()

    # 1. Empty / too short
    if len(text) < MIN_QUERY_LENGTH:
        return ValidationResult(
            False,
            "Please type a question before sending.\n"
            "For example: *'What are the admission requirements?'*",
        )

    # 2. No alphabetic characters
    if not _alpha_chars(text):
        return ValidationResult(
            False,
            "I only understand text questions.\n"
            "Please type your question in words.",
        )

    # 3. Tokenise into words
    tokens = re.findall(r"[a-zA-Z]+", text)
    if not tokens:
        return ValidationResult(
            False,
            "Your message doesn't seem to contain any words.\n"
            "Try asking: *'How do I apply for admission?'*",
        )

    # 4. Whole-query vowel ratio
    if _vowel_ratio(text) < MIN_VOWEL_RATIO_QUERY:
        return ValidationResult(
            False,
            "That doesn't look like a proper question. 🤔\n"
            "Please ask something like: *'What courses does NAUB offer?'*",
        )

    # 5. Long consonant run anywhere in the query
    if _max_consonant_run(text) > MAX_CONSONANT_RUN:
        return ValidationResult(
            False,
            "I couldn't understand that. Could you rephrase your question?\n"
            "Try something like: *'How do I check my results?'*",
        )

    # 6. Score the tokens
    known_count, pronounceable_count = _score_tokens(tokens)

    # Must have at least 1 known dictionary word
    if known_count < MIN_KNOWN_WORDS:
        return ValidationResult(
            False,
            "Your message doesn't look like a question I can help with. 😕\n"
            "Please ask a clear question about NAUB, for example:\n"
            "*'What is the school fee?'* or *'Where is the hostel?'*",
        )

    # Must have at least MIN_REAL_WORDS pronounceable tokens in total
    if pronounceable_count < MIN_REAL_WORDS:
        return ValidationResult(
            False,
            "Your message doesn't look like a question I can help with. 😕\n"
            "Please ask a clear question about NAUB, for example:\n"
            "*'What is the school fee?'* or *'Where is the hostel?'*",
        )

    return ValidationResult(True)
