"""Persistent request allowance. This is not a provider billing or dollar cap."""
from contextlib import closing
import argparse
import json
import os
import sqlite3
from pathlib import Path

class LiveBudgetError(ValueError):
    pass

def budget_path():
    return Path(os.environ.get('REQUESTGUARD_DATA_DIR', str(Path(__file__).resolve().parents[1] / 'local-data'))) / 'live-budget.sqlite'

def initialize(limit=1):
    if type(limit) is not int or not 1 <= limit <= 20:
        raise LiveBudgetError('Request allowance must be between 1 and 20')
    path = budget_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidentally resetting an existing allowance.
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('CREATE TABLE budget (id INTEGER PRIMARY KEY CHECK(id=1), allowance INTEGER NOT NULL, used INTEGER NOT NULL)')
        db.execute('INSERT INTO budget VALUES (1, ?, 0)', (limit,))
    return status()

def connect():
    # mode=rw prevents a missing ledger from silently resetting usage.
    return sqlite3.connect(budget_path().resolve().as_uri() + '?mode=rw', uri=True, timeout=5)

def status():
    try:
        with closing(connect()) as db, db:
            row = db.execute('SELECT allowance, used FROM budget WHERE id=1').fetchone()
        if row is None or not 1 <= row[0] <= 20 or not 0 <= row[1] <= row[0]:
            raise LiveBudgetError('Invalid request allowance')
        return {'allowance': row[0], 'used': row[1], 'remaining': row[0]-row[1]}
    except (sqlite3.Error, OSError, TypeError) as exc:
        raise LiveBudgetError('Live allowance unavailable; no request permitted') from None

def reserve():
    if os.environ.get('REQUESTGUARD_LIVE_ENABLED') != 'YES':
        raise LiveBudgetError('Live requests disabled; explicit activation required')
    try:
        with closing(connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            changed = db.execute('UPDATE budget SET used=used+1 WHERE id=1 AND allowance BETWEEN 1 AND 20 AND used>=0 AND used<allowance').rowcount
            if changed != 1:
                raise LiveBudgetError('Live request allowance exhausted or invalid')
        # Commit before dispatch. Errors, timeouts and crashes do not refund slots.
    except (sqlite3.Error, OSError):
        raise LiveBudgetError('Live allowance unavailable; no request permitted') from None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'status'])
    parser.add_argument('--requests', type=int, default=1)
    args = parser.parse_args()
    try:
        print(json.dumps(initialize(args.requests) if args.command == 'init' else status()))
    except (LiveBudgetError, FileExistsError) as exc:
        parser.exit(1, 'Allowance unavailable or already initialized. Existing usage is never reset.\n')
