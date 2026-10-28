import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from requestguard import budget
from requestguard.runner import guarded_call


class RunnerTests(unittest.TestCase):
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

    def test_allowed_request_reaches_provider_once(self):
        provider = Mock(return_value={"result": "mock"})
        result = guarded_call(provider, {"text": "example"})
        self.assertEqual(result, {"result": "mock"})
        provider.assert_called_once_with({"text": "example"})
        self.assertEqual(budget.status()["remaining"], 0)

    def test_exhausted_request_never_reaches_provider(self):
        budget.reserve()
        provider = Mock()
        with self.assertRaises(budget.LiveBudgetError):
            guarded_call(provider, {})
        provider.assert_not_called()

    def test_disabled_request_never_reaches_provider(self):
        os.environ.pop("REQUESTGUARD_LIVE_ENABLED")
        provider = Mock()
        with self.assertRaises(budget.LiveBudgetError):
            guarded_call(provider, {})
        provider.assert_not_called()

    def test_provider_failure_consumes_slot_without_retry(self):
        provider = Mock(side_effect=TimeoutError("simulated"))
        with self.assertRaises(TimeoutError):
            guarded_call(provider, {})
        provider.assert_called_once()
        self.assertEqual(budget.status()["remaining"], 0)

        with self.assertRaises(budget.LiveBudgetError):
            guarded_call(provider, {})
        provider.assert_called_once()


if __name__ == "__main__":
    unittest.main()
