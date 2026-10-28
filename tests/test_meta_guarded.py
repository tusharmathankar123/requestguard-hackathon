import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from requestguard import budget
from requestguard.meta import MetaProvider, MetaError
from requestguard.runner import guarded_call


class GuardedMetaTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = patch.dict(os.environ, {
            "REQUESTGUARD_DATA_DIR": temp.name,
            "REQUESTGUARD_LIVE_ENABLED": "YES",
        })
        env.start()
        self.addCleanup(env.stop)
        budget.initialize(1)
        self.provider = MetaProvider("dummy-test-key")

    def test_success_records_usage_and_blocks_second_call(self):
        body = json.dumps({
            "status": "completed",
            "output": [{
                "type": "message",
                "role": "assistant",
                "content": [{
                    "type": "output_text",
                    "text": "PRIVATE_RESPONSE",
                }],
            }],
            "usage": {
                "input_tokens": 12,
                "output_tokens": 8,
                "total_tokens": 20,
            },
        }).encode()

        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = body
        records = []

        with patch(
            "urllib.request.OpenerDirector.open",
            return_value=response,
        ) as opened:
            guarded_call(
                self.provider, {"text": "PRIVATE_REQUEST"}, records=records
            )
            with self.assertRaises(budget.LiveBudgetError):
                guarded_call(
                    self.provider, {"text": "Second"}, records=records
                )
            opened.assert_called_once()

        self.assertEqual(
            [r["outcome"] for r in records], ["completed", "blocked"]
        )
        self.assertEqual(records[0]["reported_usage"]["total_tokens"], 20)
        self.assertNotIn("PRIVATE", json.dumps(records))
        self.assertEqual(budget.status()["remaining"], 0)

    def test_disabled_mode_never_dispatches_http(self):
        os.environ.pop("REQUESTGUARD_LIVE_ENABLED")
        with patch("urllib.request.OpenerDirector.open") as opened:
            with self.assertRaises(budget.LiveBudgetError):
                guarded_call(self.provider, {"text": "Hello"})
            opened.assert_not_called()

    def test_timeout_consumes_slot_without_retry(self):
        records = []
        with patch(
            "urllib.request.OpenerDirector.open",
            side_effect=TimeoutError("PRIVATE_DETAIL"),
        ) as opened:
            with self.assertRaises(MetaError):
                guarded_call(
                    self.provider, {"text": "Hello"}, records=records
                )
            with self.assertRaises(budget.LiveBudgetError):
                guarded_call(
                    self.provider, {"text": "Hello"}, records=records
                )
            opened.assert_called_once()

        self.assertEqual(
            [r["outcome"] for r in records], ["provider_failed", "blocked"]
        )
        self.assertNotIn("PRIVATE_DETAIL", json.dumps(records))
        self.assertEqual(budget.status()["remaining"], 0)


if __name__ == "__main__":
    unittest.main()
