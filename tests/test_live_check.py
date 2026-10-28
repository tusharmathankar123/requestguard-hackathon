import contextlib
import io
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from requestguard import budget, live_check
from requestguard.meta import MetaError


class LiveCheckTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = patch.dict(os.environ, {
            "REQUESTGUARD_DATA_DIR": temp.name,
            "REQUESTGUARD_LIVE_ENABLED": "NO",
        })
        env.start()
        self.addCleanup(env.stop)

    def run_command(self, *args):
        output = io.StringIO()
        with patch("sys.argv", ["live_check", *args]):
            with contextlib.redirect_stdout(output):
                code = live_check.main()
        return code, output.getvalue()

    def test_default_never_prompts_or_calls_provider(self):
        with patch.object(live_check, "getpass") as keys, \
             patch.object(live_check, "MetaProvider") as provider:
            code, output = self.run_command()
        self.assertEqual(code, 0)
        keys.getpass.assert_not_called()
        provider.assert_not_called()
        self.assertIn("No request made", output)

    def test_missing_allowance_never_prompts(self):
        with patch.object(live_check, "getpass") as keys, \
             patch.object(live_check, "MetaProvider") as provider:
            code, output = self.run_command("--run")
        self.assertEqual(code, 1)
        keys.getpass.assert_not_called()
        provider.assert_not_called()
        self.assertIn("initialise", output)

    def test_exhaustion_never_prompts_or_calls_provider(self):
        budget.initialize(1)
        os.environ["REQUESTGUARD_LIVE_ENABLED"] = "YES"
        budget.reserve()
        os.environ["REQUESTGUARD_LIVE_ENABLED"] = "NO"

        with patch.object(live_check, "getpass") as keys, \
             patch.object(live_check, "MetaProvider") as provider:
            code, output = self.run_command("--run")
        self.assertEqual(code, 1)
        keys.getpass.assert_not_called()
        provider.assert_not_called()
        self.assertIn("one unused request slot", output)

    def test_success_consumes_slot_and_restores_disabled_mode(self):
        budget.initialize(1)
        provider = Mock(return_value={
            "text": "PRIVATE_RESPONSE",
            "usage": {
                "input_tokens": 14,
                "output_tokens": 31,
                "total_tokens": 45,
            },
        })
        with patch.object(
            live_check.getpass, "getpass", return_value="dummy-test-key"
        ), patch.object(
            live_check, "MetaProvider", return_value=provider
        ):
            code, output = self.run_command("--run")

        self.assertEqual(code, 0)
        provider.assert_called_once()
        self.assertEqual(budget.status()["remaining"], 0)
        self.assertEqual(os.environ["REQUESTGUARD_LIVE_ENABLED"], "NO")
        self.assertIn('"total_tokens": 45', output)
        self.assertNotIn("PRIVATE_RESPONSE", output)
        self.assertNotIn("dummy-test-key", output)

    def test_failure_consumes_slot_without_retry(self):
        budget.initialize(1)
        provider = Mock(side_effect=MetaError("authentication_rejected"))
        with patch.object(
            live_check.getpass, "getpass", return_value="dummy-test-key"
        ), patch.object(
            live_check, "MetaProvider", return_value=provider
        ):
            code, output = self.run_command("--run")

        self.assertEqual(code, 1)
        provider.assert_called_once()
        self.assertEqual(budget.status()["remaining"], 0)
        self.assertEqual(os.environ["REQUESTGUARD_LIVE_ENABLED"], "NO")
        self.assertIn("authentication_rejected", output)


if __name__ == "__main__":
    unittest.main()
