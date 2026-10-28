import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from requestguard import budget
from requestguard.runner import guarded_call


class RecordTests(unittest.TestCase):
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

    def test_completed_record_excludes_sensitive_content(self):
        records = []
        provider = Mock(return_value={
            "text": "PRIVATE_RESPONSE",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "secret": "PRIVATE_METADATA",
            },
        })
        guarded_call(provider, {"text": "PRIVATE_REQUEST"}, records=records)
        self.assertEqual(len(records), 1)
        row = records[0]
        self.assertEqual(row["outcome"], "completed")
        self.assertEqual(row["reported_usage"]["total_tokens"], 15)
        self.assertGreaterEqual(row["duration_ms"], 0)
        self.assertNotIn("PRIVATE", json.dumps(records))

    def test_blocked_record_without_dispatch(self):
        budget.reserve()
        records = []
        provider = Mock()
        with self.assertRaises(budget.LiveBudgetError):
            guarded_call(provider, {}, records=records)
        provider.assert_not_called()
        self.assertEqual(records[0]["outcome"], "blocked")
        self.assertEqual(records[0]["reported_usage"], {})

    def test_failure_record_excludes_error_details(self):
        records = []
        provider = Mock(side_effect=TimeoutError("PRIVATE_ERROR"))
        with self.assertRaises(TimeoutError):
            guarded_call(provider, {}, records=records)
        self.assertEqual(records[0]["outcome"], "provider_failed")
        self.assertNotIn("PRIVATE_ERROR", json.dumps(records))
        self.assertEqual(budget.status()["remaining"], 0)


if __name__ == "__main__":
    unittest.main()
