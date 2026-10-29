import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from requestguard import budget, dashboard


class DashboardTests(unittest.TestCase):
    def test_report_is_offline_and_preserves_existing_allowance(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'REQUESTGUARD_DATA_DIR':folder,'REQUESTGUARD_LIVE_ENABLED':'NO'}):
                budget.initialize(1)
                before = budget.budget_path().read_bytes()
                with patch.object(socket.socket, 'connect', side_effect=AssertionError('No network')):
                    report = dashboard.build_report()
                self.assertTrue(report['passed'])
                self.assertEqual(report['network_requests'], 0)
                self.assertEqual(len(report['scenarios']), 2)
                self.assertEqual(budget.budget_path().read_bytes(), before)
                self.assertEqual(os.environ['REQUESTGUARD_LIVE_ENABLED'], 'NO')
                self.assertEqual(os.environ['REQUESTGUARD_DATA_DIR'], folder)

    def test_embedded_data_cannot_escape_json_script(self):
        report = {'value':'</script><script>alert(1)</script>'}
        page = dashboard.render(report)
        embedded = page.split('<script id="report" type="application/json">',1)[1].split('</script>',1)[0]
        self.assertNotIn('<', embedded)
        self.assertEqual(json.loads(embedded), report)

    def test_page_explains_historical_and_mock_evidence(self):
        page = dashboard.render(dashboard.build_report())
        self.assertIn('Historical live evidence', page)
        self.assertIn('user-reported', page)
        self.assertIn('not a live connection', page)
        self.assertIn('Token usage: unknown (mock)', page)
        self.assertNotIn('__REPORT_JSON__', page)
        self.assertNotIn('fetch(', page)

    def test_cli_writes_self_contained_report(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'report.html'
            with patch('sys.argv',['dashboard','--output',str(output)]):
                self.assertEqual(dashboard.main(), 0)
            self.assertIn('"mode": "offline_mock"', output.read_text())


if __name__ == '__main__':
    unittest.main()
