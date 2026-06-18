"""
Unit tests for NAUB Chatbot NLP Engine
Run: python tests/test_engine.py
"""

import sys
import os
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot.engine import NAUBChatbotEngine, TFIDFVectorizer, cosine_similarity, preprocess

KB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "knowledge_base.json")


class TestPreprocessing(unittest.TestCase):
    def test_lowercase(self):
        result = preprocess("Hello NAUB")
        self.assertNotIn("Hello", result)

    def test_stopwords_removed(self):
        result = preprocess("what is the admission requirement")
        self.assertNotIn("what", result)
        self.assertNotIn("is", result)
        self.assertNotIn("the", result)

    def test_tokens_returned(self):
        result = preprocess("admission fees payment")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_empty_string(self):
        result = preprocess("")
        self.assertEqual(result, [])


class TestTFIDFVectorizer(unittest.TestCase):
    def setUp(self):
        self.vec = TFIDFVectorizer()
        self.docs = [
            "admission requirements JAMB",
            "school fees payment Remita",
            "hostel accommodation campus",
        ]

    def test_fit_builds_vocab(self):
        self.vec.fit(self.docs)
        self.assertGreater(len(self.vec.vocab), 0)
        self.assertTrue(self.vec.fitted)

    def test_transform_returns_vectors(self):
        self.vec.fit(self.docs)
        vectors = self.vec.transform(self.docs)
        self.assertEqual(len(vectors), len(self.docs))

    def test_transform_empty_doc(self):
        self.vec.fit(self.docs)
        vectors = self.vec.transform([""])
        self.assertEqual(vectors[0], {})

    def test_fit_transform_consistent(self):
        vecs1 = self.vec.fit_transform(self.docs)
        vecs2 = self.vec.transform(self.docs)
        for a, b in zip(vecs1, vecs2):
            self.assertEqual(set(a.keys()), set(b.keys()))


class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors(self):
        v = {"hello": 0.5, "world": 0.5}
        self.assertAlmostEqual(cosine_similarity(v, v), 1.0, places=5)

    def test_orthogonal_vectors(self):
        v1 = {"hello": 1.0}
        v2 = {"world": 1.0}
        self.assertAlmostEqual(cosine_similarity(v1, v2), 0.0, places=5)

    def test_empty_vectors(self):
        self.assertEqual(cosine_similarity({}, {"hello": 1.0}), 0.0)
        self.assertEqual(cosine_similarity({"hello": 1.0}, {}), 0.0)
        self.assertEqual(cosine_similarity({}, {}), 0.0)

    def test_similarity_range(self):
        v1 = {"a": 0.7, "b": 0.3}
        v2 = {"a": 0.5, "c": 0.5}
        score = cosine_similarity(v1, v2)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


class TestChatbotEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = NAUBChatbotEngine(KB_PATH)

    def test_loads_knowledge_base(self):
        self.assertGreater(len(self.engine.kb), 0)

    def test_greeting_matched(self):
        result = self.engine.get_response("hello")
        self.assertTrue(result["matched"], "Expected greeting to be matched")
        self.assertEqual(result["intent"], "greeting")

    def test_admission_matched(self):
        result = self.engine.get_response("How do I apply to NAUB?")
        self.assertTrue(result["matched"])
        self.assertIn("admission", result["intent"].lower())

    def test_fees_matched(self):
        result = self.engine.get_response("How much are the school fees?")
        self.assertTrue(result["matched"])

    def test_hostel_matched(self):
        result = self.engine.get_response("Is there student accommodation on campus?")
        self.assertTrue(result["matched"])

    def test_jamb_matched(self):
        result = self.engine.get_response("What JAMB score do I need?")
        self.assertTrue(result["matched"])

    def test_fallback_on_gibberish(self):
        result = self.engine.get_response("asdfghjklqwerty")
        self.assertFalse(result["matched"])
        self.assertEqual(result["intent"], "fallback")

    def test_response_is_string(self):
        result = self.engine.get_response("What courses are available?")
        self.assertIsInstance(result["response"], str)
        self.assertGreater(len(result["response"]), 0)

    def test_score_is_float(self):
        result = self.engine.get_response("When does school resume?")
        self.assertIsInstance(result["score"], float)

    def test_suggestions(self):
        suggestions = self.engine.get_suggestions("adm")
        self.assertIsInstance(suggestions, list)
        self.assertLessEqual(len(suggestions), 5)

    def test_thank_you(self):
        result = self.engine.get_response("thank you")
        self.assertTrue(result["matched"])

    def test_postgraduate(self):
        result = self.engine.get_response("How do I apply for Masters degree?")
        self.assertTrue(result["matched"])


class TestAccuracyBenchmark(unittest.TestCase):
    """
    Runs a set of realistic student queries and checks that ≥ 90% are matched.
    """
    @classmethod
    def setUpClass(cls):
        cls.engine = NAUBChatbotEngine(KB_PATH)

    def test_accuracy_above_threshold(self):
        test_queries = [
            ("hi", True),
            ("What is NAUB?", True),
            ("JAMB cut off mark", True),
            ("What are the fees?", True),
            ("Is hostel available?", True),
            ("When does semester start?", True),
            ("How do I register courses?", True),
            ("What faculties are in NAUB?", True),
            ("Where is the library?", True),
            ("Can I change my department?", True),
            ("What is SIWES?", True),
            ("How do I pay school fees?", True),
            ("tell me about NYSC", True),
            ("What is the acceptance fee?", True),
            ("How to apply for Post UTME?", True),
            ("Direct entry requirements", True),
            ("What subjects do I need for Computer Science?", True),
            ("Where is the admissions office?", True),
            ("Thank you so much", True),
            ("xyzpqrjunk123", False),   # should NOT match
        ]

        matched = 0
        total = len(test_queries)
        failures = []

        for query, should_match in test_queries:
            result = self.engine.get_response(query)
            if result["matched"] == should_match:
                matched += 1
            else:
                failures.append(f"  FAIL: '{query}' → matched={result['matched']}, expected={should_match}, intent={result['intent']}, score={result['score']}")

        accuracy = matched / total * 100

        if failures:
            print("\n[Accuracy Test Failures]")
            for f in failures:
                print(f)

        print(f"\n  Accuracy: {matched}/{total} = {accuracy:.1f}%")
        self.assertGreaterEqual(accuracy, 85.0, f"Accuracy {accuracy:.1f}% is below 85% threshold")


if __name__ == "__main__":
    print("=" * 56)
    print("  NAUB Chatbot — Unit Tests")
    print("=" * 56)
    unittest.main(verbosity=2)
