"""Only synthetic ledger operations. Receipt and balance changes share a transaction."""
from .policy import Decision, PolicyError


def simulate_refund(db, workflow_id, decision):
    if not isinstance(decision, Decision) or decision.outcome not in ('READY','AWAITING_APPROVAL') or not 0 < decision.cents <= 50000:
        raise PolicyError('executor_authorisation_invalid')
    changed = db.execute('''UPDATE ledger SET refunded_cents=refunded_cents+?
WHERE id=? AND state='settled' AND currency='EUR' AND refunded_cents+?<=original_cents''',
                         (decision.cents,decision.transaction_id,decision.cents)).rowcount
    if changed != 1:
        raise PolicyError('executor_balance_check_failed')
    db.execute('INSERT INTO receipts VALUES(?,?,?)',(workflow_id,decision.transaction_id,decision.cents))
