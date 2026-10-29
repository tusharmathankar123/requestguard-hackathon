"""New event-built orchestration: persist, propose, authorise, approve, execute."""
import re
import threading
import uuid

from .evidence import EvidenceStore, now
from .executor import simulate_refund
from .policy import AgentContract, evaluate


class Conflict(ValueError):
    pass


class IntegrityError(Conflict):
    pass


class Orchestrator:
    def __init__(self, path, agent, contract=None):
        self.store = EvidenceStore(path)
        self.agent = agent
        self.contract = contract or AgentContract()
        self.lock = threading.RLock()
        self._detect_interruptions()

    def _assert_integrity(self, db, wid):
        if not self.store.valid(db, wid):
            raise IntegrityError('audit_integrity_failed')
        # Bind current execution inputs to the recorded, validated proposal.
        workflow = self.store.load(db, wid)
        proposals = [e['detail'] for e in self.store.events(db,wid) if e['kind']=='proposal_validated']
        if workflow.get('proposal') is not None and (not proposals or proposals[-1] != workflow['proposal']):
            raise IntegrityError('persisted_proposal_mismatch')
        creations = [e['detail'] for e in self.store.events(db,wid) if e['kind']=='workflow_created']
        if not creations or creations[0]['customer_text'] != workflow['text']:
            raise IntegrityError('persisted_request_mismatch')
        if workflow.get('approved'):
            approvals = [e for e in self.store.events(db,wid) if e['kind']=='human_approved']
            if not approvals:
                raise IntegrityError('approval_evidence_missing')

    def _detect_interruptions(self):
        with self.store.db() as db:
            ids = [row['id'] for row in db.execute('SELECT id FROM workflows')]
            for wid in ids:
                workflow = self.store.load(db,wid)
                if workflow['status'] in ('INTERPRETING','EXECUTING','READY'):
                    if not self.store.valid(db,wid):
                        continue
                    workflow['interrupted_stage'] = 'interpretation' if workflow['status']=='INTERPRETING' else 'execution'
                    workflow['status']='INTERRUPTED'
                    workflow['message']='Restart detected. No model call or action was automatically retried.'
                    self.store.save(db,workflow)
                    self.store.append(db,wid,'interruption_detected',{'stage':workflow['interrupted_stage']})

    def snapshot(self, wid):
        with self.store.db() as db:
            workflow = self.store.load(db,wid)
            workflow['events'] = self.store.events(db,wid)
            try:
                self._assert_integrity(db,wid)
                workflow['audit_valid'] = True
            except IntegrityError:
                workflow['audit_valid'] = False
            receipt=db.execute('SELECT * FROM receipts WHERE workflow_id=?',(wid,)).fetchone()
            workflow['receipt']=dict(receipt) if receipt else None
            return workflow

    def list(self):
        with self.store.db() as db:
            ids=[row['id'] for row in db.execute('SELECT id FROM workflows ORDER BY rowid DESC LIMIT 100')]
        return [self.snapshot(wid) for wid in ids]

    def create(self,text, pause_before_execution=False):
        if not isinstance(text,str) or not text.strip() or len(text)>2000:
            raise ValueError('customer_text_invalid')
        with self.lock:
            wid=str(uuid.uuid4())
            workflow={'id':wid,'text':text,'mode':self.agent.mode,'status':'INTERPRETING',
                      'created_at':now(),'pause_before_execution':bool(pause_before_execution),'proposal':None,'approved':False,'message':'Awaiting proposal.'}
            with self.store.db() as db:
                self.store.save(db,workflow)
                self.store.append(db,wid,'workflow_created',{'customer_text':text,'agent':self.contract.name,'mode':self.agent.mode})
            records=[]
            try:
                proposal=self.agent.propose(text,records)
            except Exception:
                with self.store.db() as db:
                    workflow=self.store.load(db,wid)
                    workflow.update(status='FAILED',message='Model unavailable or invalid. No action executed; no automatic retry.')
                    for record in records:
                        self.store.append(db,wid,'model_call',record)
                    self.store.append(db,wid,'proposal_failed',{'reason':'unavailable_or_invalid'})
                    self.store.save(db,workflow)
                return self.snapshot(wid)
            with self.store.db() as db:
                for record in records:
                    self.store.append(db,wid,'model_call',record)
                decision=evaluate(proposal,text,self.store.ledger(db),self.contract)
                workflow.update(status=decision.outcome,message=decision.reason)
                if decision.outcome in ('READY','AWAITING_APPROVAL'):
                    workflow['proposal']=proposal
                    self.store.append(db,wid,'proposal_validated',proposal)
                self.store.append(db,wid,'policy_evaluated',{'outcome':decision.outcome,'reason':decision.reason})
                self.store.save(db,workflow)
            if decision.outcome=='READY':
                self._dispatch_or_checkpoint(wid)
            return self.snapshot(wid)

    def approve(self,wid,reviewer):
        if not isinstance(reviewer,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{2,60}',reviewer):
            raise ValueError('reviewer_label_invalid')
        with self.lock:
            with self.store.db() as db:
                self._assert_integrity(db,wid)
                workflow=self.store.load(db,wid)
                if workflow['status']!='AWAITING_APPROVAL' or workflow['approved']:
                    raise Conflict('not_awaiting_approval')
                workflow.update(approved=True,status='READY')
                self.store.append(db,wid,'human_approved',{'reviewer_label':reviewer,'identity':'unauthenticated_local_demo'})
                self.store.save(db,workflow)
            self._dispatch_or_checkpoint(wid)
            return self.snapshot(wid)

    def _dispatch_or_checkpoint(self,wid):
        with self.store.db() as db:
            workflow=self.store.load(db,wid)
            if workflow.get('pause_before_execution'):
                workflow.update(status='INTERRUPTED',interrupted_stage='execution',message='Demo checkpoint: paused before execution for restart rehearsal. No debit has occurred.')
                self.store.append(db,wid,'demo_checkpoint',{'simulated_interruption':True})
                self.store.save(db,workflow)
                return
        self._execute(wid)

    def _execute(self,wid):
        with self.store.db() as db:
            self._assert_integrity(db,wid)
            workflow=self.store.load(db,wid)
            if workflow['status']!='READY':
                raise Conflict('not_ready')
            workflow['status']='EXECUTING'
            self.store.append(db,wid,'execution_started',{'tool':'simulate_refund'})
            self.store.save(db,workflow)
        # A crash here is recoverable without another model call.
        self._settle(wid)

    def _settle(self,wid):
        with self.store.db() as db:
            self._assert_integrity(db,wid)
            workflow=self.store.load(db,wid)
            receipt=db.execute('SELECT * FROM receipts WHERE workflow_id=?',(wid,)).fetchone()
            if receipt:
                workflow.update(status='SUCCEEDED',message='Existing simulated receipt reconciled; no second debit.')
                self.store.append(db,wid,'receipt_reconciled',{'simulated':True})
                self.store.save(db,workflow)
                return
            if workflow['status']!='EXECUTING':
                raise Conflict('not_executing')
            decision=evaluate(workflow['proposal'],workflow['text'],self.store.ledger(db),self.contract)
            if decision.outcome not in ('READY','AWAITING_APPROVAL') or (decision.outcome=='AWAITING_APPROVAL' and not workflow['approved']):
                workflow.update(status='DENIED',message=decision.reason)
                self.store.append(db,wid,'execution_denied',{'reason':decision.reason})
                self.store.save(db,workflow)
                return
            # Simulated debit, unique receipt and completion evidence commit together.
            simulate_refund(db,wid,decision)
            workflow.update(status='SUCCEEDED',message='Simulated refund committed. No real payment was made.')
            self.store.append(db,wid,'tool_executed',{'tool':'simulate_refund','amount_cents':decision.cents,'transaction_id':decision.transaction_id,'simulated':True})
            self.store.save(db,workflow)

    def recover(self,wid):
        with self.lock:
            with self.store.db() as db:
                self._assert_integrity(db,wid)
                workflow=self.store.load(db,wid)
                if workflow['status']!='INTERRUPTED':
                    raise Conflict('not_interrupted')
                if workflow.get('interrupted_stage')!='execution':
                    raise Conflict('interpretation_requires_new_request_no_automatic_retry')
                workflow['status']='READY'
                self.store.append(db,wid,'recovery_requested',{'model_recalled':False})
                self.store.save(db,workflow)
            self._execute(wid)
            return self.snapshot(wid)

    def ledger(self):
        with self.store.db() as db:
            return list(self.store.ledger(db).values())
