"""Offline timeout demonstration. No network requests."""

import json
import os
import tempfile

from . import budget
from .runner import guarded_call


def main():
    names = ("REQUESTGUARD_DATA_DIR", "REQUESTGUARD_LIVE_ENABLED")
    previous = {name: os.environ.get(name) for name in names}

    try:
        with tempfile.TemporaryDirectory() as folder:
            os.environ["REQUESTGUARD_DATA_DIR"] = folder
            os.environ["REQUESTGUARD_LIVE_ENABLED"] = "YES"
            budget.initialize(1)
            records = []
            calls = 0

            def failing_provider(request):
                nonlocal calls
                calls += 1
                raise TimeoutError("Simulated provider timeout")

            print("OFFLINE FAILURE DEMO — no API calls")

            try:
                guarded_call(failing_provider, {}, records=records)
            except TimeoutError:
                print("Request 1: TIMED OUT; slot remains consumed")

            try:
                guarded_call(failing_provider, {}, records=records)
            except budget.LiveBudgetError:
                print("Request 2: BLOCKED before provider dispatch")

            assert calls == 1
            assert [r["outcome"] for r in records] == [
                "provider_failed", "blocked"
            ]
            assert budget.status()["remaining"] == 0

            print("Request records:")
            print(json.dumps(records, indent=2))
            print("Mock provider calls:", calls)
            print("Final allowance:", budget.status())
            print("PASS — timeout consumed the slot; retry was blocked")
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    main()
