"""One supervised Meta request. Requires --run and an unused one-slot ledger."""

import argparse
import getpass
import json
import os

from . import budget
from .meta import MetaProvider, MetaError
from .runner import guarded_call


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    if not args.run:
        print("No request made. Explicit --run is required.")
        return 0

    try:
        current = budget.status()
    except budget.LiveBudgetError:
        print("Stopped: initialise a separate one-request allowance first.")
        return 1

    if current != {"allowance": 1, "used": 0, "remaining": 1}:
        print("Stopped: expected exactly one unused request slot.")
        return 1

    key = getpass.getpass("Full Meta API key (hidden): ").strip()
    if (
        not key
        or any(c.isspace() for c in key)
        or "*" in key or "…" in key or "..." in key
        or key.lower().startswith("bearer ")
        or '"' in key or "'" in key
    ):
        print("Stopped: key appears empty, masked or incorrectly pasted.")
        return 1

    previous = os.environ.get("REQUESTGUARD_LIVE_ENABLED")
    records = []

    try:
        provider = MetaProvider(key)
        os.environ["REQUESTGUARD_LIVE_ENABLED"] = "YES"
        guarded_call(
            provider,
            {"text": "Reply with exactly READY."},
            records=records,
        )
        print("Live response completed.")
        return 0
    except MetaError as exc:
        print("Meta request stopped:", str(exc))
        return 1
    except Exception:
        print("Check failed. Do not retry or reset the allowance.")
        return 1
    finally:
        key = None
        if previous is None:
            os.environ.pop("REQUESTGUARD_LIVE_ENABLED", None)
        else:
            os.environ["REQUESTGUARD_LIVE_ENABLED"] = previous
        print("Request records:")
        print(json.dumps(records, indent=2))
        print("Allowance:", budget.status())


if __name__ == "__main__":
    raise SystemExit(main())
