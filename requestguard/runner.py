"""Guard provider dispatch and record safe operational metadata."""

from datetime import datetime, timezone
from time import monotonic
from uuid import uuid4

from .budget import reserve, LiveBudgetError


def guarded_call(provider, request, *, records=None):
    started = monotonic()
    request_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    def record(outcome, response=None):
        usage = {}
        if isinstance(response, dict):
            reported = response.get("usage")
            if isinstance(reported, dict):
                for name in ("input_tokens", "output_tokens", "total_tokens"):
                    value = reported.get(name)
                    if type(value) is int and value >= 0:
                        usage[name] = value

        if records is not None:
            records.append({
                "request_id": request_id,
                "timestamp": timestamp,
                "outcome": outcome,
                "duration_ms": round((monotonic() - started) * 1000, 3),
                "reported_usage": usage,
            })

    try:
        reserve()
    except LiveBudgetError:
        record("blocked")
        raise

    try:
        response = provider(request)
    except Exception:
        record("provider_failed")
        raise

    record("completed", response)
    return response
