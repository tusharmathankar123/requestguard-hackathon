import json
import ssl
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from requestguard.meta import MetaProvider, MetaError, NoRedirect


class FakeResponse:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, size):
        return self.body[:size]


def completed(usage=None):
    return json.dumps({
        "status": "completed",
        "output": [{
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Example"}],
        }],
        "usage": usage,
    }).encode()


class MetaTests(unittest.TestCase):
    def test_response_usage_and_request_controls(self):
        fake = FakeResponse(completed({
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "private_field": "DO_NOT_RECORD",
        }))
        with patch(
            "urllib.request.OpenerDirector.open", return_value=fake
        ) as opened:
            result = MetaProvider("dummy-test-key")({"text": "Hello"})

        self.assertEqual(result["text"], "Example")
        self.assertEqual(result["usage"], {
            "input_tokens": 10, "output_tokens": 5, "total_tokens": 15,
        })
        opened.assert_called_once()
        request = opened.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.meta.ai/v1/responses")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(
            request.get_header("Authorization"), "Bearer dummy-test-key"
        )
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "muse-wonder-1.0")
        self.assertEqual(payload["max_output_tokens"], 1024)
        self.assertEqual(payload["tools"], [])
        self.assertIs(payload["store"], False)
        self.assertIs(payload["background"], False)
        self.assertEqual(opened.call_args.kwargs["timeout"], 30)

    def test_missing_usage_stays_unknown(self):
        with patch(
            "urllib.request.OpenerDirector.open",
            return_value=FakeResponse(completed()),
        ):
            result = MetaProvider("dummy-test-key")({"text": "Hello"})
        self.assertEqual(result["usage"], {})

    def test_http_failure_is_redacted_without_retry(self):
        error = urllib.error.HTTPError(
            "https://api.meta.ai/v1/responses",
            401, "PRIVATE_PROVIDER_DETAIL", {}, None,
        )
        with patch(
            "urllib.request.OpenerDirector.open", side_effect=error
        ) as opened:
            with self.assertRaises(MetaError) as caught:
                MetaProvider("dummy-test-key")({"text": "Hello"})
        self.assertEqual(str(caught.exception), "authentication_rejected")
        opened.assert_called_once()

    def test_oversized_input_never_dispatches(self):
        with patch("urllib.request.OpenerDirector.open") as opened:
            with self.assertRaises(ValueError):
                MetaProvider("dummy-test-key")({"text": "x" * 12001})
        opened.assert_not_called()

    def test_incomplete_response_is_rejected(self):
        body = json.dumps({"status": "incomplete", "output": []}).encode()
        with patch(
            "urllib.request.OpenerDirector.open",
            return_value=FakeResponse(body),
        ):
            with self.assertRaises(MetaError):
                MetaProvider("dummy-test-key")({"text": "Hello"})

    def test_tls_verification_and_redirect_rejection(self):
        original = urllib.request.build_opener

        def inspect(*handlers):
            handler = next(
                h for h in handlers
                if isinstance(h, urllib.request.HTTPSHandler)
            )
            self.assertEqual(handler._context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(handler._context.check_hostname)
            self.assertTrue(any(isinstance(h, NoRedirect) for h in handlers))
            return original(*handlers)

        with patch(
            "urllib.request.build_opener", side_effect=inspect
        ), patch(
            "urllib.request.OpenerDirector.open",
            return_value=FakeResponse(completed()),
        ):
            MetaProvider("dummy-test-key")({"text": "Hello"})

        self.assertIsNone(
            NoRedirect().redirect_request(
                None, None, 302, "", {}, "https://example.com"
            )
        )


if __name__ == "__main__":
    unittest.main()
