"""Offline demonstration. No network requests or credentials."""

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

            calls = 0
            records = []

            def mock_provider(request):
                nonlocal calls
                calls += 1
                return {"source": "OFFLINE MOCK", "result": "example response"}

            print("OFFLINE DEMO — no API calls")
            print("Starting allowance:", budget.status())

            result = guarded_call(mock_provider, {"text": "First request"}, records=records)
            print("Request 1: ALLOWED")
            print("Response:", result)

            try:
                guarded_call(mock_provider, {"text": "Second request"}, records=records)
            except budget.LiveBudgetError:
                print("Request 2: BLOCKED before provider dispatch")
            else:
                raise AssertionError("Exhausted request was not blocked")

            assert calls == 1, "Unexpected provider dispatch count"
            print("Request records:")
            print(json.dumps(records, indent=2))
            print("Mock provider calls:", calls)
            print("Final allowance:", budget.status())
            print("PASS — exhausted request never reached the provider")
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    main()
