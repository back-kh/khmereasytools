"""Local HTTP protocol tests only; no model or translation-quality evaluation."""
import http.client
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from khmereasytools import KhmerRAG, LocalModel, LocalModelError, TranslationError, khtranslate


class LocalModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                cls.requests.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode())))
                self.send_response(cls.status)
                if cls.status == 302:
                    self.send_header("Location", cls.url + "/redirect")
                self.end_headers()
                try:
                    self.wfile.write(cls.response)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_port)
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
        type(self).response = json.dumps({"message": {"role": "assistant", "content": "សួស្តី & hello"},
                                         "done": True, "done_reason": "stop"}).encode()
        self.model = LocalModel("fixture-local", base_url=self.url)

    def test_utf8_chat_request_complete_response_and_no_environment_proxy(self):
        with patch.dict(os.environ, {"HTTP_PROXY": "http://127.0.0.1:1", "HTTPS_PROXY": "http://127.0.0.1:1", "NO_PROXY": ""}):
            self.assertEqual(self.model("សួស្តី"), "សួស្តី & hello")
        path, body = self.requests[0]
        self.assertEqual(path, "/api/chat")
        self.assertEqual(body["model"], "fixture-local")
        self.assertEqual(body["messages"][1], {"role": "user", "content": "សួស្តី"})
        self.assertFalse(body["stream"])
        self.assertEqual(body["options"]["num_predict"], 1024)

    def test_local_translation_ignores_google_environment_and_preserves_plain_text(self):
        with patch.dict(os.environ, {"GOOGLE_TRANSLATE_API_KEY": "must-not-be-used"}):
            self.assertEqual(khtranslate("Hello", source="en", target="km", local_model=self.model), "សួស្តី & hello")
        body = self.requests[0][1]
        self.assertIn("from en into km", body["messages"][0]["content"])
        self.assertNotIn("must-not-be-used", json.dumps(body))
        self.assertEqual(body["messages"][1]["content"], "Hello")

    def test_rag_local_http_path_keeps_retrieved_source_provenance(self):
        result = KhmerRAG({"notes": "សិស្សអានសៀវភៅ។"}, generator=self.model).ask("សៀវភៅ")
        self.assertTrue(result.generated)
        self.assertEqual(result.sources[0].document_id, "notes")
        body = self.requests[0][1]
        prompt = body["messages"][1]["content"]
        evidence = json.loads(prompt.split("\n\n", 1)[1])
        self.assertEqual(evidence["sources"][0]["text"], result.sources[0].text)

    def test_empty_and_same_language_translation_make_no_request(self):
        self.assertEqual(khtranslate(" ", local_model=self.model), " ")
        self.assertEqual(khtranslate("ក", target="km", local_model=self.model), "ក")
        with self.assertRaises(ValueError):
            khtranslate("ក", api_key="secret", local_model=self.model)
        with self.assertRaises(TypeError):
            khtranslate("ក", local_model=lambda text: text)
        self.assertEqual(self.requests, [])

    def test_http_failures_and_redirects_do_not_retry_or_echo_server_text(self):
        for status in (302, 404, 429, 500):
            type(self).status = status
            type(self).response = b"private-document"
            with self.assertRaisesRegex(LocalModelError, "HTTP {}".format(status)) as raised:
                self.model("private-prompt")
            self.assertNotIn("private", str(raised.exception))
        self.assertEqual(len(self.requests), 4)

    def test_partial_tool_empty_malformed_and_oversized_responses_are_errors(self):
        invalid = [b"not-json", b"[]", b"{}", b"\xff",
                   json.dumps({"done": False, "message": {"role": "assistant", "content": "partial"}}).encode(),
                   json.dumps({"done": True, "message": {"role": "user", "content": "wrong-role"}}).encode(),
                   json.dumps({"done": True, "message": {"role": "assistant", "content": "", "tool_calls": [{}]}}).encode()]
        for response in invalid:
            type(self).response = response
            with self.subTest(response=response), self.assertRaisesRegex(LocalModelError, "invalid response"):
                self.model("question")
        type(self).response = b"x" * 1048577
        with self.assertRaisesRegex(LocalModelError, "oversized"):
            self.model("question")
        type(self).response = json.dumps({"done_reason": "length"}).encode()
        with self.assertRaisesRegex(LocalModelError, "output limit"):
            self.model("question")

    def test_transport_errors_are_safe_and_translation_wraps_them(self):
        with patch("urllib.request.OpenerDirector.open", side_effect=http.client.BadStatusLine("private")):
            with self.assertRaisesRegex(LocalModelError, "start Ollama"):
                self.model("question")
            with self.assertRaisesRegex(TranslationError, "start Ollama"):
                khtranslate("ក", local_model=self.model)

    def test_validation_is_offline(self):
        for origin in ("https://example.com", "http://0.0.0.0:11434", "file:///tmp/model", "http://127.0.0.1/path",
                       "http://user:secret@localhost", "http://localhost:0", "http://localhost:bad", "http://localhost?key=x"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                LocalModel("fixture", base_url=origin)
        for options in ({"timeout": 0}, {"timeout": True}, {"timeout": float("nan")}, {"max_tokens": 0}, {"max_tokens": True}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                LocalModel("fixture", **options)
        for name in (None, "", "qwen:cloud", "qwen-cloud", "model with spaces"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                LocalModel(name)
        with self.assertRaises(ValueError):
            self.model(" ")
        with self.assertRaises(ValueError):
            self.model("a" * 64001)
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
