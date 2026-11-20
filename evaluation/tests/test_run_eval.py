from __future__ import annotations

import json
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from evaluation.run_eval import RunConfig, endpoint_url, load_cases, run_case, safe_endpoint


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.case = {
            "id": "smoke-1",
            "category": "general",
            "messages": [{"role": "user", "content": "Hello"}],
            "rubric": ["Clear response"],
        }
        self.config = RunConfig(
            base_url="http://localhost:8000/v1",
            model="served-name",
            role="core_prime",
            candidate_id="test/candidate",
            revision="abcdef123456",
        )

    def test_endpoint_normalization(self):
        self.assertEqual(endpoint_url("http://localhost:8000"), "http://localhost:8000/v1/chat/completions")
        self.assertEqual(endpoint_url("http://localhost:8000/v1"), "http://localhost:8000/v1/chat/completions")
        self.assertEqual(endpoint_url("http://localhost:8000/v1/chat/completions"), "http://localhost:8000/v1/chat/completions")

    def test_safe_endpoint_drops_credentials_query_and_fragment(self):
        value = safe_endpoint("https://user:secret@example.test/v1?token=hidden#fragment")
        self.assertEqual(value, "https://example.test/v1/chat/completions")
        with_port = safe_endpoint("http://localhost:8000/v1")
        self.assertEqual(with_port, "http://localhost:8000/v1/chat/completions")
        self.assertNotIn("secret", value)
        self.assertNotIn("hidden", value)

    def test_success_records_output_and_tool_calls(self):
        payload = {
            "choices": [{
                "finish_reason": "tool_calls",
                "message": {
                    "content": None,
                    "tool_calls": [{"id": "call-1", "type": "function"}],
                    "refusal": None,
                },
            }],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4},
        }

        def opener(request, timeout):
            self.assertEqual(request.full_url, "http://localhost:8000/v1/chat/completions")
            self.assertEqual(timeout, 180.0)
            body = json.loads(request.data.decode("utf-8"))
            self.assertEqual(body["model"], "served-name")
            return FakeResponse(payload)

        result = run_case(self.case, self.config, opener=opener)
        self.assertIsNone(result["error"])
        self.assertEqual(result["finish_reason"], "tool_calls")
        self.assertEqual(result["tool_calls"][0]["id"], "call-1")
        self.assertEqual(result["usage"]["prompt_tokens"], 3)
        self.assertEqual(len(result["prompt_sha256"]), 64)

    def test_api_key_is_only_sent_as_authorization_header(self):
        config = RunConfig(**{**self.config.__dict__, "api_key": "do-not-log-this"})
        captured = {}

        def opener(request, timeout):
            captured["authorization"] = request.get_header("Authorization")
            return FakeResponse({"choices": [{"message": {"content": "ok"}}]})

        result = run_case(self.case, config, opener=opener)
        self.assertEqual(captured["authorization"], "Bearer do-not-log-this")
        self.assertNotIn("do-not-log-this", json.dumps(result))

    def test_default_opener_does_not_follow_redirects(self):
        redirected_requests = []

        class TargetHandler(BaseHTTPRequestHandler):
            def _record(self):
                redirected_requests.append((self.command, self.headers.get("Authorization")))
                self.send_response(200)
                self.end_headers()

            do_GET = _record
            do_POST = _record

            def log_message(self, *_args):
                pass

        class RedirectHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(302)
                self.send_header("Location", self.server.target_url)
                self.end_headers()

            def log_message(self, *_args):
                pass

        target = ThreadingHTTPServer(("127.0.0.1", 0), TargetHandler)
        target_url = f"http://127.0.0.1:{target.server_port}/capture"
        origin = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        origin.target_url = target_url
        threads = [Thread(target=server.serve_forever, daemon=True) for server in (target, origin)]
        for thread in threads:
            thread.start()
        try:
            config = RunConfig(**{
                **self.config.__dict__,
                "base_url": f"http://127.0.0.1:{origin.server_port}/v1",
                "api_key": "redirect-secret",
                "timeout_seconds": 3.0,
            })
            result = run_case(self.case, config)
            self.assertEqual(result["http_status"], 302)
            self.assertIsNotNone(result["error"])
            self.assertEqual(redirected_requests, [])
        finally:
            for server in (origin, target):
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join(timeout=2)

    def test_malformed_response_becomes_error_record(self):
        result = run_case(self.case, self.config, opener=lambda *_args, **_kwargs: FakeResponse({"choices": []}))
        self.assertIsNotNone(result["error"])
        self.assertIsNone(result["response_text"])

    def test_load_fixture_suites(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1] / "fixtures"
        self.assertEqual(len(load_cases(root / "prime_smoke.jsonl")), 3)
        self.assertEqual(len(load_cases(root / "prima_smoke.jsonl")), 3)


if __name__ == "__main__":
    unittest.main()
