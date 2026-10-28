"""Reserve before dispatch; never retry or refund a failed attempt."""

from .budget import reserve


def guarded_call(provider, request):
    reserve()
    return provider(request)
