"""SQLite workflow evidence with per-workflow hash chains (not externally anchored)."""
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(event):
    return hashlib.sha256(canonical(event).encode()).hexdigest()


class EvidenceStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''
CREATE TABLE IF NOT EXISTS workflows(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, workflow_id TEXT NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ledger(id TEXT PRIMARY KEY, original_cents INTEGER NOT NULL, refunded_cents INTEGER NOT NULL DEFAULT 0, currency TEXT NOT NULL, state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS receipts(workflow_id TEXT PRIMARY KEY, transaction_id TEXT NOT NULL, amount_cents INTEGER NOT NULL);
''')
            for tx, amount, state in [('DEMO-125',12500,'settled'),('DEMO-300',30000,'settled'),('DEMO-750',75000,'settled'),('DEMO-VOID',12500,'void')]:
                db.execute('INSERT OR IGNORE INTO ledger VALUES(?,?,0,?,?)',(tx,amount,'EUR',state))

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def load(self, db, wid):
        row = db.execute('SELECT payload FROM workflows WHERE id=?',(wid,)).fetchone()
        if row is None:
            raise KeyError('workflow_not_found')
        return json.loads(row['payload'])

    def save(self, db, workflow):
        workflow['updated_at'] = now()
        db.execute('INSERT OR REPLACE INTO workflows VALUES(?,?)',(workflow['id'],canonical(workflow)))

    def append(self, db, wid, kind, detail):
        previous = db.execute('SELECT hash FROM events WHERE workflow_id=? ORDER BY seq DESC LIMIT 1',(wid,)).fetchone()
        event = {'workflow_id':wid, 'timestamp':now(), 'kind':kind, 'detail':detail,
                 'previous_hash': previous['hash'] if previous else '0'*64}
        db.execute('INSERT INTO events(workflow_id,payload,hash) VALUES(?,?,?)',(wid,canonical(event),digest(event)))

    def events(self, db, wid):
        return [{**json.loads(row['payload']), 'hash':row['hash']} for row in db.execute('SELECT payload,hash FROM events WHERE workflow_id=? ORDER BY seq',(wid,))]

    def valid(self, db, wid):
        previous = '0'*64
        events = self.events(db, wid)
        for raw in events:
            event = dict(raw)
            saved = event.pop('hash')
            if event['previous_hash'] != previous or digest(event) != saved:
                return False
            previous = saved
        return bool(events)

    def ledger(self, db):
        return {row['id']:dict(row) for row in db.execute('SELECT * FROM ledger')}
