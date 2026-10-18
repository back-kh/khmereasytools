"""Real HTTP round trips to a local protocol fixture; no provider calls."""
import json
import http.client
import os
import threading
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from khmereasytools import TranslationError, khtranslate


class TranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                cls.requests.append((self.path, dict(self.headers), self.rfile.read(length)))
                self.send_response(cls.status)
                if cls.status == 302:
                    self.send_header("Location", cls.url + "/redirect-target")
                self.end_headers()
                try:
                    self.wfile.write(cls.response)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.url = "http://127.0.0.1:{}/translate".format(cls.server.server_port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        type(self).requests = []
        type(self).status = 200
        type(self).response = json.dumps({"data": {"translations": [{"translatedText": "Hello &amp; welcome"}]}}).encode()
        self.url_patch = patch("khmereasytools.translation._API_URL", self.url)
        self.url_patch.start()
        self.addCleanup(self.url_patch.stop)
        self.env_patch = patch.dict(os.environ, {"GOOGLE_TRANSLATE_API_KEY": "fixture-key"})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_plain_text_request_and_response_decoding(self):
        self.assertEqual(khtranslate("សួស្តី"), "Hello & welcome")
        self.assertEqual(len(self.requests), 1)
        path, headers, raw = self.requests[0]
        self.assertEqual(path, "/translate")
        headers = {key.lower(): value for key, value in headers.items()}
        self.assertEqual(headers["x-goog-api-key"], "fixture-key")
        self.assertNotIn("fixture-key", path)
        self.assertEqual(json.loads(raw.decode()), {"q": "សួស្តី", "source": "km", "target": "en", "format": "text"})

    def test_reverse_translation_and_auto_source(self):
        type(self).response = json.dumps({"data": {"translations": [{"translatedText": "សួស្តី"}]}}).encode()
        self.assertEqual(khtranslate("Hello", target="km", source="en", api_key="explicit-key"), "សួស្តី")
        headers = {key.lower(): value for key, value in self.requests[0][1].items()}
        self.assertEqual(headers["x-goog-api-key"], "explicit-key")
        khtranslate("Hello", target="km", source=None)
        self.assertNotIn("source", json.loads(self.requests[1][2].decode()))

    def test_no_network_for_empty_same_language_or_missing_configuration(self):
        with patch.dict(os.environ, {"GOOGLE_TRANSLATE_API_KEY": ""}):
            self.assertEqual(khtranslate("  \n"), "  \n")
            self.assertEqual(khtranslate("សួស្តី", source="km", target="km"), "សួស្តី")
            with self.assertRaisesRegex(TranslationError, "GOOGLE_TRANSLATE_API_KEY"):
                khtranslate("សួស្តី")
        self.assertEqual(self.requests, [])

    def test_failure_messages_do_not_expose_key_or_text_and_do_not_retry(self):
        for status in (400, 401, 403, 429, 500):
            type(self).status = status
            type(self).response = b'private-source-and-key'
            with self.subTest(status=status), self.assertRaisesRegex(TranslationError, "HTTP {}".format(status)) as raised:
                khtranslate("private-source", api_key="private-key")
            self.assertNotIn("private", str(raised.exception))
        self.assertEqual(len(self.requests), 5)

    def test_redirect_is_refused(self):
        type(self).status = 302
        with self.assertRaisesRegex(TranslationError, "HTTP 302"):
            khtranslate("private-source")
        self.assertEqual(len(self.requests), 1)

    def test_invalid_or_oversized_provider_response(self):
        invalid = [b"not json", b"\xff", b"[]", b"{}", b'{"data":null}',
                   b'{"data":{"translations":[]}}', b'{"data":{"translations":[{}]}}',
                   b'{"data":{"translations":[{"translatedText":null}]}}',
                   b'{"data":{"translations":[{"translatedText":""}]}}']
        for raw in invalid:
            type(self).response = raw
            with self.subTest(raw=raw), self.assertRaisesRegex(TranslationError, "invalid response"):
                khtranslate("សួស្តី")
        type(self).response = b"x" * 1048577
        with self.assertRaisesRegex(TranslationError, "oversized"):
            khtranslate("សួស្តី")

    def test_connectivity_and_timeout(self):
        for error in (urllib.error.URLError("private-key"), TimeoutError("private-source"),
                      http.client.BadStatusLine("private-source")):
            with patch("urllib.request.OpenerDirector.open", side_effect=error):
                with self.assertRaisesRegex(TranslationError, "connectivity") as raised:
                    khtranslate("សួស្តី")
                self.assertNotIn("private", str(raised.exception))

    def test_validation_before_network(self):
        with self.assertRaises(TypeError):
            khtranslate(None)
        for options in ({"target": ""}, {"source": "auto"}, {"source": 5}, {"timeout": 0},
                        {"timeout": float("inf")}, {"timeout": True}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                khtranslate("សួស្តី", **options)
        with self.assertRaises(ValueError):
            khtranslate("ក" * 5001)
        with self.assertRaises(TranslationError):
            khtranslate("សួស្តី", api_key="bad\nkey")
        self.assertEqual(self.requests, [])


@unittest.skipUnless(os.environ.get("KET_RUN_TRANSLATION_TESTS") == "1", "Set KET_RUN_TRANSLATION_TESTS=1 for paid provider checks")
class LiveTranslationTests(unittest.TestCase):
    def test_google_khmer_and_english(self):
        # Deliberately not an exact-word quality benchmark. A configured live
        # run must actually reach the provider; missing credentials fail.
        english = khtranslate("សួស្តី", target="en", source="km")
        self.assertIn("hello", english.casefold())
        khmer = khtranslate("Hello", target="km", source="en")
        self.assertTrue(any("\u1780" <= char <= "\u17ff" for char in khmer))


if __name__ == "__main__":
    unittest.main()
