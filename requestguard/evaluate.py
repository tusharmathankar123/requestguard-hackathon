"""Offline evaluation of guarded dispatch. No network requests."""

import json
import os
import tempfile

from . import budget
from .runner import guarded_call


def evaluate_case(fail=False):
    names = ("REQUESTGUARD_DATA_DIR", "REQUESTGUARD_LIVE_ENABLED")
    previous = {name: os.environ.get(name) for name in names}

    try:
        with tempfile.TemporaryDirectory() as folder:
            os.environ["REQUESTGUARD_DATA_DIR"] = folder
            os.environ["REQUESTGUARD_LIVE_ENABLED"] = "YES"
            budget.initialize(1)
            records = []
            calls = 0

            def provider(request):
                nonlocal calls
                calls += 1
                if fail:
                    raise TimeoutError("Simulated")
                return {"source": "offline_mock"}

            try:
                guarded_call(provider, {}, records=records)
            except TimeoutError:
                if not fail:
                    raise

            try:
                guarded_call(provider, {}, records=records)
            except budget.LiveBudgetError:
                pass

            expected = [
                "provider_failed" if fail else "completed",
                "blocked",
            ]
            passed = (
                calls == 1
                and [r["outcome"] for r in records] == expected
                and budget.status()["remaining"] == 0
            )
            return {
                "scenario": "timeout_then_retry" if fail else "success_then_retry",
                "passed": passed,
                "mock_provider_calls": calls,
                "remaining": budget.status()["remaining"],
                "records": records,
            }
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def main():
    cases = [evaluate_case(), evaluate_case(fail=True)]
    passed = all(case["passed"] for case in cases)
    print(json.dumps({
        "mode": "offline_mock",
        "network_requests": 0,
        "passed": passed,
        "scenarios": cases,
    }, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
