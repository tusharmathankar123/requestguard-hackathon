import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from requestguard import budget


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {
            "REQUESTGUARD_DATA_DIR": self.temp.name,
            "REQUESTGUARD_LIVE_ENABLED": "YES",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_disabled_by_default(self):
        budget.initialize(1)
        os.environ.pop("REQUESTGUARD_LIVE_ENABLED")
        with self.assertRaises(budget.LiveBudgetError):
            budget.reserve()
        self.assertEqual(budget.status()["used"], 0)

    def test_exhausted_allowance_blocks(self):
        budget.initialize(1)
        budget.reserve()
        with self.assertRaises(budget.LiveBudgetError):
            budget.reserve()
        self.assertEqual(budget.status()["remaining"], 0)

    def test_restart_preserves_usage(self):
        budget.initialize(1)
        budget.reserve()
        result = subprocess.run(
            [sys.executable, "-m", "requestguard.budget", "status"],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(result.stdout), {
            "allowance": 1, "used": 1, "remaining": 0,
        })

    def test_existing_allowance_cannot_be_reset(self):
        budget.initialize(1)
        budget.reserve()
        with self.assertRaises(FileExistsError):
            budget.initialize(20)
        self.assertEqual(budget.status()["remaining"], 0)

    def test_concurrent_requests_respect_limit(self):
        budget.initialize(5)

        def attempt(_):
            try:
                budget.reserve()
                return True
            except budget.LiveBudgetError:
                return False

        with ThreadPoolExecutor(max_workers=8) as executor:
            successes = sum(executor.map(attempt, range(20)))

        self.assertEqual(successes, 5)
        self.assertEqual(budget.status()["used"], 5)

    def test_missing_ledger_blocks(self):
        with self.assertRaises(budget.LiveBudgetError):
            budget.reserve()
        self.assertFalse(budget.budget_path().exists())

    def test_corrupt_ledger_blocks(self):
        budget.budget_path().write_bytes(b"invalid database")
        with self.assertRaises(budget.LiveBudgetError):
            budget.reserve()


if __name__ == "__main__":
    unittest.main()
