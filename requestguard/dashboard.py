"""Build a self-contained offline dashboard. No server or network required."""
import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

from .evaluate import evaluate_case
from .compare import run_comparison


def build_report():
    cases = [evaluate_case(), evaluate_case(fail=True)]
    comparison = run_comparison()
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'mode': 'offline_mock',
        'network_requests': 0,
        'passed': all(case['passed'] for case in cases) and comparison['passed'],
        'comparison': comparison,
        'scenarios': cases,
    }


def render(report):
    template = Path(__file__).with_name('dashboard.html').read_text()
    payload = json.dumps(report).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    fonts = Path(__file__).with_name('fonts')
    for marker, filename in [('__INTER_FONT__', 'Inter.ttf'), ('__MONO_FONT__', 'IBMPlexMono-Regular.ttf')]:
        template = template.replace(marker, base64.b64encode((fonts / filename).read_bytes()).decode('ascii'))
    return template.replace('__REPORT_JSON__', payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('local-data/dashboard.html'))
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(report))
    print('Offline dashboard:', args.output.resolve())
    print('Evaluation:', 'PASS' if report['passed'] else 'FAIL')
    print('No network requests. Existing live allowance unchanged.')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
