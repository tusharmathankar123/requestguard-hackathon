import contextlib
import io
import json
import os
import socket
import tempfile
import unittest
from unittest.mock import patch

from requestguard import budget, compare


class ComparisonTests(unittest.TestCase):
    def test_identical_attempt_count_and_observed_dispatch_counts(self):
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('No network')):
            result = compare.run_comparison()
        self.assertTrue(result['passed'])
        self.assertEqual(result['unguarded']['attempts'], result['guarded']['attempts'])
        self.assertEqual(result['unguarded']['provider_calls'], 3)
        self.assertEqual(result['guarded']['provider_calls'], 1)
        self.assertEqual(result['guarded']['outcomes'], ['provider_failed','blocked','blocked'])
        self.assertEqual(result['network_requests'], 0)

    def test_existing_storage_and_mode_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'REQUESTGUARD_DATA_DIR': folder, 'REQUESTGUARD_LIVE_ENABLED':'NO'}):
                budget.initialize(1)
                before = budget.budget_path().read_bytes()
                compare.run_comparison()
                self.assertEqual(budget.budget_path().read_bytes(), before)
                self.assertEqual(os.environ['REQUESTGUARD_LIVE_ENABLED'], 'NO')
                self.assertEqual(os.environ['REQUESTGUARD_DATA_DIR'], folder)

    def test_bypassed_guard_causes_failed_comparison(self):
        def bypass(provider, request, **kwargs):
            return provider(request)
        with patch.object(compare, 'guarded_call', bypass):
            report = compare.run_comparison()
        self.assertFalse(report['passed'])
        self.assertEqual(report['guarded']['provider_calls'], 3)

    def test_command_outputs_observations(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = compare.main()
        report = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(report['passed'])
        self.assertIn('monetary savings and recovery are not established', report['note'])


if __name__ == '__main__':
    unittest.main()
