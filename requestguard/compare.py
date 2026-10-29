"""Controlled offline comparison, not a cost estimate or recovery strategy."""
import json
import os
import tempfile

from . import budget
from .runner import guarded_call


def run_comparison():
    names = ('REQUESTGUARD_DATA_DIR', 'REQUESTGUARD_LIVE_ENABLED')
    previous = {name: os.environ.get(name) for name in names}
    sides = {}
    try:
        with tempfile.TemporaryDirectory() as folder:
            os.environ['REQUESTGUARD_DATA_DIR'] = folder
            os.environ['REQUESTGUARD_LIVE_ENABLED'] = 'YES'
            budget.initialize(1)
            for name in ('unguarded', 'guarded'):
                calls = 0
                outcomes = []
                records = []

                def timeout_provider(request):
                    nonlocal calls
                    calls += 1
                    raise TimeoutError('Synthetic timeout')

                # An identical, deliberately naive three-attempt policy on both sides.
                for _ in range(3):
                    try:
                        if name == 'guarded':
                            guarded_call(timeout_provider, {'text': 'synthetic'}, records=records)
                        else:
                            timeout_provider({'text': 'synthetic'})
                    except budget.LiveBudgetError:
                        outcomes.append('blocked')
                    except TimeoutError:
                        outcomes.append('provider_failed')
                    else:
                        outcomes.append('completed')
                sides[name] = {'attempts': 3, 'provider_calls': calls,
                               'outcomes': outcomes, 'records': records}
            remaining = budget.status()['remaining']
            passed = (
                sides['unguarded']['provider_calls'] == 3
                and sides['unguarded']['outcomes'] == ['provider_failed'] * 3
                and sides['guarded']['provider_calls'] == 1
                and sides['guarded']['outcomes'] == ['provider_failed', 'blocked', 'blocked']
                and [r['outcome'] for r in sides['guarded']['records']] == ['provider_failed', 'blocked', 'blocked']
                and remaining == 0
            )
            return {'mode': 'offline_mock', 'network_requests': 0, 'passed': passed,
                    **sides, 'remaining': remaining,
                    'note': 'Both requests fail. Dispatch reduction is observed only in this controlled simulation; monetary savings and recovery are not established.'}
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def main():
    report = run_comparison()
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
