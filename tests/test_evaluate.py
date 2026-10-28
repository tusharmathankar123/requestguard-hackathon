import contextlib
import io
import json
import unittest
from unittest.mock import patch

from requestguard import evaluate


class EvaluationTests(unittest.TestCase):
    def test_both_real_guard_scenarios_pass(self):
        for fail in (False, True):
            with self.subTest(provider_failure=fail):
                result = evaluate.evaluate_case(fail=fail)
                self.assertTrue(result["passed"])
                self.assertEqual(result["mock_provider_calls"], 1)
                self.assertEqual(result["remaining"], 0)

    def test_bypassed_guard_is_detected(self):
        def bypass(provider, request, *, records=None):
            return provider(request)

        with patch.object(evaluate, "guarded_call", bypass):
            result = evaluate.evaluate_case()

        self.assertFalse(result["passed"])
        self.assertEqual(result["mock_provider_calls"], 2)

    def test_main_reports_success(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = evaluate.main()

        self.assertEqual(exit_code, 0)
        self.assertTrue(json.loads(output.getvalue())["passed"])

    def test_main_returns_failure_when_guard_is_bypassed(self):
        def bypass(provider, request, *, records=None):
            return provider(request)

        output = io.StringIO()
        with patch.object(evaluate, "guarded_call", bypass):
            with patch.object(
                evaluate, "evaluate_case",
                side_effect=lambda **kwargs: original_case()
            ):
                with contextlib.redirect_stdout(output):
                    exit_code = evaluate.main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(json.loads(output.getvalue())["passed"])


original_case = evaluate.evaluate_case

if __name__ == "__main__":
    unittest.main()
