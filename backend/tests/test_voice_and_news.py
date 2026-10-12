import asyncio
import unittest
import sys
sys.path.insert(0, ".")

from app.services.command_executor import execute_in_backend, detect_query_language
from app.services.web_search_context import gather_all_web_context, fetch_live_news_rss
from app.services.tts_service import TTSService

class TestFridayVoiceAndNews(unittest.TestCase):
    def test_tanglish_false_positives(self):
        english_queries = [
            "What is the price of Japanese yen?",
            "Can you deliver to PO box 123?",
            "Anna has invited me to the party",
            "What is the capital of France?",
            "Explain how series circuits work"
        ]
        for q in english_queries:
            detected = detect_query_language(q, default_lang="english")
            self.assertEqual(detected, "english", f"Query '{q}' mistakenly detected as {detected}")

    def test_tanglish_true_positives(self):
        tanglish_queries = [
            "Friday enna panra epdi iruka?",
            "sollunga friday enna help venum",
            "romba nandri friday seekiram vaanga",
            "call pannu nanba"
        ]
        for q in tanglish_queries:
            detected = detect_query_language(q, default_lang="english")
            self.assertEqual(detected, "tanglish", f"Query '{q}' failed to detect tanglish")

    def test_voice_gender_commands(self):
        cmds = [
            ("convert ur voice to male", "male"),
            ("change voice to female", "female"),
            ("switch to male voice", "male"),
            ("make your voice female", "female"),
            ("convert voice to male", "male"),
        ]
        for cmd, expected_gender in cmds:
            res = asyncio.run(execute_in_backend(cmd))
            self.assertIn(f"[[ACTION:SET_VOICE_GENDER:{expected_gender}]]", res)

    def test_language_commands(self):
        res_ta = asyncio.run(execute_in_backend("speak in tamil"))
        self.assertIn("[[ACTION:SET_LANGUAGE:tamil]]", res_ta)

        res_en = asyncio.run(execute_in_backend("speak in english"))
        self.assertIn("[[ACTION:SET_LANGUAGE:english]]", res_en)

        res_tg = asyncio.run(execute_in_backend("speak in tanglish"))
        self.assertIn("[[ACTION:SET_LANGUAGE:tanglish]]", res_tg)

    def test_categorized_news_rss(self):
        for cat in ["tech news", "world news", "sports news", "business news", "entertainment news", "science news", "tamil nadu news"]:
            rss = asyncio.run(fetch_live_news_rss(cat, max_items=3))
            self.assertTrue(len(rss) > 0, f"News RSS failed for category {cat}")
            self.assertIn("Google News RSS", rss)

    def test_live_web_context_gather(self):
        ctx = asyncio.run(gather_all_web_context("latest breaking news today"))
        self.assertTrue(len(ctx) > 0, "Failed to gather live web context")

if __name__ == "__main__":
    unittest.main()

