"""
NAUB Chatbot NLP Engine
Uses TF-IDF Vectorization + Cosine Similarity for intent matching.
"""

import json
import re
import math
import os

# ─── Text Preprocessing ────────────────────────────────────────────────────────

STOP_WORDS = {
    "a","an","the","is","it","in","on","at","to","for","of","and","or","but",
    "not","with","this","that","are","was","were","be","been","being","have",
    "has","had","do","does","did","will","would","could","should","may","might",
    "shall","can","its","my","your","his","her","our","their","i","you","he",
    "she","we","they","me","him","us","them","what","which","who","how","when",
    "where","why","am","as","by","from","up","about","into","through","than",
    "then","so","if","just","more","also","there","here","some","any","all",
    "no","get","please","tell","want","need","know","find","help","much","many",
    "very","really","actually","basically","simply","also","now","still","even"
}

def tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, tokenize, remove stop words."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    tokens = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]
    return tokens

def stem(word: str) -> str:
    """Lightweight rule-based stemmer (no NLTK dependency)."""
    suffixes = ["ing", "tion", "tions", "ness", "ment", "ments", "ed", "er", "es", "s", "ly"]
    for suffix in suffixes:
        if word.endswith(suffix) and len(word) - len(suffix) > 2:
            return word[: -len(suffix)]
    return word

def preprocess(text: str) -> list[str]:
    tokens = tokenize(text)
    return [stem(t) for t in tokens]


# ─── TF-IDF Implementation ─────────────────────────────────────────────────────

class TFIDFVectorizer:
    def __init__(self):
        self.vocab: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.fitted = False
        self._corpus_tokens: list[list[str]] = []

    def fit(self, documents: list[str]):
        """Fit the vectorizer on a list of text documents."""
        self._corpus_tokens = [preprocess(doc) for doc in documents]
        n = len(self._corpus_tokens)

        # Build vocabulary & document frequencies
        df: dict[str, int] = {}
        all_terms = set()
        for tokens in self._corpus_tokens:
            unique = set(tokens)
            all_terms |= unique
            for term in unique:
                df[term] = df.get(term, 0) + 1

        self.vocab = {term: idx for idx, term in enumerate(sorted(all_terms))}
        # IDF with smoothing: log((1+N)/(1+df)) + 1
        self.idf = {
            term: math.log((1 + n) / (1 + df.get(term, 0))) + 1
            for term in self.vocab
        }
        self.fitted = True

    def transform(self, documents: list[str]) -> list[dict[str, float]]:
        """Convert documents to TF-IDF sparse vectors (dicts)."""
        if not self.fitted:
            raise RuntimeError("Vectorizer must be fitted before transform.")

        vectors = []
        for doc in documents:
            tokens = preprocess(doc)
            if not tokens:
                vectors.append({})
                continue

            # Term frequency
            tf: dict[str, float] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
            total = len(tokens)
            tf = {t: c / total for t, c in tf.items()}

            # TF-IDF vector (only known vocab terms)
            vec: dict[str, float] = {}
            for term, freq in tf.items():
                if term in self.idf:
                    vec[term] = freq * self.idf[term]
            vectors.append(vec)
        return vectors

    def fit_transform(self, documents: list[str]) -> list[dict[str, float]]:
        self.fit(documents)
        return self.transform(documents)


# ─── Cosine Similarity ─────────────────────────────────────────────────────────

def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Compute cosine similarity between two sparse TF-IDF vectors."""
    if not vec_a or not vec_b:
        return 0.0

    dot = sum(vec_a.get(term, 0) * vec_b.get(term, 0) for term in vec_b)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ─── Chatbot Engine ────────────────────────────────────────────────────────────

class NAUBChatbotEngine:
    THRESHOLD = 0.18  # Minimum similarity score to accept a match

    def __init__(self, knowledge_base_path: str):
        self.kb: list[dict] = []
        self.training_texts: list[str] = []
        self.training_labels: list[int] = []  # index into self.kb
        self.vectorizer = TFIDFVectorizer()
        self.kb_vectors: list[dict[str, float]] = []

        self._load_and_train(knowledge_base_path)

    def _load_and_train(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            self.kb = json.load(f)

        # Flatten all training questions with their intent index
        for idx, intent in enumerate(self.kb):
            for question in intent["questions"]:
                self.training_texts.append(question)
                self.training_labels.append(idx)

        # Fit TF-IDF on all training questions
        self.kb_vectors = self.vectorizer.fit_transform(self.training_texts)

    def get_response(self, user_query: str) -> dict:
        """
        Match user query to best intent and return a response dict.
        Returns: { "response": str, "intent": str, "score": float, "matched": bool }
        """
        query_vec = self.vectorizer.transform([user_query])[0]

        # Compute similarity against all training questions
        best_score = 0.0
        best_intent_idx = -1

        for i, kb_vec in enumerate(self.kb_vectors):
            score = cosine_similarity(query_vec, kb_vec)
            if score > best_score:
                best_score = score
                best_intent_idx = self.training_labels[i]

        if best_score >= self.THRESHOLD and best_intent_idx >= 0:
            intent = self.kb[best_intent_idx]
            return {
                "response": intent["response"],
                "intent": intent["intent"],
                "category": intent.get("category", "general"),
                "score": round(best_score, 4),
                "matched": True,
            }
        else:
            return {
                "response": self._fallback_response(user_query),
                "intent": "fallback",
                "category": "fallback",
                "score": round(best_score, 4),
                "matched": False,
            }

    @staticmethod
    def _fallback_response(query: str) -> str:
        return (
            "🤔 I'm sorry, I didn't quite understand that question.\n\n"
            "**Here are some things I can help you with:**\n"
            "• Type **'admission'** for admission requirements\n"
            "• Type **'fees'** for school fee information\n"
            "• Type **'courses'** for available programs\n"
            "• Type **'hostel'** for accommodation info\n"
            "• Type **'calendar'** for academic calendar\n"
            "• Type **'contact'** for office contact details\n\n"
            "Or try rephrasing your question. If you need urgent help, contact:\n"
            "📞 **ICT Directorate** | 📋 **Admissions Office** | 🏛️ **Academic Registry**"
        )

    def get_suggestions(self, partial: str) -> list[str]:
        """Return suggested questions based on partial input."""
        if len(partial) < 2:
            return []
        partial_lower = partial.lower()
        suggestions = []
        seen = set()
        for intent in self.kb:
            for question in intent["questions"]:
                if partial_lower in question.lower() and question not in seen:
                    suggestions.append(question.capitalize())
                    seen.add(question)
                    if len(suggestions) >= 5:
                        return suggestions
        return suggestions


# ─── Singleton loader ──────────────────────────────────────────────────────────

_engine_instance: NAUBChatbotEngine | None = None

def get_engine() -> NAUBChatbotEngine:
    global _engine_instance
    if _engine_instance is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        kb_path = os.path.join(base_dir, "data", "knowledge_base.json")
        _engine_instance = NAUBChatbotEngine(kb_path)
    return _engine_instance
