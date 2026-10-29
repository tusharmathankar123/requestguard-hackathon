"""Independent, default-deny authorisation; never accepts model approval flags."""
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class PolicyError(ValueError):
    pass


@dataclass(frozen=True)
class AgentContract:
    name: str = 'refund-agent'
    tools: frozenset = frozenset({'simulate_refund'})
    permissions: frozenset = frozenset({'refund:simulate'})


@dataclass(frozen=True)
class Decision:
    outcome: str
    reason: str
    cents: int = 0
    transaction_id: str = ''


def amount_cents(value):
    if type(value) not in (str, int):
        raise PolicyError('amount_type_invalid')
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0 or number > 100000:
            raise PolicyError('amount_invalid')
        pennies = number * 100
        if pennies != pennies.to_integral_value():
            raise PolicyError('subcent_amount')
        return int(pennies)
    except InvalidOperation:
        raise PolicyError('amount_invalid') from None


def evaluate(proposal, customer_text, ledger, contract):
    if not isinstance(proposal, dict) or set(proposal) != {'intent','transaction_id','amount_eur','tool'}:
        return Decision('DENIED', 'proposal_schema_invalid')
    if proposal['intent'] == 'clarify':
        if any(proposal[k] is not None for k in ('transaction_id','amount_eur','tool')):
            return Decision('DENIED', 'clarification_schema_invalid')
        return Decision('CLARIFICATION_REQUIRED', 'reference_and_explicit_EUR_refund_required')
    if proposal['intent'] != 'refund':
        return Decision('DENIED', 'intent_not_permitted')
    if proposal['tool'] != 'simulate_refund' or proposal['tool'] not in contract.tools or 'refund:simulate' not in contract.permissions:
        return Decision('DENIED', 'tool_or_permission_not_permitted')
    tx = proposal['transaction_id']
    if not isinstance(tx, str) or tx not in ledger:
        return Decision('DENIED', 'unknown_transaction')
    try:
        amount = amount_cents(proposal['amount_eur'])
    except PolicyError as exc:
        return Decision('DENIED', str(exc))
    # A deliberately narrow supported grammar ties facts to customer authority.
    # Unsupported language is clarification, never a guessed authorisation.
    match = re.fullmatch(r'\s*(?:Please\s+)?refund\s+€([0-9]+(?:\.[0-9]{1,2})?)\s+for\s+transaction\s+([A-Z0-9-]+)\.?\s*', customer_text, re.I)
    if not match:
        return Decision('CLARIFICATION_REQUIRED', 'unsupported_or_ambiguous_request')
    try:
        bound = amount_cents(match[1])
    except PolicyError:
        return Decision('DENIED', 'request_amount_invalid')
    if tx != match[2] or amount != bound:
        return Decision('DENIED', 'proposal_does_not_match_customer_authority')
    row = ledger[tx]
    if row['currency'] != 'EUR' or row['state'] != 'settled':
        return Decision('DENIED', 'transaction_not_eligible')
    if amount > 50000:
        return Decision('DENIED', 'hard_limit_500_EUR')
    if amount > row['original_cents'] - row['refunded_cents']:
        return Decision('DENIED', 'insufficient_refundable_balance')
    return Decision('AWAITING_APPROVAL' if amount > 25000 else 'READY',
                    'human_approval_above_250_EUR' if amount > 25000 else 'within_agent_authority', amount, tx)
