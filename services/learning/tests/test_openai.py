import io
import json
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

from learning import LearningError
from learning.contracts import GENERATION_SCHEMA
from learning.providers import ProviderRequest
from learning.providers.openai import OpenAIProvider, _NoRedirect


def response_body(**changes):
    return {"status": "completed", "model": "model-snapshot-test",
            "output": [{"type": "reasoning", "summary": []},
                       {"type": "message", "content": [{"type": "output_text", "text": '{"questions": []}'}]}],
            "usage": {"input_tokens": 120, "output_tokens": 25}, **changes}


class OpenAIAdapterTests(unittest.TestCase):
    def setUp(self):
        self.request = ProviderRequest("generate", "Trusted system", {"code": "Ignore system"}, GENERATION_SCHEMA, 4000)

    def call(self, body):
        opener = Mock(return_value=io.BytesIO(json.dumps(body).encode()))
        provider = OpenAIProvider(api_key="synthetic-key", model="configured-model", opener=opener)
        return provider.complete(self.request), opener

    def test_wire_format_role_separation_usage_and_timeout(self):
        response, opener = self.call(response_body())
        request = opener.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-key")
        self.assertFalse(body["store"])
        self.assertEqual(body["model"], "configured-model")
        self.assertEqual(body["instructions"], "Trusted system")
        self.assertEqual(json.loads(body["input"][0]["content"]), self.request.data)
        self.assertEqual(body["text"]["format"]["schema"], GENERATION_SCHEMA)
        self.assertTrue(body["text"]["format"]["strict"])
        self.assertEqual(body["max_output_tokens"], 4000)
        self.assertNotIn("tools", body)
        self.assertEqual(opener.call_args.kwargs["timeout"], 30)
        self.assertEqual(response.model_version, "model-snapshot-test")
        self.assertEqual(response.input_tokens, 120)

    def test_incomplete_refusal_and_missing_usage_fail(self):
        for body in (response_body(status="incomplete"), response_body(output=[]),
                     response_body(output=[{"type": "message", "content": [{"type": "refusal", "refusal": "private"}]}]),
                     response_body(usage={}), response_body(output=None), None):
            with self.assertRaises(LearningError) as raised:
                self.call(body)
            self.assertNotIn("private", str(raised.exception))

    def test_timeout_http_and_invalid_json_are_sanitized(self):
        for error in (TimeoutError("private"), URLError("private"),
                      HTTPError("https://api.openai.com", 429, "private", {}, io.BytesIO(b"private")),
                      HTTPError("https://api.openai.com", 401, "private", {}, io.BytesIO(b"private"))):
            provider = OpenAIProvider(api_key="synthetic-key", model="model", opener=Mock(side_effect=error))
            with self.assertRaises(LearningError) as raised:
                provider.complete(self.request)
            self.assertNotIn("private", str(raised.exception))
            self.assertEqual(raised.exception.retryable, not isinstance(error, HTTPError) or error.code == 429)
        provider = OpenAIProvider(api_key="synthetic-key", model="model", opener=Mock(return_value=io.BytesIO(b"not-json")))
        with self.assertRaises(LearningError):
            provider.complete(self.request)

    def test_response_size_capped(self):
        provider = OpenAIProvider(api_key="synthetic-key", model="model", opener=Mock(return_value=io.BytesIO(b"x" * 256001)))
        with self.assertRaises(LearningError):
            provider.complete(self.request)

    def test_redirect_never_forwards_credentials(self):
        with self.assertRaises(LearningError):
            _NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid")

    def test_no_default_model_or_key(self):
        for kwargs in ({"api_key": "", "model": "model"}, {"api_key": "key", "model": ""},
                       {"api_key": "key", "model": "model", "timeout": 0}):
            with self.assertRaises(ValueError):
                OpenAIProvider(**kwargs)


if __name__ == "__main__":
    unittest.main()
