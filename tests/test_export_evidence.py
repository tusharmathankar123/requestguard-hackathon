import hashlib
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_tower.agent import ProposalAgent, SCENARIOS
from control_tower.export_evidence import export_report
from control_tower.orchestrator import Orchestrator


class RecordedFixtureAgent(ProposalAgent):
    # Fabricated evidence for unit tests only, never published as a live result.
    mode='meta'
    def __init__(self): pass
    def propose(self,text,records):
        records.append({'outcome':'completed','duration_ms':1.5,'reported_usage':{'input_tokens':1,'output_tokens':2,'total_tokens':3,'private':'DO_NOT_EXPORT'},'private':'DO_NOT_EXPORT'})
        return ProposalAgent().propose(text,[])


class ExportTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'source.sqlite'
        self.tower=Orchestrator(self.path,RecordedFixtureAgent())
        self.workflows=[self.tower.create(s['text']) for s in SCENARIOS]
        self.tower.approve(self.workflows[1]['id'],'PRIVATE_REVIEWER')

    def test_export_verifies_scenarios_without_network_or_writes(self):
        before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with patch.object(socket.socket,'connect',side_effect=AssertionError('No network')):
            report=export_report(self.path)
        self.assertTrue(report['complete'])
        self.assertEqual(len(report['workflows']),4)
        self.assertEqual([w['receipt_count'] for w in report['workflows']],[1,1,0,0])
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before)
        text=json.dumps(report)
        self.assertNotIn('DO_NOT_EXPORT',text)
        self.assertNotIn('PRIVATE_REVIEWER',text)
        self.assertNotIn('Please refund',text)
        self.assertNotIn(str(self.path),text)
        self.assertNotIn(self.workflows[0]['id'],text)

    def test_tampered_chain_cannot_pass(self):
        with self.tower.store.db() as db:
            db.execute('UPDATE events SET hash=? WHERE workflow_id=?',('bad',self.workflows[0]['id']))
        report=export_report(self.path)
        self.assertFalse(report['complete'])
        self.assertFalse(report['workflows'][0]['evidence_verified'])
        self.assertIsNone(report['workflows'][0]['chain_head'])

    def test_receipt_mismatch_cannot_pass(self):
        with self.tower.store.db() as db:
            db.execute('UPDATE receipts SET amount_cents=1 WHERE workflow_id=?',(self.workflows[0]['id'],))
        report=export_report(self.path)
        self.assertFalse(report['scenario_checks']['automatic_125'])

    def test_missing_source_is_not_created(self):
        path=self.path.parent/'missing.sqlite'
        with self.assertRaises(Exception): export_report(path)
        self.assertFalse(path.exists())


if __name__=='__main__': unittest.main()
