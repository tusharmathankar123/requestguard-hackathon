"""Meta transport. Call through guarded_call to enforce the allowance."""

import json
import ssl
import urllib.error
import urllib.request


class MetaError(RuntimeError):
    """Contains only a locally defined diagnostic label."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class MetaProvider:
    def __init__(self, api_key):
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("API key required")
        if any(c.isspace() for c in api_key):
            raise ValueError("API key contains whitespace")
        self._api_key = api_key

    def __call__(self, request):
        if not isinstance(request, dict) or set(request) != {"text"}:
            raise ValueError("Expected only a text field")

        text = request["text"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Nonempty text required")

        payload = {
            "model": "muse-wonder-1.0",
            "input": text,
            "max_output_tokens": 1024,
            "tools": [],
            "store": False,
            "background": False,
        }
        encoded = json.dumps(payload).encode("utf-8")
        if len(encoded) > 12000:
            raise ValueError("Request exceeds 12000-byte bound")

        try:
            context = ssl.create_default_context()
            try:
                import certifi
            except ImportError:
                pass
            else:
                context.load_verify_locations(cafile=certifi.where())

            opener = urllib.request.build_opener(
                NoRedirect(),
                urllib.request.HTTPSHandler(context=context),
            )
            http_request = urllib.request.Request(
                "https://api.meta.ai/v1/responses",
                data=encoded,
                headers={
                    "Authorization": "Bearer " + self._api_key,
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            with opener.open(http_request, timeout=30) as response:
                body = response.read(128001)
                if response.status != 200 or len(body) > 128000:
                    raise MetaError("response_rejected")

            data = json.loads(body)
            if data.get("status") != "completed" or data.get("error"):
                raise MetaError("response_incomplete")

            texts = [
                part["text"]
                for item in data["output"]
                if item.get("type") == "message"
                and item.get("role") == "assistant"
                for part in item.get("content", [])
                if part.get("type") == "output_text"
            ]
            if not texts or not all(isinstance(t, str) for t in texts):
                raise MetaError("response_invalid")

            usage = {}
            reported = data.get("usage")
            if isinstance(reported, dict):
                for name in ("input_tokens", "output_tokens", "total_tokens"):
                    value = reported.get(name)
                    if type(value) is int and value >= 0:
                        usage[name] = value

            return {"text": "\n".join(texts), "usage": usage}

        except urllib.error.HTTPError as exc:
            label = {
                401: "authentication_rejected",
                403: "access_denied",
                429: "rate_limited",
            }.get(exc.code, "provider_http_error")
            raise MetaError(label) from None
        except MetaError:
            raise
        except Exception:
            raise MetaError("transport_or_response_failure") from None
